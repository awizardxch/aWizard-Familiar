# FLPCR — Forge Liquidity Pool Campaign Rewards

Incentive campaigns for Forge liquidity and Chia CATs: anyone funds a reward budget on a Forge pool
(rewarding LP holders) or on a CAT (rewarding holders) over a block range. An off-chain engine
scores holders every epoch, and an on-chain distributor singleton pays them, capped by each
campaign's emission schedule.

The reference design is Merkl's EVM incentive layer, rebuilt for Chia's coin set model on the
CHIP-0050 action layer that Forge V14 runs on. **Testnet only. Not audited.**

| | |
|---|---|
| [`docs/SPEC.md`](docs/SPEC.md) | The whole design: the Merkl mapping, campaign kinds, distributor, scoring, trust model, phases |
| [`docs/PUZZLES.md`](docs/PUZZLES.md) | Leaf-by-leaf build spec for the distributor (phase 2) |
| [`docs/API.md`](docs/API.md) | HTTP API, read and write |
| `flpcr/` | The engine: campaigns, exact time and fee weighting, forwarding, payout tree, manifests |
| `tests/` | Engine and hashing tests; hashing is cross-checked against `clvm` when installed |

## Run

```bash
python -m pip install pytest clvm   # clvm is optional, it enables the cross-check
python -m pytest -q
python -m flpcr fixtures/demo.json --end 2000 --state /tmp/flpcr-state.json
python -m flpcr fixtures/demo.json --end 3000 --state /tmp/flpcr-state.json
```

The engine itself is standard library only (Python 3.10+).

## Status

- **Phase 0 (here):** spec + engine + tests.
- **Phase 1:** live chain source for testnet11 (hinted LP CAT coins, `forge_v14_resync` for fee events).
- **Phase 2:** distributor puzzles in Rue, with V14-style suites.
- **Phase 3:** operator / keeper / watcher bots, API, interface tab.
