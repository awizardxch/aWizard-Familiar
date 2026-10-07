import sys, hashlib
sys.path.insert(0, sys.argv[1])
from spellbook import chia_sign as cs
# standard curry: (a (q . MOD) (c (q . PK) 1))
def std_curry(mod_sexpr, args):
    # args: list of atoms/sexprs
    fixed = b"\x01"  # 1
    for a in reversed(args):
        fixed = (b"\x04", ((b"\x01", a), (fixed, b"")))
    return (b"\x02", ((b"\x01", mod_sexpr), (fixed, b"")))
mod = cs.deser(cs.P2_DELEGATED_PUZZLE_OR_HIDDEN_PUZZLE)
# fake synthetic pk: use a real G1 from blspy
from blspy import AugSchemeMPL, PrivateKey
sk = PrivateKey.from_bytes(bytes.fromhex("0"*63+"7"))
pk = bytes(AugSchemeMPL.sk_to_g1(sk))
spell_ph = cs.puzzle_hash_for_synthetic_pk(pk)
std = std_curry(mod, [pk])
std_ph = cs.sha256tree(std)
print("spellbook puzzle_hash_for_synthetic_pk:", spell_ph.hex())
print("standard curry sha256tree:            ", std_ph.hex())
print("standard curry bytes prefix:", cs.ser(std)[:12].hex())
print("spellbook reveal prefix:   ", cs.standard_puzzle_reveal(pk)[:12].hex())
print("EQUAL" if spell_ph == std_ph else "DIFFERENT")
# cross-check with chia_rs curry_tree_hash if available
try:
    from chia_rs import tree_hash
    print("chia_rs tree_hash(std):", tree_hash(cs.ser(std)).hex())
    print("chia_rs tree_hash(spellbook reveal):", tree_hash(cs.standard_puzzle_reveal(pk)).hex())
except Exception as e:
    print("chia_rs unavailable:", e)
try:
    from chia_rs import run_chia_program
    # run both puzzles with same solution and compare output conditions
    conds = cs._list([cs.create_coin_condition(bytes(32), 1)])
    sol = cs.ser(cs.standard_solution_sexpr(conds))
    c1, o1 = run_chia_program(cs.ser(std), sol, 11_000_000_000, 0)
    c2, o2 = run_chia_program(cs.standard_puzzle_reveal(pk), sol, 11_000_000_000, 0)
    print("std run cost", c1, "spellbook run cost", c2)
except Exception as e:
    print("run failed:", e)
