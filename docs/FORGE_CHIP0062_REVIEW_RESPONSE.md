# CHIP-0062 review — the findings, and how Forge answers them

> **Source.** The review by greimela on [Chia-Network/chips PR #217](https://github.com/Chia-Network/chips/pull/217#pullrequestreview-5177426192)
> (review `5177426192`, "changes requested", against commit `29203bd`), plus the Cursor bot
> finding posted against an earlier commit (`9713658`). Both reviews name the reference
> implementation at `awizardxch/forge-puzzles` as well as the CHIP text.
>
> **Written 2026-09-11** against **V11.1 (protocol 12)**, live on testnet11 with twenty pools.
> Companion: [`FORGE_V12_UPGRADE_PLAN.md`](FORGE_V12_UPGRADE_PLAN.md) is the implementation
> plan that follows from this document. The shipping shape is `skills/forgePuzzleV11.md`; the
> method every fix must follow is `skills/clvmPuzzleAudit.md`.
>
> **Publication note.** The house rule for anything public (`FORGE_CHIP_WORKFLOW.md`) is no
> exploit mechanics for live code. Everything below is limited to what the reviewer has already
> published on the public PR, against a testnet-only revision. Keep it that way when editing.

---

## The verdict in one paragraph

Six findings: one **P0**, four **P1**, and one **High** from the Cursor bot. Five are real
against V11.1. The sixth (empty action spend) is already refused by the pinned upstream action
layer, but the CHIP never says so, and the reviewer could not have known without reading the
vendored source — so it is a specification defect, not a puzzle defect. Two findings are
document-only (fee units, empty spend). **Four need puzzle changes**, and because each touches
the prologue, the state shape, the TAIL or the registry, they are one revision: **V12
(protocol 13)** — a new TAIL, new registry constants, new LP asset ids, a testnet redeploy of
the launch matrix, and retirement of every V11.1 pool. Nothing here is a third-party drain of
an existing testnet pool. The P0 is exploitable by a **pool creator against later depositors**;
the oracle finding by any trader against a future oracle consumer; the terminal-LP finding is a
liveness defect; the reserve-parent finding is a lineage hijack that breaks the accounting the
spec promises. The CHIP should not move to *Review* until all six are closed in code, in the
suites, and in the text — in that order.

---

## How we address a CHIP review

This is the protocol, so that the next review is handled the same way.

1. **Acknowledge on the PR the same day.** One comment on the review thread: a table of the
   findings, our severity reading, the planned fix, and a link to this document. No claim of a
   fix until the suite proves it. Drafts are in the appendix.
2. **Regressions first.** Every finding gets a probe that **fails against the V11.1 build and
   passes against V12**, with the honest case beside it in the same file — the audit skill's
   rule, because a failure for the wrong reason (an arity error after a solution-shape change)
   looks exactly like a fix. The V11.1 hex stays loadable in the monorepo archive so the
   "fails-before" half keeps running; the published `forge-puzzles` copy carries the suites and
   skips with exit 2 where the archived build is absent, as today.
3. **Code before text.** The CHIP says its specification and its reference implementation
   "cannot drift apart". So the CHIP is edited only after the puzzle change is built, pinned and
   green, one commit per finding, each naming the `forge-puzzles` commit it describes.
4. **The objections log.** The CHIP's Rationale promises "each substantive objection raised
   against this draft, and how the design answers it — or, where it does not, why". Add an
   **Objections and responses** subsection with one entry per finding, including the one where
   the design did not change (F6) and the two where the text was wrong (F4, F6).
5. **Security section and threat table** updated for every changed mechanism; "no external
   audit" stays in *Known gaps* — a review is not an audit.
6. **Re-request review** from greimela after the last commit; reply once per thread; leave
   resolution to the reviewer.
7. **Discord.** Post the update in the CNI thread, in the paste-ready form
   `FORGE_CHIP_WORKFLOW.md` uses, once V12 is live on testnet11.

Order of work is dictated by dependencies, not severity: the two document-only findings land
first (they are free), then the four puzzle findings ship together as V12.

---

## Findings at a glance

| # | Reviewer's label | Sev. | Where in V11.1 | Class | Fix in one line | Revision |
|---|---|---|---|---|---|---|
| F1 | Genesis can authorize excess LP | **P0** | `forge_lp_cat_tail.rue` genesis branch (l. 102–114); `forge_registry_register.rue` | authorisation not bound to a coin | the launcher's announcement names the one eve coin id; the TAIL asserts it with its own id | V12 |
| F2 | Oracle backfilling across generations | P1 | `forge_action_common.rue::prologue`; `Oracle` state | spender-chosen time | elapsed time = difference of consensus-verified birth heights (`ASSERT_MY_BIRTH_HEIGHT`) | V12 |
| F3 | Terminal LP position unredeemable | P1 | `forge_action_remove.rue` `burn < total_lp`; prologue `total_lp > 0` | liveness | a counted-but-never-minted minimum liquidity, locked at genesis, registry-enforced | V12 |
| F4 | Protocol-fee unit mismatch | P1 | CHIP "parts per million" vs `protocol_fee_bps` / denominator 10,000 | spec ≠ code | basis points everywhere; normative constants table; rename the misnamed `WEIGHT_SCALE` | text + rename |
| F5 | Reserve receiver derivation trusts solution data | P1 | `forge_multi_reserve_finalizer.rue` `...reserve_parent_ids` (l. 178, receiver at l. 145–149) | solution-supplied identity | reserve coin ids live in state; the finalizer derives receivers and successors from state | V12 |
| F6 | Empty action spend not forbidden | High (bot) | CHIP text; upstream `action.rue` already asserts a non-empty selector list | spec silent | one normative sentence, one probe | text + test |

Severity is the reviewer's. We agree with all six. On F5 we have not been able to construct a
direct extraction of funds, and say so below; it stays P1 because the CHIP's central normative
rule ("MUST NOT be taken from the solution") is false for it and the fix is cheap.

---

## F1 — Genesis can authorize excess LP (P0)

**The reviewer's claim.** The TAIL's genesis branch accepts the singleton launcher's coin
announcement instead of a pool message, and that announcement does not commit to a specific
LP eve coin. Several independently funded eves in the same bundle can each assert the one
announcement and each mint the named supply. Their reproduction: a pool whose state records
5,000,000 LP while two eves minted 10,000,000. Required fix, quoted: *"Bind genesis
authorization to exactly one derived LP eve coin ID. Add a regression test that rejects
duplicate eves."*

**What V11.1 does.** `forge_lp_cat_tail.rue`, genesis branch:

```
AssertCoinAnnouncement {
    id: sha256(launcher_id + tree_hash([action.genesis_pool_puzzle_hash, 1, [action.expected_delta]])),
}
```

plus `!parent_is_cat`, `expected_delta > 0`, `new_total_lp == expected_delta`. Nothing in the
assertion is specific to the coin asserting it. The standard launcher announces
`sha256tree([full_puzzle_hash, 1, key_value_list])` exactly once; with the key-value list fixed
to `[total_lp]` the announcement is unique per launcher, but it is a **puzzle-level** fact, and
any number of one-mojo eves at the LP mint inner can assert it. Each eve runs its own CAT ring,
each ring is backed by `total_lp` of the creator's own mojos (every CAT mojo is an XCH mojo),
and each mints `total_lp` LP with genuine lineage. The registry's `register` asserts the same
announcement, so registration proves the *supply the launcher named*, not the *number of coins
that minted it*.

**Why it matters.** The excess LP is real CAT with a real CAT parent, so the TAIL's melt lock
accepts it. Its holder redeems through `remove`, up to `total_lp − 1` per spend, against
reserves that later depositors contributed. This is the creator-trusted-genesis caveat the
design already carries (`clvmPuzzleAudit.md`, "Permissionless creation is inherently
creator-trusted at genesis"), but the caveat was understood to cost the creator, not the
depositors — a mismatched state makes a pool inert. Unrecorded supply is the opposite: the pool
is live, and the creator holds a claim the state does not show. P0 is right.

**The fix.** Bind the announcement to one coin. The launcher's key-value list becomes
`[total_lp, eve_coin_id]`, and the TAIL asserts the announcement using **its own coin id from
the CAT truths** (`my_coin_id`, the second element of the CAT2 truth structure the TAIL already
walks in `cat_my_amount`):

```
AssertCoinAnnouncement {
    id: sha256(launcher_id + tree_hash([action.genesis_pool_puzzle_hash, 1,
                                        [action.new_total_lp, cat_my_coin_id(truths_any)]])),
}
```

A launcher announces one list, so exactly one eve id is authorised; a second eve has a
different id, computes a different announcement id, and is refused. The registry's `register`
asserts the same announcement, so its solution gains `eve_parent_id` and it derives the eve id
the way the `add` leaf already does — `lp_action_coin_id(config, eve_parent_id,
LP_MINT_INNER_HASH, 1)` — which additionally proves the registered eve wraps the pinned mint
inner. The creation path already knows the eve's id before it builds the launcher spend
(`forge_v11_create.plan` constructs `Coin(xch.coin.name(), eve_ph, 1)` first), so the driver
change is the key-value list and one solution field.

*Alternatives considered.* Making the eve a child of the launcher: the standard launcher
creates exactly one coin, so this needs a custom launcher and loses the singleton's standard
lineage. Minting genesis through the pool's first spend (eve state `total_lp = 0`, a first
`add`): the prologue asserts `total_lp > 0` and the mint bracket is degenerate at zero supply;
it would need a genesis branch in the most-probed leaf. Both rejected.

**Tests** (`_test_v11_create.py`, `_test_v11_registry.py`, and a new `_test_v12_genesis.py`):

- honest genesis with one eve is accepted (exists);
- **two eves, each one mojo at the mint inner, both asserting the launcher's announcement, in
  one bundle: refused** — the regression the reviewer asked for; it must be *accepted* by the
  V11.1 build;
- an eve whose id is not the one the launcher named: refused;
- a registration whose `eve_parent_id` does not match the launcher's announcement: refused;
- the genesis mint of one LP more than the launcher named: refused (exists).

**Spec text.** *Authorization*: "The genesis mint is authorised by the launcher's creation
announcement, whose key-value list names the total supply **and the id of the single eve coin
permitted to mint it**; the TAIL asserts that announcement with its own coin id, so one
launcher authorises exactly one eve. The registry asserts the same list." Threat table: add
"Genesis supply minted by more than one coin | the launcher names one eve id; the TAIL asserts
with its own".

---

## F2 — Oracle backfilling across generations (P1)

**The reviewer's claim.** The same-height guard covers the leaves of one action-layer spend
only. Spending the pool at two different heights inside one bundle (two generations, one
block) lets the attacker report elapsed blocks at a price the same bundle set. Their
reproduction: 31 blocks recorded at a manipulated price at a single actual height. Required fix,
quoted: *"Bind elapsed time to actual coin birth heights across singleton generations. If the
puzzle cannot enforce that relationship, remove the oracle from this proposal."*

**What V11.1 does.** The prologue takes `h` from the solution, asserts `h > last_height`,
emits `ASSERT_HEIGHT_ABSOLUTE h` and `ASSERT_BEFORE_HEIGHT_ABSOLUTE h + oracle_window` (32),
and accumulates `cums += spot(pre-spend reserves) × (h − last_height)`. The pre-spend rule
makes a spend unable to move the price *and* record it in the same spend. But `h` is the
spender's choice anywhere in a 32-block window, and a successor coin can be spent in the block
it was born in. Generation g moves the price and records honestly; generation g + 1, in the
same block, names an `h` up to 31 higher and records the moved price for 31 blocks; generation
g + 2 moves it back. The accumulator now carries 31 blocks of a price that existed for zero
blocks.

**Why it matters.** No oracle consumer exists yet, so no funds are at risk today. But the CHIP
lists the oracle as a use case and the threat table claims "oracle manipulation within one
spend" is addressed — which is true and beside the point. A TWAP that can be filled at a price
the filler chose is worse than no TWAP, because someone will build on it.

**The fix — accumulate on birth heights, one generation lagged.** Chia's consensus knows
exactly when a coin was born, and CHIP-0014 exposes it: `ASSERT_MY_BIRTH_HEIGHT` (opcode 75)
fails unless the named height is the spent coin's birth height. Every generation of the pool
is a coin, so every interval during which a set of reserves was in force has two
consensus-verified endpoints: the birth of the coin holding those reserves and the birth of its
successor. The puzzle cannot know the second endpoint while it is being spent, but it knows it
at the *next* spend. So the accumulator lags one generation:

- state carries `oracle = { last_birth, last_spots[N−1], cums[N−1] }`;
- the prologue takes `birth` from the solution and emits `ASSERT_MY_BIRTH_HEIGHT birth`;
- it accumulates `cums += last_spots × (birth − last_birth)` — the spot prices of the
  *previous* generation, weighted by exactly the blocks that generation existed;
- then stores `last_birth = birth` and `last_spots = spot(pre-spend reserves)` for the next
  spend to weight.

Two generations in one block have the same birth height: the manipulated generation is
weighted by zero. A moved price gets weight only for the blocks it survived on chain, exposed
to arbitrage the whole time. This is the relationship the reviewer asked for, enforced by
consensus rather than by the puzzle's opinion of the height. The `h` height pin and the
32-block window exist only to serve the old accumulator and are removed; the ephemeral
same-value rule across actions in one spend stays, carrying `birth`. Genesis opens with
`last_birth = 0` and zero spots, so the first interval contributes nothing — stated in the
spec. An observation slot then holds `(last_birth . cums)`, and a consumer computes
`(cum_b − cum_a) / (birth_b − birth_a)`.

*Cost.* One condition per spend, `N − 1` extra integers of state, and a real testing cost: the
in-memory harness validates conditions without coin records, so the backfill probe needs
blocks. `chia.clvm.spend_sim` (in `chia-blockchain`) farms them; a new `_test_v12_oracle.py`
runs on it. The driver reads the pool coin's `confirmed_block_index` instead of the peak.

*Fallback.* If the birth-height accounting is judged too large for this revision, take the
reviewer's alternative: delete the oracle (`Oracle`, `price_scale`, `oracle_window`, the
`observe` leaf and its slot), drop the use-case bullet and the threat row, and re-propose it as
its own revision. Recommendation: **fix it**; it is the one feature that makes a pool usable
by other puzzles, and the fix is a contained change to the prologue.

**Tests.**

- prologue conditions carry `ASSERT_MY_BIRTH_HEIGHT birth` and no height pin (unit, existing
  harness);
- a `birth` that is not the coin's birth height is refused by the mempool (`spend_sim`);
- two honest spends two blocks apart accumulate exactly `spot(R_1) × (B_2 − B_1)`;
- **two generations in one block: the second adds zero weight at the first's price** — the
  regression; against V11.1 the same sequence records `oracle_window − 1` blocks;
- the three-action manipulation suite still values the actor at pre-sequence prices.

**Spec text.** *State*: "the oracle accumulator with the birth height of the current coin and
the spot prices in force since it". *Threat table*: replace the oracle row with "Oracle
manipulation within one spend or across generations in one block | elapsed time is the
difference of consensus-verified birth heights (CHIP-0014 `ASSERT_MY_BIRTH_HEIGHT`); a price is
weighted only by the blocks it survived". Add CHIP-0014 to *Requires*.

---

## F3 — Terminal LP position unredeemable (P1)

**The reviewer's claim.** `burn < total_lp` forbids burning the remaining supply, so the last
holder can never fully exit and a pool at `total_lp = 1` is locked. Required fix, quoted:
*"Add a terminal close path. Alternatively, define a bounded minimum-liquidity amount, lock it
deliberately at genesis, and enforce that invariant during registration."*

**What V11.1 does.** `remove` asserts `burn < p.state.total_lp`; the prologue asserts
`total_lp > 0`; the TAIL asserts `new_total_lp >= 0`. The rule exists so every reserve stays
positive and the invariant stays defined — a pool at zero reserves has a zero product and
`exact_swap_output` divides by it. The cost of that rule is that the last unit of LP, and its
pro-rata share of every reserve, is trapped, and nothing in the design says so or bounds it.

**The fix — count a minimum liquidity that is never minted.** Uniswap V2 burns its first 1,000
LP units to the zero address; the effect is that no holder can take the pool to empty, and the
locked value is negligible for any real pool. Forge can do the same without a coin: the genesis
state's `total_lp` **includes** `MIN_LP` units that the eve does not mint. The invariant, the
mint bracket and the withdrawal share all run on `total_lp`, so those units own a pro-rata
share of every reserve for the life of the pool, and:

- `remove` asserts `burn <= total_lp − MIN_LP` (the pool always keeps `MIN_LP` outstanding);
- the prologue asserts `total_lp >= MIN_LP`;
- the TAIL's genesis branch asserts `new_total_lp == expected_delta + MIN_LP`, so the state's
  supply and the minted supply differ by exactly the lock;
- the registry's `valid_pool` asserts `total_lp >= MIN_GENESIS_LP`, which **bounds** the lock
  as a fraction of the creator's deposit — with `MIN_LP = 1_000` and
  `MIN_GENESIS_LP = 1_000_000` the lock is at most 0.1 % of genesis liquidity.

The last real holder then exits with `burn = total_lp − MIN_LP` and receives
`reserves × burn / total_lp`, which is everything but the lock. There is no coin to hint, no
burn address, and no path that can ever spend the locked share. Vaults: the lock is in LP
units, so a vault's creator chooses `lpRatio` and genesis supply knowing `MIN_LP` units are
theirs to lose; the registry floor makes it at most 0.1 % whatever the ratio.

*Alternative considered.* A terminal `close` leaf that burns the whole supply, pays every
reserve out, and melts the singleton. It needs the finalizer to skip recreation, the reserves
to skip theirs, and the registry to tolerate a dead key; that is new logic in the one puzzle
whose correctness everything rests on, for a case the minimum lock makes unnecessary.
Rejected for V12; a later revision can add it as a leaf if a use case appears.

**Tests** (`_test_v11_actions.py` remove section; `_test_v11_registry.py`):

- a remove leaving exactly `MIN_LP` outstanding is accepted and pays the full pro-rata share;
- a remove leaving `MIN_LP − 1` is refused; against V11.1 a remove to `total_lp = 1` is
  accepted and the next remove is impossible — the regression;
- a genesis with `total_lp < MIN_GENESIS_LP` is refused by the registry;
- the TAIL refuses a genesis mint of `total_lp` (it must be `total_lp − MIN_LP`).

**Spec text.** *Leaves*, `remove`: "Requires the burn to be positive and to leave at least
`MIN_LIQUIDITY` LP outstanding. `MIN_LIQUIDITY` units are counted in total LP at genesis but
never minted; their pro-rata share of every reserve is locked for the life of the pool, which
is what keeps every reserve positive and the invariant defined. A pool MUST open with at least
`MIN_GENESIS_LP` total LP, which the registry enforces, bounding the lock at 0.1 % of genesis
liquidity." Name both constants in the constants table (F4).

---

## F4 — Protocol-fee unit mismatch (P1)

**The reviewer's claim.** The CHIP specifies the protocol fee in parts per million
(denominator 1,000,000); the reference code uses basis points (denominator 10,000) —
`forge_curve.rue` l. 235–237. A value of 5 means 5 ppm in the text and 5 bps in the puzzle, a
100× disagreement. Required fix, quoted: *"Choose one unit, denominator, and maximum. State them
normatively and use the same names in the implementation."*

**What V11.1 does.** The puzzle is consistent with itself: `fee_bps`, `protocol_fee_bps`,
`dao_fee_bps`, all over `WEIGHT_SCALE = 10000`, with caps 200 / 100 / 100. The CHIP's
*Configuration* section says "the trade fee in basis points, the protocol fee in parts per
million". The "ppm" is inherited: `FORGE_PROTOCOL_STATUS.md` records that the frontend's
`protocolFeePpm` field is vestigial from a pre-V8 design, and the CHIP text picked it up.
`WEIGHT_SCALE` is itself misnamed — weights have been integer units since V7; the constant
scales fees.

**The fix.** Basis points, everywhere, by name:

- CHIP: "the protocol fee in basis points"; a normative **Constants** table —
  `fee_bps ∈ [0, MAX_FEE_BPS = 200]`, `protocol_fee_bps ∈ [0, MAX_PROTOCOL_FEE_BPS = 100]`,
  `dao_fee_bps ∈ [0, MAX_DAO_FEE_BPS = 100]`, denominator `BPS_DENOMINATOR = 10_000`; the
  formulas `effective_in = gross × (10000 − fee_bps) / 10000`,
  `protocol_slice = floor(claimed × protocol_fee_bps / 10000)`,
  `dao_slice = floor(claimed × dao_fee_bps / 10000)`, both on the gross claimed output,
  independently floored; plus `MIN_LP`, `MIN_GENESIS_LP` (F3) and the existing
  `MIN_ASSETS … MAX_TOTAL_WEIGHT`.
- Code: rename `WEIGHT_SCALE` to `BPS_DENOMINATOR` in `forge_curve.rue`. An inline constant
  rename does not change compiled hex, and the curve-equivalence suite proves it.
- A conformance check in `_test_v11_integrity.py`: read the constants table out of the
  specification document and compare each name and value with the compiled constants, so the
  text cannot drift again.

Lands before V12 (the rename is free; the CHIP commit can go now).

---

## F5 — Reserve receiver derivation trusts solution data (P1)

**The reviewer's claim.** The finalizer accepts `reserve_parent_ids` from its solution and
uses them in `coinid(...)` without the pool committing to or authenticating them, so an
attacker-created reserve can become the successor. Required fix, quoted: *"Commit the reserve
parent or full coin ID in pool state, or prove its lineage before deriving the receiver."*

**What V11.1 does.** `forge_multi_reserve_finalizer.rue` takes `...reserve_parent_ids` as its
solution and sends each reserve's message to `coinid(parent_id, full_hash_i,
amount_program(initial_state, i))`. The puzzle hash and the amount come from curried and
committed values; the parent does not. The source comment says a wrong parent "produces a
receiver that exists nowhere and fails the bundle; it cannot misdirect funds". That is true
only if no other coin exists at that puzzle hash with that amount — and anyone can create one.
The V10 design kept `reserve_coin_id` in state; V11 dropped it ("reserve coin ids leave the
state; the finalizer derives them"), and the derivation leaned on the solution.

**What we can and cannot establish.** An impostor must be a genuine coin at the reserve's
full puzzle hash — real mojos for XCH, a real CAT of the asset for a CAT reserve — holding
exactly the pre-spend amount; it costs the attacker that amount. Once adopted, the impostor's
lineage becomes the tracked reserve and the genuine reserve is orphaned: still at the pool's
puzzle hash, still spendable only on a pool message, but unreachable until the state amount
coincides with it again, at which point whoever supplies its parent flips the tracked lineage
and orphans the other. Funds do not leave the pool's puzzle hashes, and we have not built a
sequence that nets the attacker more than they put in. What breaks is everything the state is
supposed to mean: the coin set and the state diverge, an honest router following the wrong
lineage builds bundles that fail, LP holders' pro-rata claims run against a tracked coin that
may not be the one holding the deposits, and the CHIP's "receiver ids MUST NOT be taken from
the solution" is false for the largest authorisation in the design. P1 stands on that alone.

**The fix — reserve coin ids in state, successors derived.** `ForgeState` gains a trailing
field `reserve_ids: List<Bytes32>`. The finalizer:

- takes each receiver from `Truth.State.reserve_ids[i]` — the truth, never the solution;
- commits `successor_i = coinid(reserve_ids[i], full_hash_i, amount_program(new_state, i))`
  into the state it recreates the singleton with (the reserve creates its own successor, so
  the parent is the reserve itself);
- discards whatever the leaves returned in that field, so no leaf can rewrite it;
- drops the `...reserve_parent_ids` solution entirely.

The leaves pass the field through untouched (a copy in each `ForgeState` literal; the
prologue asserts its length). The registry's `register` takes the creator's funding parents
in its solution and derives the genesis `reserve_ids[i] = coinid(parent_i, full_hash_i,
reserves[i])` into `eve_state_hash`, which means a registered pool's genesis reserves are
either coins at the correct reserve puzzle hashes or coins that do not exist — never a puzzle
the creator controls. The trailing position keeps every index-based reader stable (the audit
skill's positional-rot rule). The LP message's `next_state_root` is computed by the leaf and
therefore commits the leaf-level state, whose `reserve_ids` are the pre-spend ids; the
successor's committed state carries the derived ids, which are a deterministic function of the
truth. That is stated in the spec rather than left to be discovered.

*Alternative considered.* "Prove its lineage before deriving the receiver": the reserve puzzle
is the pinned upstream `p2_delegated_by_singleton`, which asserts nothing about its parent, and
editing it moves it into the audit's scope. Rejected.

**Tests** (`_test_v11_finalizer.py`, plus the resync and snapshot round-trip suites):

- honest N = 2 and N = 10 accepted; successor ids in the new state equal the coins the bundle
  created (the harness's `additions`);
- **an impostor coin at reserve i's puzzle hash with the pre-spend amount, present in the
  bundle while the genuine reserve is absent: refused** (the message pairs with no spent coin,
  consensus error 147). Against V11.1, the same bundle with the impostor's parent in the
  finalizer solution is accepted — the regression;
- a passthrough test action that returns a state with rewritten `reserve_ids`: the committed
  state carries the derived ids, not the leaf's;
- `pool_to_snapshot` / `snapshot_to_pool` and `forge_v11_resync.py` round-trip the ids and
  re-derive the pool coin.

**Spec text.** *Authorization*: "The pool's state commits the coin id of every reserve. The
finalizer sends each reserve's message to that id and commits each successor's id into the
successor state, derived from the reserve's own id, its curried puzzle hash and its new
amount. No reserve identity is taken from the solution." Update the *Coin layout* bullet and
the `FORGE_PUZZLE_V11.md` sentence "No puzzle takes an authorizing coin id from its own
solution", which is currently untrue for the finalizer.

---

## F6 — Empty action spend not forbidden (High, Cursor bot)

**The bot's claim.** The design never requires the inner puzzle to run at least one leaf; a
prior CHIP-0050 attempt to block no-action spends failed review.

**What V11.1 does.** The vendored upstream action layer (`puzzles/upstream/action.rue`,
pinned by hash in `pins.json` and recompiled on every integrity run) begins `main` with
`assert !(selectors_and_proofs is nil)`. An empty spend is refused before any leaf or the
finalizer runs, so every spend runs the prologue. CHIP-0050's text does not state this rule
(grep of `chip-0050.md` finds no mention); its reference implementation enforces it. The bot
reviewed the CHIP text, which is silent, and the CHIP's own "Test Cases" do not list a probe.

**The fix.** No puzzle change. One probe in `_test_v11_actions.py` — a spend with an empty
selector list, validated through consensus, refused — and one normative sentence in
*Leaves*: "A spend MUST run at least one leaf. The action layer refuses an empty selector
list, so every spend runs the prologue and no spend can recreate the pool and its reserves
without an action." Name the vendored source line and pin in the objections log so the next
reviewer does not have to find it.

---

## What the six findings mean together

- **One revision, not four.** F1 changes the TAIL (new LP asset ids per pool), F3 changes the
  TAIL and the registry, F5 changes the state shape and the registry's eve-state hash, F2
  changes the prologue and config. Every V11.1 pool on testnet11 is retired and the launch
  matrix is redeployed at V12, exactly as V10 → V11 was done.
- **The mutation sweep is part of the definition of done.** F5's finalizer comment and the swap
  leaf's defence-in-depth block both show the project already distinguishes load-bearing
  assertions from belt-and-braces; every new assertion above must be killed by a named test
  or documented as redundant.
- **Two findings were in claims, not code** (F4, F6). The fix for those is a conformance check
  and a probe, so that the text can never again say something the hex does not do.
- **Genesis trust is narrower than we said.** F1 turns "a creator can only hurt themselves" into
  "a creator could hold unrecorded supply". After V12 the statement is true again, and it should
  be re-probed the way `_test_forge_creation_audit.py` did at V10: the creator cannot withdraw
  more than they deposited, by any sequence.

## Decisions taken in the plan (change them there if you disagree)

| Decision | Chosen | Why |
|---|---|---|
| Oracle: fix or remove | **fix** (birth-height accumulation), removal as fallback | the feature is the design's one hook for other puzzles; the fix is contained |
| `MIN_LP`, `MIN_GENESIS_LP` | **1,000 and 1,000,000** | Uniswap V2's figure; the floor bounds the lock at 0.1 % of genesis liquidity |
| Fee unit | **basis points**, denominator 10,000 | the code, every driver and the frontend already use it; the CHIP is the outlier |
| Reserve identity | **coin ids in state**, trailing field | V10 had it; the finalizer stays generic except for one struct |
| Height pin `h` and `oracle_window` | **removed** with F2 | they served only the old accumulator; an offer's expiry belongs to the offer |

## Nits in the CHIP to fix in the same pass

- `Comments-URI` links to PR #192; it should link to PR #217.
- *Abstract* lists six leaves; *Reference Implementation* and one *Rationale* paragraph say
  "the five leaves". Six.
- Add CHIP-0014 to *Requires* once F2 lands.
- *Test Cases*: add the six regressions above by name.

---

## Appendix — PR reply drafts

**On the review (one comment):**

> Thank you — all five are accepted, and the Cursor finding with them. F4 (units) and F6
> (empty spend) are text defects: the puzzle uses basis points throughout and the pinned
> upstream action layer refuses an empty selector list; both get a normative sentence, a
> conformance check and a probe. F1, F2, F3 and F5 are puzzle changes and ship together as
> the next revision: the launcher's announcement will name the one eve coin id and the TAIL
> will assert it with its own; elapsed oracle time will be the difference of
> `ASSERT_MY_BIRTH_HEIGHT` values across generations; a counted-but-never-minted minimum
> liquidity, registry-bounded, replaces the bare `burn < total_lp`; and reserve coin ids
> return to state so the finalizer derives receivers and successors from the truth. Each
> comes with a regression that fails on the current build. I will push the CHIP edits after
> the revision is built and green, one commit per finding, and re-request review then. The
> working document is linked.

**Per thread, after the fix commit:** one line naming the mechanism, the `forge-puzzles`
commit, the test that fails-before/passes-after, and the CHIP commit.
