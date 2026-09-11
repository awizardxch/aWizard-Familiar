# Skill: Forge Puzzle V11 — the shipping revision

> The Forge pool on the CHIP-0050 action layer, as it runs on testnet11 since 2026-09-05.
> V10 is closed; V4–V9 are retired. **Not externally audited. Testnet only.**
> Method: `clvmPuzzleAudit.md`. Findings: `projects/chia-cfmm/docs/FORGE_SECURITY_AUDIT.md`.
> Full protocol text: `projects/chia-cfmm/docs/FORGE_PUZZLE_V11.md`. Diagrams:
> `FORGE_V11_ARCHITECTURE.md`. For the action layer itself see `chip0050ActionLayer.md`.
> **V11.1 (protocol 12), 2026-09-05:** the DAO fee shipped. Config gains `dao_puzzle_hash`; state gains
> `dao_fee_bps` and `dao_owed`; a sixth leaf `dao_fee` lowers the rate on a mode-23 message from a coin at
> the DAO's puzzle hash; swap takes the slice, collect pays both recipients, the registry key adds the
> recipient, the TAIL asserts protocol 12. Delta section in `FORGE_PUZZLE_V11.md`; every leaf read in
> `projects/chia-cfmm/docs/FORGE_V11_CLVM_PASS.md`.

---

## Domain

Load this when the quest touches a V11 pool's puzzles: config, state, the prologue, a leaf's
rule, the finalizer's ordering, the TAIL, the registry, or cutting a revision. For the LP
handshake in detail see `forgeLpCat.md`; for what to run see `forgePoolLifecycleTesting.md`.

## The shape in one paragraph

A pool is `singleton( action_layer( finalizer, merkle_root, state ) )`. A spend names leaves
(swap, add, remove, observe, collect, dao_fee) with merkle proofs and solutions; the action layer proves
and runs them in order threading `ForgeState`; the **finalizer** runs once, recreates the
singleton and sends one CHIP-0025 mode-23 message per reserve. Reserves are
`p2_delegated_by_singleton` coins (nonce = asset index; bare XCH or CAT-wrapped) holding
`reserves[i] + fees_owed[i]`; they run exactly the delegated puzzle the message names. The LP
CAT's TAIL (curried `launcher_id, 11`) mints or melts only on the pool's message (genesis: the
launcher's `[total_lp]` announcement). The registry lists each configuration once.

## Constants that gate everything

`MIN_ASSETS 1 · MAX_ASSETS 10 · MAX_WEIGHT_UNITS 8 · MAX_TOTAL_WEIGHT 20 · MAX_FEE_BPS 200 ·
MAX_PROTOCOL_FEE_BPS 100 · price_scale 2^64 · oracle_window 32 · RESERVE_TAG -42 ·
PROTOCOL_VERSION 12` (V11.1; the TAIL asserts it). Asset ids strictly ascending, `ZERO_32`
is XCH. `MAX_DAO_FEE_BPS` gates the DAO slice; the rate may only ever fall.

## Rules to carry in your head

- **Prologue, first action only**: `valid_config`, state shape, `total_lp > 0`,
  `h > last_height`, `ASSERT_HEIGHT_ABSOLUTE h`, `ASSERT_BEFORE h+32`, `ASSERT_MY_AMOUNT 1`,
  oracle accumulates the **pre-spend** price, `prev_root = tree_hash(state)`. Later actions in
  the same spend must name the same `h` and get no prologue.
- **Swap** `[h, i_in, i_out, gross, claimed, settlement]`: `exact_swap_output` brackets
  `claimed`; protocol fee = slice of `claimed` accrued to `fees_owed[i_out]`; reserve `i_out`
  pays `claimed − fee` to `OFFER_MOD`; asserts `sha256(settlement_ph + tree_hash((id . nil)))`.
- **Add** `[h, deposits, lp_delta, lp_parent, settlements]`: one settlement assertion per
  positive deposit; `SEND_MESSAGE` to the eve at `coinid(lp_parent, CAT(lp, mint_inner), 1)`.
- **Remove** `[h, burn, lp_parent, payouts]`: `burn < total_lp`; payouts floored pro-rata,
  one-asset pool withholds the liquidity fee; message to the melt coin at
  `coinid(lp_parent, CAT(lp, melt_inner), burn)`; the TAIL requires a CAT parent to melt.
- **LP message**: `tree_hash(["forge-lp-v11", lp_delta, new_total_lp, tree_hash(new_state)])`.
- **Finalizer order**: each action's tagged conditions **reversed**, concatenated in execution
  order; the reserve's delegated puzzle is `(1 . [recreate_i, *conditions_i])`; message =
  `tree_hash((recreate_i . conditions_i))` to `coinid(parent_i, full_hash_i, new amount)`.
  Wrong order → error 147.
- **Observe** creates a slot `(h . cums)` and announces `["forge-observe-v1", h, cums]`.
  **Collect** pays `fees_owed[i]` to `protocol_puzzle_hash`; naming an index twice fails.
- **Settlement binds a coin, not an amount**: a payout coin can be the next pool's settlement;
  one entry coin can fan out to children (the route composer's hubs).
- **Registry key** `tree_hash([asset_ids, weights, fee_bps, protocol_fee_bps])`; sorted slots,
  adjacency structural; a duplicate configuration cannot register. Registration asserts the
  launcher's `[total_lp]` announcement and the fee settlement `(launcher, [[treasury, fee, [treasury]]])`.

## Things that are NOT in the puzzle

Names and symbols (memos on the launcher's creation and on deployer renames), the router
fee (surplus over the trader's request), the creation gate beyond the fee (an allowlist of
approved creator addresses, checked off chain). **The DAO fee is no longer on this list** — it
shipped in V11.1 and is in the puzzle; see the header.

## Drivers

`contracts/forge_v11_driver.py` is the one implementation (`make_pool`, `run_leaf`,
`spend_action(s)`, LP rings, registry spends, `validate` through `get_conditions_from_spendbundle`).
Keyless settlement: `forge_v11_offer.py` (single pool) and `forge_v11_route.py` (hubs). Snapshot
round trip: `pool_to_snapshot` / `snapshot_to_pool` re-curries and checks the pool coin. Resync
by replay: `forge_v11_resync.py`. Run suites with the workspace venv
(`aWizard-Familiar/.venv/Scripts/python.exe`).

## Cutting a revision

New leaf set → new merkle root → new TAIL version → new registry (its constants carry the leaf
hashes). Bump `PROTOCOL_VERSION` (driver, TAIL), `FORGE_PROTOCOL_VERSION` (`api/_forgeVersion.js`,
`src/lib/poolIndexer.ts`), rebuild with `scripts/build-v11.py`, re-pin `pins.json`, run the suites
(13 `_test_v11_*.py` plus 9 `_test_vault_*.py`), restart the local host (a stale host rewrites
the index from the browser's cached copy).

## Proving which assertions carry weight

A refusal test does not say *which* line refused. `scripts/mutate-v11.py` deletes one assertion
at a time, rebuilds with `rue`, and re-runs the suites; a mutant that still passes is an
assertion nothing pins. It is multi-suite on purpose — a single suite reported the DAO fee's
monotonic-decrease guarantee as unpinned when `_test_v11_dao_fee.py` kills it. Point the driver
at a mutant build with `FORGE_V11_COMPILED`. Survivors are triaged in
`projects/chia-cfmm/docs/FORGE_AUDIT_TIBETSWAP.md`, which also tests both publicly documented
TibetSwap failures against these puzzles.

## Published

The puzzles, suites and protocol documents are public at
<https://github.com/awizardxch/forge-puzzles>; the interface is split out to `forge-ui`, so what
is in the puzzle repo is the attack surface. Pushed from the monorepo one way by
`sync-subrepos.ps1` — never edit a sub-repo directly. The design is written up as a CHIP,
`projects/chia-cfmm/docs/chip/chip-awizard-weighted-n-asset-amm.md`. House rule for anything
public: no protocol versions, no vulnerability mechanics, no puzzle hashes for retired
revisions (`FORGE_CHIP_WORKFLOW.md`).
