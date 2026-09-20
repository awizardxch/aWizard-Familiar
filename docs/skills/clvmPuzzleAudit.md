# Skill: CLVM Puzzle Audit Method

> How to audit a Chia puzzle (Rue or Chialisp) so the result is evidence rather than an opinion.
> Distilled 2026-08-27 from the Forge internal audit — 10 findings, 2 of them critical fund-loss
> bugs reachable by any third party, all found by driving the **real compiled puzzles**.
> Updated 2026-09-19 for V14 (protocol 15) with what four rounds of external review and one
> six-agent adversarial audit added: the lane discipline, broadcast authorisation, cross-leaf
> configuration, ephemeral chaining, and the two test-hygiene rules that cost us a wrong answer
> in public.
>
> Generic on purpose. Applies to `chia-cfmm`, `chia-vaults`, `chia-perps`,
> `chia-treasure-chest`, and any future singleton/CAT design in the workspace.
>
> **Two documents, one method.** This is the generic method and the defect catalogue, and it
> stays in the private tree because it names retired revisions. The operational runbook —
> the one a model loads to run an audit, and the one outside contributors can correct — is
> `projects/chia-cfmm/skills/n-asset-pool-audit/SKILL.md`, published with the puzzles. When
> they disagree, the published runbook is what an external auditor is working from: fix this
> one.

---

## Domain

Use this skill when the quest is:

- reviewing an authorisation path in a puzzle (who is allowed to move value)
- writing adversarial probes for a puzzle before or after a revision
- cutting a new protocol revision and needing to know what to re-probe
- deciding whether a "fix" actually closed the hole it claims to close
- reviewing the off-chain surface (offer storage, HTTP reads, routers) around a puzzle

Do **not** use it as a puzzle reference for a specific protocol — see
`forgePuzzleV14.md` for Forge's shipping shape (`forgePuzzleV10.md` through
`forgePuzzleV13.md` remain as the retired ones, and a finding demonstrated against a
retired revision still needs its "before" built there).

---

## Rule 0 — probe the compiled puzzle, never the source

Every finding worth having came from running the real hex with a solution an attacker
would write. Reading Rue and reasoning about it produced one confident wrong answer
(a melt path argued to be already blocked; the probe disagreed within a minute).

Three corollaries, each of which cost a real finding:

1. **A negative probe alone proves nothing.** If the harness is malformed, the puzzle
   rejects everything and every attack "fails". Always run the honest case beside the
   adversarial one, in the same file, and assert it still goes through.
2. **A failure for the wrong reason is not a fix.** The first re-run of a drain PoC
   against the fixed revision failed on *arity*, because the solution shape had
   changed — which looks exactly like a fix. Drive the new shape properly and confirm
   each mechanism separately.
3. **Reasoning about CAT ring arithmetic is not a substitute for running it.** The
   `parent_is_cat` / `extra_delta` interaction is not intuitive. Run it.

---

## Rule 0.5 — pick the lane that can answer the question

Added after a real finding went undispositioned through three reviews because everyone who
looked at it looked offline. A static validator will happily run a chain of ephemeral
spends, so a suite built on one can only ever report that the bundle is well formed.

| lane | what it runs | can decide | cannot decide |
|---|---|---|---|
| **offline** | `chia_rs.get_conditions_from_spendbundle` — the mempool's own validator | conditions, message pairing, duplicate outputs, CAT ring arithmetic | whether a coin exists, its lineage, or when it was born |
| **simulator** | `chia._tests.util.spend_sim` — the real mempool manager and coin store | coin existence, lineage, birth heights, ephemeral-spend rules, whether a block advances | anything about the deployed objects' own state |
| **chain** | a node's `push_tx` | the same, against coins created over days that nobody local can rewrite | anything needing funds you are unwilling to spend |

The import is `chia._tests.util.spend_sim`. There is no `chia.clvm.spend_sim`, and
`push_tx` belongs to the **full node**, not the wallet — both wrong in a sample we shipped,
and both fail at import or first call rather than at the assertion.

**A refused push costs nothing.** Adversarial probes against live objects are free as long
as they are refusals; never push a bundle you expect to be accepted unless you meant to
spend. What a chain adds over a simulator is that the coins were not farmed by the person
making the claim.

---

## The harness shape

One shared harness per protocol (`_forge_testkit.py` is the reference), never per-suite
copies. Suites that import their fixtures from a sibling suite die together when the
sibling's puzzles are unavailable — that pattern took 6 of 33 suites down at import.

The harness owns four things:

| piece | what it does |
|---|---|
| **Synthetic makers** | real CAT and XCH spends creating `OFFER_MOD` settlements, so an Offer can be assembled with no wallet and no chain |
| **Real creation path** | build fixtures through the production deploy function in `dry_run` mode — never hand-assemble the controller, or the fixture drifts from what production mints |
| **`external` set** | the coin ids that legitimately pre-exist: the singleton, its satellites, the maker inputs |
| **`audit(bundle, external)`** | static analysis of the assembled bundle before any node sees it |

### What `audit()` must check

Run every spend through `conditions_dict_for_solution`, then assert:

- **every `ASSERT_COIN_ANNOUNCEMENT` is satisfied** by some `sha256(coin_id + msg)` created
  in-bundle, and every `ASSERT_PUZZLE_ANNOUNCEMENT` by some `sha256(puzzle_hash + msg)`
- **no spend consumes a coin that is neither created in-bundle nor in `external`** —
  otherwise the node answers `UNKNOWN_UNSPENT` and the bundle was never real
- **no coin is spent twice** (`DOUBLE_SPEND`)
- `ASSERT_MY_PARENT_ID` / `ASSERT_MY_PUZZLE_HASH` / `ASSERT_MY_AMOUNT` match the coin
  actually being spent
- a `paid_to(bundle, asset_id, puzzle_hash)` helper, so payout assertions are made against
  coins the bundle actually creates rather than against the builder's own claims

A bundle that passes `audit()` and still fails on chain is a harness bug; a bundle that
fails `audit()` was never worth pushing.

---

## The authorisation taxonomy

This is the part that produced both critical findings, and it generalises to every Chia
protocol where a singleton controls satellite coins.

| mechanism | who can satisfy it | verdict |
|---|---|---|
| `AssertCoinAnnouncement` keyed on a coin id **taken from the solution** | anyone — any coin running any puzzle can emit any message | **broken.** The spender names a coin they own and authorises themselves. |
| `AssertCoinAnnouncement` keyed on a coin id the asserting puzzle **derives, or holds in curried state** | only that specific coin | sound |
| `AssertPuzzleAnnouncement` keyed on a puzzle hash **rebuilt in-puzzle from a curried identity** | only a coin actually running that puzzle | **sound — the right default for satellite → controller** |
| A curried `launcher_id` asserted non-zero and then never used | nobody — it is decoration | **broken.** Grep for curried fields with no consumer. |
| `AssertCoinAnnouncement` **derived correctly**, where the design assumes one asserter | every spend in the bundle, independently | **broken for a once-per-lifetime event.** See below. |
| CHIP-0025 `SendMessage` / `ReceiveMessage`, mode 23 (sender by puzzle hash, receiver by coin id) | exactly one sender and one receiver, paired by consensus | **sound, and 1:1 by construction — the right default for a handshake** |

### An announcement is a broadcast, and that is the whole finding

The row above cost a CRITICAL. A correctly derived announcement still authorises *anyone
who asserts it*: consensus pairs one creation with any number of assertions. Nothing in
CAT2's ring accounting helps, because each eve is its own one-coin ring and two
independent rings are two independently valid proofs.

So the question to ask of every announcement is not "can the spender forge it" but **"what
counts the assertions?"** Wherever a design assumes an event happens once — a genesis
mint, a fee release, a one-time registration — an announcement is the wrong primitive.
Three ways out, in order of preference:

1. a CHIP-0025 message, which is 1:1 because consensus commits both ends;
2. `AssertMyParentId` against a coin that can only be spent once (a launcher pins exactly
   one child);
3. fold the identity of the intended asserter into the announced value itself, so the
   announcement names its one legitimate consumer.

The fix that shipped was (3) then (1): the launcher's announced key-value list gained the
eve's own coin id, so exactly one coin can assert it, and the ordinary mint/burn handshake
moved to a mode-23 message.

### What CHIP-0025 changes about the three-part lock below

The three-part lock was written when the handshake was announcement-based. Under mode 23
the sender is committed by puzzle hash and the receiver by coin id, so **consensus does
part 1** — the controller no longer has to derive and assert the action coin's id, and
`AssertMyCoinId` in the satellite goes away with it. Parts 2 and 3 stand unchanged: pin
the inner puzzle, and require a CAT parent on a melt. One condition replaces three, and
the part that is now consensus's job is the part that used to be got wrong.

**The rule.** A satellite coin (reserve, vault, escrow, position) must assert a **puzzle**
announcement whose id it rebuilds from *its own curried* launcher id plus the controller's
inner puzzle hash. Only a genuine singleton of that launcher can carry that puzzle hash,
and a coin fabricated at the same hash cannot be spent — the singleton top layer checks
lineage back to the launcher. The reverse direction (controller → satellite) may be a coin
announcement, because the controller names one specific coin id out of state it already
tracks.

**And pin the successor.** `AssertMyPuzzleHash` ties the solution-supplied "recreate at
this hash" value to the puzzle the coin actually runs. Without it the successor can be a
puzzle the attacker controls, and the attacker takes the remainder through the settlement.

### The three-part lock for a mint/burn handshake

Binding one thing is never enough. A CAT whose supply a singleton governs needs all three:

1. **Bind the coin id.** The controller *derives* the action coin's id —
   `sha256(parent + cat_puzzle_hash(tail, PINNED_INNER) + amount)` — instead of accepting
   one from the solution. Stops an impostor **puzzle**.
2. **Pin the inner puzzle.** A fixed inner whose only behaviour is the `-113` TAIL call.
   Without this the honest path uses an `identity` inner that imposes no melt, so
   "own the token, spend it without burning, collect the payout" still works. Stops the
   **no-op burn**.
3. **Require a CAT parent on a melt** (`parent_is_cat || expected_delta > 0`). CAT2 lets a
   coin with no valid lineage be spent when the TAIL authorises it, and for a non-CAT
   parent the TAIL scores `amount + delta` — so `delta = -2 * burn` fabricates any burn
   you like out of ordinary mojos. A melt destroys supply, so it can only come from a coin
   that held supply. Stops an impostor **coin**.

Findings 1, 4 and 6 in the Forge log are these three, discovered one at a time — each by
the fix for the one before it.

---

## Recurring defect classes — the checklist

Run this against any puzzle-plus-builder system. Every row is a real finding.

| # | class | what to look for |
|---|---|---|
| 1 | **Solution-supplied identity** | a field asserted `!= 0` and never otherwise used |
| 2 | **Unbound satellite** | a satellite puzzle not curried with its controller's launcher id |
| 3 | **Builder accepts a config the puzzle refuses** | a zero recipient with a non-zero fee passes a length check and mints a permanently unspendable coin |
| 4 | **Impostor coin via CAT2 lineage** | any TAIL branch reachable with `parent_is_cat` false |
| 5 | **Arithmetic that disagrees with the puzzle** | a closed-form solve where the puzzle *brackets* |
| 6 | **A fix that breaks a lane nobody tests** | after any revision, grep every builder for the old action shape |
| 7 | **Frontend quote != puzzle** | a second implementation of the curve in TypeScript |
| 8 | **Weight-blind maths** | `reserve_in * reserve_out` with no exponent |
| 9 | **Positional-structure rot** | numeric indices into a curried config |
| 10 | **Off-chain leak of a bearer instrument** | an unauthenticated read that returns a raw offer string |
| 11 | **Broadcast authorisation** | an announcement authorising a once-per-lifetime event — what counts the assertions? |
| 12 | **Cross-leaf configuration** | a merkle-dispatched action layer: membership is proved, agreement is not |
| 13 | **Ephemeral chaining** | any counter, height or price that advances per spend, with the object spendable twice in one bundle |
| 14 | **An interval credited by nobody** | accounting that advances a cursor further than it credits; the gap is free and permanent |
| 15 | **Solution-supplied width** | a `Bytes32` that is a compile-time tag only, feeding a hash compared against something consensus did NOT commit |
| 16 | **Duplicate outputs** | two `CreateCoin`s alike in puzzle hash and amount from one coin |

### Class 3 in full — mirror the validator, do not patch the case

Do not fix the single bad config that was found. Mirror the puzzle's entire
`validate_config` in the builder and run it **before anything is built from the config**.
Any future divergence between builder and puzzle then fails at build time instead of on
chain. The stakes are absolute once satellites are properly bound: a controller that
cannot pass its own config validation can never emit the announcement its satellites
require, so the deposit is not "recoverable" — it is gone.

### Classes 5, 7 and 8 are one defect written four times

The same curve existed in four implementations — the Rue puzzle, the Python builder, the
Python route planner, and the TypeScript quote. **Three of the four were weight-blind**,
and the one that was right was right by accident of using a continuous formula, not
because anyone checked it.

The failure mode is not theft. The puzzle brackets the value exactly and refuses anything
else, so a disagreement is a spend that **can never settle** — and when the frontend is
the *correct* one, the user signs a quote they can see against a bundle that dies on
chain.

Two things make this tractable:

- **The puzzle is the third party.** Pin every mirror to values taken from what the
  compiled puzzle actually accepts, never to each other. One parity suite per
  implementation, all asserting the same table.
- **Bracket, do not solve.** A puzzle that verifies `claimed` and refuses `claimed +/- 1`
  needs only integer multiplication — no fractional exponents on chain, which is the usual
  reason weighted curves are avoided. The builder then has to reproduce that bracket
  (binary search when the exponents differ), not a closed form that is exact only in the
  symmetric case.

Symmetry hides all of it: equal weights hide the exponent, a balanced deposit hides the
fee share, a free vault hides the vault branch. **Probe the asymmetric shape or you have
probed nothing.**

### Class 9 — positional rot, in two guises

A revision inserted two fields at indices 5 and 6, pushing two others from 5/6 to 7/8.
Every reader indexing past them kept compiling, kept running, and started returning a
neighbouring value — one serialised the *fee recipient* as a puzzle hash. Because that
value round-trips through a persisted snapshot, **every new pool worked exactly once and
then failed for good**.

- Index trailing fields **from the end**, where they have sat in every revision.
- Better, name them: the curried config is positional, the JSON mirror need not be.
- What caught it was a guard re-deriving the hash. Without that guard it would have been
  *worse* — a silent rebuild at a different puzzle hash, spending against a controller
  that does not exist.

### Class 12 — membership is not agreement

An action layer proves that each leaf a spend runs is a member of the merkle root, and
that is all it proves. Where the configuration is curried into each leaf separately, six
leaves curried with six *different* configurations still make a valid root, and each leaf
validates only its own. A `remove` leaf curried with a foreign LP TAIL released 99.80% of
both reserves to a worthless self-minted CAT, and every leaf passed its own checks.

The fix is structural: something on the coin must rebuild the root from a single
configuration hash on every spend. Check also **when** the configuration is validated — if
`valid_config` runs only on the first action of a spend, a second action riding the same
spend is never independently validated at all.

### Class 13 — one spend per block, or the counter is free

If an object can be spent twice inside one bundle, every per-spend quantity is free:
a price-time accumulator, a rate limit, a nonce. The chain of `swap → observe ×N →
swap-back` on ephemeral coins moves a TWAP through its whole window at no market risk,
because no time passes between the manipulated price appearing and it being weighted.

`ASSERT_MY_BIRTH_HEIGHT` closes this by construction rather than by bounding anything: a
coin created inside the bundle has no birth height for a coin store to confirm, so **no
claimed value satisfies it** and a node answers `EPHEMERAL_RELATIVE_CONDITION`. The
invariant it buys comes free, because `ASSERT_HEIGHT_ABSOLUTE` is checked against the
*previous* transaction block, so the block including a spend is always strictly above the
height that spend claimed.

Only the chain lane can test this. See Rule 0.5.

### Class 14 — a legal zero is free

Distinct from an illegal negative. Accounting that writes `cursor = claimed` but credits
only `claimed - start` loses everything between the previous claim and the block that
included it — credited by nobody, and never creditable afterwards, so understating is free
and repeatable. Credit **both** intervals: the previous state over `(last_cursor, birth]`
at the value it recorded, and the current state from `birth` onward. Then understating
defers credit to the next spend instead of destroying it.

The general shape: any time a cursor moves further than the thing it accounts for, ask who
owns the gap.

### Class 15 — where a derived id is compared decides whether width matters

Rue emits no runtime `strlen`: a `Bytes32` in a signature is a compile-time tag and nothing
more, and values of 0, 4, 32 and 64 bytes are all silently accepted, each producing a
different downstream hash. That is safe **only** while every such value feeds a preimage
whose result is compared against a consensus-committed coin id or announcement — a wrong
width then names a coin that exists nowhere.

So the rule is about the comparison, not the type: derive ids through the native `coinid`
operator, which hard-rejects a non-32-byte operand, or make sure the result meets
something consensus committed. Where neither holds, assert the length. And test it:
feed every solution-supplied `Bytes32` at 0, 1, 4, 31, 33 and 64 bytes plus a
non-canonically encoded integer, and require each to be refused. Nothing in a suite that
only exercises canonical inputs is positioned to catch this.

### Class 16 — a coin id is (parent, puzzle hash, amount)

Two `CreateCoin`s alike in the last two from the same coin are one coin id twice, and the
node rejects the whole bundle as `DUPLICATE_OUTPUT` naming nothing. It bit a `collect`
leaf paying a protocol fee and a DAO fee of equal size to the same recipient — and integer
flooring makes equal balances common even when the rates differ. Merge the payouts where
the recipient is the same, and catch the composed cases in the composer, where the
information about which pair collided still exists.

---

## Test hygiene — the rules that made the findings findable

**A skip that exits 0 is a lie.** Fifteen suites signalled "skipped" by exiting
successfully, so a run that exercised almost nothing reported `34 passed / 0 skipped`.
**Skips exit 2.** A test count is evidence only when not-running is distinguishable from
passing.

**A suite pinned to live chain state tests that revision only.** The vault suites passed
throughout a finding that made every vault route unbuildable, because the pools they load
are three revisions old. Read any chain-loading suite as covering *that* revision, and
build a synthetic fixture at the shipping revision beside it.

**A round trip nobody performs in a test is a round trip nobody has tested.** Every suite
built its object in memory and handed it straight to a builder. Production serialises and
reloads between *every* pair of actions, and that step had no coverage at all. Round-trip
the persisted form — twice in succession — and assert the derived hash is unchanged.

**Identify the revision with a number the reader can recompute.** The 2026-09-19 record
named its build with a digest described in prose — "sha256 over every `.rue`, `.hex`,
`.hash` and the manifest, sorted" — that reproduced under none of its readings and
appeared nowhere but the record quoting it. "Which build did you test" is the question
every other answer depends on. Ship the command (`scripts/revision-fingerprint.py`,
per-file LF-normalised digests so a mismatch names the file) and cite it beside the
number. Runbook rule 8.

**A failure must say whether the record is stale or the system is broken.** A suite that
compares a local record against the chain fails for two unrelated reasons: the record is
behind (a fact about the checkout) or the chain never had what the record claims (serious).
`_test_v14_discoverability.py` printed one line for both, so 42 ordinary drift failures
looked like 42 missing reserves until a chain query per coin said otherwise — in a suite
that already held the spent flag. If a check can fail boringly and alarmingly, it says
which, and names the remedy (`v14-resync-records.py` then `import-v14-pools.mjs`).
Runbook rule 9.

**Run tools at the coverage the audit claims, not at their defaults.** The testnet probe's
`--pools` defaults to 8 of 32. Run plainly it covered a quarter of the pools, and the
first draft of the 2026-09-20 record explained that shortfall with the index drift it had
just been looking at — a tidy story reached without reading the argument parser. Check
what produced a number before explaining it; state the coverage actually exercised.
Runbook rule 10. The same failure in miniature: `curl -k` passes exactly the certificate
check a webview fails, and `$?` after a pipe is `tail`'s exit, not the suite's.

**Duplicated consensus logic diverges.** One redemption path existed in three copies and
the revision updated none of them. Delete the copies; import one implementation.

**An archive is not neutral.** When a file moves to `development/`, grep for its old path
before calling the move done. A live caller shelling out to a moved script failed with
`ENOENT`, was caught, and reported `success: true` while doing nothing at all.

**Every fix ships with a probe that fails against the vulnerable revision.** Keep the
proof-of-concept in the tree as the historical record, and keep archived puzzles loadable
so it can still run.

**Assert the "before", or the suite stops testing it silently.** A before-and-after suite
must require the attack to be ACCEPTED against the vulnerable build as loudly as it
requires it to be REFUSED against the fixed one. Without that, the day the construction
stops reaching the old build — a renamed field, a changed solution shape — the suite goes
on passing while proving half of what it claims, and nothing says so. A finding that can
no longer be demonstrated where it was found is as much a failure as one the fix still
allows.

**Never search through a mirror of the logic.** This one cost a wrong answer in public. A
reviewer reported that an `assert deposit >= 0` was load-bearing; we searched for a vector
that would satisfy the mint bracket with a negative slot, found none, and published "does
not reproduce". The search ran through the Python mirror of the curve, whose *wrapper*
refuses negative deposits before the bracket is ever reached — it tested the guard it was
trying to test. Solving the bracket directly produced the vector immediately, and the
shipped leaf refuses it only because of that line. Mirrors carry their own guards; solve
the condition, then run the compiled leaf.

**A mutation survivor is UNREACHED, never "redundant".** A refusal test does not say which
line refused, so delete the assert, rebuild, and see whether the suite still passes. When
a line survives, the default reading is that no test reaches it — probe it with hand-sized
inputs before arguing that it is unnecessary, because a mirror's guard or an earlier assert
routinely masks the leaf's own line. The line above was recorded SURVIVED for exactly that
reason, and it was load-bearing all along.

---

## The off-chain surface is in scope

The most valuable finding in the Forge audit involved no puzzle at all — which is exactly
why no contract suite could have caught it.

**Offers are bearer instruments.** A wallet RPC will not build an offer with an empty
requested list, so an all-CAT pool creation manufactures a request: one mojo of a CAT it
is already offering, added to both sides so the amounts wash out. Internally consistent.
Read as a standalone offer the same bytes say *pay one mojo, receive the entire genesis
reserve*, and whoever takes it first gets it. Fifteen such records sat in an index served
in full by two unauthenticated `GET` endpoints.

Rules that follow:

- A creation offer is a bearer instrument between the wallet and the router. **Never
  logged, never mirrored to a public venue, never rendered in a UI with a copy button.**
- Redact at the **HTTP boundary**, not in storage — the router legitimately needs the raw
  bytes in-process.
- **Detect over-broadly:** match on source *or* id prefix *or* status, and keep a record
  redacted for life. A record whose status has moved on to `matched` or `deploy-failed` is
  still a creation record, and its coins may still be unspent.
- Give the boundary its own check suite, wired into the same command as the quoting
  checks so it cannot be skipped.
- Redaction closes the route that handed the bytes out. It does not make the offer safe.

---

## Audit routine for a new revision

1. **Integrity** — every source compiles to the hex actually shipped, matches the
   constants baked into the controller, agrees with the manifest, and is byte-identical to
   its archived snapshot.
2. **Authorisation probes** — one suite per authorising puzzle, each mechanism asserted
   separately, honest case included.
3. **Curve probes** — over-sized output, under-sized output, output for no input, no-op,
   both reserves rising, whole-supply burn.
4. **Fee probes** — skip, underpay, overpay, redirect; and a hostile router asking an
   absurd rate still stops exactly at the surplus, with
   `trader + protocol + router == released`.
5. **Isolation** — a hostile controller whose curried state *claims* a victim's satellite
   coins is refused.
6. **Creation and lineage** — malformed creations refused, the minted object live, the
   successor a genuine singleton of the same launcher, and the creator unable to withdraw
   more than they deposited.
7. **Parity** — every mirror implementation against the puzzle's own numbers.
8. **Round trip** — persist, reload, act again.
9. **Boundary checks** — what the HTTP layer hands out.
10. **Lane coverage** — every claim that depends on a coin existing, its lineage, or its
    birth height runs on a simulator or a chain, not offline (Rule 0.5).
11. **Ephemeral composition** — the object spent twice in one bundle, and each per-spend
    quantity checked for what that buys.
12. **Adversarial widths** — every solution-supplied `Bytes32` at 0, 1, 4, 31, 33 and 64
    bytes, and one non-canonically encoded integer.
13. **Mutation run** — every assert deleted in turn, with each survivor argued in writing
    beside the line or killed by a new vector.
14. **Fingerprint** — `scripts/revision-fingerprint.py` before and after; identical means
    no artefact moved, and the number is one the reader can recompute.
15. **No silent skips, full coverage** — provenance with `FORGE_REPO=<a clone tracking
    contracts/v14>` so it checks git rather than the working copy; chain probes at their
    full pool count (`--pools 32`), not their default. A record that reads "all pass" with
    a skip or a default hidden inside it has not earned the phrase.

Publish the findings log with severity, revision introduced, revision fixed, the proof
file, and the reasoning that turned out to be wrong. That document is what an external
auditor reads first. Publish it as a **named-model pass** — say who ran it and why a
different model running the same runbook matters — scrubbed of personal and operational
detail (no paths, hosts, names; "the checkout's index", not this machine), with every
script it cites added to the publish slice and `scripts/check-doc-links.py` run, since the
gate is the real slice now rather than a copy of it.

---

## Permissionless creation is inherently creator-trusted at genesis

Worth stating rather than discovering. At genesis the creator controls both the curried
state and the supply the TAIL is told to mint, because the coin authorising that mint is
an ordinary coin in their own bundle — there is no controller yet to authorise it. Probe
the consequences instead of assuming them: a mismatched state should make the object
inert (`AssertMyAmount` failing against the real satellite coins), which costs the
creator, and a full withdrawal test should show the creator taking out strictly less than
they put in. Gating creation to an allowlist or an NFT is a product decision on top, not a
substitute.

**What later revisions narrowed.** Creator-trust at genesis is not all-or-nothing, and
three changes moved real ground without adding an authority:

- the launcher's announced key-value list names the one eve that may mint, so the genesis
  supply a registered object claims is the supply that exists (class 11);
- a locked minimum stays burned for the object's life, so the last holder can always
  redeem and the object outlives every withdrawal — the boundary matters, `total_lp >
  MIN_LOCKED` at registration and `>=` in the prologue, or an object minted below the
  floor is a trap rather than merely inert;
- registration derives every satellite's parent from a launcher the registration bundle
  must spend, so a listing whose reserves were never funded is refused. Before that, a
  market key could be taken forever for the price of a creation fee by an object nobody
  could ever spend.

What remains creator-trusted is an **unregistered** object: nothing on the coin
distinguishes one, which is why registry membership — not a single leaf's merkle proof —
is the integrity guarantee to state in the documents and to reconstruct in client
tooling.

---

## Reference

Forge's own findings log — the worked example for everything above — is
[`docs/FORGE_SECURITY_AUDIT.md`](../FORGE_SECURITY_AUDIT.md), which ships with this repo. The
fuller version, carrying the proof file names, the numbers each probe produced, and the
reproduction commands, sits with the code at `projects/chia-cfmm/docs/FORGE_SECURITY_AUDIT.md` —
workspace only, since `projects/` is not published here. That reproduction block is the model for
a suite index: one line per suite, naming which finding it covers.

The operational runbook that pairs with this method —
`projects/chia-cfmm/skills/n-asset-pool-audit/SKILL.md`, published with the puzzles as
`skills/n-asset-pool-audit/SKILL.md` — carries the model pipeline, the strict finding
format, the completion gate, and the runnable entry points. This document is the *why*
and the catalogue; that one is the *how*, and it is the one an outside auditor reads.

Related skills: `forgePuzzleV14.md` (the shipping shape), `forgeLpCat.md` (the LP
handshake in detail), `forgePoolLifecycleTesting.md` (what to run), and
`chiaPrimitivesPatterns.md` (singleton and CAT fundamentals).
