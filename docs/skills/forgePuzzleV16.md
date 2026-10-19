# Skill: Forge puzzle V16 — the shipping revision (protocol 17)

> **The live revision.** V16 (protocol 17) is the only revision on mainnet (21 pools on
> 2026-10-18) and runs on testnet11 beside the kept V15 (protocol 16, 51 pools) and V14
> (protocol 15, 50 pools). Unaudited; four rounds of external review have found real
> defects in earlier revisions.
>
> V16 and V15 are **deltas on V14**: the shape (action layer, six leaves, multi-reserve
> finalizer, reserve launcher, registry) is V14's, so read `forgePuzzleV14.md` for the
> architecture and this file for what changed since. Authority: the monorepo docs
> `projects/chia-cfmm/docs/FORGE_PUZZLE_V16.md` and `FORGE_PUZZLE_V15.md` win on any
> disagreement.

---

## Protocol vs revision

Off by one, always: **protocol 17 = V16**, 16 = V15, 15 = V14. Derived from one number
(`PROTOCOL_VERSION` in `contracts/forge_v16_driver.py`); `api/__checks__/
revisionAgreement.check.mjs` holds the driver, the responder and the browser together.
`FORGE_KEPT_PROTOCOLS = [15, 16, 17]`: all three settle, a creation takes the newest lane.

## What V16 changed (2026-10-09, one thing)

The locked minimum (`LOCKED_BURN = 1` LP unit) is burned to **Chia's burn address**
`0x000...dead` (`xch1qqqq…m6ks6e8mvy` / `txch1qqqq…m6ksh7qddh`) instead of the all-zero hash.
Both are unspendable; `...dead` is the one wallets and explorers show as a burn, where an
all-zero hash reads like a cleared field. `register` asserts the genesis settlement paid
`LOCKED_BURN` there (`BURN_PUZZLE_HASH` in `forge_action_common.rue`). Everything else is
V15's: the action layer, finalizer and four of six leaves hash identically; the LP TAIL,
`add` and `remove` move only by their message tags.

## What V15 changed (2026-10-07, after the sixth review)

| # | Change | Why it matters |
|---|---|---|
| F4 | `lp_action_coin_id` and `register`'s launcher id derived with `coinid` | A malformed parent or a leading-zero amount is refused **in the leaf**, not later at message pairing; validators that only run the puzzle (relay in-app lane, mirrors) see it |
| F7 | `h` and `new_bps` stored after `+ 0` | The hashed state is canonical by construction; V14's state hash diverged on a leading-zero spelling |
| fee | Creation fee is registry **state** `(initialized, pool_count, creation_fee)`; new `set_fee` leaf | The fee moves without a successor registry, authorized by a mode-23 message from a coin at the treasury puzzle hash (mainnet: the treasury lock). The dev-fee **recipient** still needs `registry --rollover` |

Neither F4 nor F7 closed an exploit (no funds moved on V14); they move refusals into the
leaf. rCATs stay out of scope by construction, as on V14.

## Tooling (V16)

| What | Command / file |
|---|---|
| Build, re-check pins | `python scripts/build-v16.py` (rue 0.8.4) |
| Simulator lifecycle | `python scripts/sim-v16.py`, `scripts/sim-v16-chip0062.py` |
| Mutation run | `python scripts/mutate-v16.py` (UNREACHED rule; arguments in `contracts/v16/mutation-arguments.json`) |
| Suites | `contracts/_test_v16_*.py` (actions, registry, reserves_proved, settlement_amount, before_after vs V13, manipulation, curve_equivalence, genesis, integrity, …) |
| Operator flow | `scripts/deploy-v16-testnet.py <registry\|create-pool\|swap\|add\|remove\|observe\|collect\|status>`; `FORGE_NETWORK=mainnet` for mainnet |
| Lifecycle matrix | `scripts/v16-lifecycle-matrix.py`, `scripts/plan-v16-matrix.py` |
| Records → index | `scripts/v16-resync-records.py` then `node scripts/import-v16-pools.mjs` |
| Registry records | `.awizard/v16-testnet.json`, `.awizard/v16-mainnet.json` (router: `/data/v16-<network>.json`) |
| Relay in-app lane | `src/lib/relay/v16/` (`gen-relay-v16-modules.py`, `gen-relay-v16-actions.py`) |

Testnet registry: `f483a16a854e469f7aa9b2908d63daab47f27b328534857a39d2cd6090996b69`
(8 pools A1–A4, B1–B4). V14/V15 keep their own `v14_`/`v15_` scripts for their pools
(`v15_ops.py`, `v15-offer-lane-test.py` have no V16 twin yet).

## Traps

- **"V14" in an older doc is not the live revision.** Docs written before 2026-10-09 say
  V14 (protocol 15) where they mean the shipping set; the published artifact pages still
  describe V14 until refreshed.
- **`pool_module_hash` no longer identifies a revision** (V14–V16 share the action layer):
  snapshots carry `revision_hash` (the LP TAIL mod hash).
- **Wallet-built offers** (Sage, Spellbook `forge_swap`) are sized by
  `/api/v1/agent/size`, never from a quote's `intent`: see the agent contract
  `docs/FORGE_AGENT_API.md`.

Related: `forgePuzzleV14.md` (the architecture), `forgePuzzleV11.md` (the shape),
`clvmPuzzleAudit.md` (method), `forgeLpCat.md`, `forgePoolLifecycleTesting.md`.
