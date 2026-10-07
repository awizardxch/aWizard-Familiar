"""Simulator probes for the Nightspire HTLC findings N1, N2, N4, N8.

Runs the committed htlc.hex on chia._tests.util.spend_sim (the real mempool manager and
coin store), with real BLS AGG_SIG_ME signatures. Honest control beside every attack.
"""
import asyncio, hashlib, sys
from chia._tests.util.spend_sim import sim_and_client
from chia.types.blockchain_format.program import Program
from chia.types.coin_spend import make_spend
from chia.types.mempool_inclusion_status import MempoolInclusionStatus as MIS
from chia_rs import AugSchemeMPL, G1Element, G2Element, SpendBundle, PrivateKey
from chia_rs.sized_bytes import bytes32

HEX = open(sys.argv[1]).read().strip()
MOD = Program.fromhex(HEX)
TIMELOCK = 300  # seconds

def ib(n):  # CLVM minimal big-endian, canonical zero is empty
    if n == 0: return b""
    l = (n.bit_length() + 8) // 8
    return n.to_bytes(l, "big", signed=True)

def sig_msg(fill_id, tag, dest_ph, amount):
    return hashlib.sha256(b"NS-HTLC-v1" + fill_id + tag + dest_ph + ib(amount)).digest()

SK_C = AugSchemeMPL.key_gen(b"\x11" * 32); PK_C = SK_C.get_g1()
SK_R = AugSchemeMPL.key_gen(b"\x22" * 32); PK_R = SK_R.get_g1()
CLAIM_PH = bytes32(b"\xaa" * 32); REFUND_PH = bytes32(b"\xbb" * 32); FILL_ID = bytes32(b"\xcc" * 32)

def htlc(preimage):
    hashlock = hashlib.sha256(preimage).digest()
    return MOD.curry(hashlock, TIMELOCK, bytes(PK_C), bytes(PK_R), CLAIM_PH, REFUND_PH, FILL_ID, None)

async def push(client, sim, label, spends, sigs, expect):
    agg = AugSchemeMPL.aggregate(sigs) if sigs else G2Element()
    status, err = await client.push_tx(SpendBundle(spends, agg))
    verdict = "ACCEPTED" if status == MIS.SUCCESS else f"REFUSED {err.name if err else err}"
    ok = (status == MIS.SUCCESS) == expect
    print(f"  [{'ok ' if ok else 'XX '}] {label}: {verdict}")
    if status == MIS.SUCCESS:
        await sim.farm_block()
    return status == MIS.SUCCESS

def claim_spend(coin, puzzle, preimage, amount, add):
    sol = Program.to([0, preimage, amount])
    sig = AugSchemeMPL.sign(SK_C, sig_msg(FILL_ID, b"claim", CLAIM_PH, amount) + coin.name() + add)
    return make_spend(coin, puzzle, sol), sig

def refund_spend(coin, puzzle, amount, add, payload=None):
    sol = Program.to([1, payload, amount])
    sig = AugSchemeMPL.sign(SK_R, sig_msg(FILL_ID, b"refund", REFUND_PH, amount) + coin.name() + add)
    return make_spend(coin, puzzle, sol), sig

async def fund(sim, client, puzzle):
    ph = puzzle.get_tree_hash()
    await sim.farm_block(ph)
    recs = await client.get_coin_records_by_puzzle_hash(ph, include_spent_coins=False)
    return sorted((r.coin for r in recs), key=lambda c: c.amount, reverse=True)

async def main():
    async with sim_and_client() as (sim, client):
        add = sim.defaults.AGG_SIG_ME_ADDITIONAL_DATA
        print(f"simulator up; AGG_SIG_ME_ADDITIONAL_DATA={add.hex()[:16]}…; htlc mod hash {MOD.get_tree_hash().hex()[:16]}…")

        print("\n== control: 32-byte preimage claim; wrong preimage refused")
        s32 = b"s" * 32; P = htlc(s32); coins = await fund(sim, client, P)
        sp, sg = claim_spend(coins[0], P, b"x" * 32, coins[0].amount, add)
        await push(client, sim, "wrong preimage (32 bytes)", [sp], [sg], expect=False)
        sp, sg = claim_spend(coins[0], P, s32, coins[0].amount, add)
        await push(client, sim, "correct 32-byte preimage", [sp], [sg], expect=True)
        paid = await client.get_coin_records_by_puzzle_hash(CLAIM_PH, include_spent_coins=False)
        print(f"       coins at CLAIM_PH after control: {[c.coin.amount for c in paid]}")

        print("\n== N1: preimage width is unbounded (EVM/Solana legs take exactly 32 bytes)")
        for n in (1, 33, 64, 1000):
            s = bytes([n % 251]) * n; P = htlc(s); coins = await fund(sim, client, P)
            sp, sg = claim_spend(coins[0], P, s, coins[0].amount, add)
            await push(client, sim, f"claim with {n}-byte preimage", [sp], [sg], expect=True)

        print("\n== N2: claim and refund overlap after TIMELOCK; refund refused before it")
        P = htlc(s32); coins = await fund(sim, client, P); a, b = coins[0], coins[1]
        sp, sg = refund_spend(a, P, a.amount, add)
        await push(client, sim, f"refund before timelock", [sp], [sg], expect=False)
        sim.pass_time(TIMELOCK + 60); await sim.farm_block()
        sp_c, sg_c = claim_spend(a, P, s32, a.amount, add)
        sp_r, sg_r = refund_spend(b, P, b.amount, add)
        # both branches valid in the same block, on two coins of the same puzzle
        st_c, _ = await client.push_tx(SpendBundle([sp_c], sg_c))
        st_r, _ = await client.push_tx(SpendBundle([sp_r], sg_r))
        print(f"  claim after timelock: {st_c.name}; refund after timelock: {st_r.name}  (both in mempool together)")
        await sim.farm_block()
        print(f"       coins at CLAIM_PH: {[c.coin.amount for c in await client.get_coin_records_by_puzzle_hash(CLAIM_PH, include_spent_coins=False)]}; at REFUND_PH: {[c.coin.amount for c in await client.get_coin_records_by_puzzle_hash(REFUND_PH, include_spent_coins=False)]}")

        print("\n== N4: refund PAYLOAD is unconstrained; a relayer can rewrite it under the same signature")
        P = htlc(s32); coins = await fund(sim, client, P); sim.pass_time(TIMELOCK + 60); await sim.farm_block()
        sp, sg = refund_spend(coins[0], P, coins[0].amount, add, payload=b"J" * 500)
        await push(client, sim, "refund with 500-byte junk PAYLOAD", [sp], [sg], expect=True)
        sp, sg = refund_spend(coins[1], P, coins[1].amount, add, payload=[b"a", [b"b", b"c"]])
        await push(client, sim, "refund with a list PAYLOAD", [sp], [sg], expect=True)

        print("\n== N8: AMOUNT below the coin's value is accepted; the remainder goes to the farmer")
        P = htlc(s32); coins = await fund(sim, client, P); c = coins[0]
        sp, sg = claim_spend(c, P, s32, c.amount - 12345, add)

        await push(client, sim, f"claim with AMOUNT = coin.amount - 12345", [sp], [sg], expect=True)
        paid = await client.get_coin_records_by_puzzle_hash(CLAIM_PH, include_spent_coins=False)
        print(f"       largest coin now at CLAIM_PH: {max(x.coin.amount for x in paid)} (coin was {c.amount}); 12345 mojos became fee")
        sp, sg = claim_spend(coins[1], P, s32, coins[1].amount + 1, add)
        await push(client, sim, "claim with AMOUNT = coin.amount + 1", [sp], [sg], expect=False)

asyncio.run(main())
