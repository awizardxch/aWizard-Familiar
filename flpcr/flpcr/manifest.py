"""The published form of an epoch and of the engine's state.

An epoch manifest is what the operator pins (IPFS or object storage) and names
by hash in the `post_epoch` spend, like Merkl's `ipfsHash`. It holds every entry
with its proof, so a claim can be built from the manifest alone. Fractions are
written as [numerator, denominator] so a replay in another language is exact.
"""

from __future__ import annotations

import json
from fractions import Fraction
from hashlib import sha256

from .engine import EngineState, Epoch


def epoch_to_json(epoch: Epoch) -> dict:
    return {
        "distributor_id": epoch.distributor_id.hex(),
        "epoch_id": epoch.epoch_id,
        "start": epoch.start,
        "end": epoch.end,
        "root": epoch.root.hex() if epoch.root else None,
        "total": epoch.total,
        "entry_count": len(epoch.entries),
        "allocations": {cid.hex(): amt for cid, amt in sorted(epoch.allocations.items())},
        "entries": [
            {
                "index": e.index,
                "puzzle_hash": e.puzzle_hash.hex(),
                "amount": e.amount,
                "proof": {"path": e.proof[0], "hashes": [h.hex() for h in e.proof[1]]},
            }
            for e in epoch.entries
        ],
    }


def manifest_hash(epoch: Epoch) -> bytes:
    """sha256 of the canonical JSON; the value `post_epoch` carries as a memo."""
    canonical = json.dumps(epoch_to_json(epoch), sort_keys=True, separators=(",", ":"))
    return sha256(canonical.encode()).digest()


def state_to_json(state: EngineState) -> dict:
    return {
        "distributor_id": state.distributor_id.hex(),
        "epoch_id": state.epoch_id,
        "height": state.height,
        "accrued": {
            cid.hex(): {ph.hex(): [x.numerator, x.denominator] for ph, x in sorted(v.items())}
            for cid, v in sorted(state.accrued.items())
        },
        "allocated": {
            cid.hex(): {ph.hex(): a for ph, a in sorted(v.items())}
            for cid, v in sorted(state.allocated.items())
        },
    }


def state_from_json(data: dict) -> EngineState:
    h = bytes.fromhex
    return EngineState(
        distributor_id=h(data["distributor_id"]),
        epoch_id=data["epoch_id"],
        height=data["height"],
        accrued={
            h(cid): {h(ph): Fraction(n, d) for ph, (n, d) in v.items()}
            for cid, v in data["accrued"].items()
        },
        allocated={h(cid): {h(ph): a for ph, a in v.items()} for cid, v in data["allocated"].items()},
    )
