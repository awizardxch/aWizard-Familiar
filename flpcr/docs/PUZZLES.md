# FLPCR — Distributor Puzzles (build spec)

> The phase 2 build spec, in the shape the V14 specs took. Nothing here is written in Rue yet. It is
> meant to be built in `contracts/flpcr/` on the Forge workstation, where `rue` 0.8.4, `chia_rs` and
> the V14 harness live. Read with `SPEC.md` §5, `chip0050ActionLayer.md` and `clvmPuzzleAudit.md`.

## Shape

```
distributor = singleton( action_layer( reserve_finalizer, LEAVES_ROOT, state ) )
reserve     = p2_delegated_by_singleton(distributor_launcher, nonce 0), bare XCH or CAT(reward_asset)
```

- `action_layer`, `reserve_finalizer`, `p2_delegated_by_singleton` and `slot` are the
  upstream builds, hash-pinned. **None is edited.** The reserve finalizer's
  `RESERVE_AMOUNT_PROGRAM` is `flpcr_reserve_amount.rue`: `state -> state.reserve_total`.
- Eight leaves, each curried with the same `Config` (the M-4 lesson: the finalizer is curried
  with `CONFIG_HASH` and the leaf mod hashes, and rebuilds the root every spend; copy V14's
  `config_root`).
- A shared prologue in the first action only: `h > last_height`, `ASSERT_HEIGHT_ABSOLUTE h`,
  `ASSERT_BEFORE_HEIGHT_ABSOLUTE h + 32`, `ASSERT_MY_BIRTH_HEIGHT birth` with `h >= birth`,
  `ASSERT_MY_AMOUNT 1`. Later actions read `h` from ephemeral state.
- Every solution is a proper list of fixed fields, `[h, …]`. **Derived, never claimed**: any value
  the puzzle can compute (campaign id, settlement coin id, entry leaf) is computed, not read
  from the solution.

## Config (curried)

| Field | Bound |
|---|---|
| `distributor_id` | the launcher id; also in every entry leaf |
| `reward_asset` | `ZERO_32` = XCH |
| `treasury_ph`, `fee_bps` | `fee_bps <= MAX_FEE_BPS` (500) |
| `guardian_ph` | intended: a Forge multisig safe's puzzle hash |
| `dispute_blocks` | `>= MIN_DISPUTE_BLOCKS` (384 ≈ 2 h) |
| `payout_window` | blocks after activation an epoch stays payable |
| `max_campaigns`, `max_live_epochs`, `max_entries` | e.g. 32, 4, 2048. These bound the state hashed every spend |
| `max_duration` | e.g. 4,608 × 365 blocks |

## State

```
[engine_ph, campaigns, epochs, last_epoch_id, last_epoch_end, fees_owed, reserve_total, last_height]
campaign = (id, creator_ph, amount, start, end, allocated)
epoch    = (epoch_id, root, entry_count, remaining, paid_bitmap, activates_at, expires_at, allocations)
allocations = ((campaign_id . mojos) ...)
```

Invariant every leaf must preserve, and a suite must check after every leaf on random state:
`reserve_total == Σ(amount − allocated) + Σ remaining + fees_owed`.

## Leaves

### `create` `[h, campaign_fields, params, settle_parent, settle_amount]`

- Rebuild `params_hash = sha256tree(params)` and
  `id = sha256tree(["flpcr-campaign-v1", distributor_id, creator, reward_asset, amount, start, end, kind, target, params_hash, nonce])`.
- `amount > 0`, `start >= h`, `start < end <= start + max_duration`, `kind ∈ {1,2}`,
  `time_bps + fees_bps == 10000`, `kind == 2 ⇒ fees_bps == 0`, `len(campaigns) < max_campaigns`,
  id not already in `campaigns`. Params list shape is checked; list contents are not (the engine
  interprets them).
- `fee = amount * fee_bps / 10000` (floor); `settlement_binding(reward_asset, settle_parent, settle_amount, amount + fee)`
  (V14 §2: derived id, `ASSERT_CONCURRENT_SPEND`, `amount >= at_least`). **Bundle slack:** the
  settlement's excess over `amount + fee` is the trader's gift to the distributor. Accrue the excess
  to `fees_owed` instead of dropping it, so `reserve_total` matches the coins.
- State: append the campaign with `allocated = 0`; `fees_owed += fee + excess`;
  `reserve_total += settle_amount`. Reserve conditions: none (the settlement is spent into the
  reserve by the finalizer's recreate amount).
- Emit `CREATE_PUZZLE_ANNOUNCEMENT ["flpcr-created", id]` for indexers.

### `post_epoch` `[h, epoch_id, start, end, root, entry_count, allocations, manifest_hash]`

- Message: `RECEIVE_MESSAGE` mode 23 from a coin at `engine_ph`, content
  `sha256tree(["flpcr-post", distributor_id, epoch_id, start, end, root, entry_count, allocations, manifest_hash])`.
- `epoch_id == last_epoch_id + 1`, `start == last_epoch_end` (except the first, where
  `last_epoch_end` is nil and `start` is free), `start < end <= h`, `0 < entry_count <= max_entries`,
  `len(epochs) < max_live_epochs`.
- `allocations` is sorted by campaign id with no duplicates. For each `(cid . a)`: `a > 0`, the campaign
  exists, and `allocated + a <= amount * (min(end, c.end) − c.start) / (c.end − c.start)`, with the
  right-hand side `0` when `end <= c.start`. Then `allocated += a`.
- Append the epoch: `remaining = Σ a`, `paid_bitmap = 0`, `activates_at = h + dispute_blocks`,
  `expires_at = activates_at + payout_window`. `last_epoch_id`, `last_epoch_end` advance.
  `reserve_total` is unchanged (allocated money moves from "unallocated" to "remaining").

### `veto` `[h, epoch_id]`

- `RECEIVE_MESSAGE` mode 23 from `guardian_ph`, content `sha256tree(["flpcr-veto", distributor_id, epoch_id])`.
- The epoch must be pending (`h < activates_at`) **and the newest** (vetoing an older pending one
  would break `start == last_epoch_end` tiling). Undo its allocations, remove it, and roll
  `last_epoch_id` / `last_epoch_end` back to the previous epoch's. The engine then re-posts a
  corrected epoch with the same id.

### `payout` `[h, epoch_id, items]` where `item = (index, puzzle_hash, amount, path, hashes)`

- The epoch is active: `activates_at <= h < expires_at`.
- Per item: `0 <= index < entry_count`; bit `index` of `paid_bitmap` is clear (then set it);
  `amount > 0`; `simplify_merkle_proof(sha256tree(["flpcr-entry-v1", distributor_id, epoch_id, index, ph, amount]), (path . hashes)) == root`;
  `remaining -= amount`, refused below zero. Reserve condition `(-42 . (CREATE_COIN ph amount (ph)))`.
- `reserve_total -= Σ amount`. Two items to the same `ph` in one spend create two coins with the
  same `(ph, amount)` only if the amounts are equal. Refuse equal `(ph, amount)` pairs in one call,
  otherwise the bundle fails `DUPLICATE_OUTPUT` (the V13 `collect` lesson).
- Remove the epoch when `remaining == 0` and every bit is set.

### `expire` `[h, epoch_id]`

- `h >= expires_at`. Return `remaining` to campaigns pro rata by the epoch's `allocations` (floor;
  the remainder goes to the largest allocation so the sum is exact) by reducing each `allocated`.
  Remove the epoch. `reserve_total` unchanged.

### `reclaim` `[h, campaign_id]`

- `h >= end`; no live epoch has `end > campaign.start` while still not covering `campaign.end`.
  In practice: `last_epoch_end >= campaign.end` and no live epoch's `allocations` names this
  campaign. Pay `amount − allocated` to `creator_ph` (hinted), remove the campaign,
  `reserve_total -= that`.

### `collect` `[h]`

- Pay `fees_owed` to `treasury_ph` (hinted) if positive; `fees_owed = 0`; `reserve_total -= it`.

### `rotate` `[h, new_engine_ph]`

- Message from `guardian_ph`, content `sha256tree(["flpcr-rotate", distributor_id, new_engine_ph])`.

## Registry

Copy `forge_registry_{common,init,register}` with key = `reward_asset`, one distributor per
asset. `register` rebuilds the distributor's full puzzle hash from config (so a registry entry
**is** a known-good config: `dispute_blocks` floor, `fee_bps` cap, the protocol `treasury_ph`
pinned by `RegistryConstants`) and asserts the launcher's announcement. Same squat analysis
as V14's R-1: a distributor needs no funded reserve to be valid (an empty reserve is a real
coin of 0 mojos created by the launcher), so the launcher creates it and `register` proves it.

## Suites to write (V14 conventions)

| Suite | Proves |
|---|---|
| `_test_flpcr_integrity.py` | every puzzle recompiles to its pinned hash; upstream untouched |
| `_test_flpcr_ceiling.py` | `post_epoch` refuses any allocation one mojo above `emittable(end)` at the boundaries (start, mid, end, after end, before start) |
| `_test_flpcr_payout.py` | double payout (same index, same and different spends), wrong epoch's proof, other distributor's proof, `remaining` underflow, duplicate output |
| `_test_flpcr_tiling.py` | epoch id gaps, overlaps, future `end`, veto of a non-newest epoch |
| `_test_flpcr_reclaim.py` | reclaim before end, with a live epoch, twice |
| `_test_flpcr_invariant.py` | the `reserve_total` identity after random leaf sequences |
| `_test_flpcr_engine_agrees.py` | the engine's manifest pays out on the simulator entry by entry; `root_from_proof` matches the CLVM `simplify_merkle_proof` |
| `scripts/mutate-flpcr.py` | every assertion killed or reported UNREACHED with a written argument |
