"""The payout tree.

Same construction as chia's `merkle_utils` (leaf prefix 0x01, node prefix 0x02,
midpoint split, proof = (path bitmask, sibling hashes bottom-up)), which is also
what `merkle_utils.clib`'s `simplify_merkle_proof` checks on chain. The leaves
are tree hashes of claim entries (see `entry_hash`).
"""

from __future__ import annotations

from hashlib import sha256
from typing import Dict, List, Sequence, Tuple

from .clvm import sha256tree

LEAF_PREFIX = b"\x01"
NODE_PREFIX = b"\x02"
ENTRY_TAG = "flpcr-entry-v1"

Proof = Tuple[int, List[bytes]]


def entry_hash(distributor_id: bytes, epoch_id: int, index: int, puzzle_hash: bytes, amount: int) -> bytes:
    """The value the puzzle tree-hashes before checking the proof.

    `distributor_id` and `epoch_id` keep a leaf from verifying against any other
    distributor's or epoch's root; `index` is the entry's bit in the epoch's
    paid bitmap.
    """
    return sha256tree([ENTRY_TAG, distributor_id, epoch_id, index, puzzle_hash, amount])


def _split(items: Sequence[bytes]):
    if len(items) == 1:
        return items[0]
    mid = (len(items) + 1) >> 1
    return (_split(items[:mid]), _split(items[mid:]))


def _build(node) -> Tuple[bytes, Dict[bytes, Proof]]:
    if isinstance(node, bytes):
        return sha256(LEAF_PREFIX + node).digest(), {node: (0, [])}
    left_root, left = _build(node[0])
    right_root, right = _build(node[1])
    proofs: Dict[bytes, Proof] = {}
    for leaf, (path, hashes) in left.items():
        proofs[leaf] = (path, hashes + [right_root])
    for leaf, (path, hashes) in right.items():
        proofs[leaf] = (path | (1 << len(hashes)), hashes + [left_root])
    return sha256(NODE_PREFIX + left_root + right_root).digest(), proofs


def build_tree(leaves: Sequence[bytes]) -> Tuple[bytes, Dict[bytes, Proof]]:
    """Root and per-leaf proofs, leaves in the order given. Leaves must be distinct."""
    if not leaves:
        raise ValueError("an epoch with no entries is not posted")
    if len(set(leaves)) != len(leaves):
        raise ValueError("duplicate leaf")
    return _build(_split(list(leaves)))


def root_from_proof(leaf: bytes, proof: Proof) -> bytes:
    path, hashes = proof
    acc = sha256(LEAF_PREFIX + leaf).digest()
    for sibling in hashes:
        if path & 1:
            acc = sha256(NODE_PREFIX + sibling + acc).digest()
        else:
            acc = sha256(NODE_PREFIX + acc + sibling).digest()
        path >>= 1
    return acc
