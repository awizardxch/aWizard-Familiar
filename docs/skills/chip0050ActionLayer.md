# Skill: CHIP-0050 Action Layer — the V11 candidate

> Reference for CHIP-0050 (Action Layer and Slots) and the evaluation of building Forge V11 on it.
> Written 2026-09-04 while V10 is on testnet11 and V11 has not started.
>
> **The rule being tested.** Forge adopts the CHIP-0050 methods *if* they are more secure with
> fewer points of exploit over the long term. This file is the check. The surface count below
> says the rule holds, with two conditions: V11 launches with a single-action guard, and the
> Forge-written finalizer is reviewed to the same standard as the upstream pieces. Under those
> conditions the recommendation is to adopt. **Adoption is a recommendation, not a decision, until
> the protocol owner confirms it.**
>
> **Nothing in V11 exists yet. Nothing is audited.** The upstream components are reviewed and on
> mainnet; the Forge actions and the multi-reserve finalizer are new code until proven otherwise.

---

## Domain

Load this when the quest touches V11 design, the multi-reserve finalizer, action puzzles, slots,
or any question of "how does CHIP-0050 do this compared to V10". For the V10 shape you are
migrating from, `forgePuzzleV10.md`. For how the result gets audited, `clvmPuzzleAudit.md`, which
this file extends with the action-layer checks. For the LP CAT, which does not change,
`forgeLpCat.md`.

---

## What CHIP-0050 is

| | |
|---|---|
| Title | Action Layer and Slots |
| Author | yakuhito. Status **Final**, Informational / Puzzle, created 2025-07-22 |
| Text | `github.com/Chia-Network/chips/blob/main/CHIPs/chip-0050.md`, discussion in CHIPs PR #165 |
| Reference puzzles | `github.com/Yakuhito/slot-machine`, `rue-puzzles/singleton/`, pinned at commit `2d37ba1014e14220c26a0541b5d3199f9d15ec21` — the commit the CHIP itself links |
| Drivers | `chia-wallet-sdk` (crates `chia-sdk-types` and `chia-sdk-driver`, checked at 0.36.0): `ActionLayer`, `Reserve`, `P2DelegatedBySingletonLayer`, `DefaultFinalizer`, `ReserveFinalizer` |
| Language | Rue, the same language as the Forge puzzles |
| In production | CATalog, XCHandles, the Reward Distributor (CHIP-0051) |

The CHIP is a framework for the four things every dApp singleton needs: several callable
functions, several calls per spend, persistent state, and reserves. It is explicitly optional and
explicitly **not a security sandbox** — the CHIP says apps must audit their own actions and any
custom finalizer.

### The components and their contracts

**Action layer** (`action.rue`) is the singleton's inner puzzle.

```
curried:  FINALIZER, MERKLE_ROOT, STATE
solution: puzzles, selectors_and_proofs, solutions, ...finalizer_solution
```

`MERKLE_ROOT` commits to the set of action puzzles that may ever run. Each spend reveals the
actions it uses with a merkle proof; a second use of the same action in one spend references the
first reveal by index instead of re-hashing it. Actions run in order and thread two states:

```
action solution:  ((ephemeral_state . state) . user_solution)
action returns:   ((new_ephemeral . new_state) . conditions)
```

`state` is persistent — curried into the next singleton. `ephemeral_state` starts as `()` every
spend and is passed action to action, then discarded. It is the only way an action can know
whether it is first in the spend, which matters for anything relative.

**Finalizer** runs once after the last action. Its contract, fixed by `action.rue`:

```
FINALIZER(FinalizerTruths { Merkle_Root, State },      // State = pre-spend state
          (final_state_truth, list_of_condition_lists), // output of the action chain
          ...finalizer_solution)
```

The **default finalizer** re-creates the singleton at
`curry(ACTION_LAYER, curry(FINALIZER_SELF, self_hash), MERKLE_ROOT, new_state)` with amount 1 and
flattens the conditions through. The singleton puzzle hash therefore changes on every spend,
exactly as V10's does.

The **reserve finalizer** does the same and additionally manages **one** reserve:

- the reserve amount is read from state by a curried program, default `(f state)`
- any action can emit a condition *for the reserve* by prefixing it with the opcode `-42`
- the finalizer strips those, prepends `CREATE_COIN(RESERVE_INNER_PUZZLE_HASH, new_amount)`, and
  sends `SEND_MESSAGE` (mode: sender puzzle, receiver coin) carrying the tree hash of that quoted
  delegated puzzle to `coinid(reserve_parent_id, RESERVE_FULL_PUZZLE_HASH, old_amount)`
- `reserve_parent_id` is the finalizer's solution; a wrong value points the message at a coin that
  does not exist and the bundle fails, so it cannot misdirect funds

**Reserve coin** is a plain CAT (or bare XCH) wrapping `p2_delegated_by_singleton`:

```
curried:  SINGLETON_MOD_HASH, SINGLETON_STRUCT_HASH, NONCE
solution: singleton_inner_puzzle_hash, delegated_puzzle, ...delegated_solution
emits:    RECEIVE_MESSAGE(sender puzzle = the controlling singleton, message = hash(delegated_puzzle))
          ...delegated_puzzle(delegated_solution)
```

It has no logic of its own. The message is what makes it safe: the coin only ever runs the exact
delegated puzzle whose hash its controlling singleton sent it, and the receiver coin id already
commits to parent, puzzle hash and amount.

**Slots** are 0-mojo coins the singleton creates to park rarely-read values (a position, an order,
a handle). Only the owning singleton can spend one, via a message. Not needed for the CFMM;
needed for perps and the CLOB, which is why the perps plan already cites this CHIP.

### Upstream tree hashes (chia-sdk-types 0.36.0)

Pin these in the integrity test so a Forge build can never silently drift from the reviewed
puzzles.

| puzzle | tree hash |
|---|---|
| action layer | `afa03f2903f9e4a293523237799074b13ab2361f250df10de5df884b0b09a22b` |
| default finalizer | `9d274de59aeaa128d1b0a802b52911838420ef9720d605c78942e8dadfc0810b` |
| reserve finalizer | `5b406eb66d10998027924c9bdea4254966e27ca765a8992227f826cb0e868095` |
| p2_delegated_by_singleton | `3f2358e5141470a084ab2f68126f6f07269f01a690994f364e67c9624bb6e05e` |
| slot | `8ab9f3b57a65d7f7a0810f79f7bc1e96bda680d16dd6f51d51e868e13fc7bbb3` |

### What does not exist upstream

**There is no multi-reserve finalizer.** The reserve finalizer manages exactly one reserve, and
chia-sdk 0.36.0 ships only `DefaultFinalizer` and `ReserveFinalizer`. The SDK's `Reserveful`
trait takes a reserve index, which shows multiple reserves were anticipated, but every caller
passes index 0. yakuhito confirmed the same in conversation: the reserve finalizer is the
template and the N-reserve version has to be built. That finalizer is the one piece of V11 that is
both new and holds every reserve, so it gets the deepest review.

---

## V10 versus the CHIP — where they differ

V10 and CHIP-0050 made opposite structural choices, and TibetSwap sits on the CHIP side of each.

| | V10 | CHIP-0050 |
|---|---|---|
| Dispatch | one 897-line inner puzzle with a `mode` integer | merkle tree of small action puzzles |
| Actions per spend | one | many, from one or several users |
| Persistent state | curried `[reserves, total_lp]` | curried `STATE`, same idea |
| Spend-local context | none | ephemeral state |
| Reserve puzzle | custom, curried with `launcher_id`, checks itself | generic `p2_delegated_by_singleton`, trusts the singleton |
| Reserve binding | puzzle announcement rebuilt in-puzzle, coin announcement back | `SEND_MESSAGE` / `RECEIVE_MESSAGE` with sender-puzzle and receiver-coin modes |
| Reserve payouts | the reserve creates the settlement and fee coins from a plan it re-verifies | the finalizer relays `-42`-tagged conditions; the reserve runs them |
| Two or more reserves | native | not supported by any published finalizer |
| Puzzle reveal per spend | whole inner puzzle | action layer plus only the actions used |
| Tooling | Forge's own Python and TS drivers | `chia-wallet-sdk` drivers, reviewed and tested |
| Rarely-read data | not needed | slots |

The V10 reserve fix is the same binding the CHIP gets from the `SINGLETON_STRUCT_HASH` curry plus
a message. V10 arrived there by hand after V4–V9 shipped without it; the CHIP had it from the
start.

---

## The surface count — does "fewer points of exploit" hold?

Counted from the V10 sources, not estimated. Forge owns 1,248 lines at V10. About 530 are
binding and recreation glue — plan validation, coin-id and puzzle-hash checks, announcement
hashing, and the entire reserve puzzle. About 500 are curve, LP and fee logic. The exploitable
surface is the set of solution inputs and trust links that need a Forge-written check to be safe:

| V10 surface | count | in the findings log |
|---|---|---|
| Pool solution fields needing a binding: `mode`, `current_pool_coin_id`, 8 `ReservePlan` fields per reserve, `lp_action_coin_id`, `lp_delta`, `lp_parent_id` | 13 | the LP-burn critical was `lp_action_coin_id` |
| Reserve solution fields: `asset_id`, `reserve_inner_puzzle_hash`, `pool_inner_puzzle_hash`, `plan` | 4 | the reserve critical was all four |
| Hand-rolled announcement links: pool→reserve, reserve→pool, pool↔LP TAIL, reserve→settlement | 4 | each a `sha256(id + message)` with a domain separator |
| Curve and LP checks | unchanged in both designs | the V9 fabricated-melt and vault-redemption defects |

Every third-party-reachable fund-loss finding sits in the first three rows. None sits in the
fourth.

| V11 surface | count | why |
|---|---|---|
| Action solution fields: swap 5, add ~4, remove ~3 — the curve inputs only | ~12 | no coin ids, successor ids, successor puzzle hashes or pool identity exist in any solution; reserve identity comes from the curried puzzle hash, the pre-spend amount in state, and a parent id that can only be right or fail the bundle |
| Forge-written binding checks | ~4 | LP action coin id derivation, settlement assertion, LP TAIL handshake, tag index range |
| Upstream-written binding checks | N messages + merkle proofs | reviewed code; Forge pins the hashes and never edits it |
| New Forge component: the multi-reserve finalizer | 1 (~120 lines) | holds every reserve; the one place that needs upstream-grade review |
| Multi-action state threading and sequencer ordering | 0 at launch | each action asserts the ephemeral state is empty and sets it — this restores V10's one-action-per-spend property at the puzzle level until batching is wanted |

Net: Forge-written binding checks fall from about 21 to about 4, one exploit class disappears
outright (a reserve-only bug, which is what V4–V9 had, cannot exist because the reserve puzzle
contains no Forge code), and the binding primitive is stronger. The curve and LP surface is
identical in both designs, the off-chain bearer-offer surface is untouched, and the migration
itself is the largest near-term risk — V9 showed that rewrites ship bugs, which is why the curve is
ported, not rewritten, and the existing adversarial suites carry forward.

So the rule holds on the glue, is neutral on the maths, and costs one re-audit cycle. Long term,
the upstream components are reviewed, on mainnet in three apps, and are what the TibetSwap
successor is built on, so auditors and tooling converge there. Pool puzzles are immutable in both
designs, so an upstream bug would hit V11 pools exactly as a Forge bug hits V10 pools; neither
has an upgrade path.

---

## Why the CHIP model is the more secure one

1. **Review pedigree.** The action layer, both finalizers, the slot puzzle and
   `p2_delegated_by_singleton` were reviewed by several community members and run on mainnet in
   three apps. V10 is internally audited only and has never left testnet.
2. **No solution surface on the reserve.** Every V10 reserve critical came from a
   solution-supplied value that constrained nothing: the launcher id, the pool coin id, the
   successor puzzle hash. The CHIP reserve's solution is the singleton inner puzzle hash and the
   delegated puzzle, and the message verifies both. There is nothing left in it to lie about.
3. **Messages, not announcements.** V10 binds with `sha256(puzzle_hash + message)` and hand-rolled
   domain separators like `forge-reserve-plan-v4`. `SEND_MESSAGE` binds sender puzzle hash and
   receiver coin id through mode bits, with no concatenation to get wrong and no cross-type
   collision to defend.
4. **Fewer trust roots.** V10 correctness is spread across a pool puzzle and a reserve puzzle that
   must agree. In V11 the curve library, three actions and one finalizer are the only code that
   matters, and the merkle root guarantees nothing else can ever run.
5. **Reviewable in pieces.** Three actions of a few hundred lines each audit in isolation. The
   V10 audit found the same curve in four implementations, three weight-blind; splitting by action
   makes that drift visible instead of buried in a mode switch.

What V11 gives up, or adds as new risk:

- **The reserve no longer checks itself.** V10's reserve asserts its own id, amount and puzzle
  hash and re-verifies the plan hash. The CHIP reserve does none of that. It is not weaker in the
  composed system, because the message receiver's coin id commits to all three, but it is a single
  point of trust. If the singleton is wrong, nothing downstream catches it.
- **The finalizer is the drain point.** About a hundred lines Forge writes, holding every
  reserve. Small and formulaic, and unreviewed until reviewed.
- **Multi-action semantics are new surface.** Two swaps in one spend must thread state; relative
  conditions become spend-scoped; a sequencer ordering user actions is a sandwich vector inside
  one spend. Offer-based settlement already enforces each trader's minimum output, which contains
  it, but it must be reasoned about explicitly and tested.
- **Slots can be forged** by spending and re-creating the same value in one spend unless values
  carry a nonce. Irrelevant until slots are used.

---

## V11 target design

### Coin layout

```
singleton_top_layer_v1_1
        |
action layer (FINALIZER = forge multi-reserve finalizer, MERKLE_ROOT, STATE)   <- 1 mojo
   /      |       \
reserve reserve   LP CAT     <- one reserve coin per asset, CAT(asset, p2_delegated_by_singleton)
```

The reserve nonce is the **asset index** in the pool's sorted asset list, so two reserves of the
same pool never share a puzzle hash and a message can never satisfy the wrong one. XCH reserves
are bare `p2_delegated_by_singleton`; CAT reserves wrap it in the CAT layer.

### State

`STATE = [[amount_0, amount_1, ...], total_lp]` in asset-index order. The reserve coin ids drop
out of the state: V10 tracked them so the pool could name the coin it authorised, and in V11 the
finalizer derives each coin id from the parent id in its solution, the reserve's full puzzle hash
and the old amount. Pool config (asset ids, weights, fee bps, protocol fee and recipient, LP TAIL
hash) stays curried into each action puzzle, so it is committed by the merkle root.

### Actions

Exactly three leaves in the merkle tree, and no upgrade action in V11.

| action | solution (after the state truth) | must enforce |
|---|---|---|
| `swap` | `asset_in, asset_out, gross_input, claimed_output, settlement_puzzle_hash` | `exact_swap_output` bracketing on the traded pair, all other reserves frozen, protocol fee derived and paid as a second output |
| `add` | `deposits per asset, lp_delta, lp_parent_id, settlement info` | `non_decreasing_with_increase`, `exact_invariant_lp_mint`, imbalance fee, derived LP action coin id, `lp_delta > 0` |
| `remove` | `burn, lp_parent_id, settlement info` | `burn < total_lp`, `exact_withdrawal` strictly proportional, derived LP action coin id |

Each action returns the next state and its conditions. Every condition that must be executed by a
reserve is tagged `(-42 index . condition)` — the reserve index goes inside the tag because one
opcode cannot address N coins. Conditions for the singleton itself (LP announcements, assertions
of the offer settlement announcements) are untagged.

The curve functions move out of the pool puzzle into a shared Rue module used by all three
actions: `exact_swap_output`, `exact_invariant_lp_mint`, `exact_withdrawal`, `effective_product`,
`valid_protocol_fees`, `pow_int`. They are pure functions of old state, new state and inputs, and
they port without change. Porting them **is** the V11 curve; no new maths.

### The multi-reserve finalizer

Derived from `reserve_finalizer.rue` at the pinned commit. The contract it must satisfy is fixed by
`action.rue`; only the body changes. Sketch, not compilable as written:

```rue
// curried, first curry
ACTION_LAYER_MOD_HASH: Bytes32,
RESERVE_FULL_PUZZLE_HASHES: List<Bytes32>,  // per asset index: CAT-wrapped or bare
RESERVE_INNER_PUZZLE_HASH: Bytes32,         // shared p2_delegated_by_singleton curry, minus nonce
HINT: Bytes32,
// curried, second curry
FINALIZER_SELF_HASH: Bytes32,
// runtime
Truth: FinalizerTruths,                      // Truth.State is the PRE-spend state
last_action_output: (StateTruth, List<List<Condition>>),
...reserve_parent_ids: List<Bytes32>,        // the finalizer solution, one per asset index

// 1. bucket conditions: untagged -> base; (-42 i . c) -> reserve_conditions[i];
//    any i outside 0..N-1 must FAIL, not be dropped
// 2. for each index i:
//      old_amount = Truth.State.reserves[i]
//      new_amount = last_action_output.first.actual_state.reserves[i]
//      recreate   = CreateCoin { RESERVE_INNER_PUZZLE_HASH_i, new_amount, memos: [hint] }
//      SendMessage {
//        mode: SENDER_PUZZLE | RECEIVER_COIN,
//        message: tree_hash((1, (recreate, reserve_conditions[i]))),
//        receiver: [coinid(reserve_parent_ids[i], RESERVE_FULL_PUZZLE_HASHES[i], old_amount)]
//      }
// 3. recreate the singleton exactly as the template does:
//      CreateCoin { curry(ACTION_LAYER_MOD_HASH, [curry(FINALIZER_SELF_HASH, [self]), Merkle_Root, new_state]), 1 }
// 4. return [recreate_singleton, ...messages, ...base_conditions]
```

Two properties matter more than the rest. Every reserve is re-created every spend at its new state
amount, whether or not any action touched it — that is the V10 rule "untouched reserves still need
a plan", now enforced in one place. And the old amount used for the receiver coin id comes from
`Truth.State`, never from anything an action returned, so an action cannot point a message at a
coin that is not the current reserve.

### The LP CAT does not change

The TAIL still curries `(launcher_id, protocol_version)`; the mint and melt inners stay pinned and
unparameterised; the CAT-parent rule on a melt stays. The `add` and `remove` actions derive the LP
action coin id exactly as `assert_lp_coin_bound` does in V10, from `lp_parent_id`, the pinned inner
hash and the amount. What changes is the pool side of the handshake: the LP TAIL asserts the
action-layer singleton's puzzle announcement (or a message, if the TAIL is revised to accept
one) instead of the V10 pool's.

### Ephemeral state rules

- The first action of a spend sees `()`. Any action that emits a relative condition, or that must
  run at most once per spend, checks the ephemeral state and writes a marker into it.
- **Launch condition: single-action guard.** Every V11 action asserts the ephemeral state is `()`
  and returns a non-nil marker. A second action in the same spend then fails. This makes V11's
  per-spend surface identical to V10's and removes the multi-action and sequencer-ordering risks
  from the launch audit. Removing the guard is a later revision with its own audit.
- **No relative or height conditions in any action.** Add them later only behind the guard.
- When the guard is eventually lifted, batching several traders' swaps in one spend is safe by
  construction only because each trader's minimum output is enforced by their own offer's
  settlement announcement; that property must be re-proved in the multi-action suites at that
  time.

### Migration

A pool's puzzle is fixed at creation, so V10 pools cannot become V11 pools. V11 means a new LP
asset id per pool (the TAIL curries the protocol version), new pools, and the same retire-and-
recreate path used for V4–V9. The launch matrix runs again under V11. No liquidity is live on
V10, so there is nothing to migrate; the cost is deployment, not funds.

---

## Audit additions for the action layer

Run the full routine in `clvmPuzzleAudit.md` first. These checks are on top of it and are specific
to this architecture.

**Integrity**

- The compiled action layer, `p2_delegated_by_singleton` and slot puzzles match the upstream
  tree hashes above byte for byte. Forge never edits them; a mismatch fails the suite.
- The merkle root in every deployed pool resolves to exactly the three Forge action hashes and
  nothing else. Test that a fourth puzzle with a valid-looking proof is rejected.

**Finalizer**

- A `-42` tag with an index outside the pool's asset count fails the spend.
- Every reserve gets a `CREATE_COIN` and a `SEND_MESSAGE` on every spend, including a spend that
  only touches the LP side. Diff the emitted conditions against N.
- Omitting a parent id, supplying a wrong one, or supplying one for the wrong index fails.
- The receiver coin id is built from the pre-spend amount. Probe with an action that lies about
  the old amount in its returned state and confirm the message still targets the real coin.
- An action's untagged conditions never reach a reserve, and a tagged `CREATE_COIN` for the
  reserve's own puzzle hash from an action (not the finalizer) is rejected or provably harmless.
- The singleton is asserted at amount 1 and recreated at amount 1.

**Actions**

- Each action alone, then every ordered pair and the three-action combination in one spend, with
  the state threaded and the invariant checked at the end of the chain, not per action.
- The same action twice in one spend, including two swaps in opposite directions.
- Sandwich inside a spend: a sequencer orders swap A, swap B, swap A'. Confirm B's settlement
  announcement still guarantees B's minimum output.
- Swap output ±1 rejected, as in V10.
- Merkle proof for an action revealed by index on the second use resolves to the same puzzle.

**Reserves**

- A reserve coin cannot be spent with a delegated puzzle whose hash was not sent by the pool.
- A reserve of pool A cannot be satisfied by a message from pool B, including a pool with the same
  asset set (the struct hash differs by launcher).
- Two reserves of the same pool with the same asset are impossible; two with different assets have
  different puzzle hashes (nonce = index).

**Off-chain**

- The sequencer or router is the only party that can order actions in a batch. Log the order and
  the per-trader settlement it produced; the bearer-instrument rules in `clvmPuzzleAudit.md` still
  apply to every offer it holds.

---

## Test plan hooks

Map onto the lanes in `forgePoolLifecycleTesting.md`; the guardrails there do not change.

| lane | V11 addition |
|---|---|
| integrity | upstream hash pins; merkle root membership; finalizer and action hashes byte-identical to the archived snapshot |
| simulator | single action per spend for all three; multi-action combos; N-reserve recreation on every spend |
| adversarial | the finalizer and reserve probes above, each as a named suite that exits 2 on skip |
| lifecycle | launch matrix re-run under V11 through the real creation path, dry run first |
| driver | build spends with `chia-wallet-sdk`'s `ActionLayer` and `Reserve` drivers as a second implementation and confirm the Python driver produces identical bundles |

---

## Open items to settle before code

0. **Confirm adoption.** The surface count above is the evidence; the protocol owner decides.
1. **Tag encoding.** `(-42 index . condition)` versus one opcode per reserve (`-42 - index`).
   The former keeps a single strip rule in the finalizer; settle it before writing actions.
2. **LP TAIL handshake.** Keep the puzzle announcement from the action-layer singleton, or revise
   the TAIL to use a message. A message is cleaner; it means a TAIL change and therefore already
   the new asset id V11 brings anyway.
3. **Protocol fee.** V10 pays it as a second output from the shrinking reserve. In V11 it is a
   second `-42`-tagged `CREATE_COIN` from the `swap` action. Confirm the fee recipient is curried
   into `swap`, not solution-supplied.
4. **Router as sequencer.** Settled by the launch condition above: one action per spend, enforced
   in the puzzle by the ephemeral guard, not by router policy. Batching is a later revision.
5. **Config placement.** Curried into each action versus carried in state. Curried is cheaper and
   immutable, which is the V10 property worth keeping.

---

## Reference

- CHIP text: `github.com/Chia-Network/chips/blob/main/CHIPs/chip-0050.md`
- Reference puzzles at the CHIP's pinned commit
  `github.com/Yakuhito/slot-machine/blob/2d37ba1014e14220c26a0541b5d3199f9d15ec21/rue-puzzles/singleton/`:
  `action.rue`, `finalizer.rue`, `reserve_finalizer.rue`, `slot.rue`,
  `p2_delegated_by_singleton.rue`
- Drivers and tests: `github.com/xch-dev/chia-wallet-sdk`, `chia-sdk-driver/src/layers/action_layer/`
  and `chia-sdk-driver/src/primitives/action_layer/` (`reserve.rs` shows the delegated-puzzle
  reconstruction a driver must do to spend a reserve alongside the singleton)
- Technical manual: `docs.catalog.cat/technical-manual/action-layer` and `/slots`
- Companion CHIP-0051 (Reward Distributor) is the worked example of a reserve-finalizer app

Related skills: `forgePuzzleV10.md` (what V11 replaces and what it keeps), `forgeLpCat.md` (the
unchanged handshake), `clvmPuzzleAudit.md` (the base audit routine), `chiaTibetAmm.md` (the
other merkle-action AMM, for comparison), `chiaPerpetuals.md` (the first consumer of slots).
