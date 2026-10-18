"""CLVM tree hashing, the subset the engine needs.

The distributor puzzle verifies claim leaves with `sha256tree`, so the engine must
hash exactly what CLVM would. Values are bytes (atoms), ints (atoms in CLVM's
minimal two's-complement encoding), str (UTF-8 atoms), tuples of two (pairs) and
lists (nil-terminated). No dependency on `clvm` here; `tests/test_clvm.py`
cross-checks against it when it is installed.
"""

from __future__ import annotations

from hashlib import sha256
from typing import Union

Value = Union[bytes, int, str, tuple, list]


def int_to_atom(n: int) -> bytes:
    """CLVM's minimal signed big-endian encoding; 0 is the empty atom."""
    if n == 0:
        return b""
    length = (n.bit_length() + 8) // 8
    atom = n.to_bytes(length, "big", signed=True)
    # Strip redundant sign bytes the fixed length may have added.
    while len(atom) > 1 and (
        (atom[0] == 0x00 and atom[1] < 0x80) or (atom[0] == 0xFF and atom[1] >= 0x80)
    ):
        atom = atom[1:]
    return atom


def atom_of(value: Union[bytes, int, str]) -> bytes:
    if isinstance(value, bool):
        raise TypeError("bool is not a CLVM value; use 0 or 1")
    if isinstance(value, bytes):
        return value
    if isinstance(value, int):
        return int_to_atom(value)
    if isinstance(value, str):
        return value.encode("utf-8")
    raise TypeError(f"not an atom: {type(value).__name__}")


def sha256tree(value: Value) -> bytes:
    if isinstance(value, list):
        acc = sha256(b"\x01").digest()  # nil
        for item in reversed(value):
            acc = sha256(b"\x02" + sha256tree(item) + acc).digest()
        return acc
    if isinstance(value, tuple):
        if len(value) != 2:
            raise ValueError("a pair is a tuple of exactly two")
        return sha256(b"\x02" + sha256tree(value[0]) + sha256tree(value[1])).digest()
    return sha256(b"\x01" + atom_of(value)).digest()
