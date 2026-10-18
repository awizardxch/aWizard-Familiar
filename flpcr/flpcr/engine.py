"""The reward engine: chain data in, one epoch's payout tree out.

Pure and deterministic. Every quantity is an exact rational until a holder's
cumulative accrual is floored, so two implementations that follow SPEC.md §6
produce the same root, and anyone can replay a posted epoch and dispute it.

Accounting per (campaign, holder):
    accrued   exact Fraction, everything the schedule has credited them so far
    allocated int, what posted epochs have already put in a payout tree
    delta     floor(accrued) - allocated, what this epoch may pay
Because each delta is a floor of a share of whole-mojo segment budgets, the sum
over holders never exceeds the campaign's `emittable(height)`, which is the
ceiling the distributor puzzle enforces.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Dict, Iterable, List, Optional, Tuple

from .merkle import build_tree, entry_hash, Proof
from .model import BPS, Campaign, Kind
from .sources import HolderEvent, Source

Balances = Dict[bytes, Fraction]


@dataclass
class EngineState:
    distributor_id: bytes
    epoch_id: int = 0  # the last posted epoch; the first epoch is 1
    height: Optional[int] = None  # start of the next epoch
    accrued: Dict[bytes, Dict[bytes, Fraction]] = field(default_factory=dict)
    allocated: Dict[bytes, Dict[bytes, int]] = field(default_factory=dict)


@dataclass(frozen=True)
class Entry:
    index: int
    puzzle_hash: bytes
    amount: int
    leaf: bytes
    proof: Proof


@dataclass
class Epoch:
    distributor_id: bytes
    epoch_id: int
    start: int
    end: int
    root: Optional[bytes]  # None when there was nothing to pay; not posted
    total: int
    allocations: Dict[bytes, int]  # campaign id -> mojos placed in this tree
    entries: List[Entry]


# --- balance timelines -------------------------------------------------------


class Timeline:
    """Balances of one asset as a step function of height."""

    def __init__(self, events: Iterable[HolderEvent]):
        self._steps: List[Tuple[int, bytes, int]] = sorted(
            ((e.height, e.puzzle_hash, e.delta) for e in events), key=lambda s: s[0]
        )

    def at(self, height: int) -> Dict[bytes, int]:
        bal: Dict[bytes, int] = defaultdict(int)
        for h, ph, d in self._steps:
            if h > height:
                break
            bal[ph] += d
        for ph, b in bal.items():
            if b < 0:
                raise ValueError(f"negative balance for {ph.hex()} at {height}")
        return {ph: b for ph, b in bal.items() if b}

    def changes(self, start: int, end: int) -> List[int]:
        return sorted({h for h, _, _ in self._steps if start < h < end})


class Holdings:
    """Effective positions in a tracked asset: system holders removed, wrapper
    holdings passed through to the wrapper's own holders (one level)."""

    def __init__(self, source: Source, asset_id: bytes, before: int, forward: bool):
        self.excluded = source.excluded(asset_id)
        self.main = Timeline(source.holder_events(asset_id, before))
        self.wrappers: Dict[bytes, Tuple[Timeline, set]] = {}
        if forward:
            for wrapper_ph, share_asset in source.forwarders(asset_id).items():
                self.wrappers[wrapper_ph] = (
                    Timeline(source.holder_events(share_asset, before)),
                    source.excluded(share_asset),
                )

    def changes(self, start: int, end: int) -> List[int]:
        hs = set(self.main.changes(start, end))
        for tl, _ in self.wrappers.values():
            hs.update(tl.changes(start, end))
        return sorted(hs)

    def at(self, height: int) -> Balances:
        out: Balances = defaultdict(Fraction)
        for ph, b in self.main.at(height).items():
            if ph in self.excluded:
                continue
            wrapper = self.wrappers.get(ph)
            if wrapper is None:
                out[ph] += b
                continue
            tl, wrapper_excluded = wrapper
            shares = {p: s for p, s in tl.at(height).items() if p not in wrapper_excluded}
            total = sum(shares.values())
            # A wrapper nobody holds a share of earns for no one.
            for p, s in shares.items():
                out[p] += Fraction(b * s, total)
        return dict(out)


def _eligible(campaign: Campaign, balances: Balances) -> Balances:
    return {ph: b for ph, b in balances.items() if campaign.eligible(ph, b)}


# --- one campaign over one epoch ----------------------------------------------


def accrue(campaign: Campaign, source: Source, start: int, end: int) -> Balances:
    """Exact credit each holder earns from `campaign` in [start, end)."""
    window = campaign.active_in(start, end)
    if window is None:
        return {}
    lo, hi = window
    asset = source.lp_asset(campaign.target) if campaign.kind == Kind.LP_HOLD else campaign.target
    holdings = Holdings(source, asset, hi, campaign.params.forward)

    cuts = [lo, *holdings.changes(lo, hi), hi]
    segments = [(a, b, _eligible(campaign, holdings.at(a))) for a, b in zip(cuts, cuts[1:])]

    p = campaign.params
    fee_points: List[Tuple[int, Balances]] = []
    if p.fees_bps:
        fee_points = [
            (w, _eligible(campaign, holdings.at(h)))
            for h, w in source.fee_events(campaign.target, lo, hi)
            if w > 0
        ]
        fee_points = [(w, bal) for w, bal in fee_points if bal]
    # An epoch with no fee-paying action spends its fee share on time weighting,
    # so the budget is never stranded because a pool was quiet.
    time_bps = p.time_bps if fee_points else BPS

    credit: Balances = defaultdict(Fraction)
    for a, b, bal in segments:
        total = sum(bal.values())
        if not total:
            continue  # nobody eligible: this budget stays unallocated, reclaimable
        budget = Fraction((campaign.emittable(b) - campaign.emittable(a)) * time_bps, BPS)
        for ph, x in bal.items():
            credit[ph] += budget * x / total

    if fee_points:
        fee_budget = Fraction((campaign.emittable(hi) - campaign.emittable(lo)) * p.fees_bps, BPS)
        weight = sum(w for w, _ in fee_points)
        for w, bal in fee_points:
            total = sum(bal.values())
            for ph, x in bal.items():
                credit[ph] += fee_budget * w * x / (weight * total)
    return dict(credit)


# --- one epoch for one distributor ---------------------------------------------


def run_epoch(
    state: EngineState,
    campaigns: Iterable[Campaign],
    source: Source,
    end: int,
    min_payout: int = 0,
) -> Tuple[EngineState, Epoch]:
    """Compute epoch `state.epoch_id + 1` over [state.height, end).

    `min_payout` defers a holder whose live-campaign total is below it to a
    later epoch (their accrual is kept, nothing is lost); any amount from a
    campaign that has ended is always paid so the creator's reclaim is final.
    Returns a new state; `state` is not modified.
    """
    campaigns = [c for c in campaigns if c.distributor_id == state.distributor_id]
    if not campaigns:
        raise ValueError("no campaigns for this distributor")
    start = state.height if state.height is not None else min(c.start for c in campaigns)
    if end <= start:
        raise ValueError("epoch must end after it starts")

    accrued = {cid: dict(v) for cid, v in state.accrued.items()}
    allocated = {cid: dict(v) for cid, v in state.allocated.items()}

    deltas: Dict[bytes, Dict[bytes, int]] = defaultdict(dict)  # holder -> campaign -> mojos
    for c in campaigns:
        cid = c.id
        acc = accrued.setdefault(cid, {})
        for ph, x in accrue(c, source, start, end).items():
            acc[ph] = acc.get(ph, Fraction(0)) + x
        alloc = allocated.setdefault(cid, {})
        for ph, x in acc.items():
            d = int(x) - alloc.get(ph, 0)  # int() floors a non-negative Fraction
            if d > 0:
                deltas[ph][cid] = d

    ended = {c.id for c in campaigns if c.end <= end}
    paid: Dict[bytes, int] = {}
    allocations: Dict[bytes, int] = defaultdict(int)
    for ph in sorted(deltas):
        by_campaign = deltas[ph]
        amount = sum(by_campaign.values())
        if amount < min_payout and not any(cid in ended for cid in by_campaign):
            continue
        paid[ph] = amount
        for cid, d in by_campaign.items():
            allocated[cid][ph] = allocated[cid].get(ph, 0) + d
            allocations[cid] += d

    epoch_id = state.epoch_id + 1
    if not paid:
        # Nothing to post. The state is left as it was, so the next run covers
        # the longer window and posted epochs keep tiling the timeline.
        return state, Epoch(state.distributor_id, epoch_id, start, end, None, 0, {}, [])

    leaves = [
        entry_hash(state.distributor_id, epoch_id, i, ph, amt)
        for i, (ph, amt) in enumerate(paid.items())
    ]
    root, proofs = build_tree(leaves)
    entries = [
        Entry(i, ph, amt, leaves[i], proofs[leaves[i]])
        for i, (ph, amt) in enumerate(paid.items())
    ]

    for c in campaigns:
        # The engine's own copy of the puzzle's ceiling check. Failing here is a
        # bug in the engine, never something to post.
        total_alloc = sum(allocated[c.id].values())
        if total_alloc > c.emittable(end):
            raise AssertionError(f"campaign {c.id.hex()} over-allocated: {total_alloc} > {c.emittable(end)}")

    new_state = EngineState(state.distributor_id, epoch_id, end, accrued, allocated)
    epoch = Epoch(state.distributor_id, epoch_id, start, end, root, sum(paid.values()), dict(allocations), entries)
    return new_state, epoch


def unallocated(campaign: Campaign, state: EngineState) -> int:
    """What the creator may reclaim once the campaign has ended and every epoch
    covering it is posted."""
    return campaign.amount - sum(state.allocated.get(campaign.id, {}).values())
