# Forge V12 — the upgrade plan that answers the CHIP-0062 review

> The implementation half of [`FORGE_CHIP0062_REVIEW_RESPONSE.md`](FORGE_CHIP0062_REVIEW_RESPONSE.md).
> Read that first for *why*; this document is *what to change, in what order, and how to know
> it is done*. Written 2026-09-11 against V11.1 (protocol 12). Workspace paths are pointers for
> someone with the monorepo open (`projects/chia-cfmm/`); the public mirror is
> `awizardxch/forge-puzzles`, pushed one way by `sync-subrepos.ps1` — never edit it directly.
>
> Method: `skills/clvmPuzzleAudit.md`. Every probe below runs the **compiled** puzzle through
> `chia_rs.get_conditions_from_spendbundle` (the harness's `kit.validate`), with the honest case
> beside it. A probe that only fails on the V11.1 build for an arity reason is not a regression.

---

## 0. Scope and shape of the revision

| | |
|---|---|
| Revision | **V12**, `PROTOCOL_VERSION = 13` in the TAIL and the registry (V11.1 is 12) |
| What changes hash | the TAIL (F1, F3), the prologue and every leaf (F2, F5), the finalizer (F5), the registry leaves (F1, F3, F5), the config shape (F2) and the state shape (F2, F5) |
| What does not | `forge_curve.rue` bodies (F4 is a constant rename, hex-identical), the pinned upstream puzzles, the LP mint and melt inners |
| Consequence | new LP asset ids for every pool; every V11.1 pool retired; the launch matrix redeployed; `FORGE_PROTOCOL_VERSION` bumped in `api/_forgeVersion.js` and `src/lib/poolIndexer.ts` |
| Landing order | **step 1 (F4, F6) can land today** as a docs + test commit. Steps 2–5 are one revision and one testnet deploy. Step 6 is the CHIP. |

Work the steps in order: each later step builds on the state and solution shapes the earlier
one fixes, and cutting the revision twice would mean two LP-asset migrations.

---

## 1. Document-only findings — land first

### 1a. F4 — basis points, named (no hex change)

1. `contracts/v11/puzzles/forge_curve.rue`: rename `WEIGHT_SCALE` → `BPS_DENOMINATOR`
   (every use: `exact_invariant_lp_mint`, `effective_product`, `exact_withdrawal`,
   `exact_swap_output`, `protocol_fee_owed`). Rebuild; the `byte_identical_to_v10` list in
   `pins.json` and `_test_v11_curve_equivalence.py` must still pass unchanged — that is the
   proof the rename is free.
2. `docs/FORGE_PUZZLE_V11.md` (→ V12 doc later): add a **Constants** table with exactly these
   names and values — `MIN_ASSETS 1`, `MAX_ASSETS 10`, `MAX_WEIGHT_UNITS 8`,
   `MAX_TOTAL_WEIGHT 20`, `BPS_DENOMINATOR 10_000`, `MAX_FEE_BPS 200`,
   `MAX_PROTOCOL_FEE_BPS 100`, `MAX_DAO_FEE_BPS 100`, `RATIO_SCALE 10^12`, plus `MIN_LP` and
   `MIN_GENESIS_LP` from step 3 — and the three fee formulas (input fee inside the curve;
   protocol and DAO slices each `floor(claimed × bps / 10_000)` on the gross claimed output).
3. `contracts/_test_v11_integrity.py`: a conformance check that parses that table out of the
   spec document and compares name and value against the compiled constants (read them from
   the rue sources' `inline const` lines, which is what the build compiles). The check fails
   if the table names a constant the source lacks, or vice versa.
4. Frontend: retire the vestigial `protocolFeePpm` field name wherever it still exists
   (`grep -rn Ppm src api`); it is where the CHIP's "ppm" came from.

### 1b. F6 — the empty spend, stated and probed

1. `contracts/_test_v11_actions.py`, prologue section: `refuses("a spend with no actions is
   refused", …)` — assemble the action-layer solution with `selectors_and_proofs = []` and
   `solutions = []` through `kit.assemble` and validate. Expect a CLVM assertion (error 117).
2. Spec sentence (see response doc, F6) in `FORGE_PUZZLE_V11.md` under the action layer, and
   in the CHIP's *Leaves*.
3. Objections-log entry names `puzzles/upstream/action.rue` `assert !(selectors_and_proofs is
   nil);` and the pin `afa03f29…` from `pins.json`.

---

## 2. F5 — reserve coin ids in state (do this first among the puzzle changes)

State shape first, because F1/F3 (registry eve state) and F2 (prologue) both write the state.

### 2a. `forge_action_common.rue`

```
export struct ForgeState {
    reserves: List<Int>,
    total_lp: Int,
    fees_owed: List<Int>,
    oracle: Oracle,
    prev_root: Bytes32,
    dao_fee_bps: Int,
    dao_owed: List<Int>,
    // V12: the coin id of each reserve, committed by the finalizer every spend.
    // Leaves carry it through untouched; the finalizer overwrites it from the truth.
    reserve_ids: List<Bytes32>,
}
```

Trailing on purpose: every index-based reader (`state_to_list`, `_state_amounts`, the JS
snapshot) keeps its offsets. Prologue, first action: `assert count_bytes(state.reserve_ids) == n`.

### 2b. Every leaf

`swap`, `add`, `remove`, `observe`, `collect`, `dao_fee`: each `ForgeState { … }` literal gains
`reserve_ids: p.state.reserve_ids`. Nothing else.

### 2c. `forge_multi_reserve_finalizer.rue`

- Import `ForgeState` from `forge_action_common` (the finalizer is Forge's own; it may know
  the shape). `forge_reserve_amount.rue`'s private struct gains the same trailing field.
- Remove `...reserve_parent_ids: List<Bytes32>` from `main`; the finalizer solution becomes
  `..._my_solution: Any`, unused, as upstream's default finalizer has it.
- `reserve_messages` takes `reserve_ids: List<Bytes32>` (from
  `unchecked_cast::<ForgeState>(Truth.State).reserve_ids`) in place of `parent_ids`, and:

```
receiver:  [ reserve_ids.first ]                                   // the truth, never the solution
successor: coinid(reserve_ids.first, full_hashes.first, amount_program(new_state, index))
```

- Build `committed_state = ForgeState { …acted, reserve_ids: successors }` where `acted` is
  `last_action_output.first.actual_state` and `successors` is the list above in asset order;
  the singleton is recreated with `tree_hash(committed_state)`. The leaves' `reserve_ids` are
  discarded, not compared — there is nothing to compare against that the leaves could not
  also have copied.
- The `count(RESERVE_FULL_PUZZLE_HASHES)` range check stays; add
  `assert count(reserve_ids) == count(RESERVE_FULL_PUZZLE_HASHES)`.

### 2d. Registry

`forge_registry_register.rue` solution gains `reserve_parent_ids: List<Bytes32>` (the
creator's funding coins, one per asset, in asset order). `forge_registry_common.rue`:

- `eve_state_hash(reserves, total_lp, n, dao_fee_bps, reserve_ids)` appends `reserve_ids`;
- `genesis_reserve_ids(parent_ids, full_hashes, reserves)` = `coinid(parent_i, full_hash_i,
  reserves[i])` per asset, so the registered eve state can only name coins at the reserve
  puzzle hashes; `pool_full_puzzle_hash` takes the parents and uses it.

### 2e. Drivers and tooling

| file | change |
|---|---|
| `forge_v11_driver.py` | `Reserve` carries `coin_id`; `forge_state(...)` takes `reserve_ids`; `spend_actions` drops `parent_ids`; `advance` computes successor ids exactly as the finalizer does and asserts they match the bundle's additions; `make_pool` seeds ids from the fabricated genesis coins |
| `forge_v11_create.py` | passes the funding parents into `register_solution`; the eve state carries the derived ids |
| `pool_to_snapshot` / `snapshot_to_pool` | serialise `reserve_ids` (hex strings); `snapshot_to_pool` re-curries and checks the pool coin — this is the guard that caught finding 9, keep it |
| `forge_v11_resync.py`, `scripts/verify-v11-pool.py` | follow reserves by the ids in state, not by hint scan; assert each generation's committed successors are the coins the chain created |
| `api/pools.js`, `src/lib/poolIndexer.ts` | read `reserve_ids` from the trailing slot; never index by position before it |

### 2f. Probes (`_test_v11_finalizer.py` → keep the name, add cases)

- honest N=2, N=10: accepted; `committed_state.reserve_ids == [coin ids of the recreated reserves in additions]`
- **regression:** a bundle in which reserve `i`'s genuine coin is absent and an attacker-funded
  coin at the same full puzzle hash and pre-spend amount is present → refused (unpaired
  message, 147). Against V11.1, the same bundle with the impostor's parent in the finalizer
  solution → accepted. Keep both halves in one file.
- a passthrough action (`puzzles/testing/passthrough_action.rue`) that returns a state with
  `reserve_ids` rewritten → the committed state carries the derived ids.
- two successive snapshot round trips → pool coin unchanged (existing rule).

---

## 3. F3 — minimum liquidity, counted not minted

### 3a. Constants (`forge_action_common.rue`)

```
export inline const MIN_LP: Int = 1000;            // never minted; owns a pro-rata share forever
export inline const MIN_GENESIS_LP: Int = 1000000; // registry floor: the lock is ≤ 0.1 % of genesis
```

### 3b. Puzzle edits

| where | V11.1 | V12 |
|---|---|---|
| prologue, first action | `assert state.total_lp > 0;` | `assert state.total_lp >= MIN_LP;` |
| `forge_action_remove.rue` | `assert burn < p.state.total_lp;` | `assert burn <= p.state.total_lp - MIN_LP;` |
| TAIL genesis branch | `assert action.new_total_lp == action.expected_delta;` | `assert action.new_total_lp == action.expected_delta + MIN_LP;` |
| registry `valid_pool` | `total_lp > 0` | `total_lp >= MIN_GENESIS_LP` |

`exact_withdrawal` and `exact_invariant_lp_mint` are untouched: they run on `total_lp`, which
now includes the lock, which is the whole mechanism.

### 3c. Drivers

`forge_v11_create.plan`: the eve mints `total_lp - MIN_LP`; the launcher's key-value list and
the registry's `total_lp` carry the state value. `make_pool(total_lp=1_000_000)` default is
already at the floor. `forge_math.py` mirrors: withdrawal quotes use the state `total_lp`
(unchanged formula), and the "max burn" a UI offers is `total_lp - MIN_LP`.

### 3d. Probes (`_test_v11_actions.py` remove section, `_test_v11_registry.py`)

- remove to exactly `MIN_LP` outstanding: accepted, payout `reserves × burn / total_lp`;
- remove to `MIN_LP - 1`: refused. **Regression:** on V11.1 a remove to `total_lp = 1` is
  accepted and a follow-up remove is unbuildable;
- genesis `total_lp = MIN_GENESIS_LP - 1`: refused by the registry;
- genesis eve minting `total_lp` (not `total_lp - MIN_LP`): refused by the TAIL;
- creation audit: the creator, burning everything they hold, receives strictly less than they
  deposited — re-run at V12 (`_test_forge_creation_audit.py`'s V10 assertion, ported).

---

## 4. F1 — one launcher, one eve

### 4a. TAIL (`forge_lp_cat_tail.rue`)

Add a truths accessor beside `cat_my_amount`:

```
// CAT2 truths: ((inner_puzzle_hash . cat_struct) . (my_coin_id . (parent, full_puzzle_hash, amount)))
fn cat_my_coin_id(truths: Any) -> Bytes32 {
    let outer = unchecked_cast::<(Any, Any)>(truths);
    let id_and_coin = unchecked_cast::<(Any, Any)>(outer.rest);
    unchecked_cast::<Bytes32>(id_and_coin.first)
}
```

Genesis branch:

```
} else {
    assert !parent_is_cat;
    assert action.expected_delta > 0;
    assert action.new_total_lp == action.expected_delta + MIN_LP;   // step 3
    [
        AssertCoinAnnouncement {
            id: sha256(launcher_id + tree_hash([
                action.genesis_pool_puzzle_hash,
                1,
                [action.new_total_lp, cat_my_coin_id(truths_any)],
            ])),
        },
    ]
}
```

`PROTOCOL_VERSION = 13`. The CAT layer asserts `my_coin_id` itself, so the truth is sound.

### 4b. Registry (`forge_registry_register.rue`)

Solution gains `eve_parent_id: Bytes32`. The announcement assertion becomes:

```
AssertCoinAnnouncement {
    id: sha256(launcher_id + tree_hash([
        pool_puzzle_hash, 1,
        [total_lp, lp_action_coin_id(config, eve_parent_id, LP_MINT_INNER_HASH, 1)],
    ])),
}
```

`lp_action_coin_id` is the `add` leaf's derivation, reused, so the registered eve necessarily
wraps the pinned mint inner. `forge_registry_common.rue` `PROTOCOL_VERSION = 13`.

### 4c. Drivers

`forge_v11_driver.launcher_spend(pool, kv_list=[total_lp, eve_id])`;
`lp_genesis_mint_spends` unchanged in shape; `register_solution` gains the eve parent;
`forge_v11_create.plan` already builds the eve coin before the launcher spend — pass its
parent through. `genesis_action(pool)` sets `new_total_lp = total_lp`,
`expected_delta = total_lp - MIN_LP`.

### 4d. Probes (new `_test_v12_genesis.py`, plus `_test_v11_registry.py`)

- one eve: accepted; the creator receives `total_lp - MIN_LP`, hinted;
- **regression:** two eves (distinct parents, one mojo each, at the mint inner), both
  asserting the launcher's announcement, in one bundle → refused; on V11.1 → accepted and
  `2 × total_lp` LP created while state says `total_lp` (the reviewer's reproduction);
- an eve whose parent is not the one the launcher named → refused;
- registry `eve_parent_id` mismatching the launcher → refused;
- one LP more than the launcher named → refused (exists).

---

## 5. F2 — the oracle on birth heights

### 5a. Config and state (`forge_action_common.rue`)

- `PoolConfig`: **remove** `oracle_window`. Keep `price_scale`.
- `Oracle` becomes:

```
export struct Oracle {
    last_birth: Int,         // birth height of the coin being spent, as verified at its spend
    last_spots: List<Int>,   // spot prices (asset i in asset 0, × price_scale) in force since last_birth; N-1 entries
    cums: List<Int>,         // price × blocks, accumulated through last_birth; N-1 entries
}
```

### 5b. Prologue

Signature `prologue(config, truth, birth: Int)`; every leaf's solution replaces `h` with
`birth`. First action of a spend:

```
assert birth >= state.oracle.last_birth;       // consensus guarantees it; defence in depth
let elapsed = birth - state.oracle.last_birth;
oracle: Oracle {
    last_birth: birth,
    last_spots: spots(state.reserves, config.weights, config.price_scale),
    cums: accumulate(state.oracle.last_spots, state.oracle.cums, elapsed),
},
conditions: [
    AssertMyBirthHeight { height: birth },     // opcode 75, CHIP-0014
    AssertMyAmount { amount: 1 },
],
```

`accumulate` becomes `cums[i] += last_spots[i] × elapsed`; `spots` is the existing per-asset
`divmod(r0 × wi × price_scale, ri × w0)`. Later actions: `ephemeral_state == birth`. If rue
0.8.4's std lacks `AssertMyBirthHeight`, emit `unchecked_cast::<Condition>((75, birth))` the
way `for_reserve` builds the tagged condition, and add a probe that the raw opcode is 75.

Genesis state (`eve_state_hash`): `[0, zeros(n-1), zeros(n-1)]` — the first interval
contributes nothing.

### 5c. `observe`

Slot value `(p.state.oracle.last_birth . p.state.oracle.cums)`; announcement
`["forge-observe-v2", last_birth, cums]`. A consumer's TWAP is
`(cum_b − cum_a) / (birth_b − birth_a)`.

### 5d. Drivers

- `spend_actions` takes `birth` (the pool coin's `confirmed_block_index` from the node, or the
  simulator's height); the responder reads it from the coin record, never the browser.
- Snapshots carry `birth_height`; `snapshot_to_pool` requires it; resync takes it from each
  generation's coin record.
- `expected_cums` in the driver mirrors the lagged rule; `_test_v11_actions.py`'s prologue
  check ("oracle accumulated the pre-spend price") is rewritten to the lagged form.

### 5e. Probes (new `_test_v12_oracle.py` on `chia.clvm.spend_sim`; existing suites updated)

- conditions carry `ASSERT_MY_BIRTH_HEIGHT birth`; no height pin, no window;
- wrong `birth` → mempool refuses (`ASSERT_MY_BIRTH_HEIGHT_FAILED`);
- two honest spends, blocks apart: `cums == spot(R_1) × (B_2 − B_1)`;
- **regression:** generation g swaps (moves the price), generation g+1 in the *same block*
  runs any leaf: the manipulated price gets weight 0; then a block passes and g+2 weights it
  by exactly 1. On V11.1 the same sequence with `h` chosen at the window edge weights it by 31;
- `_test_v11_manipulation.py`: unchanged assertions still hold (the actor is never richer at
  pre-sequence prices).

### 5f. Fallback (only if 5a–5e are deferred)

Delete `Oracle`, `price_scale`, `observe` and its slot, `accumulate`; five-leaf tree; the
registry's `six_leaf_root` becomes five; CHIP loses the use-case bullet and the threat row.
Record the deferral in the objections log as "removed pending a revision that can bind time".

---

## 6. Cutting V12 — the checklist

Adapted from `skills/forgePuzzleV11.md` "Cutting a revision".

1. `PROTOCOL_VERSION = 13` in `forge_lp_cat_tail.rue` and `forge_registry_common.rue`;
   `FORGE_PROTOCOL_VERSION` in `api/_forgeVersion.js` and `src/lib/poolIndexer.ts`.
2. `python scripts/build-v11.py` (rename to `build-v12.py` or parameterise); re-pin
   `pins.json` (`lp_inners` unchanged, TAIL hash new); `compiled/manifest.json`,
   `merkle.json` regenerated.
3. Archive the V11.1 hex under `contracts/development/` in the monorepo so every
   fails-before probe keeps running; do not publish the archive (`FORGE_SECURITY.md` scope).
4. Suites: all `_test_v11_*.py` (rename to `_test_v12_*` only when the shapes are final),
   the new `_test_v12_genesis.py` and `_test_v12_oracle.py`, the nine `_test_vault_*.py`,
   `_test_forge_creation_audit.py` ported to V12, `node scripts/run-checks.mjs`,
   `npx tsc --noEmit`. **Skips exit 2.**
5. Mutation sweep `scripts/mutate-v11.py` over the new assertions: `MIN_LP` in prologue and
   remove; `new_total_lp == expected_delta + MIN_LP`; the eve-id announcement; the
   `reserve_ids` length check; `birth >= last_birth`. Each must be killed by a named test or
   documented as unreachable (the swap leaf's comment is the template).
6. Retire V11.1: `normalizeDeploymentIndex` drops protocol-12 batches in both directions;
   clear `.awizard/v11-testnet.json` after a timestamped backup; restart the local host.
7. Deploy: `scripts/deploy-v11-testnet.py registry` at V12, then the launch matrix
   (`v11-lifecycle-matrix.py adds|swaps|collects|removes|observe|multihop|resync`), the
   offer lanes, keyless creation, and one two-generations-in-one-block oracle probe on
   testnet11 to confirm the birth-height condition is consensus there.
8. Docs in `forge-puzzles`: `FORGE_PUZZLE_V12.md` (copy V11, apply F1–F5 text, constants
   table), `FORGE_V11_CLVM_PASS.md` extended with the new asserts and their tests,
   `FORGE_SECURITY.md` "what has been checked" gains the six regressions, `README.md`
   status line.
9. Docs here: `skills/forgePuzzleV11.md` → add a V12 header (or a `forgePuzzleV12.md` and
   demote V11 as V10 was), `FORGE_SECURITY_AUDIT.md` external-review section moves from
   *open* to *closed* with the proof file per finding, `skills/README.md`, `manifest.json`.

---

## 7. The CHIP commits (after step 6 is green)

One commit per finding, in this order, each naming the `forge-puzzles` commit:

| commit | CHIP sections touched |
|---|---|
| F4 units | *Configuration and state* ("basis points"); new *Constants* table; *Rationale → Objections and responses* entry |
| F6 empty spend | *Leaves* sentence; *Test Cases* bullet; objections entry naming the vendored assert and pin |
| F5 reserve ids | *Coin layout*, *Authorization*, *Security* bullet "Reserves are owned by the finalizer"; threat row; objections entry |
| F3 minimum liquidity | *Leaves* `remove` row; *Constants*; objections entry |
| F1 genesis | *Authorization* genesis paragraph; threat row; objections entry |
| F2 oracle | *Configuration and state*; *Motivation* use-case bullet reworded; threat row; *Requires* gains CHIP-0014; objections entry |
| nits | `Comments-URI` → PR #217; "five leaves" → six; *Test Cases* lists the six regressions; *Reference Implementation* points at `FORGE_PUZZLE_V12.md` |

Then re-request review from greimela and post the Discord update.

---

## 8. Definition of done

- every regression above fails on the archived V11.1 build and passes on V12, honest case
  beside it, through consensus validation;
- the mutation sweep reports each new assertion as killed or documented;
- the constants conformance check passes against the V12 spec document;
- twenty pools live on testnet11 at protocol 13 with the lifecycle matrix confirmed, and
  no protocol-12 pool listed;
- the CHIP text describes the built puzzle, commit for commit, and the reviewer has been
  re-requested.
