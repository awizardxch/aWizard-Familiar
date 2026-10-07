"""Simulator probe for Spellbook finding S1: the daemon's curried standard puzzle is not the
standard curry, so its addresses are not the addresses any stock wallet derives from the key.

Honest control: the daemon's own signer spends a coin at its own address (funds are not lost
to the daemon). Attack-shaped checks: the standard wallet puzzle for the SAME key sits at a
different puzzle hash; the daemon cannot spend coins sent to that standard address; a standard
wallet's reveal cannot spend the daemon's coin.
"""
import asyncio, sys
sys.path.insert(0, sys.argv[1])
from spellbook import chia_sign as cs
from chia._tests.util.spend_sim import sim_and_client
from chia.types.blockchain_format.program import Program
from chia.types.coin_spend import make_spend
from chia.types.mempool_inclusion_status import MempoolInclusionStatus as MIS
from chia.wallet.puzzles.p2_delegated_puzzle_or_hidden_puzzle import (
    puzzle_for_synthetic_public_key, solution_for_conditions, calculate_synthetic_secret_key,
    DEFAULT_HIDDEN_PUZZLE_HASH)
from chia_rs import AugSchemeMPL, G1Element, G2Element, PrivateKey, SpendBundle
from chia_rs.sized_bytes import bytes32

OUT_PH = bytes32(b"\x42" * 32)

async def main():
    async with sim_and_client() as (sim, client):
        add = sim.defaults.AGG_SIG_ME_ADDITIONAL_DATA
        net = next(k for k, v in cs.GENESIS_CHALLENGE.items() if v == add)
        print(f"simulator genesis challenge matches spellbook network {net!r}")

        master = bytes(AugSchemeMPL.key_gen(b"\x07" * 32))
        wsk = cs.wallet_sk(master, 0); wpk = cs.pk_bytes(wsk); spk = cs.synthetic_pk(wpk)
        spell_ph = cs.puzzle_hash_for_synthetic_pk(spk)
        std_puzzle = puzzle_for_synthetic_public_key(G1Element.from_bytes(spk))
        std_ph = std_puzzle.get_tree_hash()
        # the key half agrees with chia-blockchain; the puzzle half does not
        chia_spk = bytes(calculate_synthetic_secret_key(PrivateKey.from_bytes(wsk), DEFAULT_HIDDEN_PUZZLE_HASH).get_g1())
        print(f"synthetic pk equal to chia-blockchain's: {chia_spk == spk}")
        print(f"spellbook puzzle hash : {spell_ph.hex()}")
        print(f"standard  puzzle hash : {std_ph.hex()}")
        print(f"same address: {spell_ph == std_ph}")

        # fund both addresses for the same key
        await sim.farm_block(bytes32(spell_ph)); await sim.farm_block(std_ph)
        spell_coin = max((r.coin for r in await client.get_coin_records_by_puzzle_hash(bytes32(spell_ph), include_spent_coins=False)), key=lambda c: c.amount)
        std_coin = max((r.coin for r in await client.get_coin_records_by_puzzle_hash(std_ph, include_spent_coins=False)), key=lambda c: c.amount)

        # control: the daemon spends its own coin with its own reveal and signature
        spend = cs.build_standard_spend(master, 0, (spell_coin.parent_coin_info, spell_coin.puzzle_hash, spell_coin.amount),
                                        [(OUT_PH, spell_coin.amount)], net)
        bundle = SpendBundle.from_bytes(cs.build_spend_bundle([spend]))
        st, err = await client.push_tx(bundle)
        print(f"[control] daemon reveal spends daemon coin: {st.name} {err.name if err else ''}")
        if st == MIS.SUCCESS: await sim.farm_block()

        # the daemon cannot spend a coin at the standard address for the same key
        try:
            cs.build_standard_spend(master, 0, (std_coin.parent_coin_info, std_coin.puzzle_hash, std_coin.amount), [(OUT_PH, std_coin.amount)], net)
            print("[S1] daemon spends standard-address coin: BUILT (unexpected)")
        except cs.ChiaSignError as e:
            print(f"[S1] daemon spending a coin at the standard address for its own key: refused by its own builder — {e}")

        # a standard wallet (chia-blockchain's puzzle, same synthetic key) cannot spend the daemon's coin
        spell_coin2 = max((r.coin for r in await client.get_coin_records_by_puzzle_hash(bytes32(spell_ph), include_spent_coins=False)), key=lambda c: c.amount)
        conds = [[51, OUT_PH, spell_coin2.amount]]
        sol = solution_for_conditions(Program.to(conds))
        ssk = calculate_synthetic_secret_key(PrivateKey.from_bytes(wsk), DEFAULT_HIDDEN_PUZZLE_HASH)
        msg = Program.to((1, conds)).get_tree_hash() + spell_coin2.name() + add
        sig = AugSchemeMPL.sign(ssk, msg)
        st, err = await client.push_tx(SpendBundle([make_spend(spell_coin2, std_puzzle, sol)], sig))
        print(f"[S1] standard wallet reveal spending the daemon's coin: {st.name} {err.name if err else ''}")

        # and the standard wallet DOES spend the coin at the standard address (so the key is fine; only the address is wrong)
        sol = solution_for_conditions(Program.to([[51, OUT_PH, std_coin.amount]]))
        msg = Program.to((1, [[51, OUT_PH, std_coin.amount]])).get_tree_hash() + std_coin.name() + add
        st, err = await client.push_tx(SpendBundle([make_spend(std_coin, std_puzzle, sol)], AugSchemeMPL.sign(ssk, msg)))
        print(f"[control] standard wallet reveal spends standard-address coin: {st.name} {err.name if err else ''}")

asyncio.run(main())
