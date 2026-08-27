# Forge Security Audit — findings log

Internal audit of the Forge pool puzzles and their builders, carried out on **2026-08-24** after
the TibetSwap V2 incident prompted a review of our own authorisation logic. Every finding was
found by probing the **real compiled puzzles**, not by reading them; each has a proof-of-concept
or a regression test that fails against the vulnerable revision and passes against the fixed one.

**Status: 10 findings, all fixed. V10 is the shipping revision.**

Forge is testnet-only and unaudited externally.

> This is the repo-resident record, kept here because this repository is the agent's standalone
> knowledge base. The full log — with proof file names, the exact numbers each probe produced, and
> the reproduction commands — lives with the code in the workspace at
> `projects/chia-cfmm/docs/FORGE_SECURITY_AUDIT.md`, which is **not** published here.
>
> The transferable method is in [skills/clvmPuzzleAudit.md](skills/clvmPuzzleAudit.md); the
> shipping shape is in [skills/forgePuzzleV10.md](skills/forgePuzzleV10.md).

---

## Summary

| # | Finding | Severity | Introduced | Fixed in |
|---|---------|----------|-----------|----------|
| 1 | LP burn was unauthenticated — withdraw reserves without owning LP | **Critical** | V4 | V9 |
| 2 | Reserves were not bound to their pool — anyone could drain any pool | **Critical** | V4 | V10 |
| 3 | Creation could mint an unspendable pool, stranding the deposit | High | V8 | builder |
| 4 | A fabricated coin could satisfy an LP melt | High | V9 | TAIL |
| 5 | Mint maths disagreed with the puzzle for weighted pools and vaults | Medium | V7 | builder |
| 6 | Vault redemption unbuildable in all three routing lanes | Medium | V9 | builders |
| 7 | Frontend quotes disagreed with the puzzle (same defects as 5) | Medium | V7 | `cfmm.ts` |
| 8 | Swap maths was weight-blind in two more places | Medium | V7 | `forge_math.py` |
| 9 | Every V10 pool worked exactly once — successor snapshots unreadable | Medium | V8 | serialiser |
| 10 | Create-pool offers were served to anyone who asked | **Critical** | — | HTTP boundary |

Two (1, 2) are fund-loss bugs reachable by any third party. Finding 3 is fund-loss but
self-inflicted. Findings 4 and 6 were **introduced by the fixes for earlier ones**. Findings 5, 7
and 8 are one arithmetic defect repeated across four independent implementations of the same
curve. Findings 5 and 9 are the same structural mistake in two guises. Finding 10 involved no
puzzle at all.

---

## 1. LP burn was unauthenticated (Critical, V4–V8)

On a remove, the pool released reserves in exchange for burning LP, and its only link to that burn
was a coin announcement whose id came from a free field in the action — checked only `!= 0`.
Nothing tied it to the pool's own LP CAT.

A coin announcement's id is `sha256(coin_id, message)`, and **any coin running any puzzle can emit
any message**. An attacker names a plain coin they control, spends it emitting the
acknowledgement, and the pool releases reserves. No LP is destroyed. Repeatable up to
`total_lp - 1` per spend. Same class as TibetSwap's V1 bug, not their V2 one.

**Fixed in V9** by having the pool derive the LP action coin's id itself, from the LP parent, the
CAT puzzle hash of the pool's own TAIL wrapped in a **pinned inner**, and the amount. Binding the
id alone was not sufficient: the honest path used a plain `identity` inner that imposes no melt,
leaving "own the LP, spend it without burning, collect the reserves". Pinning the inner is what
closes it.

## 2. Reserves were not bound to their pool (Critical, V4–V9)

The reserve inner puzzle was never curried. Every pool of a revision shared one reserve puzzle,
and the pool's identity arrived entirely in the solution — `launcher_id` was asserted non-zero and
then never used for anything. The sole authorisation was a coin announcement keyed on a pool coin
id the spender also supplied.

So the attacker picks a coin they already own, derives the message from their own crafted plan,
and announces it. **The pool singleton is never involved at all.** Worse, the solution also
carried the puzzle hash the successor reserve is recreated at — so the "successor" could be a
puzzle the attacker controls. Strictly worse than finding 1: it needs no LP, no pool, and no
interaction with the protocol.

**Fixed in V10** by three changes, each load-bearing:

1. `launcher_id` is **curried**, so a reserve's puzzle hash commits to its pool.
2. The authorisation is a **puzzle announcement** asserted against the owning pool's singleton
   puzzle hash, rebuilt in-puzzle from the curried launcher and the pool's inner puzzle hash. Only
   a genuine singleton of that launcher can carry that puzzle hash, and a coin fabricated at the
   same hash cannot be spent — the singleton top layer checks lineage back to the launcher.
3. `AssertMyPuzzleHash` pins the solution-supplied reserve hash to the puzzle the coin actually
   runs, so the successor is always a real reserve of the same pool.

*Verification note:* the first re-run of the proof-of-concept against V10 failed with an **arity**
error from the changed solution shape — which would have looked like a fix without being one. A
dedicated suite drives the V10 shape properly and confirms each mechanism separately.

## 3. Creation could mint an unspendable pool (High)

The deploy path accepted a protocol fee with no recipient: an absent recipient falls through to
32 zero bytes, which passes a length check, while the puzzle asserts the recipient is non-zero
whenever the fee is. The result is a singleton minted on chain holding the full bootstrap deposit
whose config validation fails on every spend.

The code comment beside the check assumed such funds were "recoverable". **Under V10 they are
not:** a reserve only moves on an announcement from its own pool, and a pool that cannot pass
config validation can never produce one. The deposit is permanently gone.

**Fixed** by mirroring the puzzle's entire config validation in the builder and running it before
anything is built from the config — so any future divergence fails at build time, not on chain.

## 4. A fabricated coin could satisfy an LP melt (High, V9)

Introduced by finding 1's fix. CAT2 lets a coin with no valid lineage be spent when the TAIL
authorises it, so an attacker could `CREATE_COIN` at the melt puzzle hash out of an ordinary coin
and melt an amount that was never issued. For a non-CAT parent the TAIL scored `amount + delta`,
so choosing `delta = -2 * burn` made the effective delta equal whatever burn the pool asked for.

Binding the melt coin's id stops an impostor *puzzle*; nothing stopped an impostor *coin*.

**Fixed** with `parent_is_cat || expected_delta > 0`. A melt destroys supply, so it can only come
from a coin that held supply; minting stays open because a genesis eve has no CAT parent by
definition.

*This case had been reasoned to be already blocked. The probe disproved the reasoning.*

## 5. Mint maths disagreed with the puzzle (Medium, V7)

The builder's mint reference was not weight-aware: it took no weights, raised the invariant to the
**asset count** instead of the **sum of the weights**, and shared the imbalance fee as `(n-1)/n`
instead of `(K-k_i)/K`. From V8 it also missed that a vault charges the liquidity fee on the whole
deposit.

Not theft — the puzzle brackets the mint exactly and refuses anything else, so a disagreement is a
deposit that can never settle. Weighted pools and V8+ vault deposits were silently unbuildable.

It survived because symmetry hides all of it: equal weights hide the exponent, a balanced deposit
hides the fee share, and V7 vaults are free so the vault case only breaks from V8. Nothing
exercised a weighted or V8+ vault **add**.

**Fixed** by threading weights and version through the mint path, with two version gates: **V6
stores weights as basis points** in the same config slot, and **V7 vaults must stay free**.

## 6. Vault redemption was broken on V9/V10 (Medium — availability)

The vault-redeem path routes LP through an intermediate coin the TAIL can melt. V9 pinned that
coin to a specific melt puzzle, but **all three routing implementations** still wrapped it in a
bare identity puzzle, and V10's action shape was never added. Any route crossing a vault was
unbuildable.

It hid because every vault suite runs against **live V7 chain pools**. Fixed in all three lanes;
the duplicated 105-line copy was deleted in favour of importing the shared implementation.

## 7. Frontend quotes disagreed with the puzzle (Medium)

The TypeScript quote carried **the same three defects as finding 5**, independently: no weight
exponents, the asset count as the invariant's exponent, and `(n-1)/n` as the imbalance share. It
also had no vault branch, so a V8+ vault deposit was quoted free, and the withdrawal quote was
exactly proportional with no vault fee.

The user signs an Offer for a mint the chain will refuse. No funds move, but weighted-pool and
V8+ vault deposits fail from the UI.

**Fixed** by making both quote paths weight- and version-aware, and pinning them to the same
expected values as the Python parity suite — so the two implementations are anchored to the same
third party: the puzzle.

## 8. Swap maths was weight-blind in two more places (Medium, V7)

Found by following up a question about whether the frontend's swap quote was right for V10. It
was. Two Python functions were not: the direct swap output and the route planner's leg solver,
both plain constant product.

The puzzle holds `reserve_in^w_in * reserve_out^w_out` constant and brackets the output exactly.
The closed form is only exact when the traded pair's weights are equal — at `[4,1]` the puzzle
allows 194,527 where the builder computed 49,357.

Weighted swaps were unbuildable directly and through routes, and because the frontend quoted them
*correctly*, the two disagreed in the worst direction: a quote the user could see and sign, and a
bundle that could never settle.

**Fixed** by reproducing the puzzle's bracket with a binary search when the weights differ, keeping
the closed form where it is exact and cheaper. This was the **fourth** implementation of the same
curve in the codebase; three of the four were weight-blind, and the correct one was correct by
accident.

## 9. Every V10 pool worked exactly once (Medium — availability)

Pool config is positional. V8 inserted the protocol fee and its recipient at indices 5 and 6,
pushing the LP asset id and the reserve inner puzzle hash from 5/6 to 7/8. The JSON serialiser was
never updated and kept reading the reserve hash from index 6 — so on every V8+ pool it serialised
the **protocol fee recipient** as the reserve hash, and omitted the two fee fields entirely.

This is not a display path: the responder writes that JSON into the deployment index as the pool
snapshot and hands the same field straight back on the pool's next action. The loader verifies the
reserve hash, so it rejected the snapshot the responder had just written — **a V10 pool settled
its first action and then failed every one after it.** Had the guard not been there it would have
been worse: the pool would have been rebuilt with a zero protocol fee, hashing to a different
inner puzzle, and spent against a pool that does not exist.

**Fixed** by indexing both fields from the END of the config, where they have sat in every
revision. Found while building a routing lane, not by a test — nothing exercised the
serialise-then-reload path, because every suite builds its pools in memory.

## 10. Create-pool offers were served to anyone who asked (Critical — off-chain)

Not a puzzle bug. The puzzle was never involved, which is why nothing in the contract suites could
have caught it.

The wallet RPC will not build an offer with an empty requested list. A pool whose reserves are all
CATs has no native leg to ask back, so the UI manufactures a request: it asks for **one mojo of a
CAT it is already offering**, and adds that same mojo to the offered side so the amounts wash out.
The router settles that mojo while it spends the launcher, so the creator pays nothing and the
pool receives its exact bootstrap. Internally consistent.

Read as a standalone offer, the same bytes say something else entirely — *offering 1.100 XCH +
10.001 T6, requesting 0.001 T6*. Pay one mojo, receive the pool's entire genesis reserve. Whoever
takes it first gets it.

Those strings were stored in the local offer index and served in full by two **unauthenticated**
GET endpoints. Fifteen such records were present, eight in a `deploy-failed` or `stale` state —
meaning their coins were plausibly never spent and the offers were still live. On testnet, so the
loss was play money; the same code on mainnet hands out every pool's bootstrap for a mojo apiece.

**Fixed** by stripping the offer at the HTTP boundary rather than in storage, since the router
legitimately needs the raw bytes in-process. Detection is deliberately over-broad — source, id
prefix, **or** status — and permanent: a record that has moved on to `matched` or `deploy-failed`
is still a creation record, and its coins may still be unspent.

**What this does not fix.** The offer is still free money to anyone holding the bytes. Redaction
closes the one route that handed them out. A creation offer is a bearer instrument between the
wallet and the router and must be treated as one — never logged, never mirrored to a public venue,
never rendered in a UI with a copy button.

---

## What was probed and found clean

- **Pool singleton** (21 probes) — curve bracket (over- and under-sized output, output for no
  input), protocol fee (skip, underpay, overpay, redirect), config validation, accounting
  (minting LP during a swap, no-op swaps, both reserves rising, burning the whole supply).
- **Payouts** (20 probes) — a hostile router asking 100,000 bps still stops exactly at the
  surplus; the trader always receives their notarised floor;
  `trader + protocol + router == released`.
- **Cross-pool isolation** — a hostile pool whose curried state *claims* a victim's reserve coins
  is refused.
- **Routing at V10** — multi-hop, split and vault-crossing all build and audit clean; over-asking,
  pool reuse and branches sharing a pool are refused.
- **Creation and lineage** — 12 malformed creations refused; the minted pool is live; the
  successor is a genuine singleton of the same launcher carrying one mojo; burning *all* creator
  LP returns strictly less than was deposited.
- **Shipping-set integrity** — every source compiles to the hex actually shipped, matches the
  constants baked into the pool puzzle, agrees with the manifest, and is byte-identical to its
  archived snapshot.

**Permissionless creation note.** At genesis the creator controls both the pool's curried state
and the LP supply the TAIL is told to mint, because the coin authorising that mint is an ordinary
coin in their own bundle — there is no pool yet to authorise it. This is inherent and was probed
rather than assumed: a mismatched state makes the pool inert (an amount assertion fails against
the real reserve coins), which costs the creator, and the withdrawal test shows a creator cannot
take out more than they put in.

---

## Lessons carried forward

These are the durable output of the audit. The full reasoning behind each, with the code that
proves it, is in [skills/clvmPuzzleAudit.md](skills/clvmPuzzleAudit.md).

- **An archive is not neutral** — a live caller left pointing at a moved file is a silent failure.
  One endpoint shelled out to a script three directories away, failed with `ENOENT`, caught it, and
  reported `success: true` throughout.
- **Two of ten findings were introduced by the fix for an earlier one.** Every fix now ships with a
  probe that fails against the vulnerable revision, and the honest case is tested beside the
  adversarial one — a negative probe proves nothing if the harness rejects everything.
- **Tests that run against live chain state do not test the shipping code.** Any suite pinned to
  chain state covers *that* revision only.
- **Duplicated consensus logic diverges.** One redemption existed in three copies; the revision
  updated none of them.
- **Reasoning about CAT ring arithmetic is not a substitute for running it.**
- **The same arithmetic in two implementations drifts the same way.** Pin every mirror to the
  puzzle's own numbers, never to each other.
- **Positional structures rot silently when a field is inserted.** Index trailing fields from the
  end.
- **A round trip nobody performs in a test is a round trip nobody has tested.**
- **A skip that exits 0 is a lie.** Fifteen suites signalled "skipped" by exiting successfully, so
  a run that exercised almost nothing reported 34 passed / 0 skipped. Skips now exit 2.
