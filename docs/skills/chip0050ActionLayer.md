# Skill: CHIP-0050 — Action Layer and Slots

> The upstream framework Forge V11 is built on. **CHIP-0050 is a CNI CHIP** (Informational,
> Puzzle, Final) in `Chia-Network/chips`, not a Forge document —
> <https://github.com/Chia-Network/chips/blob/main/CHIPs/chip-0050.md>. This file is the
> working summary plus what it means for Forge; the CHIP is the authority and wins on any
> disagreement.
>
> Written 2026-09-05 because the V11 Build Spec cited this file and it had never been copied
> onto the workstation.

> **V11-era tooling.** A few helpers below still carry `v11` in their names and have no
> V14 counterpart: `scripts/v11_offer_router.py`, `scripts/v11-lp-holders.py`,
> `scripts/v11-create-pool-keyless.py`, `scripts/v11-respond-offer.mjs` and
> `scripts/verify-v11-pool.py`. They are named accurately — the files exist — but they
> predate the V14 lanes; for V14 use `scripts/v14_ops.py`, `scripts/v14-lifecycle-matrix.py`
> and `scripts/v14-offer-lane-test.py`.


---

## Domain

Use this for:

- reasoning about the V11 pool as an action-layer singleton rather than a monolithic puzzle
- writing or reviewing an action, the shared prologue, or the multi-reserve finalizer
- deciding whether data belongs in persistent state, ephemeral state, or a slot
- understanding why the V4–V9 reserve bug class cannot exist under this framework

For the V10 puzzle being replaced see `forgePuzzleV10.md`; for the LP CAT handshake that
carries over see `forgeLpCat.md`; for the audit method see `clvmPuzzleAudit.md`.

---

## What CHIP-0050 provides

Three pieces, and Forge uses all three.

### 1. The action layer

Every puzzle allowed to run inside the singleton goes into a **merkle tree**, and the layer
curries that tree's **root**. An action is invoked by revealing the puzzle plus a merkle proof
against the root — the pattern of `p2_1_of_n`, generalised to many actions per spend. For a
second and later action in the same spend the previous reveal is referenced rather than
re-hashed, so running several actions is cheaper than running them separately.

The set is fixed at creation. **There is no upgrade leaf and no way to add one**, which is the
property that makes a pool's behavior auditable once and forever.

### 2. State — persistent and ephemeral

Each action receives `((ephemeral . state) . solution)` and returns
`((ephemeral' . state') . conditions)`.

- **Persistent state** survives the spend and is what the finalizer commits into the successor.
- **Ephemeral state** starts empty on every spend and is discarded after the last action. It is
  how actions in one spend coordinate — Forge uses it to pin a single height across every
  action in a bundle.

Actions are chained: one action's output state is the next one's input.

### 3. Slots

**0-amount coins** holding data, spendable only by the owning singleton. Intended for "lists or
mappings that grow to have a large number of entries, each of which is only rarely accessed",
and they can enforce uniqueness through key–value pairs.

Choose by access pattern, not by size:

| | persistent state | slot |
|---|---|---|
| hashed every spend | yes | no |
| read on most spends | yes | no |
| grows without bound | bad fit | good fit |
| cost | cheap to read, paid always | a coin and a spend, paid on use |

The CHIP does **not** specify a lookup mechanism for finding a slot. That is fine when the
reader already knows the singleton — derive the slot puzzle hash from it and query by puzzle
hash. It is *not* fine for anything a third party must discover cold; that needs a hint
(`CHIP-0020`), which is a different mechanism entirely.

---

## Finalizers

The finalizer runs after every action and is the only component that creates the successor.

- **Default finalizer** — recreates the singleton with the new state.
- **Reserve finalizer** — additionally manages **one** reserve whose amount lives in persistent
  state. An action marks a condition as belonging to the reserve with the marker **`-42`**.

Forge needs N reserves, so `forge_multi_reserve_finalizer.rue` is written from the upstream
reserve finalizer, extending the marker to `(-42 index . condition)` and sending one
`SEND_MESSAGE` per reserve.

**A finalizer is not our router.** It is the end-of-spend commit step. The Forge router does two
separable jobs and only one of them is this:

- *route discovery* — cycle finding, equilibrium, flow-versus-split. Search over the whole
  market; stays off chain, and a puzzle should not attempt it.
- *settlement* — reconciling reserve deltas, producing successors, proving the bundle balances.
  This is the half a reserve finalizer covers.

Adopting CHIP-0050 moves settlement into the puzzle layer and leaves discovery where it is.

---

## Why Forge adopted it

The rule was: adopt if it is more secure with fewer points of exploit long term.

Forge-written binding checks drop from roughly 21 to roughly 4, and the **reserve-only bug
class — which every V4 to V9 critical belonged to — cannot exist**, because reserves are no
longer bound by hand-rolled announcements. Two concrete examples of what that class looked like:

- **Through V8**: the pool released reserves against a burn whose only link was an announcement
  from a free-form `lp_action_coin_id`. Any coin can emit any message, so an attacker could
  nominate a coin they controlled and drain reserves for LP that was never destroyed.
- **Through V9**: the reserve took the announcing coin's id from its own solution, so any coin
  the spender owned could authorize draining any pool. The singleton was never consulted.

Both are the failure class `CHIP-0025` message conditions exist to remove, and V10's fixes are a
correct but manual reconstruction of what the mode byte does structurally.

---

## How Forge V11 uses it

Five leaves, fixed forever per pool: **`swap`, `add`, `remove`, `observe`, `collect`**.

- A **shared prologue** runs in the first action of a spend only: height pin, `ASSERT_MY_AMOUNT(1)`,
  oracle accumulation on the *pre-spend* price, and `prev_root` chaining. Later actions assert the
  same height out of ephemeral state.
- **Persistent state** is `[reserves, total_lp, fees_owed, oracle, prev_root]`. Config is curried
  into the actions, so the merkle root commits to it.
- **Slots** hold observation snapshots (nonce 1) and, in the separate registry singleton, one
  entry per pool in a sorted list so a duplicate key cannot be inserted.
- The **multi-reserve finalizer** recreates every reserve on every spend, touched or not, and
  derives each receiver coin id from the *pre-spend* amount in the truth — so an action cannot
  aim a message at a coin that is not the current reserve.

---

## Established in phase 1 (2026-09-05)

Facts the first V11 sprint pinned down; each is checked by a suite rather than remembered.

- **The pins are the rue builds.** chia-sdk-types 0.36.0 ships the tree hashes of
  `rue-puzzles/singleton/*.rue.hex` from Yakuhito/slot-machine at `2d37ba1`; the clsp builds of
  the same puzzles hash differently. Upstream's manifest names rue 0.9.0, but the installed
  **rue 0.8.4 reproduces every hash** — `contracts/_test_v14_integrity.py` recompiles the vendored
  sources in a scratch copy on every run to prove it.
- **V11 is a rue project**, `contracts/v14/` (`Rue.toml`: entrypoint `puzzles`, dist `compiled`).
  Every `.rue` under `puzzles/` is a module named by its stem; `import forge_curve::*;` and
  `import upstream::finalizer::*;` are how actions and the finalizer reach shared code, `super::`
  walks up a directory, and `export fn` marks what other modules (and `rue build --export`) may
  use. Upstream sources live verbatim under `puzzles/upstream/` and their sha256s are in
  `pins.json`.
- **Message conditions are consensus on testnet11.** A mode-23 (`SENDER_PUZZLE | RECEIVER_COIN`)
  pair confirmed in block 4,647,109 (`scripts/probe-chip0025-testnet11.py`). The finalizer design
  is no longer gated on activation.
- **Reserve tag is `(-42 index . condition)`.** Upstream's `parse_conditions` strips on one marker;
  the index goes inside the tag, and an index outside the asset count is the one added failure
  branch.
- **The curve is a module, not a puzzle.** `puzzles/forge_curve.rue` exports the V10 functions over
  `List<Int>` amounts; four of them (`exact_swap_output`, `pow_int`, `sum_weights`, `vault_fee_bps`)
  compile byte-identical to V10, and `_test_v14_curve_equivalence.py` holds the rest to identical
  output on the 81-spend testnet corpus and 300 randomized pools.
- **Observe announces, it does not message.** A `SEND_MESSAGE` with no receiver in the block fails
  the spend, so an oracle snapshot with no consumer present could never land; a puzzle
  announcement is one-directional.
- **The multi-reserve finalizer exists and is probed.** `contracts/v14/puzzles/forge_multi_reserve_finalizer.rue`
  generalizes upstream's in two places only: the index inside the tag, and one mode-23 message per
  reserve with the receiver derived from the **pre-spend** amount in the truth. The curried
  `RESERVE_AMOUNT_PROGRAM` is `forge_reserve_amount.rue`, `(state, i) -> reserves[i] + fees_owed[i]`.
  `_test_v14_finalizer.py` (42 checks) runs it through `chia_rs.get_conditions_from_spendbundle`, the
  mempool's validator: a CLVM assertion in the singleton surfaces as error 117, an unmatched message
  as 147. Costs with a passthrough leaf: N=2 about 120M, N=10 about 404M.
- **Conservation is the reserve's job, honesty is the action's.** The finalizer sizes the recreated
  reserve from state; the reserve coin refuses to create more than it holds, so an action whose state
  omits a payout dies in the reserve spend. The reverse, a state that shrinks a reserve with no payout,
  burns the difference as fee and is *legal*; the curve actions must make that impossible.
- **The five leaves exist** (`forge_action_{swap,add,remove,observe,collect}.rue`, shared prologue in
  `forge_action_common.rue`), each curried with `PoolConfig` and every solution a proper list of fixed
  fields. Driver conventions that must match the wallet-sdk: `puzzles` is a list, selectors are 2, 5,
  11, … in order of first use, a proof is `(path . hashes)` from the sdk's midpoint-split tree
  (`contracts/forge_merkle.py`), and a reserve's delegated puzzle lists its tagged conditions in
  reverse emission order because the finalizer prepends. The observe slot is double-curried like
  upstream's: `(singleton info, nonce)` first, the value hash second.
- **Every CAT mojo is an XCH mojo.** A mint eve of one mojo minting `lp_delta` LP fails MINTING_COIN
  unless a coin in the bundle carries `lp_delta` mojos; V10's creation offer sized it so, and the
  harness must too.
- **The registry exists** (`forge_registry_{common,init,register}.rue`, default finalizer, two-leaf
  tree). `register` derives the launcher id from the launcher's parent, recomputes the pool's full
  puzzle hash in rue (`pool_full_puzzle_hash`, including `five_leaf_root` in the sdk shape) and asserts
  the launcher's `sha256tree([full_ph, 1, kv])` announcement; the fee is an OFFER_MOD payment to the
  treasury under the launcher id as nonce. Slots are `(key . (launcher . (left . right)))`, key =
  `tree_hash([asset_ids, weights, fee_bps, protocol_fee_bps])`, sentinels 0x00 and 0xff, adjacency
  structural as in CATalog. `init` is one-shot and creates the sentinels.
- **Genesis LP is launcher-authorized.** No singleton of a new pool has spent at creation, so the TAIL's
  message path cannot authorize the first mint. The TAIL's genesis branch asserts the launcher's coin
  announcement `sha256tree([full_puzzle_hash, 1, (expected_delta)])` — once, only in the launcher's
  bundle, only for that supply — and the registry asserts the same with `(total_lp)`. Found and closed
  during phase 4 (finding V11-1).
- **V11 is live on testnet11** (2026-09-05): registry `31ab7ead7b06d698…`, pool `be4c270006a43e3f…`, every leaf
  confirmed via `scripts/deploy-v14-testnet.py`; `forge_v14_driver.py` is the one implementation both the
  suites and the deploy script use. Fees: about 6 mojos per cost, or the full mempool refuses the bundle.
- **Multi-action ordering.** The action layer prepends each action's condition list, so the finalizer
  walks the LAST action first; the per-reserve delegated puzzle is each action's tagged conditions
  reversed, concatenated in execution order. `forge_v14_driver.spend_actions` mirrors this and the
  wallet-sdk's selector/proof convention (proof carried by the last use of a selector in execution
  order; earlier uses pass nil). The sandwich and same-spend-observe probes live on it.
- **The eve singleton is not hinted.** The standard launcher attaches no memo, so a pool that has never
  spent is found as its launcher's child; every later generation the finalizer re-creates is hinted.
- **Launch matrix live**: 16 registered V11 pools on testnet11 (2026-09-05), record in
  `.awizard/v14-testnet.json`; vaults, nested LP reserves, weighted, three- and five-asset, fee edges.
- **Lifecycle across the matrix is on chain** (71 confirmed transactions on 2026-09-05): adds on all pools,
  swaps on every multi-asset pool, collects, removes (both vaults, the nested pool), observes, and a two-pool
  multi-hop where pool A's CAT payout settlement is pool B's input in the same bundle — separate CAT rings
  per pool balance on their own. `scripts/v14_ops.py` is the generic operator; `resync` re-runs a spend's
  leaves on the recorded state to rebuild a record, which is also how an indexer follows a pool.
- **Offer flow on V11** (`scripts/v11_offer_router.py`, live 2026-09-05): the offer's OFFER_MOD settlement
  coins are the leaf's inputs (spent under their own id, no payments); the payout coin pays the offer's
  requested groups plus a surplus group to the router; on an add the eve mints to OFFER_MOD and that coin
  pays the request; on a remove the offered LP settlement pays the pinned melt inner so the melt has a CAT
  parent; the add's LP backing rides in the offered XCH. Sign only the router coin and aggregate with the
  offer's signature; exclude the offer's coins from the router's funding pick.
- **Keyless settlement** (`contracts/forge_v14_offer.py`, behind `forge_stdin.py` for V11 snapshots, live
  2026-09-05 through the responder): no router coin at all. The trader's offer carries the network fee;
  on an add the XCH settlement's second payment group creates the one-mojo LP eve (nonce
  `sha256(coin_id || "forge-lp-eve")`, asserted by nobody) and returns XCH above the backing to the surplus
  recipient; the surplus recipient defaults to the pool's protocol puzzle hash. The builder needs
  `current_height` (the leaves bind spends to the height); the server reads the peak, never the browser.
  Snapshots round-trip node's `JSON.parse`, so state integers are strings; `snapshot_to_pool` re-curries and
  checks the pool coin's puzzle hash before anything is built.
- **Resync by replay** (`contracts/forge_v14_resync.py`): a V11 tip's state is curried, so a lagging snapshot
  is advanced by fetching each spent generation's solution, uncurrying the leaves it ran (module hash → name),
  running them on the recorded state with the ephemeral threaded through, and `advance`; verified against
  the live puzzle hash.
- **Routes as hubs** (`contracts/forge_v14_route.py`, live 2026-09-05): per asset, producers (offer settlements,
  payouts, redemptions, LP mints) and consumers (legs, the trader's request). One producer + one pool consumer
  bridge directly (the payout coin IS the next settlement, spent `[[id]]` in the consuming pool's ring);
  otherwise one standalone ring where the first producer pays child settlements `[OFFER_MOD_HASH, amount]`
  (nonce `sha256(coin_id || "forge-hub")`), the requested groups and the remainder to the surplus recipient,
  the rest empty groups. Children of one parent must differ in amount (nudge equal shares by a mojo). A pool
  crossed twice runs two actions in one spend via `spend_actions`, same `h`. Entry legs drink from the offer,
  others from earlier legs; re-derive amounts in topo order and run every leaf locally with `run_leaf`.
- **CHIP-0040's TAIL was evaluated and declined** for the LP CAT: it ignores `parent_is_cat` and
  commits only to `delta`, which reopens the fabricated-melt finding. The message mechanism is
  adopted; the standard TAIL is not.

---

## Traps

- **`-42` is upstream's marker, not ours.** An index outside the asset count must fail the
  bundle; do not let an unrecognised tag fall through to the base condition bucket.
- **The action set is immutable.** Anything a pool might ever need — the oracle is the live
  example — has to be a leaf at creation. There is no adding one later without a new pool.
- **Ephemeral state is not authenticated across spends.** It is per-spend scratch; anything that
  must survive belongs in persistent state.
- **A slot is not discoverable cold.** Singleton-owned and no lookup mechanism in the CHIP: fine
  for a reader who has the launcher id, useless as a discovery index. See `CHIP-0020`.
- **Upstream puzzles are hash-pinned and never edited.** `action.rue`,
  `p2_delegated_by_singleton.rue` and `slot.rue` come from chia-sdk-types; the integrity suite
  fails on any drift. Editing one moves it into the audit scope, which defeats the reason for
  adopting the framework.

---

## Related CHIPs

| CHIP | Title | Bearing |
|---|---|---|
| **0050** | Action Layer and Slots | this file |
| **0025** | Chialisp Message Conditions | how the finalizer binds reserves; supersedes announcements for new work |
| **0020** | Wallet Hinted Coin Discovery | how a payout coin becomes findable; unrelated to slots |
| **0014** | `ASSERT_BEFORE_*` conditions | the prologue's window bound, and a dispute window if one is built |
| **0051** | Reward Distributor | built on this framework; evaluated and declined for trading fees because it earns by staking |
| **0040** | `everything_with_singleton` TAIL | the standard singleton-controlled TAIL, message-based; candidate to replace Forge's bespoke one |
