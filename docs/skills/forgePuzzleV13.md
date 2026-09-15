# Skill: Forge Puzzle V13 — the second-audit revision

> The Forge pool on the CHIP-0050 action layer, revised after a second independent audit
> of V12 (Chia-Network/chips#217, comment 5666370916, 2026-09-14; six adversarial agents,
> `chia_rs`-executed bundles). Protocol **14**. V12 is closed and drained: one of its
> findings is a demonstrated 99.8% drain of an unregistered pool. Design and disposition:
> `projects/chia-cfmm/docs/FORGE_PUZZLE_V13.md`. Everything in `forgePuzzleV11.md` still
> describes the shape, the leaves, the finalizer and the TAIL, and `forgePuzzleV12.md`
> describes the four CNI fixes V13 carries unchanged; this file is the delta.
> **Not externally audited. Testnet only.**

---

## Domain

Load with `forgePuzzleV11.md` for any V13 pool work. Load alone when the question is
"what changed and why" since V12.

## Why a major increment

Three fixes change what a pool coin *is*: state gains a field, the finalizer gains three
curried arguments, and the registry's admission rules change. Every puzzle hash moves and
the V12 registry cannot admit a V13 pool. That is not a point release.

## The three changes, and the finding each answers

| Finding (severity) | V12 hole | V13 |
|---|---|---|
| Cross-leaf configuration mismatch (HIGH) | The action layer proves a leaf is in the merkle root and never that the six leaves agree. Six leaves of six configs make a valid root. A `remove` curried with a foreign `lp_tail_hash` answers the pool's release message with a worthless self-minted CAT: 99.80% of both reserves, reproduced. Registered pools were safe (registration rebuilds the root from one config); nothing at the coin level said which was which. | The finalizer is curried with `CONFIG_HASH`, the six `LEAVES` mod hashes and `POOL_SLOT_1ST_CURRY_HASH`, rebuilds the six-leaf root with `config_root` and asserts `Truth.Merkle_Root ==` it, every spend. `six_leaf_root` moved from the registry into `forge_action_common` so both compute it once. |
| The oracle discards the interval between a claimed height and its inclusion (MEDIUM-HIGH for consumers) | `last_height = h` but only `h - birth` credited, so `(h_prev, birth]` was lost and could never be recovered. Claiming `h = birth` froze the accumulator for free; an honest pool spent every block did the same by accident. | `Oracle` gains `last_spot`. The prologue asserts `birth > last_height`, then credits `last_spot * (birth - last_height) + spot * (h - birth)`. Every block is credited once at the price in force. Understating `h` defers credit instead of destroying it. `oracle_window` and `price_scale` are now bounded. |
| `MIN_LOCKED_LP` was never burned by the reference creation path (MEDIUM) | `scripts/deploy-v12-testnet.py` burned it; `contracts/forge_v12_create.py` — the website lane — paid the whole genesis supply to the creator. The standing reply to CNI described the deploy script as though it were the implementation. | The genesis mint lands at `CAT(lp_tail, OFFER_MOD)`, whose payments are announced, and `register` asserts the announcement of `[[zero_bytes32(), MIN_LOCKED_LP]]` under the launcher id. Only the TAIL's genesis branch can create that asset, so this also proves the mint happened (closes the INFO finding). |

Alongside: `valid_pool` requires `total_lp > MIN_LOCKED_LP` (V12's `>=` left the creator
nothing redeemable at the boundary); the prologue asserts `total_lp >= MIN_LOCKED_LP` so a
pool minted below the floor outside the registry is unspendable rather than a trap;
`RegistryConstants` pins `protocol_puzzle_hash`, `price_scale` and `oracle_window`, so a
registrant cannot take a market's key with a pool that pays the protocol fee to
themselves; and `collect` pays one coin when the protocol and DAO recipients are equal,
which V12 refused as `DUPLICATE_OUTPUT` with the fees still owed.

## What was NOT changed, and why

**No deregistration or expiry.** A registered pool cannot die (the floor keeps it alive)
and a thin pool is a live market anyone can deepen, so "the key is taken" means "the
market exists". A minimum reserve would price small markets out without stopping a
squatter who pays one creation fee.

**`add`'s `assert deposit >= 0` stays, and the audit's I-1 does not reproduce.** Rebuilt
without that line, the leaf still refuses a negative deposit, and a search over deposit
vectors with a negative slot found no mint the bracket accepts: `exact_invariant_lp_mint`
is two-sided, and a negative slot drives `min_deposit_ratio` negative, putting the target
below `total_lp^K * old_product`. Verified against a compiled mutant, not argued from the
source. The mutation run reports SURVIVED and that is genuine redundancy.

**No `strlen` asserts (L-2).** rue 0.8.4 emits none, and every solution-sourced `Bytes32`
feeds a sha256 preimage compared against a consensus-committed id, so a wrong width yields
an identifier that exists nowhere. Recorded as hardening. Re-check if a future revision
ever compares a derived hash against something that is not a committed id.

## What pins what

`_test_v12_v13_review_findings.py` is the before-and-after for every finding that needed
a puzzle change: each attack must be ACCEPTED against V12 and REFUSED against V13, so a
finding that stops reproducing fails the suite rather than quietly testing nothing. It
covers the cross-leaf drain, the discarded oracle interval, the unburned floor, the
boundary, the fee-recipient squat and the `collect` brick.

`_test_v13_oracle.py` runs the auditors' two scenarios directly: eight honest spends in
consecutive blocks credit every block once, and ten `h = birth` claims end at the same
total as one honest observe. `_test_v13_lp_receive_forgery.py` case E2 is the cross-leaf
shape beside the honest control. `_test_v13_registry.py` covers the burn, the boundary and
the three pinned parameters. `_test_v13_actions.py` covers the prologue floor on both
sides and the merged `collect`.

Mutation (`scripts/mutate-v13.py`): all four new asserts are killed —
`birth > last_height` and `last_spot is nil` by the oracle suite,
`total_lp >= MIN_LOCKED_LP` and `h >= birth` by the actions suite. Full sweep 2026-09-14:
13 of 34 killed, 21 survived, 0 unbuildable; the survivors are the documented
defence-in-depth twins whose brackets already refuse.

## Files

`contracts/v13/` (rue), `forge_v13_driver.py`, `_v13_testkit.py`,
`forge_v13_{offer,route,create,index,resync}.py`,
`scripts/{build-v13,deploy-v13-testnet,v13-launch.sh,mutate-v13,plan-v13-matrix,
v13-lifecycle-matrix,v13_ops,v13-sage-labels,import-v13-pools.mjs,live_v13_probe}`,
`scripts/v12-drain.py` (the V11 drain generalized to the locked floor), record
`.awizard/v13-testnet.json`, `FORGE_PROTOCOL_VERSION = 14` in `api/_forgeVersion.js` and
`src/lib/poolIndexer.ts`, create endpoint `api/forge-v13-create.js` with
`src/lib/forgeV13Create.ts`.

**A new test leaf.** `passthrough_action.rue` now takes a curried config, and
`passthrough_observe.rue` joins it, because the finalizer's root assertion means a test
pool needs six leaves behind one binding rather than one leaf alone.

**The fee model moves with the puzzle.** V13's finalizer rebuilds the root every spend, so
bundles cost about 3% more than V12's: worst measured 225,764,711 per pool against V12's
218,602,540. `COST_PER_POOL` in `src/lib/networkFee.ts` went 220M to 235M. A constant left
below the real cost puts the fee under the node's 5 mojo/cost floor and strands a signed
offer in the trader's wallet, so re-measure it whenever the puzzle changes.

**The matrix is planned, not hand-carried.** `scripts/plan-v13-matrix.py` sizes every pool
from one price table so the matrix is arbitrage-free at genesis, reads live balances, and
emits `v13-launch.sh`. V12's numbers were carried from V11 by hand and had drifted far
enough that a route could profit from the matrix rather than the router.
