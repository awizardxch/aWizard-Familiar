# Skill: Forge Puzzle V12 — the CHIP-0062 review revision

> The Forge pool on the CHIP-0050 action layer, revised after CNI's Draft review of
> CHIP-0062 (Chia-Network/chips#217, greimela, 2026-09-11). Protocol **13**. V11.1 is
> closed: two of the review's findings were reproduced against it with accepted bundles.
> Design and evidence: `projects/chia-cfmm/docs/FORGE_PUZZLE_V12.md`; findings table:
> `FORGE_SECURITY_AUDIT.md` § V12. Everything in `forgePuzzleV11.md` still describes the
> shape, the leaves, the finalizer and the TAIL; this file is the delta.
> **Not externally audited. Testnet only.**

---

## Domain

Load this with `forgePuzzleV11.md` for any V12 pool work. Load it alone when the question is
"what changed and why" — a reviewer's finding, a solution shape, a record field.

## The four changes, and the finding each answers

| Finding (severity) | V11 hole | V12 |
|---|---|---|
| Genesis mints more LP than state records (P0) | Any coin could assert the launcher's one announcement; two eves minted twice the supply | The launcher announces `(total_lp, eve_coin_id)`; the TAIL's genesis branch asserts that list with `my_coin_id` from its CAT truths. One eve, by construction. |
| Successive generations backfill oracle time (P1) | Elapsed = claimed `h` − previous claimed `h`, both solver-chosen inside the window; an ephemeral successor in the same bundle recorded 31 blocks at a manipulated price | The prologue asserts `ASSERT_MY_BIRTH_HEIGHT { birth }` and accumulates `h − birth`. A claimed `h` can only *understate* elapsed time. Every leaf solution is `[h, birth, ...]`. |
| The final LP position cannot redeem (P1) | `burn < total_lp`, no minimum at genesis | `MIN_LOCKED_LP = 1000`: registry requires `total_lp >= 1000`; remove allows `burn <= total_lp − 1000`. Uniswap V2's answer; the trapped value is bounded and the creator's. |
| Reserve receiver derivation trusts solution data (P1) | The finalizer took reserve parent ids from its solution; a decoy at the reserve's puzzle hash and amount could be substituted, orphaning the real reserve | `ForgeState.reserve_parents` — read from the pre-spend state, written by the finalizer as the ids of the reserves it just messaged. The solution field is gone. |

Two more from the review needed no puzzle change: the protocol fee is **basis points**
(the CHIP had said ppm), and an empty action list was already refused upstream
(`action.rue` asserts non-empty; now pinned by a test).

## Rules to carry in your head

- **Solutions carry `birth`.** The driver inserts `pool.birth` in `with_birth()` on all
  three assembly paths (`run_leaf`, `spend_action`, `spend_actions`). Callers still pass
  `[h, ...]`.
- **There is a real node available without testnet.** `scripts/sim-v12.py` plus
  `contracts/_sim_harness.py` run `chia._tests.util.spend_sim`: the actual mempool and
  coin store, in process, in seconds. It farms to an anyone-can-spend puzzle (no keys,
  empty signatures), issues test CATs, mints the registry and creates AND registers
  pools with real birth heights. It is where a false birth was finally refused by
  consensus (`ASSERT_MY_BIRTH_HEIGHT_FAILED`) while testnet11 was halted. Three CAT2
  facts the harness had to learn: the mint signal is `(51 () -113 TAIL TAIL_SOLUTION)`
  with the reveal INLINE, every CAT mojo must be backed by a real XCH mojo or the node
  says `MINTING_COIN`, and two identical outputs from one parent are the same coin
  (`DUPLICATE_OUTPUT`).
- **A false birth is refused offline, not only live.** `validate` has no coin records,
  but `chia.consensus.check_time_locks` is a pure function and the mempool calls exactly
  it: give it the records the chain would have and it answers with a node's own error
  codes. `_test_v12_consensus_timelocks.py` does that. Reach for it whenever a claim
  depends on coin *records* rather than on puzzle output.
- **A V12 pool coin cannot be spent in the bundle that created it.** Consensus forbids a
  birth or relative condition on an ephemeral coin, and every V12 pool spend asserts its
  birth, so the two-generation shape is refused `EPHEMERAL_RELATIVE_CONDITION` whatever
  birth it claims; the truthful birth is refused earlier still by `h >= birth`. That is
  stronger than "accumulates nothing", which is what the design doc first said. Nothing
  legitimate needs it: many actions ride one pool spend, and a route spends other pools.
- **`reserve_parents` must be the parents of the coins the pool will actually spend.**
  `make_pool` sets them from the reserves it builds (fabricated or real). The successor's
  are the spent reserves' ids: `advance()` and `successor_puzzle_hash()` apply that
  rewrite via `pool.committed(new_state)`. Records and snapshots carry `reserve_parents`
  and `birth`.
- **Genesis kv is `[total_lp, eve_coin_id]`** in `launcher_spend`, `register_solution`
  (which also carries the eve state's `reserve_parents`), the deploy script and the create
  lane. Offline, the eve id is `genesis_eve_id(pool, salt)`; live, `pool.extra["eve_coin_id"]`.
- **The responder picks a lane by revision.** `forge_stdin._LANES = {12: V11 modules,
  13: V12 modules}`, chosen from the payload's `protocol_version` or its snapshots'; a
  bundle mixing revisions is refused. Default 13. Its internals are lane-NEUTRAL on
  purpose (`_build_lane`, `_lane_pool`, `off/rt/cre/drv`, `is_pool_snapshot`) because it
  serves both revisions; the result detail key is `forge`, not `v11`.
- **State is eight fields:** `[reserves, total_lp, fees_owed, [last_height, cums],
  prev_root, dao_fee_bps, dao_owed, reserve_parents]`.

## What pins what

`_test_v11_v12_review_findings.py` is the before-and-after for all four puzzle findings:
each attack must be ACCEPTED against V11 and REFUSED against V12, so a finding that stops
reproducing fails the suite rather than quietly testing nothing.
`_test_v12_consensus_timelocks.py` runs the mempool's `check_time_locks` over the
reviewer's two-generation bundle. Then:
`_test_v12_genesis.py` (second eve refused), `_test_v12_oracle.py` (same-block successor
accumulates nothing; `h < birth` refused), `_test_v12_finalizer.py` (decoy reserve refused;
successor parents recorded), `_test_v12_actions.py` (both sides of the `MIN_LOCKED_LP`
boundary; empty action list), `_test_v12_registry.py` (999 refused). Mutation: the two new
`assert`s are killed; the two locks inside conditions were mutated by hand and fail their
suites. `scripts/mutate-v12.py` (defaults to the v12 project; full sweep 2026-09-12:
12 of 33 leaf asserts killed, 8 of 24 in the TAIL, registry, finalizer and
reserve-amount program). `_test_v12_message_binding.py` walks every message and
derived hash and checks what binds each one; the audit carries the table.

## Files

`contracts/v12/` (rue), `forge_v12_driver.py`, `_v12_testkit.py`, `forge_v12_{offer,route,
create,index,resync}.py`, `forge_merkle.py` (shared, was `forge_v11_merkle`),
`scripts/{build-v12,deploy-v12-testnet,v12-launch.sh,mutate-v12,
v12-lifecycle-matrix,v12_ops,v12-sage-labels,import-v12-pools.mjs,live_v12_probe}`,
record `.awizard/v12-testnet.json`, `FORGE_PROTOCOL_VERSION = 13` in
`api/_forgeVersion.js` and `src/lib/poolIndexer.ts`, create endpoint
`api/forge-v12-create.js` with `src/lib/forgeV12Create.ts`.

**Registry history.** A V11-to-V12 rename corrected a stale string inside
`forge_registry_register` and enriched that announcement, so the registry root moved
(`e187e48d…` to `12e15e97…`). The pool leaves, TAIL, finalizer and reserve-amount program
are byte-identical (pool root still `46cf70c0…`), so pool hashes and LP asset ids never
moved. Launcher `3d4473a3…` and the A1/A2 pools under it are the superseded revision,
archived as `.awizard/v12-testnet.pre-rename-A1A2.json` and still spendable from it; a
pool can only be registered in its creation bundle, so they cannot be re-registered. The
live registry is `a12f0ca8e87881cc…`, minted 2026-09-12 at 4,677,846.

V11 stays in the tree until the V12 matrix is live, then moves to `development/`. Its
own suites still run, except `_test_v11_discoverability.py`, which asks the chain about
pools that were drained.
