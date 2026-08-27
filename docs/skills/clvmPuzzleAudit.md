# Skill: CLVM Puzzle Audit Method

> How to audit a Chia puzzle (Rue or Chialisp) so the result is evidence rather than an opinion.
> Distilled 2026-08-27 from the Forge internal audit — 10 findings, 2 of them critical fund-loss
> bugs reachable by any third party, all found by driving the **real compiled puzzles**.
>
> Generic on purpose. Applies to `chia-cfmm`, `chia-vaults`, `chia-perps`,
> `chia-treasure-chest`, and any future singleton/CAT design in the workspace.

---

## Domain

Use this skill when the quest is:

- reviewing an authorisation path in a puzzle (who is allowed to move value)
- writing adversarial probes for a puzzle before or after a revision
- cutting a new protocol revision and needing to know what to re-probe
- deciding whether a "fix" actually closed the hole it claims to close
- reviewing the off-chain surface (offer storage, HTTP reads, routers) around a puzzle

Do **not** use it as a puzzle reference for a specific protocol — see
`forgePuzzleV10.md` for Forge's shipping shape.

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

**Duplicated consensus logic diverges.** One redemption path existed in three copies and
the revision updated none of them. Delete the copies; import one implementation.

**An archive is not neutral.** When a file moves to `development/`, grep for its old path
before calling the move done. A live caller shelling out to a moved script failed with
`ENOENT`, was caught, and reported `success: true` while doing nothing at all.

**Every fix ships with a probe that fails against the vulnerable revision.** Keep the
proof-of-concept in the tree as the historical record, and keep archived puzzles loadable
so it can still run.

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

Publish the findings log with severity, revision introduced, revision fixed, the proof
file, and the reasoning that turned out to be wrong. That document is what an external
auditor reads first.

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

---

## Reference

Forge's own findings log — the worked example for everything above — is
[`docs/FORGE_SECURITY_AUDIT.md`](../FORGE_SECURITY_AUDIT.md), which ships with this repo. The
fuller version, carrying the proof file names, the numbers each probe produced, and the
reproduction commands, sits with the code at `projects/chia-cfmm/docs/FORGE_SECURITY_AUDIT.md` —
workspace only, since `projects/` is not published here. That reproduction block is the model for
a suite index: one line per suite, naming which finding it covers.

Related skills: `forgePuzzleV10.md` (the shipping shape), `forgeLpCat.md` (the LP
handshake in detail), `forgePoolLifecycleTesting.md` (what to run), and
`chiaPrimitivesPatterns.md` (singleton and CAT fundamentals).
