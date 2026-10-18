"""What the engine reads from chain, behind one interface.

The live adapter (not in this slice) reads a full node or coinset.org:
  * holder events: CAT coin creations and spends for one asset id, attributed to
    the inner puzzle hash by the CHIP-0020 hint. Forge LP coins are hinted; an
    unhinted coin is attributed when its spend reveals the inner puzzle.
  * fee events: each Forge pool generation replayed with `forge_v14_resync`
    (the same replay the browser uses), one event per `swap` action, weighted
    by the fee it paid valued in XCH at the pool's own pre-spend spot price.
  * exclusions and forwarders: derived from the Forge registry, not configured
    by hand.

`FixtureSource` is the in-memory implementation the tests and the CLI use.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Dict, List, Protocol, Set, Tuple


@dataclass(frozen=True)
class HolderEvent:
    height: int  # the balance change is in force from this height
    puzzle_hash: bytes
    delta: int  # mojos of the tracked asset; negative on spend


class Source(Protocol):
    def lp_asset(self, pool_launcher: bytes) -> bytes:
        """The LP CAT asset id of a Forge pool."""

    def holder_events(self, asset_id: bytes, before: int) -> List[HolderEvent]:
        """Every balance change of `asset_id` at heights < `before`, in height order."""

    def fee_events(self, pool_launcher: bytes, start: int, end: int) -> List[Tuple[int, int]]:
        """(height, weight) for each fee-paying action of the pool in [start, end)."""

    def excluded(self, asset_id: bytes) -> Set[bytes]:
        """Puzzle hashes that hold `asset_id` but are never anyone's position:
        pool reserves, OFFER_MOD settlement coins, the zero-hash burn (the
        LOCKED_BURN floor), the protocol treasury."""

    def forwarders(self, asset_id: bytes) -> Dict[bytes, bytes]:
        """Holders of `asset_id` that are wrappers, mapped to the asset that
        represents a share of the wrapper (a vault pool's LP CAT)."""


@dataclass
class FixtureSource:
    lp_assets: Dict[bytes, bytes] = field(default_factory=dict)
    events: Dict[bytes, List[HolderEvent]] = field(default_factory=dict)
    fees: Dict[bytes, List[Tuple[int, int]]] = field(default_factory=dict)
    exclusions: Dict[bytes, Set[bytes]] = field(default_factory=dict)
    wrappers: Dict[bytes, Dict[bytes, bytes]] = field(default_factory=dict)

    def lp_asset(self, pool_launcher: bytes) -> bytes:
        return self.lp_assets[pool_launcher]

    def holder_events(self, asset_id: bytes, before: int) -> List[HolderEvent]:
        return sorted(
            (e for e in self.events.get(asset_id, []) if e.height < before),
            key=lambda e: e.height,
        )

    def fee_events(self, pool_launcher: bytes, start: int, end: int) -> List[Tuple[int, int]]:
        return sorted((h, w) for h, w in self.fees.get(pool_launcher, []) if start <= h < end)

    def excluded(self, asset_id: bytes) -> Set[bytes]:
        return set(self.exclusions.get(asset_id, set()))

    def forwarders(self, asset_id: bytes) -> Dict[bytes, bytes]:
        return dict(self.wrappers.get(asset_id, {}))

    @classmethod
    def from_json(cls, data: dict) -> "FixtureSource":
        h = bytes.fromhex
        return cls(
            lp_assets={h(k): h(v) for k, v in data.get("lp_assets", {}).items()},
            events={
                h(asset): [HolderEvent(e[0], h(e[1]), e[2]) for e in evs]
                for asset, evs in data.get("events", {}).items()
            },
            fees={h(k): [tuple(x) for x in v] for k, v in data.get("fees", {}).items()},
            exclusions={h(k): {h(x) for x in v} for k, v in data.get("exclusions", {}).items()},
            wrappers={
                h(k): {h(a): h(b) for a, b in v.items()} for k, v in data.get("wrappers", {}).items()
            },
        )

    @classmethod
    def load(cls, path: str) -> "FixtureSource":
        with open(path, encoding="utf-8") as f:
            return cls.from_json(json.load(f))
