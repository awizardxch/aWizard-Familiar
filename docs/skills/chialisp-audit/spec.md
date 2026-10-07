# Skill: Chialisp Audit Spec — what the language's own documentation says must hold

> The audit checklist that falls out of reading [chialisp.com](https://chialisp.com) end to end —
> every warning, every "must", every post-mortem the Chia docs cite (CAT1, TibetSwap v1,
> AGG_SIG_UNSAFE mimicry, the pooling mask attack) — turned into rows an auditor can mark
> PASS, FAIL or N/A against a puzzle and the code around it. Distilled 2026-10-07 from the
> 28 pages the site's sidebar lists (primer, concepts, `conditions`, `costs`, `operators`,
> `modern-chialisp`, `common_issues`, `attacks-and-countermeasures`, `debugging`,
> `optimization`, the seven primitives, `clvm`), then run once against four repositories:
> `forge-puzzles`, `forge-ui`, `Spellbook` and `Nightspire-Market`. The findings of that run
> are in [`docs/CHIALISP_AUDIT_2026-10-07.md`](../../CHIALISP_AUDIT_2026-10-07.md).
>
> **Two documents, one method.** `clvmPuzzleAudit.md` is the method we learned by breaking our
> own puzzles: probe the compiled hex, pick the lane, the sixteen defect classes, test hygiene.
> This spec is the complement — what the *language's* documentation says must hold, so a review
> starts from the rules Chia Network itself publishes rather than only from the mistakes we
> happen to have made. Load both. Where they overlap, the row here cites the docs page and the
> class there cites the finding that taught it.
>
> Written for classic Chialisp (`.clsp`/`.clvm`) and for Rue alike: the rows are about what the
> compiled program and the conditions it emits must satisfy, which no source language changes.
> Protocol-agnostic. Applies to an HTLC, a TAIL, a singleton inner puzzle, a settlement wrapper,
> or an off-chain service that handles any of them.

---

## Domain

Use this spec when the quest is:

- auditing a Chialisp or CLVM puzzle that was *not* written in the workspace (a counterparty's
  HTLC, a vendored upstream puzzle, a CHIP reference implementation)
- reviewing a new puzzle before its first probe suite exists, to decide what the suite must cover
- checking an off-chain service (router, relay, wallet daemon, indexer) against the docs' rules
  for offers, signatures, CLVM deserialization and cost caps
- writing or grading an audit report, so that every claim names the documentation rule it rests on
- deciding whether a design document (a spec with no code yet) already violates a published rule

Do **not** use it as a substitute for running the puzzle. Every row below is a *claim to verify*;
`clvmPuzzleAudit.md` Rule 0 still applies — the compiled program and an attacker-shaped solution
decide, not the source and not this list. And do not use it as a reference for a specific
protocol: `forgePuzzleV14.md`, `forgeLpCat.md` and `greenwoodLockbox.md` carry those.

---

## Rule 0 — the three facts the docs keep repeating

Every security page on the site reduces to three statements about the environment a puzzle runs
in. An auditor who holds them in mind finds most of the catalogue below unaided.

1. **Farmers see and rewrite solutions.** "Farmers can see and modify coin solutions … if
   modifying any of the conditions from your coin's solution would result in the solution
   remaining valid, then you should assume the farmer will do exactly this." (`common_issues`,
   Password Coin.) A value that arrives only in the solution authorises nothing.
2. **Spend bundles are not signed.** "Unless all of the coin spends in a spend bundle are linked
   together, the spend bundle can be split" (`common_issues`, Spend Bundle Splitting), and
   Replace-By-Fee lets a third party "piggyback some coin spends of their own on top of your
   spend bundle" (Replace By Fee). Linkage is a puzzle's job.
3. **An announcement is a broadcast scoped to one block.** "The condition can be asserted
   multiple times in the same block" (Unprotected Announcements) and "they can only be asserted
   within the block they are created" (`conditions`, Announcements). Anything that assumes one
   asserter, or assumes the announcing coin is still unspent, is reasoning the chain does not do.

The site's own framing of the audit duty: "we recommend putting each of your applications through
a rigorous code review and audit before deploying them on mainnet" (`common_issues`, preamble).

---

## A. Solution trust

| row | rule (docs page) | what to look for | verdict if found |
|---|---|---|---|
| **A1** | A coin locked only by a secret in its solution is stealable by the farmer who includes it (`common_issues`: Password Coin; `chialisp-primer/first-smart-coin`) | a preimage, password, or bare `conditions` list that selects the payout without an `AGG_SIG_ME` from the beneficiary or a binding to a signed coin | **broken.** The HTLC claim path is this shape unless the claimant also signs. |
| **A2** | "Ensure that all elements of the solution are either signed, or in some other way protected" (`common_issues`: Unprotected Solution) | any solution field that changes the outcome and is neither signed, asserted (`ASSERT_MY_*`), derived, nor bound by announcement/message | broken — enumerate each field and name its binding |
| **A3** | Bundles can be split or extended by RBF (`common_issues`: Spend Bundle Splitting, Replace By Fee) | spends in one bundle that nothing links; a protocol that assumes two spends land together without an announcement or message between them | broken for any multi-spend protocol |
| **A4** | Flash loans: "it is valid to create a coin of any XCH value, as long as the total … unspent coins created … is less than or equal to the total … spent" (`common_issues`: Flash Loans) | any check of the form "a coin of amount X exists in this bundle" without lineage or birth proof | weak — see E3 |
| **A5** | "Destructure and validate solution fields … Bound input sizes — use `strlen` … Constrain unused fields … to a known harmless value (e.g. nil)" (`attacks-and-countermeasures`: Designing DoS-Resistant Puzzles) | a solution byte field hashed or concatenated with no `strlen` bound; a field the puzzle ignores on some path and never pins to nil | DoS surface, and a smuggling channel for data an off-chain reader will later parse |

**The password coin is the HTLC.** The docs' teaching example — `(if (= (sha256 password)
PASSWORD_HASH) conditions (x))` — is structurally an HTLC claim: a preimage unlocks a payout
whose destination sits in the solution. The docs' verdict ("the farmer could steal this coin as
it was being spent") transfers unchanged. The repair the docs give is a signature; the repair that
keeps the HTLC's atomicity is to curry the claimant's puzzle hash (or require the claimant's
`AGG_SIG_ME`) so the preimage selects *that* the coin moves, never *where*.

---

## B. Hashing and identity

| row | rule (docs page) | what to look for | verdict if found |
|---|---|---|---|
| **B1** | CAT1: `sha256(parent + puzzlehash + amount)` with no length checks let an attacker "shift the divider … to the left by one or two bytes" (`common_issues`: Unchecked Hashing; `conditions` warning on `ASSERT_MY_COIN_ID`) | any `sha256` over concatenated solution-supplied parts where a part's width is not fixed by a `strlen`/`size_b32` check or by the `coinid` operator | **broken** when the result is compared against something the solver also controls; sound only when it meets a consensus-committed id |
| **B2** | "`0xFF` means -1, whereas `0x00FF` means 255 … the same integer can be represented by many different atoms" (`clvm`: Integer Representation); "Careful with a delta of zero, the bytecode is 80 not 00" (`cats`: everything_with_signature) | an amount, delta or height used as *bytes* (hashed, signed, concatenated) that could arrive non-canonically; a mirror that encodes `0` as `0x00` where CLVM emits nil | mismatch between puzzle and mirror; or an alias the puzzle accepts and the mirror does not |
| **B3** | "It is not safe to compare CLVM programs in serialized form … To compare programs, use tree hash" (`clvm`: Serialization) | an indexer, relay or test comparing puzzle reveals or solutions bytewise | false negatives on overlong encodings |
| **B4** | `sha256` on a list raises; `sha256tree` "will have a different result (due to prepending a 1 or 2 based on type)" (`debugging`) | a Python/TS mirror computing a hash the puzzle also computes — same form? same type prefixes? | parity defect (class 5/7 in `clvmPuzzleAudit.md`) |
| **B5** | `coinid` "validates the length of each component … as well as the coin's value" and is cheaper than the hand-rolled derivation — "800 versus 953" in `common_issues`, base 480 in the `costs` table | hand-rolled coin-id derivations in post-CHIP-11 code | not a defect by itself; a missed hardening, and a flag to re-check B1 |

The CAT1 patch the docs reproduce is the minimum any pre-`coinid` derivation must carry:

```chialisp
(defun calculate_coin_id (parent puzzlehash amount)
  (if (all (size_b32 parent) (size_b32 puzzlehash) (> amount -1))
    (sha256 parent puzzlehash amount)
    (x)))
```

Rue emits no runtime `strlen` for a `Bytes32` parameter (`clvmPuzzleAudit.md` class 15), so in
Rue the same rule reads: route every derived id through `coinid` or make sure it meets a committed
value, and assert the length where neither holds.

---

## C. Announcements and messages

The docs now say plainly: "While `ASSERT_COIN_ANNOUNCEMENT` and `ASSERT_PUZZLE_ANNOUNCEMENT`
will continue to be supported, they are no longer recommended. Instead, you should consider using
the `SEND_MESSAGE` and `RECEIVE_MESSAGE` conditions" (`conditions`, list preamble).

| row | rule (docs page) | what to look for | verdict if found |
|---|---|---|---|
| **C1** | TibetSwap v1: an announcement of `"mint"`/`"burn"` with no coin id in the message was asserted twice per block "until all funds were drained" (`common_issues`: Unprotected Announcements) | a `CREATE_COIN_ANNOUNCEMENT` whose message does not name its one intended consumer | **broken** for any once-per-event authorisation — ask *what counts the assertions* (class 11) |
| **C2** | "If an `ASSERT_COIN_ANNOUNCEMENT` condition is used in a coin's puzzle, the coin will be bricked … if the coin being asserted has already been spent" (`common_issues`; `conditions` warning) | an `ASSERT_COIN_ANNOUNCEMENT` emitted from puzzle logic (not taken from the solution) naming a coin that can be spent independently | **brickable.** `ASSERT_PUZZLE_ANNOUNCEMENT` in a puzzle is "less dangerous because … many such coins might exist" but still "best practice to only use … in a coin's solution" |
| **C3** | `SEND_MESSAGE`/`RECEIVE_MESSAGE`: "The `mode` parameter must be identical for both"; "exactly one of the source coin issues exactly one corresponding `SEND_MESSAGE`"; message ≤ 1024 bytes; sends and receives must balance per block (`conditions` §66/§67) | mode bits that commit less than the design assumes (sender by puzzle hash alone lets any coin at that hash send); a receiver that names the sender by amount only | under-committed handshake |
| **C4** | CAT ring announcements are namespaced: an inner puzzle's `CREATE_COIN_ANNOUNCEMENT` that is 33 bytes and begins `0xcb` is refused by the CAT layer (`cats`: prefixes, `morph_condition`); the NFT ownership layer refuses 34-byte `0xad4c…` puzzle announcements (`nfts`) | an inner puzzle that emits announcements shaped like its wrapper's | spend fails, or — if the wrapper forgot the guard — the inner puzzle can forge the wrapper's handshake |
| **C5** | p2_singleton asserts a *puzzle* announcement from the singleton "because if we curried [the coin id] in, the singleton could spend and then this puzzle becomes unsolvable", creates `'$'` back so the claim cannot be dropped, and asserts its own coin id so it cannot "piggy back on another claim" (`singletons`: Pay to Singleton) | a satellite keyed on a controller *coin id*; a satellite that does not announce back; a satellite that trusts a solution-supplied `my_id` | the three defects the reference puzzle exists to avoid |

**Mode bits.** Sender and receiver each get three bits — parent, puzzle, amount — so `0x3f`
(`111 111`) is coin-to-coin and `0x17` (`010 111`) is sender-by-puzzle to receiver-by-coin. The
docs' table (`conditions`, About MESSAGE conditions' `mode` parameter) is the reference; any
design that says "the pool sends to the reserve" must be read off the bits, not the prose.

---

## D. Signatures

| condition | what is appended to the message (docs: `conditions`) | replay surface |
|---|---|---|
| `AGG_SIG_ME` (50) | coin id, then genesis challenge | one coin — "the recommended condition for requiring signatures" |
| `AGG_SIG_PARENT` (43) | parent id, `sha256(genesis_id + 43)` | every child of one parent |
| `AGG_SIG_PUZZLE` (44) | puzzle hash, `sha256(genesis_id + 44)` | every coin at one puzzle hash — the fast-forward tool |
| `AGG_SIG_AMOUNT` (45) | amount, `sha256(genesis_id + 45)` | every coin of one amount |
| `AGG_SIG_PUZZLE_AMOUNT` (46) · `AGG_SIG_PARENT_AMOUNT` (47) · `AGG_SIG_PARENT_PUZZLE` (48) | the two named fields, `sha256(genesis_id + code)` | the intersection |
| `AGG_SIG_UNSAFE` (49) | nothing; "domain strings are not permitted at the end of `AGG_SIG_UNSAFE` messages" | everywhere, forever |

| row | rule (docs page) | what to look for | verdict if found |
|---|---|---|---|
| **D1** | `AGG_SIG_UNSAFE` carries no coin binding and may not end in a domain string (post-mortem 2023-05-08 linked from `conditions`) | an `AGG_SIG_UNSAFE` over a message that is not itself unique per spend (no nonce, no coin id, no expiry) | replayable authorisation; a TAIL or DID recovery signed this way is a standing permission |
| **D2** | Signature subtraction: given `A+B` and `B`, a farmer derives `A`; individual signatures leak on mempool eviction, re-org and RBF (`common_issues`: Signature Replay / Subtraction) | one-sided offers; any wallet that re-signs an identical message after a failed broadcast; any service that persists or re-broadcasts a bundle's signature | "the safest way to secure a one-sided Offer is to make it two-sided" — request 1 mojo; otherwise a nonce per bundle |
| **D3** | Vault rekey edge case: rekey A→B then B→A with no fee coin spent lets the old signature replay the A→B rekey (`attacks-and-countermeasures`: Edge Case) | a singleton whose puzzle hash can return to an earlier value, signed with `AGG_SIG_PUZZLE` and no coin id, nonce or expiry | replayable state transition; the docs' preferred fix is `ASSERT_MY_COIN_ID` on rekeys |
| **D4** | Fast forward: "assert the puzzle hash, but not the coin id, and instead use messages to specific coins to prevent replay attacks" (`attacks-and-countermeasures`: Fast Forward) | a singleton that wants mempool rebasing but emits `ASSERT_MY_COIN_ID`, or one that wants replay protection but relies only on `AGG_SIG_PUZZLE` | the two halves must both be present |
| **D5** | Standard transaction: `AGG_SIG_ME` over `sha256tree(delegated_puzzle)`; hidden path `synthetic = original + pubkey_for_exp(sha256(original ‖ hidden_hash))`, default hidden puzzle `(=)` (`standard-transactions`) | any address-derivation mirror (wallet daemon, indexer) that computes the synthetic key or p2 puzzle hash itself | parity: compare against a known address from Sage before trusting a scan |
| **D6** | `bls_verify` and `bls_pairing_identity` "return nil if … valid, otherwise raise" (`operators`) | a puzzle testing the *result* of `bls_verify` for truth | inverted check — valid signatures read as false |

---

## E. Time, height and ephemeral coins

Every `ASSERT_SECONDS_*` / `ASSERT_HEIGHT_*` condition is defined against **"the previous
transaction block"** (`conditions` §80–§87), not the block including the spend. `ASSERT_BEFORE_*`
means strictly before. From those two facts:

| row | rule (docs page) | what to look for | verdict if found |
|---|---|---|---|
| **E1** | Ephemeral coins "are not allowed to emit any relative time lock conditions; `ASSERT_SECONDS_RELATIVE`, `ASSERT_HEIGHT_RELATIVE`, `ASSERT_BEFORE_SECONDS_RELATIVE`, `ASSERT_BEFORE_HEIGHT_RELATIVE`, `ASSERT_MY_BIRTH_HEIGHT` or `ASSERT_MY_BIRTH_SECONDS`" (`conditions`: Ephemeral coins) | a puzzle that emits a relative lock or birth assertion on a coin the protocol may create and spend in one bundle | that path is unspendable ephemerally — a defect if the protocol needs it, a lock if it does not (class 13 uses this deliberately) |
| **E2** | Previous-block semantics plus strict `BEFORE` | an HTLC or auction whose claim window (`ASSERT_BEFORE_*`) and refund window (`ASSERT_*_ABSOLUTE`) meet at one boundary value; two branches both satisfiable against the same previous block | race the docs do not resolve for you: leave a gap, or make one branch exclusive by signature |
| **E3** | Flash loans (A4) and "ephemeral coins are not allowed to introspect their own creation height nor creation time" | a protocol that reads "this coin was born at height h" from its solution without `ASSERT_MY_BIRTH_HEIGHT` | the value is free |
| **E4** | Pooling: "with a large enough lock height and a big enough farmer … this singleton can be 'frozen'" (`pooling`) | relative lock heights that reset on every spend of a frequently-spent object | liveness, not theft — name it as such |

---

## F. Singleton invariants (`singletons`)

What the reference top layer enforces, and therefore what a probe of any singleton-wrapped design
must show still holds after the inner puzzle has had its say:

| row | invariant | probe |
|---|---|---|
| **F1** | amount is odd; exactly one odd `CREATE_COIN` child (or `-113` melt); the odd child is re-wrapped. "If an attacker were to launch an even singleton … it would succeed, but be stuck forever." | emit two odd outputs → refused; emit an even "successor" → accepted and dead — check the builder can never do this |
| **F2** | lineage proof: 3 fields for a normal parent, 2 for the eve; the eve path must verify `launcher_id == sha256(parent_parent, LAUNCHER_PUZZLE_HASH, amount)` | eve spend with a forged launcher id → refused |
| **F3** | the launcher's solution is protected only by its *parent* asserting the launcher's announcement: "if any of those values are changed, the coin that creates the launcher will fail" | a creation bundle whose parent does not assert the launcher announcement lets a farmer rewrite `key_value_list` and the singleton's first puzzle hash |
| **F4** | `singleton_truths` are prepended to the inner solution: "an inner puzzle needs to know that it is going inside a singleton or else all of its solution arguments will be shifted to the right" | an inner puzzle written standalone and later wrapped without `(a (q . INNER) (r 1))` |
| **F5** | pay-to-singleton: puzzle announcement in, `'$'` announcement out, `ASSERT_MY_COIN_ID` (C5) | each of the three removed in turn → the docs name the attack each one stops |

---

## G. CAT and TAIL invariants (`cats`)

| row | invariant | probe |
|---|---|---|
| **G1** | the TAIL runs only when the inner puzzle emits `(51 0 -113 TAIL SOLUTION)`; "if the extra delta is anything other than 0, the TAIL program is forced to run"; "if the TAIL program is not revealed and the extra delta is not 0, then the spend will fail" | spend with `extra_delta ≠ 0` and no reveal → refused; with reveal and a TAIL that forgets to check `delta` → mint |
| **G2** | "The TAIL should check diligently for and authorize or reject … Is the extra delta issuing or melting any coins? Is this coin's parent not a CAT of the same type?" — and `lineage_proof` "is only guaranteed to be true if `parent_is_cat`" | any TAIL branch reachable with `parent_is_cat` false and `delta < 0` → impostor melt (class 4) |
| **G3** | "If the TAIL is programmed incorrectly, the tokens may be issued by attackers … There's no easy way to patch the TAIL" | treat a TAIL review as irreversible: the completion gate is stricter than for an inner puzzle |
| **G4** | ring announcements carry `0xcb`; inner announcements of that shape are refused (C4) | inner puzzle emits a 33-byte `0xcb…` announcement → refused |
| **G5** | 1 CAT = 1000 mojos, "the official Chia wallet will not support CATs with a ratio other than 1:1000" | a builder or quote that assumes any other ratio |
| **G6** | `everything_with_signature` signs `delta` with `AGG_SIG_ME`; `delegated_tail` signs `sha256tree(delegated_puzzle)` with `AGG_SIG_UNSAFE` — "any permissions granted can never be revoked" | a delegated TAIL in use: list every delegated puzzle ever signed; each is a permanent mint/melt key (D1) |

---

## H. Offers and settlement (`offers`)

| row | rule | what to look for |
|---|---|---|
| **H1** | `settlement_payments` asserts every payment amount `> 0` and announces `sha256tree(notarized_payment)` as a *puzzle* announcement; "every coin id needs to be included in the nonce to prevent the maker from creating two offers that can both be completed with just one payment" | a builder that constructs notarized payments with its own nonce rule; a zero-amount payment |
| **H2** | "If an offer file falls into a hacker's hands, they only have two options … Ignore the offer; Accept it" — an offer is a bearer instrument | offer strings logged, stored in a public index, returned by an unauthenticated route, rendered with a copy button (Forge finding 10) |
| **H3** | "If the offer is already publicly available, it will have to be cancelled on-chain … by spending the coins involved" | a service that marks an offer cancelled, expired or failed without a spend of the maker's coins, and stops guarding the bytes |
| **H4** | one-sided offers and signature subtraction (D2) | an airdrop or free-claim offer with an empty requested side |
| **H5** | "Offers trade by puzzle not specific coins … anyone can accept the offer" and may be aggregated | a protocol that assumes a particular taker, or that the maker's coins settle against exactly one counterparty |

---

## I. Cost and denial of service (`costs`; `attacks-and-countermeasures`)

| quantity | value (docs) |
|---|---|
| block cost limit | 11,000,000,000 |
| per serialized byte (puzzle reveal + solution) | 12,000 |
| `CREATE_COIN` | 1,800,000 |
| every `AGG_SIG_*` | 1,200,000 |
| `coinid` base / `sha256` | 480 / 87 base + 134 per argument + 2 per byte |
| `/` · `divmod` · `>` · `strlen` · `concat` | 988 · 1116 · 498 · 173 · 142 (+135 per arg) |
| malloc | 10 per byte of result, except 0 and 1 |
| `run_program` with `max_cost = 0` | unlimited ("`Cost::MAX`") |

| row | rule | what to look for |
|---|---|---|
| **I1** | a puzzle that recurses over a solution-supplied list is bounded only by block cost | is the list length constrained? can a hostile solution make the honest counterparty's bundle exceed the limit (a griefing vector on shared bundles)? |
| **I2** | "Use the non-backref deserializer (`node_from_bytes`) for all untrusted CLVM deserialization … the backref-aware deserializer should only be used when the source is trusted" and "all production `run_program` calls should use `MAX_BLOCK_COST_CLVM`" | every off-chain call site that parses or runs CLVM from the chain, a wallet, an HTTP body or a peer: which deserializer, which cost cap |
| **I3** | "Move data and similar fields should be typed as flat byte strings with explicit length checks, not arbitrary CLVM trees" | protocol messages that embed a CLVM tree where bytes would do |
| **I4** | `defun-inline` "gets verbatim copied multiple times"; `(logand x 1)` beats `(r (divmod x 2))`; "the more parameters a function or program has, the more cost will be paid" (`optimization`) | cost regressions between revisions; a leaf that newly recurses |

---

## K. Language footguns (`syntax`; `operators`; `modern-chialisp`; `debugging`)

| row | rule | what to look for |
|---|---|---|
| **K1** | a hex literal without `0x` "will compile as a string" (`first-smart-coin`); names inside `q` are not substituted (`syntax`) | constants and puzzle hashes in source; anything quoted that was meant to be computed |
| **K2** | `if` is lazy; `i` evaluates both branches; Chialisp "doesn't natively have `and` and `or`" and `all`/`any` document no short-circuit (`operators`; `modern-chialisp`) | a `substr` or `f`/`r` guarded by a length or list check through `all`/`any` instead of `if` — the guard does not protect it |
| **K3** | `/` "always rounds towards negative infinity" (re-enabled at the hard fork after the 2,300,000 soft-fork disablement); `divmod` likewise; `modpow` "exponent must not be [negative], modulus must not be 0" (`operators`) | arithmetic on values that can be negative; an `assert x >= 0` that reads as redundant (Forge's was load-bearing) |
| **K4** | `(x)` is the only failure; a function that returns nil does not stop a spend | validators whose result is not consumed by `assert`/`if … (x)` |
| **K5** | pooling mask attack: a solution integer OR'd into a prefix must be masked — "only bits on the right can change", else "a pool could grind out a coin whose parent ID has all of those bits set" (`pooling`) | any `logior`/`concat` of a solution value into an identifier or namespace |
| **K6** | condition morphing rebuilds conditions; the coin-doubler example keeps only opcode, puzzle hash and amount (`condition-morphing`) | wrappers that drop memos/hints from `CREATE_COIN`, so wallets cannot find the child (`conditions`: Memos and Hinting — first 32-byte memo is the hint) |
| **K7** | modern Chialisp (`(include *standard-cl-24*)`) "guarantees that programs with a specific sigil … compile to the same representation forever"; classic does not. `defconst` is computed at compile time and "the compiler chooses the smaller representation of inlining it or placing it in the environment" (`modern-chialisp`) | can the committed hex be reproduced from source with the pinned compiler? does the repo say which compiler? a `defconst` whose placement moved between builds changes the puzzle hash |
| **K8** | strict vs non-strict CLVM: "an unknown opcode will cause the program to terminate … non-strict mode … allows for unknown opcodes to be used and treated as no-ops" (`clvm`) | a test runner on `brun` defaults where consensus is strict; `softfork` guards that "pre-softfork … always pass and return `()`" |
| **K9** | "a variable typo will often result in the variable being evaluated as a string, and if that gets hashed into something it's impossible to tell" (`debugging`); modern mode turns this into a diagnostic | classic-mode puzzles: grep every symbol against the argument list and definitions |

---

## The toolchain probe (`commands`; `costs`; `debugging`)

The docs' own command set is enough to verify a shipped artefact without trusting the repository
that shipped it. Run these before reading any source:

```bash
# 1. Rebuild and compare. Classic: run; project: cdv clsp build. Include path matters.
run -i include puzzle.clsp > rebuilt.clvm
cdv clsp build puzzle.clsp
# 2. Serialise and hash. opc -H is the tree hash == puzzle hash of an uncurried program.
opc rebuilt.clvm            # compare to the committed .hex byte for byte
opc -H rebuilt.clvm         # compare to the committed .hash
cdv clsp treehash puzzle.clvm.hex
# 3. Curry exactly as the builder does, then hash — this is the address users pay to.
cdv clsp curry puzzle.clsp -a 0x<param> ... | opc -H
cdv clsp uncurry <curried hex>   # read back what was actually curried into a live coin
# 4. Disassemble the hex you were given, not the source you were shown.
opd <hex>  |  cdv clsp disassemble puzzle.clvm.hex
# 5. Run the honest solution and the attacker's, with cost, with the symbol table.
brun --cost -y main.sym rebuilt.clvm '(<solution>)'
brun --verbose ...   # follow "(didn't finish)" to the deepest failure
# 6. Cost of a whole bundle as the mempool would see it.
cdv inspect spendbundles bundle.json -ec
```

What each step decides: (1)–(2) whether the artefact is the source (J-rows); (3) whether the
builder's address is the puzzle's (B4/D5); (4) what a live coin actually runs (K7); (5) the A–K
rows for one spend; (6) I1. A probe that skips (1)–(2) has audited a document, not a program.

---

## Recurring defect classes — the Chialisp.com rows

The rows above, flattened, so a report can mark each one. Every row cites the page that
establishes it; "Forge class" maps to the catalogue in `clvmPuzzleAudit.md` where one exists.

| row | class | docs page | Forge class |
|---|---|---|---|
| A1 | secret-in-solution selects payout | `common_issues` Password Coin | — |
| A2 | unbound solution field | `common_issues` Unprotected Solution | 1 |
| A3 | unlinked spends in one bundle | `common_issues` Splitting / RBF | — |
| A4 | amount-exists assumption | `common_issues` Flash Loans | — |
| A5 | unbounded or unconstrained solution bytes | `attacks-and-countermeasures` DoS | 15 |
| B1 | unchecked-width hash preimage | `common_issues` Unchecked Hashing | 15 |
| B2 | non-canonical integer as bytes | `clvm` Integer Representation | 15 |
| B3 | bytewise program comparison | `clvm` Serialization | — |
| B4 | hash-form mirror mismatch | `debugging` sha256tree | 5, 7 |
| C1 | announcement without consumer id | `common_issues` Unprotected Announcements | 11 |
| C2 | assert-coin-announcement in puzzle body | `conditions` warning | — |
| C3 | under-committed message mode | `conditions` §66/§67 | — |
| C4 | wrapper-shaped inner announcement | `cats` prefixes; `nfts` | — |
| C5 | satellite keyed on controller coin id / no return announcement / trusted my_id | `singletons` p2_singleton | 1, 2 |
| D1 | AGG_SIG_UNSAFE without uniqueness | `conditions` §49 | — |
| D2 | signature subtraction / one-sided offer | `common_issues` Signature Replay | — |
| D3 | rekey replay to an earlier puzzle hash | `attacks-and-countermeasures` Edge Case | — |
| D4 | fast-forward half-implemented | `attacks-and-countermeasures` Fast Forward | — |
| D5 | address-derivation mirror drift | `standard-transactions` | 7 |
| D6 | bls_verify result used as truth | `operators` | — |
| E1 | relative lock on a possibly-ephemeral coin | `conditions` Ephemeral coins | 13 |
| E2 | overlapping or adjacent time windows | `conditions` §80–§87 | — |
| E3 | birth read from solution | `conditions` Ephemeral coins | 13 |
| E4 | liveness freeze by lock height | `pooling` | — |
| F1–F5 | singleton invariants | `singletons` | 2, 6 |
| G1–G6 | CAT / TAIL invariants | `cats` | 4 |
| H1–H5 | settlement and bearer offers | `offers` | 10 |
| I1 | solution-bounded recursion vs block cost | `costs` | — |
| I2 | untrusted CLVM without cost cap / with backrefs | `attacks-and-countermeasures` DoS | — |
| I3 | CLVM tree where bytes would do | `attacks-and-countermeasures` DoS | — |
| I4 | inline duplication / cost regression | `optimization` | — |
| K1–K9 | language footguns | `syntax`, `operators`, `modern-chialisp`, `clvm`, `debugging` | 9 |

---

## Audit routine for a Chialisp puzzle

1. **Artefact first.** Reproduce the hex from source with the pinned compiler; tree-hash it;
   uncurry a live coin and compare (toolchain probe steps 1–4). Record the compiler, the include
   path, and the digest. "Which build did you test" comes before every other answer.
2. **Enumerate the solution.** Every field: signed, asserted, derived, bound, or *free*. A free
   field that changes the outcome is a finding (A1/A2) before any probe runs.
3. **Enumerate the conditions.** Every emitted condition against the C/D/E tables: what it
   commits, who else can satisfy it, whether it lives in the puzzle or the solution, what it does
   on an ephemeral coin.
4. **Rule 0 pass.** For each authorisation: can the farmer rewrite it? can a split bundle land
   half of it? who counts the assertions?
5. **Primitive pass.** If wrapped in a singleton, CAT, NFT layer or settlement puzzle: the F/G/H
   invariants as probes, honest case beside each.
6. **Width and encoding pass.** Every hashed or signed preimage: widths fixed? integers
   canonical? (B1/B2/A5). Feed 0, 1, 4, 31, 33, 64 bytes and a non-canonical integer.
7. **Time pass.** Each `ASSERT_*` against the previous-block rule; windows checked for overlap and
   adjacency (E2); every relative lock checked against the ephemeral case (E1).
8. **Cost pass.** `brun --cost` honest and hostile; the longest solution list the puzzle accepts;
   `cdv inspect spendbundles -ec` on the composed bundle (I1).
9. **Off-chain pass.** Every deserializer and `run_program` call site (I2); every place an offer or
   bundle is stored, logged or served (H2/H3); every signature persisted (D2).
10. **Language pass.** K1–K9 by grep: unprefixed hex, `all`/`any` guards, `/` on signed values,
    `bls_verify` truth tests, unmasked `logior`, dropped memos, strict-mode runner.
11. **Record** in the finding format below, one row id per finding, PASS table for the rows that
    held, and an explicit "not evaluated" list. A report with no PASS table has not said what it
    looked at.

---

## Finding format

The strict format from the published runbook (`skills/n-asset-pool-audit/SKILL.md`), with one
field added so every claim names its rule:

```
### [ID] — [title]
- Severity: Critical / High / Medium / Low / Info
- Status: CONFIRMED (executed against the compiled artefact) / PROVISIONAL (reasoned)
- Docs row: e.g. A1 (common_issues: Password Coin)
- Where: path:line, with the lines quoted
1. Observed condition & exploit path
2. Probe (honest control beside the attack; the refusal code pinned, not "refused")
3. Chain verification command, if the finding depends on a live object
4. Remediation — minimal, in the source language the target uses
```

Severity follows consequence, not row letter: a C2 brick on a coin holding funds is High; the
same row on a fee coin is Low. A PROVISIONAL finding is still a finding; it is labelled so the
reader knows which half of the work remains.

---

## What this spec does not cover

The docs are silent on several things an auditor still needs, and a review should say when it
is relying on one of them rather than on the site:

- the exact inputs `coinid` rejects (the operators page says only "validates inputs")
- `all`/`any` evaluation order
- NFT transfer-program and royalty source (the page says only that royalties "get paid upon sale")
- CHIP-0050 action layers, CHIP-0038 revocable CATs, vault MIPS puzzles — covered in the
  workspace by `chip0050ActionLayer.md`, the rCAT section of the published runbook, and
  `forgeMultisig.md`
- the lane discipline (offline validator vs simulator vs chain) — `clvmPuzzleAudit.md` Rule 0.5

Where the docs' own printed code looked wrong on reading (the DID recovery recursion appears to
drop an argument; the NFT ownership layer's odd-check reads as unary `logand`), the rule is the
one the docs teach everywhere else: verify against the upstream `.clsp` in `chia-blockchain`, not
against a rendering of it.

---

## Reference

- The run this spec was written for: [`docs/CHIALISP_AUDIT_2026-10-07.md`](../../CHIALISP_AUDIT_2026-10-07.md)
  — four repositories, findings by row, PASS tables, and what was not evaluated.
- Pages, in sidebar order: `/intro`, `/chialisp-primer/*`, `/chialisp-concepts/{currying,
  inner-puzzles, condition-morphing}`, `/commands`, `/syntax`, `/modern-chialisp`, `/operators`,
  `/examples`, `/costs`, `/conditions`, `/optimization`, `/common_issues`,
  `/attacks-and-countermeasures`, `/debugging`, `/primitives/{standard-transactions, singletons,
  cats, nfts, dids, offers, pooling}`, `/clvm`. Source: `Chia-Network/chialisp-web` on GitHub,
  which is where to read them if the site is unreachable.
- Post-mortems the docs cite: CAT1 (2022-07-29), TibetSwap v1 (blog.kuhi.to), AGG_SIG_UNSAFE
  mimicry (Chia-Network/post-mortem 2023-05-08).
- Related skills: `clvmPuzzleAudit.md` (the method and the Forge-derived catalogue — load first),
  `chiaPrimitivesPatterns.md` (singleton and CAT fundamentals), `forgePuzzleV14.md` and
  `forgeLpCat.md` (the shipping Forge shape), `greenwoodLockbox.md` (an EIP-712 custody puzzle),
  `forgePoolLifecycleTesting.md` (what to run). Companion runbook, outside this repo:
  `skills/n-asset-pool-audit/SKILL.md` in `awizardxch/forge-puzzles`.
