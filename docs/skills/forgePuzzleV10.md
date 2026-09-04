# Skill: Forge Puzzle V10 — the shipping revision

> Reference for the Forge pool puzzle set as it ships. V10 is the only revision intended for
> mainnet; V4–V9 exist on testnet and are described only where behaviour differs.
> Updated 2026-08-27, after the internal audit closed 10 findings and the old pools were retired.
>
> **Not externally audited. Testnet only.** `clvmPuzzleAudit.md` for the method,
> [`docs/FORGE_SECURITY_AUDIT.md`](../FORGE_SECURITY_AUDIT.md) for the findings log.

---

## Domain

Load this when the quest touches the Forge pool puzzle itself — its config, state, invariant,
authorisation, fees, or modes — or when cutting a new revision. For the LP CAT handshake in
detail see `forgeLpCat.md`; for what to run see `forgePoolLifecycleTesting.md`.

Forge is an **N-asset weighted constant-function market maker on Chia**. A pool is a singleton
holding a small config and state; the assets live in separate reserve coins the singleton
authorises. Trades arrive as signed Offers and a router assembles the bundle — it never holds a
key and cannot alter what the trader signed.

---

## The shipping set

Shipping puzzles carry **no version in the filename** (`*_FORGE.rue`); superseded revisions live
in `contracts/development/`. `contracts/forge_puzzles.py` resolves a request for the current
revision onto the `_FORGE` file and falls back to the archive for older ones —
`FORGE_VERSION = 10`.

| puzzle | role |
|---|---|
| `pool_singleton_FORGE` | pool inner: config, state, all three modes |
| `forge_reserve_FORGE` | reserve inner, **curried with the pool's launcher id** |
| `forge_lp_cat_tail_FORGE` | LP CAT TAIL, curried with `(launcher_id, protocol_version)` |
| `forge_lp_melt_inner_FORGE` | pinned inner for a burn |
| `forge_lp_mint_inner_FORGE` | pinned inner for a mint |

Tree hashes are in the local `FORGE_PUZZLE_V10.md` and in `compiled/v3-manifest.json` — do not
memorise them here; they change with every revision and `_test_forge_integrity.py` is the
authority.

---

## Coin layout

```
              singleton_top_layer_v1_1
                        |
              pool_singleton_FORGE          <- 1 mojo, curried (singleton, config, state)
               /        |        \
        reserve      reserve      LP CAT     <- one reserve coin per asset
      (asset 0)    (asset 1)     (TAIL)
```

- **Pool coin** — always exactly one mojo, holds no assets. Curried with the singleton struct,
  the config, and the current state. State changes every spend, so **the pool's puzzle hash
  changes every spend**.
- **Reserve coins** — hold the actual assets, one per asset. Native XCH runs the reserve inner
  directly; a CAT wraps it in the CAT layer. From V10 the reserve is curried with its pool's
  `launcher_id`, so a reserve's puzzle hash commits to the pool that owns it.
- **LP CAT** — an ordinary CAT whose TAIL is curried per pool, so its asset id is unique per
  pool.

### Config — curried, permanent for the life of a pool

| # | field | notes |
|---|---|---|
| 0 | `protocol_version` | must equal the puzzle's own `PROTOCOL_VERSION` |
| 1 | `pool_module_hash` | this puzzle's own hash, for successor derivation |
| 2 | `asset_ids` | canonically sorted ascending; native XCH is the zero id, so it sorts first |
| 3 | `weights` | **integer units** — V6 stored basis points in the same slot |
| 4 | `fee_bps` | liquidity fee, 0…`MAX_FEE_BPS` |
| 5 | `protocol_fee_bps` | 0…`MAX_PROTOCOL_FEE_BPS` |
| 6 | `protocol_puzzle_hash` | must be non-zero when the protocol fee is non-zero |
| 7 | `lp_tail_hash` | the LP CAT's asset id |
| 8 | `reserve_inner_puzzle_hash` | curried reserve, so pool-specific from V10 |

Indices 5 and 6 were **inserted in V8**, pushing 7 and 8 down from 5 and 6. Index the trailing
fields from the END — that shift caused finding 9 (see `clvmPuzzleAudit.md`).

### State — curried, changes every spend

```
[[[asset_id, reserve_coin_id, amount], ...], total_lp]
```

Every reserve amount must be positive and every coin id non-zero.

### Constants (`inline const`, therefore permanent per pool)

| constant | value | meaning |
|---|---|---|
| `MIN_ASSETS` / `MAX_ASSETS` | 1 / 10 | one asset is a vault |
| `MAX_WEIGHT_UNITS` | 8 | per-asset weight cap |
| `MAX_TOTAL_WEIGHT` | 20 | bounds the invariant's exponent |
| `MAX_FEE_BPS` | 200 | 2%; the interface offers at most 1% |
| `MAX_PROTOCOL_FEE_BPS` | 100 | 1% |
| `WEIGHT_SCALE` | 10000 | basis-point scale for fees |
| `RATIO_SCALE` | 1e12 | fixed-point scale for the balanced-deposit ratio |

Changing one requires a new revision and only affects pools minted afterwards.

---

## The invariant

A pool holds `prod(reserve_i ** weight_i)` constant, where each weight is a small positive
integer and `K` is their sum. Equal weights are all ones; an 80/20 pool is `[4, 1]`. Displayed
percentages are `weight_i / K`.

Fractional exponents are the usual reason weighted pools are avoided on chain. They are not
needed here, because **the puzzle never solves for an output — it only verifies one.** Both the
swap and the mint are checked by bracketing: the claimed value must hold the invariant, and one
unit more must break it. That pins the result exactly using nothing but integer multiplication.
With every weight at one it reduces to constant product, output for output.

### Swap

Exactly one reserve rises and one falls; every other reserve must be untouched.

```
effective_in = gross_in * (WEIGHT_SCALE - fee_bps) / WEIGHT_SCALE
charged_in   = reserve_in + effective_in
floor        = reserve_in^w_in * reserve_out^w_out

require  charged_in^w_in * next_out^w_out        >= floor
   and   charged_in^w_in * (next_out - 1)^w_out  <  floor
```

The liquidity fee stays inside the curve, so it accrues to the reserve and is earned by LP
holders.

### Mint (add liquidity)

```
ratio        = min over i of (deposit_i * RATIO_SCALE / old_i)
balanced_i   = old_i * ratio / RATIO_SCALE
excess_i     = deposit_i - balanced_i
fee_i        = fee_base * fee_bps * fee_share / (K * WEIGHT_SCALE)
effective_i  = old_i + deposit_i - fee_i

require  new_lp^K       * prod(old_i^w_i) <= total_lp^K * prod(effective_i^w_i)
   and   (new_lp + 1)^K * prod(old_i^w_i) >  same
```

The imbalance fee falls only on the share of the excess that is effectively a trade into the
other assets — **`(K - k_i)/K` in weight units, not `(n-1)/n`**. Without it, an unbalanced add
followed by a pro-rata remove would be a fee-free swap.

### Burn (remove liquidity)

```
withdrawal_i = old_i * burn * (WEIGHT_SCALE - vault_fee) / (total_lp * WEIGHT_SCALE)
```

`vault_fee` is zero for every multi-asset pool, which leaves this exactly proportional and free.
`burn < total_lp` is required, so the pool always outlives the withdrawal.

### The vault (one asset)

A single-asset pool cannot swap — `valid_pairwise_swap` needs one reserve up and one down, which
is unsatisfiable with one reserve, so the pool refuses to trade rather than needing a separate
guard. What it is instead is a vault: deposits mint a receipt CAT against one reserve, and
burning it redeems the share.

Because a vault cannot swap, **crossing between its LP and its reserve is the only trade it
has**, and from V8 the pool's liquidity fee applies to that crossing in both directions — the fee
falls on the **whole deposit** rather than the excess. What is withheld stays in the reserve,
where its holders own it. A vault's LP is an ordinary CAT, so routes reach a vault's liquidity by
acquiring its LP elsewhere and redeeming here.

---

## Authorisation — the part worth reading closely

### Reserves — who may move the assets

A reserve only moves when its **own pool** says so:

```
AssertMyPuzzleHash       { puzzle_hash: reserve_cat_puzzle_hash }
AssertPuzzleAnnouncement { id: sha256(pool_full_puzzle_hash + pool_message) }
```

`pool_full_puzzle_hash` is rebuilt inside the reserve from its **curried launcher id** and the
pool's inner puzzle hash. Only a genuine singleton of that launcher can carry that puzzle hash,
and a coin fabricated at the same hash cannot be spent — the singleton top layer checks lineage
back to the launcher. `AssertMyPuzzleHash` pins the solution-supplied reserve hash to the puzzle
the coin actually runs, so the successor is always a real reserve of the same pool.

> **Why a puzzle announcement and not a coin announcement.** A coin announcement is keyed by coin
> id alone, and any coin can emit any message. Through V9 the reserve asserted a coin
> announcement from a pool coin id supplied in its own solution, so *anyone* could authorise
> draining *any* pool.

The reverse direction is a coin announcement and always was sound: the pool names one specific
reserve coin id taken from its own tracked state.

### LP — who may mint or burn

The pool derives the LP action coin's id rather than accepting one. See `forgeLpCat.md` for the
full three-part lock (derive the id, pin the inner, require a CAT parent on a melt).

---

## Fees — four distinct charges

| fee | where | when | paid to | compounds per hop |
|---|---|---|---|---|
| **Liquidity fee** | in-puzzle, per pool | every swap; a vault's wrap/redeem | stays in the reserve → LP holders | yes |
| **Protocol fee** | in-puzzle, per pool | swaps only | `protocol_puzzle_hash` | yes |
| **Router fee** | outside the puzzle | when we settle | router address | no, once per swap |
| **Pool creation** | outside the puzzle | once, at creation | platform address | n/a |

**In-puzzle fees are necessarily per-pool** — a puzzle only sees its own reserves, so it cannot
know it is one hop of a route. **Once-per-swap fees are necessarily router-enforced**, and
therefore bypassable by anyone who builds their own bundle.

The protocol fee sits **on top of** the liquidity fee rather than being carved out of it,
following Uniswap V4. The pool releases the same curve output either way; the trader receives
that output minus the fee. Paying it out of the *output* is what makes it enforceable: a
shrinking reserve is the one spend that physically creates coins, so it creates two — the
trader's settlement and the recipient's payment. The pool derives the amount from its own config
and binds it into the reserve plan announcement, so a reserve cannot be spent with any other
split.

The **router fee comes only out of surplus** — the gap between what the curve releases and the
smaller amount the trader notarised in their Offer. It is capped at that surplus, so the trader
is always paid at least what they signed for, at any rate the router asks (verified to
100,000 bps).

---

## Modes

| mode | value | LP delta | what must hold |
|---|---|---|---|
| `MODE_SWAP` | 0 | zero, and `lp_action_coin_id` must be zero | one reserve up, one down, rest frozen; bracket holds |
| `MODE_ADD` | 1 | positive | no reserve falls, at least one rises; mint bracket holds |
| `MODE_REMOVE` | 2 | negative | `burn < total_lp`; withdrawal is exactly proportional |

The action passed in the solution:

```
[mode, current_pool_coin_id, reserve_plans, lp_action_coin_id, lp_delta, lp_parent_id]
```

`lp_parent_id` is V10+; earlier revisions take the first five fields.

---

## Cutting a new revision

1. Bump `PROTOCOL_VERSION` in `pool_singleton_FORGE.rue` and `forge_lp_cat_tail_FORGE.rue`.
2. Bump `FORGE_VERSION` in `contracts/forge_puzzles.py`.
3. Copy the FORGE files to `development/puzzles/*_v{N}.*` as the versioned record, and the
   compiled hex to `development/compiled/`.
4. Register both in `compiled/v3-manifest.json`. The JS reconciler matches
   `pool_singleton_v(\d+)\.rue`, so the versioned entry is what maps a module hash back to a
   version.
5. Register the version in `forge_create_pool.py`, `forge_stdin.py`, `forge_transition.py`, and
   the gates in `api/_forgeResponder.js`.
6. Run the suite. `_test_forge_integrity.py` enforces that sources compile to the shipped hex,
   match the pool's baked constants, and stay byte-identical to the archived snapshot.
7. Re-probe per `clvmPuzzleAudit.md` — two of the ten findings were **introduced by the fix for
   an earlier one**, both arriving with the same revision.

A pool's puzzle is fixed at creation and old pools stay on chain, so archived revisions must
remain loadable — that is what `development/` and the resolver are for. New pools mint at
`DEFAULT_VERSION` only; minting a superseded revision is refused unless
`allowUnsafeLegacyVersion` is set, which the HTTP relay drops.

### V11 is not a revision of this puzzle

V11 replaces `pool_singleton_FORGE` and `forge_reserve_FORGE` with the CHIP-0050 action layer,
generic singleton-delegated reserves and a Forge-written multi-reserve finalizer. The curve, the
fees and the LP CAT carry over unchanged. The steps above still apply to the LP TAIL bump and the
version registration, but the puzzle set is different — `chip0050ActionLayer.md` is the design.

---

## Version history — what is unsafe and why

| | what changed | safety |
|---|---|---|
| V4 | 2 CATs, `geometric-invariant-v1`, signed-offer creation | LP burn unauthenticated; reserves unbound |
| V5 | one asset may be native XCH; keyless creation; genesis LP lock added mid-project | same two criticals |
| V6 | 2–10 assets, weights stored as **basis points**, imbalance fee on adds | same two criticals |
| V7 | real integer weights, single-asset vaults (free) | same two criticals |
| V8 | per-pool protocol fee + recipient inserted at config 5/6; vault crossing charges the liquidity fee | reserves still unbound |
| V9 | LP action coin id derived and inner pinned | reserves still unbound; introduced the fabricated-melt and vault-redemption defects |
| V10 | reserve curried with `launcher_id`, puzzle-announcement authorisation, `AssertMyPuzzleHash`, `lp_parent_id` | **shipping** |
| V11 | CHIP-0050 action layer: merkle-tree actions, message-bound generic reserves, multi-reserve finalizer; curve, fees and LP CAT unchanged | **planned, not started** — `chip0050ActionLayer.md` |

All pre-V10 testnet pools were retired; the deployment index was cleared and
`normalizeDeploymentIndex` now drops any batch that is not the shipping revision, on the way in
as well as out. **Never re-enable an older revision for creation** — an LP coin, once minted,
cannot be undone, and a pool's puzzle is fixed at creation.
