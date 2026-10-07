#!/usr/bin/env python3
"""F3 probe, exact-settlement shape (Forge#86): can a farmer rewrite the payout coin's router-fee/trader-refund group
to pay itself, while the trader's requested payment stays intact and the bundle
stays valid, on the REAL Chia simulator?

Run with cwd = contracts (drivers do sys.path.insert(0, ".")):

    cd /home/user/awizardxch/forge-puzzles/contracts
    /tmp/claude-0/-home-user-aWizard-Familiar/f2fdccd5-2d6f-5000-b0d2-2456b85199f8/scratchpad/venv-fp/bin/python \
        /tmp/claude-0/-home-user-aWizard-Familiar/f2fdccd5-2d6f-5000-b0d2-2456b85199f8/scratchpad/sim-f3/sim_f3_payout_redirect.py

Shape: production-lane pool (sim-v14's create_pool), honest CAT->XCH swap through the
offer route lane (forge_v14_offer.settle_swap) with a non-zero router fee_bps so the
output leg carries BOTH a router-fee group and a trader-refund group. CONTROL pushes
the honest bundle. ATTACK rewrites only the payout coin's OFFER_MOD solution.
"""
from __future__ import annotations

import asyncio
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, ".")

from chia.types.blockchain_format.program import Program
from chia.types.coin_spend import make_spend
from chia.wallet.cat_wallet.cat_utils import (
    CAT_MOD, SpendableCAT, construct_cat_puzzle, unsigned_spend_bundle_for_spendable_cats,
)
from chia.wallet.conditions import CreateCoin
from chia.wallet.lineage_proof import LineageProof
from chia.wallet.puzzle_drivers import PuzzleInfo
from chia.wallet.puzzles.singleton_top_layer_v1_1 import SINGLETON_LAUNCHER, SINGLETON_LAUNCHER_HASH
from chia.wallet.trading.offer import OFFER_MOD, OFFER_MOD_HASH, Offer
from chia.types.mempool_inclusion_status import MempoolInclusionStatus
from chia_rs import Coin, G2Element, SpendBundle
from chia_rs.sized_bytes import bytes32
from chia_rs.sized_ints import uint64

import forge_math
import forge_v14_driver as drv
import forge_v14_offer as v14off
from _sim_harness import (CREATE_COIN, IDENTITY, IDENTITY_HASH, SimRejected, Wallet,
                          farm_to_identity, issue_cat, push, sim_and_client, split_xch)

# Reuse the production create_pool / mint_registry lane verbatim from the deploy script.
sys.path.insert(0, str(Path("../scripts").resolve()))
import importlib.util
_spec = importlib.util.spec_from_file_location("simv14", str(Path("../scripts/sim-v14.py").resolve()))
simv14 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(simv14)

TRADER_PH = bytes32(b"\x77" * 32)   # where the trader asks XCH be paid (and the refund `back`)
ROUTER_PH = bytes32(b"\x66" * 32)   # surplus_ph: the honest router-fee recipient
ATTACKER_PH = bytes32(b"\xee" * 32)  # the farmer paying itself
OFFER_PH = bytes32(OFFER_MOD_HASH)


def log(msg: str = "") -> None:
    print(msg, flush=True)



def build_trader_offer(cat_coin: Coin, cat_lineage: LineageProof, asset: bytes32,
                       gross: int, payments: list[tuple[bytes32, int]], salt: int) -> Offer:
    """A wallet-shaped offer under exact settlement: the trader's REAL CAT coin creates the
    CAT(OFFER_MOD) settlement of `gross` and asserts the announcement of its ONE requested
    XCH group, which carries every payment -- the trader's own and the router's fee -- so
    the group as a whole is inside the maker's spend. Keyless (IDENTITY)."""
    notarized = Offer.notarize_payments(
        {None: [CreateCoin(ph, uint64(amt), [ph]) for ph, amt in payments]}, [cat_coin])
    announcements = []
    for a, group in notarized.items():
        settle = OFFER_MOD_HASH if a is None else construct_cat_puzzle(CAT_MOD, a, OFFER_MOD).get_tree_hash()
        by_nonce: dict = {}
        for p in group:
            by_nonce.setdefault(p.nonce, []).append(p)
        for nonce, ps in by_nonce.items():
            msg = Program.to((nonce, [p.as_condition_args() for p in ps])).get_tree_hash()
            announcements.append([63, bytes32(hashlib.sha256(bytes(settle) + bytes(msg)).digest())])
    conditions = [[CREATE_COIN, OFFER_MOD_HASH, int(gross)], *announcements]
    ring = unsigned_spend_bundle_for_spendable_cats(CAT_MOD, [SpendableCAT(
        cat_coin, asset, IDENTITY, Program.to(conditions), lineage_proof=cat_lineage)]).coin_spends
    driver = {asset: PuzzleInfo({"type": "CAT", "tail": "0x" + asset.hex()})}
    return Offer(notarized, SpendBundle(ring, G2Element()), driver)


async def coin_total(client, ph: bytes32) -> tuple[int, int]:
    recs = await client.get_coin_records_by_puzzle_hash(ph, include_spent_coins=False)
    return len(recs), sum(int(r.coin.amount) for r in recs)


def mutate_payout(bundle: SpendBundle, payout_coin: Coin, redirect: dict, add_group: list | None = None) -> SpendBundle:
    """Rebuild `bundle` with ONLY the payout coin's OFFER_MOD solution changed: every payment
    whose puzzle hash is a key of `redirect` is re-pointed at its value (amount unchanged);
    `add_group`, if given, is appended as a new (nonce . payments) group. Every other spend
    is byte-identical, so the aggregate signature still verifies."""
    out, changed = [], 0
    for cs in bundle.coin_spends:
        if cs.coin.name() != payout_coin.name():
            out.append(cs); continue
        groups = []
        for g in Program.from_bytes(bytes(cs.solution)).as_iter():
            nonce = g.first()
            rebuilt = []
            for pay in g.rest().as_iter():
                items = list(pay.as_iter())
                ph = bytes32(items[0].as_atom()); amount = items[1].as_int()
                if ph in redirect:
                    ph = redirect[ph]; changed += 1
                rebuilt.append([ph, amount, [ph]])
            groups.append(Program.to((nonce.as_atom(), rebuilt)))
        if add_group is not None:
            groups.append(Program.to((payout_coin.name(), add_group))); changed += 1
        out.append(make_spend(cs.coin, Program.from_bytes(bytes(cs.puzzle_reveal)), Program.to(groups)))
    assert changed >= 1, "nothing was mutated"
    return SpendBundle(out, bundle.aggregated_signature)


async def build_pool_and_offer(sim, client):
    coins = await farm_to_identity(sim, client, blocks=6)
    wallet = Wallet(xch=list(coins), cats={})
    funding = wallet.take_xch(1_000_000_000)
    pieces, bundle = split_xch(funding, [500_000_000])
    await push(client, sim, bundle, "split for token issuance")
    asset, minted, lineage, mint_bundle = issue_cat(pieces[0], 60_000_000, salt=0xA7)
    await push(client, sim, mint_bundle, "issue token")
    wallet.cats.setdefault(asset, []).append((minted, lineage))
    reg = await simv14.mint_registry(sim, client, wallet)
    assets = [None, asset]
    order = sorted(range(2), key=lambda i: bytes(32) if assets[i] is None else bytes(assets[i]))
    assets = [assets[i] for i in order]
    reserves = [[50_000_000, 20_000_000][i] for i in order]
    pool = await simv14.create_pool(sim, client, wallet, reg, assets, reserves, [1, 1],
                                    fee_bps=30, protocol_fee_bps=5, label="XCH/CAT F3")
    i_xch = pool.asset_ids.index(None); i_cat = 1 - i_xch

    fee_bps = 300
    gross_cat = 400_000
    r, w = pool.state[0], pool.weights
    honest = forge_math.swap_output(r[i_cat], r[i_xch], gross_cat, pool.fee_bps, w[i_cat], w[i_xch])
    pfee = honest * pool.protocol_fee_bps // 10_000 + honest * pool.dao_fee_bps // 10_000
    payout = honest - pfee
    router_fee = payout * fee_bps // 10_000
    trader_gets = payout - router_fee
    log(f"  swap math: gross_cat {gross_cat}, payout {payout} = trader {trader_gets} + router fee {router_fee} (exact, no refund)")

    cat_coin, cat_lineage = wallet.take_cat(asset, gross_cat)
    if int(cat_coin.amount) > gross_cat:
        rest = int(cat_coin.amount) - gross_cat
        ring = unsigned_spend_bundle_for_spendable_cats(CAT_MOD, [SpendableCAT(
            cat_coin, asset, IDENTITY, Program.to([
                [CREATE_COIN, IDENTITY_HASH, gross_cat, [IDENTITY_HASH]],
                [CREATE_COIN, IDENTITY_HASH, rest, [IDENTITY_HASH]],
            ]), lineage_proof=cat_lineage)]).coin_spends
        await push(client, sim, SpendBundle(ring, G2Element()), "split trader CAT")
        inner_ph = construct_cat_puzzle(CAT_MOD, asset, IDENTITY).get_tree_hash()
        trader_coin = Coin(cat_coin.name(), bytes32(inner_ph), uint64(gross_cat))
        trader_lineage = LineageProof(cat_coin.parent_coin_info, IDENTITY_HASH, cat_coin.amount)
    else:
        trader_coin, trader_lineage = cat_coin, cat_lineage

    offer = build_trader_offer(trader_coin, trader_lineage, asset, gross_cat,
                               [(TRADER_PH, trader_gets), (ROUTER_PH, router_fee)], salt=0x31)
    result = v14off.settle_swap(pool, offer, sim.block_height, surplus_ph=ROUTER_PH, fee_bps=fee_bps)
    d = result.details
    log(f"  settle_swap ok: router_fee {d['router_fee']} (side {d['router_fee_side']}), refund {d['refund']}, requested {d['requested']}")
    reserve = pool.reserves[i_xch]
    payout_coin = Coin(reserve.coin.name(), OFFER_PH, uint64(payout))
    return {"pool": pool, "asset": asset, "offer": offer, "result": result, "payout_coin": payout_coin,
            "trader_gets": trader_gets, "router_fee": router_fee, "payout": payout}


async def payees(client, tag=""):
    (tc, ts), (rc, rs), (ac, as_) = await coin_total(client, TRADER_PH), await coin_total(client, ROUTER_PH), await coin_total(client, ATTACKER_PH)
    log(f"  {tag}TRADER sum={ts:,} | ROUTER sum={rs:,} | ATTACKER sum={as_:,}")
    return ts, rs, as_


async def phase(title, mutate, expect_accept: bool):
    log("=" * 78); log(title); log("=" * 78)
    async with sim_and_client() as (sim, client):
        ctx = await build_pool_and_offer(sim, client)
        bundle = ctx["result"].bundle
        if mutate is not None:
            bundle = mutate(bundle, ctx)
            orig = {cs.coin.name(): bytes(cs.solution) for cs in ctx["result"].bundle.coin_spends}
            identical = all(bytes(cs.solution) == orig[cs.coin.name()] for cs in bundle.coin_spends if cs.coin.name() != ctx["payout_coin"].name())
            log(f"  every non-payout spend byte-identical: {identical}; signature unchanged: {bytes(bundle.aggregated_signature) == bytes(ctx['result'].bundle.aggregated_signature)}")
        status, error = await client.push_tx(bundle)
        log(f"  push -> status={status.name} error={error.name if error else None}")
        if status == MempoolInclusionStatus.SUCCESS:
            await sim.farm_block()
            ts, rs, as_ = await payees(client, "after: ")
            ok = expect_accept and ts == ctx["trader_gets"] and rs == ctx["router_fee"] and as_ == 0
        else:
            ok = not expect_accept
        log(f"  {'ok ' if ok else 'XX '} {'accepted' if status == MempoolInclusionStatus.SUCCESS else 'refused'} ({'expected' if ok else 'UNEXPECTED'})")
        return ok, (error.name if error else None)


async def main() -> int:
    results = {}
    results["control"] = await phase("CONTROL: honest exact-settlement swap (trader + router fee in the trader's one group)", None, True)
    results["A fee->attacker"] = await phase("ATTACK A: redirect the router's fee payment to ATTACKER_PH",
        lambda b, c: mutate_payout(b, c["payout_coin"], {ROUTER_PH: ATTACKER_PH}), False)
    results["B trader->attacker"] = await phase("ATTACK B: redirect the trader's payment to ATTACKER_PH",
        lambda b, c: mutate_payout(b, c["payout_coin"], {TRADER_PH: ATTACKER_PH}), False)
    results["C extra group"] = await phase("ATTACK C: add an unsigned group paying ATTACKER_PH 1 mojo",
        lambda b, c: mutate_payout(b, c["payout_coin"], {}, add_group=[[ATTACKER_PH, 1, [ATTACKER_PH]]]), False)
    log(""); log("SUMMARY")
    for k, (ok, err) in results.items():
        log(f"  {k:22} {'ok ' if ok else 'XX '} {err or 'accepted'}")
    return 0 if all(ok for ok, _ in results.values()) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
