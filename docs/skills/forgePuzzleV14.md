# Skill: Forge Puzzle V14 — the fourth-review revision

> The Forge pool on the CHIP-0050 action layer, revised after a fourth independent review
> of V13 (Chia-Network/chips#217, trgarrett, 2026-09-15) and a fifth review of the
> published documents. Protocol **15**, live on testnet11 since 2026-09-16 with 32 pools.
> V13 is closed and drained: its registry admitted a pool whose reserves were never
> funded, so a market key could be taken permanently for one creation fee. Design and
> disposition: `projects/chia-cfmm/docs/FORGE_PUZZLE_V14.md`; the specification the build
> followed is `FORGE_PUZZLE_V14_SPEC.md`; the leaf-by-leaf reading is
> `FORGE_V14_CLVM_PASS.md`. Everything in `forgePuzzleV11.md` still describes the shape,
> the leaves, the finalizer and the TAIL; `forgePuzzleV13.md` describes the five fixes V14
> carries unchanged. This file is the delta.
> **Not externally audited. Testnet only.**

---

## Domain

Load with `forgePuzzleV11.md` for any V14 pool work. Load alone when the question is
"what changed and why" since V13, or when something is being claimed about what the
settlement binding guarantees.

## Why a major increment

The registry's admission rule changes and two leaves change their solutions. Every pool
puzzle hash moves, the V13 registry cannot admit a V14 pool, and R-1 is a demonstrated
denial of service rather than a hardening. That is not a point release.

## 1. The reserve is proved to exist (R-1)

V13's `register` took `reserve_parents` in its solution and used it only to rebuild the
pool's puzzle hash. Nothing in the registration bundle spent or asserted a reserve, and
`valid_pool` read the *claimed* amounts. A registration naming parents that created
nothing was accepted; the slot was taken and every later spend, by anyone, failed message
pairing forever.

V14 adds `forge_reserve_launcher.rue` — a puzzle that creates one coin at the hash it is
given, for its whole amount, hinted with the pool's launcher id, and announces exactly
that. `register` is handed each reserve's **grandparent** and derives

```
P_i = coinid(grandparent_i, launcher_hash_i, reserves[i])
      launcher_hash_i = RESERVE_LAUNCHER_HASH                      (XCH)
                      = cat_puzzle_hash(asset_i, RESERVE_LAUNCHER_HASH)  (CAT)
```

then asserts a coin announcement from `P_i`. A coin id commits to its puzzle hash, so the
only coin that can make that announcement runs the launcher, and the launcher does nothing
but create the reserve. `reserve_parents` left the solution: **derived, never claimed** —
the rule V12 applied to the pool's own solution, applied to the registry's.

*The ASCII prefix on the launcher's message is load-bearing.* The CAT layer refuses an
inner coin announcement beginning `0xcb` (its ring marker); a bare tree hash would collide
one time in 256.

*Why not something simpler* (all simulated against consensus first): a puzzle announcement
binds the puzzle and not the coin; a coin announcement from an arbitrary coin binds the
coin and not the deed; spending the eve at genesis cannot be built at all —
`EPHEMERAL_RELATIVE_CONDITION`, because a coin created and spent in one block may not
carry `ASSERT_MY_BIRTH_HEIGHT`.

## 2. The settlement's amount is bound in the puzzle — and what that does NOT mean

A V13 leaf asserted only `AssertPuzzleAnnouncement(sha256(settle_ph + tree_hash((coin_id, nil))))`,
which binds the asset and the id the *solver* wrote into the nonce, and says nothing about
the amount. V14 leaves take the settlement's **parent and amount**, derive the id, and add
`ASSERT_CONCURRENT_SPEND` plus `amount >= input`:

```
settlement_binding(asset, parent, amount, at_least) ->
    assert amount >= at_least
    id = coinid(parent, settlement_puzzle_hash(asset), amount)
    [ settlement_assert(asset, id), AssertConcurrentSpend { coin_id: id } ]
```

`swap` binds with `at_least = gross_input`; `add` binds each **positive** deposit and skips
a zero one in the branch that already skipped its announcement; `remove`, `observe`,
`collect` and `dao_fee` carry no settlement and emit nothing. The amount bound is the
settlement's **own** — the router carves its fee from the same coin, so on the public lane
`settlement.amount = gross + router_fee`, and binding `gross` would refuse every fee-paying
swap.

**The correction that matters, measured on chain 2026-09-16.** This does *not* make a
settlement single-use. An assertion is not consumed, so two actions naming one coin both
pass. What decides the pair is conservation — and conservation is a property of the
**whole bundle**, not of an action. A network fee is slack: on H6 at 4,693,721 two swaps
naming one settlement **confirmed**, the second funded out of a 5 XCH fee (fee actually
paid 4,995,000,000), and the pool took full value for both. Nothing was stolen; the trader
overpaid. With a zero fee the same pair is refused `MINTING_COIN` by the live node.

> So the guarantee is **which coin, and its amount** — not "this coin paid for this
> action". Never write "refused by conservation" without saying "when the bundle has
> nothing spare".

## 3. `LOCKED_BURN = 1`

One constant does four jobs: the genesis settlement burns it to the zero puzzle hash and
`register` asserts that group; `valid_pool` requires `total_lp > LOCKED_BURN`; `remove`
caps at `total_lp - LOCKED_BURN`; the prologue refuses `total_lp < LOCKED_BURN`. V13's
1,000 stranded a median 2.21% of each pool's liquidity for no property the puzzle needs.

## 4. Method: a mutation verdict is UNREACHED, never "redundant"

R-2 was a line we called redundant on the strength of a "survived" verdict: `add`'s
`assert deposit >= 0` **is** load-bearing (`[-100000, +500000]` satisfies the mint bracket
at `lp_delta = 36611`), and our search had run through a Python mirror carrying the same
guard. `scripts/mutate-v14.py` now reports **UNREACHED** and fails the run unless every
unreached line has a bracket-level probe or a written argument in
`contracts/v14/mutation-arguments.json`.

When a line reads UNREACHED, ask first whether a **mirror's own guard or an earlier assert**
is refusing before the leaf runs. Three lines were masked that way in V14's first run: the
`remove` floor cap (the mirror's `withdrawal_amounts` raises first), the registry's
`valid_pool` (the suite handed its probes another pool's neighbours, so the key bracket
refused first) and the prologue's `dao_fee_bps >= 0` (no probe existed).

## 5. Three traps that are not in the puzzles

**The action layer's solution is not `zip(puzzles, solutions)`.** `puzzles` lists each
*distinct* leaf once, with selectors 2, 5, 11, …; `selectors_and_proofs` is in **reverse**
execution order; `solutions` has one entry **per action**. Zipping the first with the last
drops every repeat — a spend that ran `swap` twice replays as one swap. That bug sat in
`forge_v14_resync.replay_spend`, which is what the browser uses to repair a pool behind
the chain. Resolve each action's leaf through its selector.

**A confirmed spend does not mean the peak has caught up.** `push_and_wait` returns as
soon as the successor coin record exists; the node's reported peak can still be one block
behind. A builder that then claims `h` below the coin's birth is refused by the prologue's
`h >= birth` (clvm raise 80). Clamp to `max(peak, birth)` — `v14_ops.claim_height`.

**A route that mints LP is funded twice by the same XCH, and the router is paid out of it
first.** The entry swap spends part of the offered XCH and the rest backs the LP the vault
mints. `_Composer.feed` takes the router's rate off the hub's **whole** amount and then
prorates what is left across the declared shares, so a share reaches its pool as
`share * spendable // offered` — not as `share` less its own percentage. Split the gross and
the backing lands short by the fee's cut of it; pre-net the whole offer and the entry is
netted twice, filling ~3% small and refunding the difference; net each share by its own
percentage and you are one mojo out, which is refused exactly like a large shortfall. Size
the split through the hub's own arithmetic. The same fixed point runs in the interface's
quote, where getting it wrong is an **over-quote**, refused after signing.

> A wrap case at **zero** bps proves nothing about any of this: at zero bps the gross and
> the net are the same number. A fee-aware split needs a fee-charging test.

## What V14 carries unchanged

One configuration bound to all six leaves (M-4), the exact two-interval oracle with
`last_spot` (S3), the burned floor asserted by `register` (S2), the registry's pinned
protocol parameters (M-3/L-3), the single-recipient `collect` (M-1), genesis bound to one
eve (C-1), reserve parents written by the finalizer (L-1). The curve is byte-identical to
V10's.

## Evidence

Thirty suites; the ones that are V14's own: `_test_v14_reserves_proved.py` (R-1, 21),
`_test_v14_before_after.py` (each change against the V13 **and** V14 builds, 13),
`_test_v14_settlement_amount.py` (12), `_test_v14_action_binding.py` (13, including the
duplicate settlement both ways), `_test_v14_replay.py` (9), `_test_v14_review_corrections.py`
(11), `_test_v14_asset_scope.py` (8), `_test_v14_lanes_agree.py` (10),
`_test_v14_integrity.py` (122, every puzzle recompiled; exit 2 without `rue`),
`_test_v14_provenance.py`. `scripts/sim-v14.py` runs the lifecycle on an in-process node
(72). On chain: the registry at 4,692,794, 32 pools, 146 confirmed transactions, and
refusal probes pushed at live pools (`v14-squat-probe.py`, `v14-settlement-probe.py`,
`v14-slack-probe.py`). Both LP-in-route shapes are settled: an LP **burn** mid-trade at
4,694,251 (`forge_action_remove` beside `forge_action_swap`) and an LP **mint** mid-trade at
4,694,314 (`forge_action_swap`, `forge_action_add`, `forge_action_swap`, one bundle).

## Cutting the next revision

Same as V11's recipe, plus: every creation lane must spend one reserve launcher per
reserve, and `_test_v14_lanes_agree.py` must show the deploy lane and the website lane
producing byte-identical launcher announcements and `register` solutions. S2 lived exactly
where two lanes differed and only one was checked.
