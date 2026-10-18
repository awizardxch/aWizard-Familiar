"""Run one epoch from a fixture.

    python -m flpcr fixtures/demo.json --end 2000 [--state state.json] [--min-payout N]

Prints the epoch manifest; with --state, reads the prior engine state from that
file if it exists and writes the new state back.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from .engine import EngineState, run_epoch
from .manifest import epoch_to_json, manifest_hash, state_from_json, state_to_json
from .model import Campaign, Kind, Params
from .sources import FixtureSource


def campaign_from_json(d: dict) -> Campaign:
    h = bytes.fromhex
    p = d.get("params", {})
    return Campaign(
        distributor_id=h(d["distributor_id"]),
        creator=h(d["creator"]),
        reward_asset=h(d["reward_asset"]),
        amount=d["amount"],
        start=d["start"],
        end=d["end"],
        kind=Kind[d["kind"]],
        target=h(d["target"]),
        params=Params(
            time_bps=p.get("time_bps", 10_000),
            fees_bps=p.get("fees_bps", 0),
            min_balance=p.get("min_balance", 0),
            blacklist=frozenset(h(x) for x in p.get("blacklist", [])),
            whitelist=frozenset(h(x) for x in p.get("whitelist", [])),
            forward=p.get("forward", True),
        ),
        nonce=d.get("nonce", 0),
    )


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="flpcr")
    ap.add_argument("fixture")
    ap.add_argument("--end", type=int, required=True, help="epoch end height (exclusive)")
    ap.add_argument("--state", help="engine state file, read if present and rewritten")
    ap.add_argument("--min-payout", type=int, default=0)
    args = ap.parse_args(argv)

    with open(args.fixture, encoding="utf-8") as f:
        data = json.load(f)
    source = FixtureSource.from_json(data)
    campaigns = [campaign_from_json(c) for c in data["campaigns"]]
    distributor = campaigns[0].distributor_id

    if args.state and os.path.exists(args.state):
        with open(args.state, encoding="utf-8") as f:
            state = state_from_json(json.load(f))
    else:
        state = EngineState(distributor)

    state, epoch = run_epoch(state, campaigns, source, args.end, args.min_payout)
    out = epoch_to_json(epoch)
    if epoch.root is not None:
        out["manifest_hash"] = manifest_hash(epoch).hex()
    json.dump(out, sys.stdout, indent=2)
    sys.stdout.write("\n")

    if args.state:
        with open(args.state, "w", encoding="utf-8") as f:
            json.dump(state_to_json(state), f, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
