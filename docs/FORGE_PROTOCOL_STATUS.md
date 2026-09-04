# Forge Protocol Status — V10

Testnet11 only. Nothing here has been audited externally or pushed to mainnet.

**Last updated 2026-08-27**, after the internal audit closed ten findings, V10 shipped, and
every pre-V10 pool was retired.

---

## Where the protocol stands

| | |
|---|---|
| Shipping revision | **V10** — `*_FORGE.rue`, no version in the filename |
| Superseded | V4–V9, archived in `contracts/development/`, still loadable because old pools stay on chain |
| Creation | V10 only. Minting a superseded revision is refused unless `allowUnsafeLegacyVersion` is set, which the HTTP relay drops |
| Live pools | none — the deployment index was cleared when the old pools were retired. The pools to create next are in the local `FORGE_LAUNCH_MATRIX.md` (16 rows, all deployed through the real creation path in a dry run before any coins are spent) |
| Audit | 10 findings, all fixed. Findings: [`docs/FORGE_SECURITY_AUDIT.md`](FORGE_SECURITY_AUDIT.md). Method: [`docs/skills/clvmPuzzleAudit.md`](skills/clvmPuzzleAudit.md) |
| Next revision | **V11 candidate, evaluated 2026-09-04, not started.** Rule: adopt the CHIP-0050 action layer if it is more secure with fewer points of exploit long term. The surface count says yes — Forge-written binding checks fall from ~21 to ~4 and the reserve-only bug class disappears — on two conditions: upstream-grade review of the Forge-written multi-reserve finalizer, and auditing the final multi-action puzzle once (one action per spend is router policy at launch, never an in-puzzle guard, because a pool's puzzle is immutable and a guard would force a V12 migration). Recommended; pending owner confirmation. Curve, fees and LP CAT unchanged. [`docs/skills/chip0050ActionLayer.md`](skills/chip0050ActionLayer.md) |

### Why every pre-V10 pool was retired

Two of the ten findings are third-party-reachable fund loss, and both predate V10:

1. **LP burn was unauthenticated (V4–V8).** The pool's only link to the burn was a coin
   announcement naming a coin id supplied in the solution. Any coin can emit any message, so
   reserves could be withdrawn with no LP destroyed at all.
2. **Reserves were not bound to their pool (V4–V9).** The reserve inner was never curried; the
   pool's identity arrived entirely in the solution. Anyone could spend any pool's reserve coin
   and recreate the "successor" at a puzzle they control. The pool singleton was never involved.

Clearing the index was not enough on its own: the frontend keeps its own copy in localStorage and
POSTs it back on load, so retired pools reappeared on the next page view. Revision filtering now
runs on the way **in** as well as out, `?anchor=<launcher>` is filtered like the list, and no
launcher is hard-coded as always-allowed.

---

## Current reference

The durable protocol knowledge has moved into skills, which are the maintained copies:

- [`docs/skills/forgePuzzleV10.md`](skills/forgePuzzleV10.md) — coin layout, curried config and
  state, the bracketed weighted invariant, swap/mint/burn, vaults, authorisation, the four fees,
  modes, cutting a revision
- [`docs/skills/forgeLpCat.md`](skills/forgeLpCat.md) — the LP CAT TAIL and its three-part lock
- [`docs/skills/forgePoolLifecycleTesting.md`](skills/forgePoolLifecycleTesting.md) — lanes,
  guardrails, the suite index, and what a green run does not prove
- [`docs/skills/clvmPuzzleAudit.md`](skills/clvmPuzzleAudit.md) — how any puzzle here gets audited
- [`docs/skills/chip0050ActionLayer.md`](skills/chip0050ActionLayer.md) — the V11 candidate: CHIP-0050
  reference, the exploit-surface count, the multi-reserve finalizer, audit additions

Project-local docs (not published in this repo, `projects/` is gitignored):
`FORGE_PUZZLE_V10.md`, `FORGE_SECURITY_AUDIT.md`, `FORGE_LAUNCH_MATRIX.md`, `FORGE_ROADMAP.md`.

---

## Historical record — V7 onward

> Everything below describes **superseded revisions** and is kept for the derivations, the
> gotchas, and the reasoning that produced V10. Version-specific claims here (live pools, "not
> built yet", hashes, "new pools are created at V7 only") are **no longer true**. Where this
> section and a skill disagree, the skill is right.

## V7 — one puzzle from a single asset upward

`pool_singleton_v7.rue` is V6 with exactly one constraint removed: `MIN_ASSETS`
is 1 rather than 2. Hash `2c4b695062cbccab…`. Reserve puzzle is again identical
(`0489ac19…`); LP tail bumps to `5a2b4dff903dbe39…`.

V7 makes two changes to V6: the asset floor drops to one, and **weights become
real**.

### Weights are integer units, and they work

V6 required every weight to be within 1 bps of equal, so an 80/20 pool was not
expressible — the UI's percentage field and slider could never produce a valid
pool. V7 stores weights as **small integer units** instead of basis points: the
pool keeps `prod(reserve_i ** weight_i)` constant, `K` is their sum, and the
percentage shown to a user is `weight_i / K`. Equal weights are all ones; 80/20
is `[4, 1]`.

Fractional exponents are the usual reason weighted pools are avoided on chain.
They are not needed, because **the puzzle never solves for an output — it only
verifies one**. Both the mint and the swap are checked by bracketing: the
claimed value must hold the invariant, and one unit more must break it. That
pins the result exactly using nothing but integer multiplication.

```
mint   (lp + d)^K * prod(old^k) <= lp^K * prod(effective^k) < (lp + d + 1)^K * prod(old^k)
swap   in^k_in * out^k_out  >=  reserve_in^k_in * reserve_out^k_out,
       and one mojo more out breaks it
```

Untouched reserves contribute the same factor to both sides of a swap and
cancel, so only the traded pair constrains it — the same property equal weights
gave, now without requiring them.

The imbalance fee generalises the same way: Balancer charges it on the share of
the excess that is effectively a trade into the other assets, which is
`(K - k_i)/K`. At equal weights that is the `(n-1)/n` V6 already used, and it
still vanishes when one asset holds all the weight.

`_test_v7_weights.py` — **16/16**. Unequal splits are pinned exactly at 66/33,
75/25, 80/20 and 20/80; **equal weights reproduce the constant product output
for output**; weighted mints are pinned including single-sided into an 80/20
pool; and out-of-range weights are refused. Cost at 80/20 is 507,980 against a
block limit of 11×10⁹.

Caps are `MAX_WEIGHT_UNITS = 8` per asset and `MAX_TOTAL_WEIGHT = 20` overall,
bounding the intermediate: a 7e12 reserve to the eighth power is 43 bytes.

### Single assets need no new maths either

The V6 invariant already degrades correctly at N = 1, which is why that half of
the change is one constant:

- **Mint** — `(new_lp/lp)^1 <= next/old` collapses to an exactly proportional
  share of the one reserve, at whatever LP-to-asset ratio the pool was created
  with. Verified exact at 1:1 and at 1 LP = 1e9 mojo.
- **Imbalance fee** — scales the excess by `(n-1)/n`, which is **zero** at N = 1.
  A single-asset deposit is never unbalanced, and the formula says so without
  special-casing. Confirmed identical mint at `fee_bps` 0, 30 and 1000.
- **Swap** — `valid_pairwise_swap` needs one reserve up and one down. With one
  reserve that is unsatisfiable, so a single-asset pool refuses to trade rather
  than needing a separate guard.

A single-asset pool is therefore a **vault**: deposits mint a receipt CAT
against one reserve, burning it redeems the share, and it cannot trade.

`_test_v7_single.py` — **37/37** against the compiled puzzle, covering a native
XCH reserve and a CAT reserve equally: proportional mint, over-mint refused,
withdrawal share, over-withdrawal refused, swap impossible in both directions,
zero-mint refused, and a non-unity LP ratio held exactly. It also asserts **V6
still refuses N = 1**, so the change is real, and that V7 returns the *same*
verdict as V6 on 2- and 3-asset pools across swap, over-claim and add.

### The LP CAT backing cost decides the ratio

On Chia a CAT coin holds its amount in mojos, so minting M LP locks M mojos of
XCH *on top of* the reserve deposit — `expected_xch = lp_delta + native_deposit`.
For a single-asset XCH vault that makes the LP-to-asset ratio a capital
decision, fixed at creation:

| LP : asset | Deposit | LP minted | XCH required | Overhead |
|---|---|---|---|---|
| 1 LP = 1 mojo | 1e12 | 1e12 | 2e12 | **2.00x** |
| 1 LP = 1e3 mojo | 1e12 | 1e9 | 1.001e12 | 1.001x |
| 1 LP = 1e9 mojo | 1e12 | 1e3 | 1.000000001e12 | ~1.00x |

Nothing is lost — burning the LP melts its mojos and the reserve pays the share,
so both come back — but at 1:1 the position ties up twice the capital it
represents for as long as it is held. A coarse ratio costs nothing but rounds
small deposits to a zero mint (`DepositTooSmall`). This trade-off is the real
design decision in a single-asset pool.

### Still needed before V7 can be used

The puzzle is proven; the surrounding lane is not built.

- `forge_v6_math.py` guards `count < 2` and would need a V7 sibling.
- `forge_v6_transition.py` has not been exercised with one reserve.
- No `forge_create_pool_v7.py`, no V7 stdin entry, no responder dispatch.
- Routing must exclude single-asset pools from the swap graph — they cannot trade.

## V8 — a protocol fee consensus enforces

`pool_singleton_v8.rue` (`7856068015a92116…`) adds a protocol fee that sits **on
top of** the liquidity fee and pays a different party. The two are separate
charges and the split is deliberate:

| | Where it goes | Who pays | Enforced by |
|---|---|---|---|
| Liquidity fee | stays in the reserve | trader | the puzzle |
| Protocol fee | leaves to a fixed recipient | trader | the puzzle |
| Router fee | leaves to us | trader | our settlement code only |

The trader pays the protocol fee, not the LPs. The pool releases the same curve
output either way; the trader simply receives that output minus the fee. Verified
across 0, 5, 25 and 100 bps — the reserve keeps exactly the same balance in every
case, and trader + recipient always sums to the released amount.

### Why the output side, and why the reserve puzzle

A shrinking reserve is the one spend that physically creates coins, so it is the
only place a payout can be *forced*. `forge_reserve_v8.rue` (`e7d3128bf5a0cb71…`)
is the first reserve revision since V5: instead of creating one settlement coin
for the whole decrease and letting the router divide it, it creates two — the
trader's settlement and the recipient's payment.

The amount and recipient arrive in the reserve plan, and the plan is covered by
the pool announcement the reserve asserts, so neither can be altered without the
pool authorising it. The pool derives both from its own fixed config. That is the
difference from the router fee: **this one cannot be avoided by anyone**, whereas
the router fee is only collected when we are the party that settles.

`_test_v8_protocol_fee.py` — **13/13**. Beyond the rate checks it confirms a plan
that claims no fee, is one mojo short, overcharges, or pays a different recipient
is refused; that deposits and withdrawals are never charged, including one that
tries to; and that a rate above the cap or with no recipient is refused at config
validation.

Capped at `MAX_PROTOCOL_FEE_BPS = 100`. A pool's config is fixed at creation, so
that bound is permanent for every pool minted against this puzzle.

### Wiring status

Creation, the transition builder, the stdin entry and the responder all accept
V8. Minting one requires asking for it explicitly — `protocolVersion: 8` plus
`protocolFeeBps` and `protocolPuzzleHash` — because `DEFAULT_VERSION` stays at
V7 until V7 has been exercised on chain.

`_test_v8_transition.py` — **10/10**, built against a pool created through the
real creation path so the singleton lineage is genuine rather than fabricated.
It confirms the recipient is paid exactly, the trader receives the remainder,
trader + recipient equals what the curve released, and that add and remove build
clean and pay the recipient nothing. With the fee set to zero the bundle is the
V7 shape again.

**Not yet wired**: frontend quoting. A V8 swap quote must subtract the protocol
fee from the output the curve gives, or the trader will be quoted more than they
receive. Nothing has touched a node.

### Three mismatches this shook out

All three came from splitting one payout into two, and none would have shown up
without running the bundle:

- **The settlement coin id.** Both the pool and the reserve reconstruct it from
  the amount released. That amount is now the trader's share, not the whole
  decrease, and both had to change together.
- **The fee bound on a growing reserve.** `fee <= current - successor` is a
  negative bound when a reserve grows, so a zero fee failed it. It now only
  applies to a reserve that is paying out.
- **The reserve acknowledgement string.** The reserve emitted `reserve-ack-v4`
  while the pool still asserted `reserve-ack-v3`, so every bundle built but no
  announcement was satisfied. The audit caught it; a build-only check would not
  have.

## Vault routing — reaching a single-asset pool

A vault cannot trade, so it is excluded from the swap graph. But its LP is an
ordinary CAT that can be paired elsewhere, and burning that LP returns the
underlying. Chaining the two reaches liquidity the graph alone cannot:

```
TXCH --swap--> vaultLP --redeem--> t8
```

**The redemption leg is exact, not a curve.** A vault can never swap, so no fee
ever accrues to it, and both deposits and withdrawals move reserve and LP
proportionally — its ratio is fixed at creation forever. Verified by running adds
and removes of very different sizes against the live vault: the ratio never
moved off 1.000000. That makes the leg a fixed-rate conversion with no price
impact and nothing to quote badly.

`forge_vault_route.py` builds the composed bundle. The swap pool may hold any
number of assets; only the vault must be single-asset, because a wider pool's
withdrawal returns every reserve pro rata and cannot be one leg of a linear
route.

`_test_vault_route.py` — **7/7** against the live pools, `TXCH → vaultLP → t8`:
the bundle audits clean at 16 assertions, the trader is paid exactly what the
route quotes, both singletons advance, the vault's LP supply falls by the burn
and its reserve by the payout, and **every LP coin the route creates is spent
inside the same bundle** so the intermediate is never claimable on its own.

### Two mismatches the composition exposed

Both come from the LP arriving from a reserve rather than from the Offer, and
neither shows up in the single-pool remove path:

- **The exit settlement needs two payment groups.** One moves the LP into a coin
  the TAIL can melt; the other is the *empty* group the swap pool's reserve
  asserts about its own exit settlement. A normal remove never needs the second,
  because there no reserve is watching that coin.
- **The pool must name the intermediate as its LP action coin**, not the
  settlement. The intermediate is what acknowledges the burn, so naming the
  settlement left the vault asserting an announcement nothing emitted.

### Wired end to end

- `forge_v3_stdin.py` gained a `vault-route` action.
- `respondToForgeVaultRoute` locks both pools in sorted order, preflights both
  tips, pushes, persists both successors and indexes the offer.
- `/api/forge-vault-route-respond` is the endpoint. A dry run against the live
  pools returns a valid bundle with both successors.
- The router graph now adds a **bidirectional vault edge** between a
  single-asset pool's LP and its reserve, priced at the fixed ratio with no fee
  and no impact — pricing it through the swap quote would be wrong in all three
  respects.
- The frontend dispatches a vault route to its own lane and confirms both
  singletons.

**Only one vault shape settles today**: a single swap feeding a single
redemption. Any other arrangement is *dropped from quoting entirely* rather than
quoted and handed to a lane that cannot settle it. That guard is deliberate —
quoting a route the router has no lane for produces an offer nobody can take,
which has bitten this project more than once.

**Settled on chain.** A live `TXCH -> t8` routed through the vault and
completed as a swap, which is the first confirmation that the lane works
outside a dry run.

### Nested LPs reach liquidity with primitives only

An LP CAT is an ordinary CAT, so a pool can hold other pools' LPs -- an index
over them. Routing such a nest needs no special case, because the router walks
assets without caring what an asset represents. It needs only that every edge is
something the puzzle validates **in a single spend**:

| Edge | What it is | Settles via |
|---|---|---|
| swap | ordinary pairwise trade | multi-hop lane |
| vault | single-asset pool's LP against its one reserve, at the creation ratio | vault-route lane |

There is deliberately **no composite join/exit edge**. Burning LP for a single
asset is not a primitive: `MODE_REMOVE` is strictly proportional and `MODE_SWAP`
strictly pairwise, one action per spend, so it would need a proportional remove
plus (n-1) same-singleton swaps chained in one bundle -- a lane that does not
exist and whose rounding has never been proven against the compiled CLVM.
Instead a single-sided exit is reached by *swapping* the LP CAT, and
remove-liquidity stays strictly proportional. Keeping both operations to
primitives is what keeps the maths sound.

The consequence, pinned by `nestedLpRouting.check.ts`: **an LP is routable
exactly when some pool pairs it, or it is a vault LP.** So an index share needs
a market of its own to be tradeable, and reaching the underlying of a
multi-asset constituent needs a market for that constituent too. A vault
constituent passes straight through, because its LP-to-reserve edge *is* a
primitive -- which is exactly the shape that just settled.

### Splits may cross a vault, and routing well is a balancer

A split can now run a swap branch and a vault branch in parallel. The vault
branch reaches its asset by swapping into the vault's LP and burning that LP for
the underlying -- `MODE_REMOVE`, not `MODE_SWAP` -- with the LP existing only
inside the bundle.

Three pieces make it work:

- `vault_leg_kind` classifies a hop across a single-asset pool, and `_Leg` carries
  a `kind`, so the planner sizes redemptions at the vault ratio rather than the
  curve.
- `_validate_branches` accepts a vault hop instead of rejecting it as "does not
  trade its assigned hop".
- `_build_vault_redeem_leg` performs the redemption but returns an exit coin for
  the split's *combined* payout. Branches are parallel; the trader is paid once
  from the merged exit, never per branch.

**The subtle part**: a swap leg feeding a redemption must leave its exit coin
unspent. The redemption spends it, because the melt payment and the announcement
group the reserve asserts have to travel together on one spend. Spending it in
the feeding leg leaves the vault asserting an announcement nothing emits -- the
same failure the vault route hit originally.

Why it matters beyond price: **a split is a balancer that pays for itself.**
Sending part of an order down each of two diverged pools moves both toward each
other, so good routing shrinks the arbitrage gap as a side effect of ordinary
flow. It does not close a standing gap when nobody is trading, which is the
remaining case for a keeper.

`_test_split_vault.py` -- 16 spends, 30 assertions, clean audit, all three
singletons advance, and the vault pays its exact ratio. The responder lane is
verified by dry run against the live pools: `total_out 6004`, branch amounts
`[2995]` and `[3009, 3009]`, three successors. **Settled on chain**: a 3 TXCH swap routed through a split whose second branch
crossed the single-sided vault.

### V8 was unroutable, and would have failed silently

A V8 reserve destructures a plan two fields wider than its predecessors --
`protocol_fee_amount` and `protocol_puzzle_hash`. `forge_v6_transition` supplied
them; the routed builders did not. A freshly minted V8 pool would therefore have
settled a **direct** swap and been rejected by every multi-hop, split and vault
route: unroutable in exactly the lanes that now produce the best prices, and only
discoverable after minting one.

Fixed across all three builders, with the gross/net distinction made explicit:

- `_Leg` carries `protocol_fee`, and `amount_out` stays **gross** -- it is what
  the reserve releases, so it is what the successor balance derives from. What
  travels onward is `amount_out - protocol_fee`.
- `protocol_fee_for` mirrors `valid_protocol_fees`: the fee is a share of what
  the reserve *releases*, never of the trader's input.
- Only the releasing reserve names a non-zero fee; every other row on a V8 pool
  still carries the two fields, set to zero. A pre-V8 plan stays six wide.

Three places computed a payout from the gross and would have created value the
CAT ring could not balance: `final_out` in multi-hop, `total_out` in split, and
the final settlement's surplus. All now net the fee first.

`_test_v8_routing.py` -- **10/10**: multi-hop across two V8 pools, the fee
reaching the recipient, the trader paid the remainder, a mixed V8+V7 route, and a
split whose branches both cross V8 pools.

### Arbitrage cannot be captured inside the puzzle

A pool validates a transition against **its own state only**. Chia has no
cross-coin state read, so a pool cannot know it is mispriced relative to another
pool -- and mispricing is by definition a cross-pool fact. A puzzle could assert
an announcement carrying another pool's state, but only if curried with that
pool's identity at creation, which couples pools at birth, forces every trade to
spend both, and reintroduces the mutual-valuation loop nested pools already have
to avoid.

What a pool *can* do is charge for the volume, which it already does: every
arbitrage trade pays the LP fee, and that fee stays in the reserve, raising
reserve-per-LP. The LP therefore already captures a slice of every arbitrage.
Capturing more means raising the fee for everyone, because the puzzle cannot tell
an arbitrageur from an ordinary trader.

## Known issues and gotchas

### V6 deposit quotes must include the imbalance fee; V4/V5 must not

The puzzles genuinely differ. Reusing one formula across versions produces
`add Offer LP minimum does not equal canonical mint` rejections. Any shared
quote path needs a version branch.

### Small single-asset adds mint zero LP on wide pools

LP scales with the *n-th root* of the product ratio, so on a 3-asset pool a
0.05% bump in one reserve yields ~0.0166% LP growth, which floors to zero. The
puzzle rejects it (`ADD` requires `lp_delta > 0`). `forge_v6_math` raises
`DepositTooSmall` with an actionable message rather than letting it fail
opaquely. This is a real behavioural difference from V4/V5, and the V6 pool is
thin enough to hit it.

### Fee-bypass leak, closed in V6 only — and it is a puzzle property

An unbalanced add followed by a pro-rata remove is a fee-free swap. Measured on
a synthetic 2-asset pool (`_measure_leak.py`, re-runnable):

| Mint used | 1% deposit | 5% deposit |
|---|---|---|
| V4 / V5 | +0.297% | +0.293% |
| V6, imbalance fee on | −0.004% | +0.003% |
| V6, imbalance fee **off** | +0.297% | +0.293% |

The live V4 pool measures **+0.287%**. The advantage is bounded by the swap fee
(0.30%), so it is an efficiency leak rather than a drain.

The third row is the proof: V6 with its fee disabled produces numbers identical
to V4/V5, so the mint formula is otherwise the same and the fee argument is the
entire difference. It is visible in the puzzle signatures —

```
V4/V5:  exact_invariant_lp_mint(reserves, next, total_lp, lp_delta)
V6:     exact_invariant_lp_mint(reserves, next, total_lp, lp_delta, config.fee_bps)
```

**This cannot be fixed in the frontend.** The mint is computed by the pool
puzzle; the puzzle accepts the spend from anyone who builds it. A UI that
declined to offer unbalanced adds would only stop our own users. And because a
pool's puzzle is fixed at creation, existing V4 and V5 pools can never be
patched — the only remedy is migrating liquidity to V6. That permanence is the
intended property, not a defect.

### Platform fee: collected on V6 swaps, still off for creation

- **Swaps, V6** — collected. The fee is carved out of the shrinking reserve's
  *surplus*: the gap between what the curve releases and the smaller amount the
  trader notarised. Previously that surplus was refunded to the trader, which is
  why the fee was displayed but never taken.

  This only works because the quote and the builder now agree on where the fee
  comes from. `calcSwapOut` gained a `DevFeeMode`:
  - `'input'` (V4/V5, unchanged) nets the fee off the input *before* the curve.
    The puzzle swaps the full input regardless, so the surplus is smaller than
    the nominal fee — and floors to zero on small trades. Under this mode the
    fee is uncollectable by construction.
  - `'output'` (V6) runs the curve on the full input, exactly matching the
    puzzle, then deducts the fee from the result. The surplus is then precisely
    `devFeeBps` of the released amount.

  `getSwapDevFeeMode()` picks the mode from `join_rule`, and `loadPool()` stamps
  it onto `PoolState`, so every quote path gets it without threading a
  parameter. V4/V5 quotes are byte-identical to before.

  The fee rate is read from **server** config in `_forgeV4Responder.js` and the
  amount is derived inside `build_transition_v6` from the actual reserve
  decrease — never taken as an absolute figure from the request, so a crafted
  client cannot understate it. It is capped at the surplus, so the trader is
  always paid at least what they notarised.
- **Creation** — plumbing works (`forge_create_pool_v5/v6.py` create a fee coin
  when `platformFeeMojos > 0`). It is simply configured off:
  `.env` line 54 `#VITE_CFMM_CREATE_POOL_PLATFORM_FEE_MOJOS=...` is commented
  out, so it resolves to 0. Uncomment to enable; no code change.
- **Swaps, V4/V5** — still displayed and still never collected. Closing this
  would mean moving them to `'output'` mode and carving the surplus, the same
  way V6 does.
- **Deposit / withdraw** — deliberately zero, as intended.

### Fee model: LP fee is per-pool, router fee is once per swap

Two different fees with two different rules, and conflating them was the bug.

**LP fee** — inside the curve (`effective_input = gross * (10000 - fee_bps) / 10000`,
then constant product), charged per pool, 100% stays in the reserve. A 2-hop
route genuinely pays it twice: that is the price of renting two pools'
liquidity. Uniswap, Aftermath (0.3% uncorrelated / 0.1% stable) and TibetSwap
(0.7%, all to LPs) all work this way.

**Router fee** — charged **once per swap**, on the final output, never per hop.
`forgeAdapter` previously multiplied it by hop count, so a 3-hop route displayed
1.50%. That also biased the router against its own best answer, making a good
3-hop route look worse than a poorer direct one. Both references charge once:
Uniswap takes its interface fee as a single `PAY_PORTION` after the swap
completes, and Aftermath's aggregator fee is "configurable per swap" — their
Smart Order Router otherwise charges nothing at all.

Mechanically the fee is carved from the exit **surplus**: the gap between what
the curve releases and the smaller amount the trader notarised. This is why legs
are now quoted with `devFeeBps = 0` — each hop's math then matches its compiled
puzzle exactly, and `netRouterFee()` takes the fee once off the route total, so
`gross - quoted` equals the fee precisely. The amount is always derived inside
the builder from the actual output and capped at the surplus, so a crafted
request cannot understate it and the trader is always paid their minimum.

Intermediate hops are never skimmed: they stay strictly ephemeral, which is what
makes a route atomic.

**This is a router fee, not a protocol fee.** Forge pools are permissionless —
the puzzle enforces the invariant, not who gets paid — so any taker who sees a
public offer can settle it and route the fee elsewhere, or charge nothing and
quote a better price. Uniswap has the same property. Note also that our carve
refunds the remaining surplus to the trader while a competing taker can keep all
of it, so every offer posted to Dexie is a visible bounty and we are the least
aggressive taker on our own offers.

**Planned for V7**: a consensus-enforced protocol fee inside the pool puzzle,
like Aftermath's 0.005%. `PoolConfig` currently holds only `fee_bps`, with no
protocol-fee or protocol-puzzle-hash field, so this needs a config change (the
frontend's `protocolFeePpm` is vestigial for V6). Note it is necessarily
**per-pool**: a puzzle only ever sees its own pool and cannot know it is hop 2
of 3, and it is denominated in that hop's input asset. In-puzzle and
once-per-swap are mutually exclusive.

### Routing through an N-asset pool: untouched reserves still need a plan

`forge_split_swap.py` and `forge_multihop_swap.py` both built `successor_amounts`
with exactly two entries — the hop's input and output — then looped over *every*
asset in the pool. That holds for 2-asset V4/V5 pools, where a hop touches both.
It breaks the moment a route crosses the 3-asset V6 pool: routing `TXCH -> T6`
leaves T11 untouched, and the lookup raises `KeyError`.

Both now seed `successor_amounts` from the current balances and move only the
two assets the hop trades. An untouched reserve carries its balance forward with
a **zero settlement id** and no settlement spend — nothing may be paid out of it.

This is why a split route surfaced as a bare `<bytes32: 1341d936...>`: see the
error-reporting note below.

Covered by `_test_route_nasset.py`: the live split route (60% one-hop V5, 40%
two-hop V6→V4), multi-hop through V6 both CAT-in and native-in, and an explicit
check that the untouched V6 reserve is *frozen* rather than merely present.

### `str(exc)` loses the exception type, and `KeyError` becomes unreadable

`str(KeyError(key))` renders only the key, so a missing dict entry reached the UI
as `[aWizard] <bytes32: 1341d936...>` — no exception type, no location, nothing
to search for. The stdin entry points now emit `f"{type(exc).__name__}: {exc}"`
and print a traceback to stderr for the server log.

### The local router dies silently, and that looks like a website hang

`local-test-host.mjs` runs two pollers plus every API route and had **no
process-level error handling**. Under Node 15+ a single unhandled rejection
anywhere terminates the process, so the router can vanish mid-session. The
symptom is confusing rather than obvious: offers are still created and signed in
the wallet, Dexie still works because it is external, but nothing takes the
offer — so the website appears to hang rather than reporting a dead server.

Verified: a bare script with one unhandled rejection exits 1 under Node 22
before its next timer fires; with the handlers it survives both a rejection and
a throw. The host now logs loudly and keeps serving, and logs its own exit and
any signal so a drop leaves evidence instead of an empty log.

Swallowing `uncaughtException` can in principle leave corrupt state, but for a
local dev host a router that stays up and complains beats one that disappears.

**If offers stop being taken, check the router is alive first:**

```bash
curl -s -o /dev/null -w "%{http_code}
" http://localhost:4184/
```

### Add and remove waited on a confirmation that was never coming

`handleDeposit` and `handleWithdraw` polled for the pool coin to be spent for
the full ~2 minute budget regardless of whether the router had actually taken
the offer, then reported "submitted but still unconfirmed". An indexed-but-
untaken offer is simply *resting* and needs a taker, so there was no spend to
wait for — making a valid offer indistinguishable from a failure.

Both now check `offerWasTaken()` (a txId, or settlement
`pending-confirmation`/`matched`/`confirmed`) and otherwise say immediately that
the offer is resting. The swap path already had this guard.

### A settled offer can sit in `pending-confirmation` forever

Several relay paths mark a record `pending-confirmation` and nothing revisits
it. The Dexie discovery poller is the clearest case: it only retries records
whose status is `open`, so anything already taken is treated as
`already-indexed` permanently. An offer that executed keeps showing as open in
the UI, which looks identical to a failure.

`_reconcileOffers.js` closes this using a venue-independent signal: an offer can
only be taken by spending the maker's own inputs, so once those are spent the
trade landed. `parse_offer.py` now returns `inputCoinIds` (spends whose coin is
not created inside the offer bundle), and the poller reconciles before scanning
so a settled offer is never re-taken. First run cleared **5** stuck records that
had all genuinely settled.

A *missing* coin record is deliberately not treated as settled — the node may be
lagging, and marking an unsettled offer as matched is the worse error.

### A stale quote is fatal for adds, not merely suboptimal

`exact_invariant_lp_mint` pins the mint exactly (bracketed with `+1`), so an add
whose notarised LP does not equal the canonical mint is rejected outright:
`add Offer requests N LP but the canonical mint is M`. Unlike a swap, there is
no surplus to absorb the difference. Quoting against reserves that have since
moved therefore produces an offer that can never be taken.

Measured by running the real `calcInvariantLpOutV6` against the block-4587768
transition: the post-add reserves give 315 while the pre-add reserves give 352,
for the same 1 TXCH deposit. Both figures match Python and the compiled puzzle
exactly, so all three implementations agree — the only thing that changes the
answer is which reserves you feed it.

This has not yet bitten a real trade: the single-sided add was quoted and
settled against the same state. It surfaced because rebuilding that offer
against the *later* snapshot reproduces the rejection, which is what a
genuinely stale quote would do.

### An offline audit that only checks announcements will miss `UNKNOWN_UNSPENT`

The first V6 add failed on chain because the LP genesis coin was spent but never
created: the native settlement was spent with an empty payment group, so nothing
produced the coin the LP leg then consumed. Every announcement assertion was
satisfied, so the original audit passed it.

`_test_v6_transition.py` now also checks that each spent coin is created
in-bundle or pre-exists, and that no coin is spent twice. Both checks were
confirmed by deliberately reintroducing the bug — worth keeping, because the
double-spend variant is what a naive fix produces.

### Snapshot lineage must be derived, never assumed

`v3PoolSnapshot.parent_inner_puzzle_hash: null` is the *eve* form and is only
valid when a singleton's parent is the launcher. Using it on a pool further down
the chain causes `ASSERT_MY_PARENT_ID_FAILED`. `rebuild_pool_snapshot.py` now
derives real lineage from chain by uncurrying the parent's reveal.

### Offer parsing is Python-backed

Wallet offers are zlib streams compressed against a versioned preset dictionary,
and the offered side can only be derived by executing puzzles. `_offerParser.js`
delegates to `contracts/parse_offer.py` and caches by offer string. Do not
reintroduce a JS-side CLVM parse.

---

## File map

**Contracts**
- `pool_singleton_v6.rue` — N-asset inner puzzle. Generalised checks:
  `valid_assets`, `exact_invariant_lp_mint` (with imbalance fee),
  `valid_pairwise_swap`.
- `forge_reserve_v6.rue`, `forge_lp_cat_tail_v6.rue`
- `forge_create_pool_v6.py` — keyless N-asset creation
- `forge_v6_math.py` — Python mirror of the V6 puzzle math
- `forge_multihop_swap.py`, `forge_split_swap.py` — atomic multi-pool settlement
- `rebuild_pool_snapshot.py` — recover a snapshot from chain, hash-verified
- `parse_offer.py` — authoritative offer parsing

**Tests** (all re-runnable; run from `contracts/`)
- `_test_v6_nasset.py` — 14 puzzle behaviour cases
- `_test_v6_math.py` — 15 Python↔CLVM agreement cases
- `_test_v6_create.py` — 3-asset creation dry run
- `_audit_split.py` — split bundle announcement + value audit
- `_test_route_nasset.py` — split and multi-hop routes crossing the N-asset pool
- `_test_route_devfee.py` — proves the router fee is charged once, not per hop
- `_test_v6_transition.py` — 4 add/remove/swap bundles, audited as a node would
- `_test_v6_devfee.py` — proves the swap dev fee reaches the dev recipient and
  that trader + dev payouts sum to exactly the gross output

**API**
- `_forgeV4Responder.js` — single-pool, multi-hop, and split lanes (locks every
  pool on a route, sorted, to avoid deadlock)
- `forge-multihop-respond.js`, `forge-split-respond.js`, `pool-confirmation.js`
- `router-create-pool-taker.js` — dispatches V6 when assets > 2

**Frontend**
- `forgeAdapter.ts` — N-hop pathfinding, split routing, true price impact
- `RouteBreakdown.tsx` — single route container (replaced `RoutePreview`)
- `OperationStatus.tsx` — shared submit → confirm status for all four operations

---

## Compile

```bash
python scripts/compile_contracts_v3.py
```

Compiles all V3–V6 sources and writes `contracts/compiled/v3-manifest.json`.
The `rue` compiler must be on PATH.
