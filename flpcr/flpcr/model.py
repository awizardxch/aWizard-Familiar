"""Campaigns: what a creator funds, and the schedule the puzzle enforces."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import FrozenSet, Optional

from .clvm import sha256tree

CAMPAIGN_TAG = "flpcr-campaign-v1"
BPS = 10_000


class Kind(IntEnum):
    # Time-weighted holders of a Forge pool's LP CAT. `target` is the pool's launcher id.
    LP_HOLD = 1
    # Time-weighted holders of any CAT. `target` is the CAT's asset id (TAIL hash).
    CAT_HOLD = 2


@dataclass(frozen=True)
class Params:
    """Scoring rules. Committed on chain by `params_hash`; published in full in the
    creation spend's solution so anyone can recover them."""

    # Split of each block's emission between share-of-supply and share-of-fees.
    # Fee weighting only means something for LP_HOLD; CAT_HOLD must be all time.
    time_bps: int = BPS
    fees_bps: int = 0
    # A holder below this balance (mojos of the tracked asset) is not eligible.
    min_balance: int = 0
    blacklist: FrozenSet[bytes] = frozenset()
    # Empty means everyone not blacklisted.
    whitelist: FrozenSet[bytes] = frozenset()
    # Credit balances held by known wrappers (a vault pool's nested LP reserve)
    # to the wrapper's own holders instead of to the wrapper.
    forward: bool = True

    def as_clvm(self) -> list:
        return [
            self.time_bps,
            self.fees_bps,
            self.min_balance,
            sorted(self.blacklist),
            sorted(self.whitelist),
            1 if self.forward else 0,
        ]

    def hash(self) -> bytes:
        return sha256tree(self.as_clvm())


@dataclass(frozen=True)
class Campaign:
    distributor_id: bytes  # launcher id of the distributor that holds the reward asset
    creator: bytes  # puzzle hash; receives the unallocated remainder after the end
    reward_asset: bytes  # ZERO_32 for XCH, else the CAT asset id
    amount: int  # mojos of reward_asset, net of the creation fee
    start: int  # block height, inclusive
    end: int  # block height, exclusive
    kind: Kind
    target: bytes
    params: Params = field(default_factory=Params)
    nonce: int = 0  # lets one creator fund two otherwise identical campaigns

    def __post_init__(self) -> None:
        if self.amount <= 0:
            raise ValueError("amount must be positive")
        if self.end <= self.start:
            raise ValueError("end must be after start")
        p = self.params
        if p.time_bps < 0 or p.fees_bps < 0 or p.time_bps + p.fees_bps != BPS:
            raise ValueError("time_bps + fees_bps must equal 10000")
        if self.kind == Kind.CAT_HOLD and p.fees_bps:
            raise ValueError("fee weighting needs a pool; CAT_HOLD is time only")
        if p.min_balance < 0:
            raise ValueError("min_balance must be >= 0")
        if p.blacklist & p.whitelist:
            raise ValueError("a puzzle hash cannot be on both lists")

    @property
    def length(self) -> int:
        return self.end - self.start

    def as_clvm(self) -> list:
        return [
            CAMPAIGN_TAG,
            self.distributor_id,
            self.creator,
            self.reward_asset,
            self.amount,
            self.start,
            self.end,
            int(self.kind),
            self.target,
            self.params.hash(),
            self.nonce,
        ]

    @property
    def id(self) -> bytes:
        return sha256tree(self.as_clvm())

    def emittable(self, height: int) -> int:
        """Mojos the schedule has released by `height`. The distributor's
        `post_epoch` leaf refuses any allocation above this, so the engine
        never has more to hand out than this number, whatever it computes.
        Telescoping floors: emittable(end) == amount exactly."""
        h = min(max(height, self.start), self.end)
        return self.amount * (h - self.start) // self.length

    def active_in(self, a: int, b: int) -> Optional[tuple]:
        """The part of [a, b) this campaign emits in, or None."""
        lo, hi = max(a, self.start), min(b, self.end)
        return (lo, hi) if lo < hi else None

    def eligible(self, puzzle_hash: bytes, balance) -> bool:
        p = self.params
        if puzzle_hash in p.blacklist:
            return False
        if p.whitelist and puzzle_hash not in p.whitelist:
            return False
        return balance > 0 and balance >= p.min_balance
