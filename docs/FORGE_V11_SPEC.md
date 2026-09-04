# Forge V11 — Build Specification

> From V10 (monolithic pool inner, custom reserve puzzle, announcements) to V11 (CHIP-0050 action
> layer, generic message-bound reserves, Forge-written multi-reserve finalizer, oracle, fee accrual,
> on-chain registry). Written 2026-09-04. Testnet11 only. Nothing here is built or audited.
>
> The durable design rationale lives in [`docs/skills/chip0050ActionLayer.md`](skills/chip0050ActionLayer.md);
> this file is the build order. V10 is described in [`docs/skills/forgePuzzleV10.md`](skills/forgePuzzleV10.md).

---

## 0. Decision ledger

All dated 2026-09-04, confirmed by the protocol owner.

| decision | outcome |
|---|---|
| Adopt CHIP-0050 | **Yes.** Rule: adopt if more secure with fewer points of exploit long term. Forge-written binding checks fall from ~21 to ~4; the reserve-only bug class disappears |
| In-puzzle single-action guard | **No.** A pool's puzzle is immutable; a guard would force a V12 migration. Audit the final multi-action puzzle once; one action per spend is router policy at launch |
| Pool type | **Weighted N-asset full range.** V10 curve, fees and LP CAT unchanged |
| Concentrated liquidity | **Off scope.** Returns as a second pool type with NFT positions so wallets and other DEXes identify them. Per-band asset ids and a per-coin position layer were both rejected. N-asset band maths kept as a research record |
| Oracle capability | **Yes.** Height-weighted price accumulator in state, updated by every spend's first action; an `observe` action snapshots to a slot and announces for same-bundle consumers |
| Protocol fee | **Accrue in state, batched `collect`.** No second payout coin per swap |
| On-chain pool registry | **Yes.** Separate CHIP-0050 singleton, one slot per pool, sorted-list uniqueness; replaces the deployment index and gates creation without a key |
| LP mining | **Yes, later,** via the CHIP-0051 reward distributor pointed at the LP CAT. No puzzle work |

---

## 1. Goals and non-goals

**Goals.** Same economics as V10 with fewer points of exploit; one external audit; oracle-capable
pools; on-chain discovery; per-swap cost no higher than V10 (one fewer coin per swap).

**Non-goals.** Concentrated liquidity; upgrade authority of any kind; any admin key; migrating
V10 pools (none hold liquidity); any change to the curve, the fee schedule or the LP CAT lock.

---

## 2. Architecture

```
singleton_top_layer_v1_1 (1 mojo)
        |
action layer  [FINALIZER = forge_multi_reserve_finalizer, MERKLE_ROOT, STATE]
        |                                      \
        |  actions (merkle leaves):             finalizer solution: reserve parent ids
        |    swap · add · remove · observe · collect
        |
   +----+----+------------------+---------------------+
   |         |                  |                     |
reserve_0  reserve_i ...    LP CAT (V10 TAIL)     observation slots (nonce 1)
CAT(asset, p2_delegated_by_singleton(struct_hash, nonce = asset index))
```

| component | source | status |
|---|---|---|
| `action.rue` (action layer) | upstream, slot-machine @ `2d37ba1` | reviewed, on mainnet; **never edited**, hash pinned |
| `p2_delegated_by_singleton.rue` (reserve inner) | upstream | reviewed; pinned |
| `slot.rue` | upstream | reviewed; pinned |
| `merkle_utils`, singleton top layer, CAT2, offer settlement | upstream | as V10 |
| `forge_curve.rue` (shared maths module) | **Forge, ported from V10** | `exact_swap_output`, `exact_invariant_lp_mint`, `exact_withdrawal`, `effective_product`, `valid_protocol_fees`, `pow_int`, `non_decreasing_with_increase`, `vault_fee_bps` — moved, not rewritten |
| `forge_multi_reserve_finalizer.rue` | **Forge, new**, from `reserve_finalizer.rue` | ~120 lines; holds every reserve; deepest review |
| `forge_action_swap.rue`, `_add.rue`, `_remove.rue` | **Forge, new** | V10 mode branches as leaves |
| `forge_action_observe.rue`, `_collect.rue` | **Forge, new** | oracle snapshot; fee payout |
| `forge_action_prologue` (shared) | **Forge, new** | height pin, oracle accumulate, amount assert — first action only |
| `forge_lp_cat_tail_FORGE.rue`, mint/melt inners | V10, `PROTOCOL_VERSION` bumped | unchanged logic |
| `forge_registry_*.rue` (separate singleton) | **Forge, new**, CATalog/XCHandles pattern | register action, pool slots, threshold list |

Upstream tree hashes to pin (chia-sdk-types 0.36.0):
action layer `afa03f29…a22b`, default finalizer `9d274de5…810b`, reserve finalizer
`5b406eb6…8095`, p2_delegated_by_singleton `3f2358e5…e05e`, slot `8ab9f3b5…bbb3` — full
values in the skill file.

---

## 3. State

```
STATE = [
  reserves,     // [r_1 .. r_N]        curve reserves, excluding owed fees
  total_lp,     // Int
  fees_owed,    // [f_1 .. f_N]        accrued protocol fees, physically inside the reserve coins
  oracle,       // [last_height, [cum_1 .. cum_{N-1}]]   cumulative price of asset i in asset 0, × PRICE_SCALE
]
```

- Reserve coin `i` holds `reserves[i] + fees_owed[i]`; the finalizer's amount program returns that sum.
- Reserve coin ids are not in state (V10 kept them). The finalizer derives each from its parent id,
  the reserve's full puzzle hash and the pre-spend amount.
- Config (asset ids, integer weights, `fee_bps`, `protocol_fee_bps`, `protocol_puzzle_hash`,
  `lp_tail_hash`, `PRICE_SCALE`, `ORACLE_WINDOW`) is **curried into each action** and therefore
  committed by the merkle root. Immutable, as in V10. Read from the end for the fee pair, never
  positionally from the front (the V8 lesson).
- The singleton amount is always 1 (asserted in the prologue).

---

## 4. Actions

All actions receive `((ephemeral . state) . solution)` and return `((ephemeral' . state') . conditions)`.
Conditions for a reserve are tagged `(-42 index . condition)`; an index outside `0..N-1` fails.
No action emits relative or height-relative conditions.

### 4.0 Prologue — shared by every action

```
if ephemeral == ():                       // first action of the spend
    assert h > oracle.last_height
    ASSERT_HEIGHT_ABSOLUTE(h)
    ASSERT_BEFORE_HEIGHT_ABSOLUTE(h + ORACLE_WINDOW)
    ASSERT_MY_AMOUNT(1)
    cum_i += spot_price_i0(reserves, weights) * (h - last_height)   for i in 1..N-1
    last_height = h
    ephemeral = (h)
else:
    assert h == ephemeral.h               // every action in a spend names the same height
```

`spot_price_i0 = (reserves[0] / w_0) / (reserves[i] / w_i) × PRICE_SCALE`, integer. The
accumulator uses the **pre-spend** price, so a spend cannot move the price and record it in the
same block; manipulation costs capital across a block, the Uniswap V2 argument. A stale `h`
shifts weighting by at most `ORACLE_WINDOW` blocks.

### 4.1 `swap`

| | |
|---|---|
| solution | `h, asset_in, asset_out, gross_input, claimed_output, settlement_ph, settlement_nonce` |
| checks | `asset_in ≠ asset_out`; `exact_swap_output` bracket on the pair with `effective_input = gross_input × (SCALE − fee_bps) / SCALE`; every other reserve unchanged (`changed_count == 2`); `protocol_fee = valid_protocol_fees(claimed_output)` |
| state' | `reserves[in] += gross_input`; `reserves[out] −= claimed_output`; `fees_owed[out] += protocol_fee` |
| conditions | `(-42 out . CREATE_COIN(settlement_ph, claimed_output − protocol_fee, [nonce]))`; assert the input settlement coin's puzzle announcement (as V10) |

The input arrives at the reserve's puzzle hash via the offer settlement coin; the CAT ring (or
XCH bundle total) makes the reserve's growth honest. **No second payout coin** — the fee stays in
the reserve as `fees_owed`.

### 4.2 `add`

| | |
|---|---|
| solution | `h, deposits[N], lp_delta, lp_parent_id, settlement info` |
| checks | `lp_delta > 0`; `non_decreasing_with_increase`; `exact_invariant_lp_mint` with the imbalance fee (`effective_product`); LP action coin id derived from `lp_parent_id`, `cat_puzzle_hash(lp_tail_hash, LP_MINT_INNER_HASH)`, amount 1 |
| state' | `reserves[i] += deposits[i]`; `total_lp += lp_delta` |
| conditions | LP handshake with the TAIL (puzzle announcement from this singleton, coin announcement back keyed on the derived LP coin id); assert deposit settlements |

### 4.3 `remove`

| | |
|---|---|
| solution | `h, burn, lp_parent_id, settlement info` |
| checks | `0 < burn < total_lp`; `exact_withdrawal` strictly proportional with `vault_fee_bps`; LP action coin id derived with `LP_MELT_INNER_HASH`, amount `burn`; CAT parent required on a melt (TAIL rule, unchanged) |
| state' | `reserves[i] −= out[i]`; `total_lp −= burn` |
| conditions | `(-42 i . CREATE_COIN(settlement_ph, out[i]))` for each `i`; LP handshake |

### 4.4 `observe`

| | |
|---|---|
| solution | `h` (prologue), optional `(h_past, cum_past, past_slot_parent_proof)` |
| checks | prologue only; if a past slot is given, its value hash matches `(h_past, cum_past)` |
| conditions | create observation slot, nonce 1, value `(h, cum)`, memo the value; `CREATE_PUZZLE_ANNOUNCEMENT(sha256("forge-observe-v1", h, cum))`; if past given: message to spend the past slot, recreate it, and announce `(h_past, cum_past)` |

A same-bundle consumer (perps oracle aggregator, a vault) asserts the announcement from the pool's
full puzzle hash and computes `TWAP = (cum − cum_past) / (h − h_past)`. Off-chain consumers read
slots by memo.

### 4.5 `collect`

| | |
|---|---|
| solution | `h`, asset index list (or all) |
| checks | prologue; `fees_owed[i] > 0` for each listed `i` |
| state' | `fees_owed[i] = 0` |
| conditions | `(-42 i . CREATE_COIN(protocol_puzzle_hash, fees_owed[i]))` per listed `i` |

Permissionless. Recipient is curried; the amount is state. Nobody can redirect it.

### Merkle root

Five leaves, fixed forever per pool: `swap, add, remove, observe, collect`. No upgrade leaf.
Test that a sixth puzzle with a valid-looking proof is rejected.

---

## 5. Multi-reserve finalizer

Contract fixed by `action.rue`; body derived from `reserve_finalizer.rue`.

```
curried (1st):  ACTION_LAYER_MOD_HASH, RESERVE_FULL_PUZZLE_HASHES[N], RESERVE_INNER_PUZZLE_HASHES[N],
                RESERVE_AMOUNT_PROGRAM (state, i) -> reserves[i] + fees_owed[i], HINT
curried (2nd):  FINALIZER_SELF_HASH
runtime:        Truth { Merkle_Root, State (pre-spend) }, last_action_output, ...reserve_parent_ids[N]

1. bucket conditions: untagged -> base; (-42 i . c) -> reserve[i]; any other i -> FAIL
2. for each i in 0..N-1:
     old = RESERVE_AMOUNT_PROGRAM(Truth.State, i)          // pre-spend, never from an action
     new = RESERVE_AMOUNT_PROGRAM(new_state, i)
     recreate = CREATE_COIN(RESERVE_INNER_PUZZLE_HASHES[i], new, [HINT])
     SEND_MESSAGE(mode = SENDER_PUZZLE | RECEIVER_COIN,
                  message = tree_hash((1, (recreate, reserve[i]))),
                  receiver = coinid(reserve_parent_ids[i], RESERVE_FULL_PUZZLE_HASHES[i], old))
3. CREATE_COIN(curry(ACTION_LAYER_MOD_HASH, [curry(FINALIZER_SELF_HASH,[self]), Merkle_Root, new_state]), 1, [HINT])
4. return [recreate_singleton, ...messages, ...base]
```

Invariants: every reserve is re-created every spend, touched or not; the receiver coin id uses
the pre-spend amount from `Truth.State`; a wrong or missing parent id fails the bundle. Tested at
N = 2 and N = 10. Reserve nonce = asset index.

---

## 6. LP CAT

Unchanged: TAIL curried `(launcher_id, protocol_version = 11)`, pinned unparameterised mint and
melt inners, CAT parent required on a melt, LP action coin id derived by the pool. The pool side
of the handshake now comes from the action-layer singleton's puzzle hash. **Open item:** keep the
puzzle announcement or revise the TAIL to accept a message; a message is cleaner and the TAIL is
already being bumped.

---

## 7. Registry singleton

A second CHIP-0050 app, one per network, default finalizer (no reserve).

| | |
|---|---|
| curried | V11 constants (five action hashes, finalizer hash, LP TAIL mod hash, singleton mod hash), `CREATION_FEE`, `TREASURY_PH`, `GATE` (none / fee / NFT collection) |
| state | `[pool_count]` |
| pool slot (nonce 0) | `(key, launcher_id, asset_ids, weights, fee_bps, protocol_fee_bps, protocol_ph, lp_asset_id, created_height)` with `key = sha256(sorted asset_ids, weights, fee_bps, protocol_fee_bps)`, kept in the XCHandles sorted doubly-linked list so a duplicate key cannot be inserted |
| `register` | in the **same bundle as pool creation**: rebuild the new pool's full puzzle hash from the launcher id and the config (the merkle root and eve state are computable), assert the launcher's puzzle announcement for that hash, assert the creation-fee coin's announcement to `TREASURY_PH` (or the NFT proof), spend the two neighbouring slots and re-create them around the new key |
| revision gate | inherent: `register` only computes V11 hashes, so no other revision can register |
| discovery | frontend and router scan pool slots by the registry's puzzle-hash pattern and memos; the server and localStorage deployment index is retired |

Closes the "gate pool creation" quest without an admin key: the gate is a fee, an NFT, or nothing,
chosen at registry creation.

---

## 8. Off-chain

- **Python driver** (`forge_transition.py` lineage): builds action-layer spends — merkle proofs,
  action solutions, finalizer solution (parent ids), reserve delegated-puzzle reconstruction
  (mirror `chia-sdk-driver`'s `Reserve::delegated_puzzle_for_finalizer_controller`).
- **Second driver** with `chia-wallet-sdk` `ActionLayer` + `Reserve` + `P2DelegatedBySingleton`;
  bundles must match the Python driver byte for byte. Two implementations, one truth.
- **Router policy:** one action per spend at launch. Batching (several traders per spend) and
  zap-add (swap then add) are switched on later with no puzzle change; both need an ordering log
  and per-trader settlement proof before they are enabled.
- **Responder** gates: only V11 hashes; revision filtering now comes from the registry.
- **Frontend:** pools from the registry; Markets tab fixes (pool price, real spread, native
  volume) land with the same touch; fee sizing from pool count (`feeFor(kind, poolCount)`).

---

## 9. Testing

Lanes per [`docs/skills/forgePoolLifecycleTesting.md`](skills/forgePoolLifecycleTesting.md); a
skip exits 2.

| lane | suites |
|---|---|
| integrity | upstream hash pins; merkle root = exactly five Forge leaves; finalizer/action hashes byte-identical to the archived snapshot; curve module output identical to V10 for a recorded corpus of V10 spends |
| simulator | each action alone; every ordered pair and the five-way combination in one spend; N-reserve recreation on every spend; two adds, two removes, add+remove; oracle accumulation across a scripted height sequence; collect after k swaps equals the sum of per-swap fees |
| adversarial | sixth leaf rejected; tag index out of range; missing/wrong/swapped parent ids; action lying about old amount; untagged reserve `CREATE_COIN` from an action; reserve spent with an unsent delegated puzzle; pool-B message on pool-A reserve; swap `output ± 1`; sandwich inside one spend cannot breach a trader's settlement minimum; observe cannot record a same-spend price; stale `h` bounded by `ORACLE_WINDOW`; duplicate registry key rejected; register with mismatched config rejected |
| lifecycle | launch matrix re-run under V11 through the real creation + registration path, dry run first; retire V10 pools as V4–V9 were |
| driver | Python and wallet-sdk bundles identical; responder rejects non-V11 |

Audit routine: [`docs/skills/clvmPuzzleAudit.md`](skills/clvmPuzzleAudit.md) in full, plus the
action-layer additions in the CHIP-0050 skill. External audit scope: the curve module, five
actions, the prologue, the finalizer, the registry actions, and the LP TAIL diff. Upstream
components are out of scope for the auditor beyond hash verification.

---

## 10. Migration

New pools only. V10 pools carry no liquidity; retire them as V4–V9 were retired. `PROTOCOL_VERSION`
11 gives every pool a new LP asset id. The launch matrix (16 rows) is the first real deployment,
each row registered in the same bundle it is created in. Future migrations need no migration
action: remove from the old pool plus add to the new one is two singleton spends in one
offer-settled bundle.

---

## 11. Build order and roadmap integration

Dependency order. Items in *italics* are existing backlog entries absorbed into the phase.

| phase | scope | absorbs |
|---|---|---|
| **0 · Close V10** | finish V10 testnet tests; *rebuild the six skipping suites at the shipping revision* (they carry forward); V10 launch matrix only if V11 is more than a quarter away | Roadmap §5; TODO 1b |
| **1 · Foundations** | `forge_curve.rue` ported with a V10 corpus equivalence test; `forge_multi_reserve_finalizer.rue`; reserve coins; integrity pins; settle open items (tag encoding, TAIL handshake, config placement, `ORACLE_WINDOW`) | — |
| **2 · Actions** | prologue; `swap`, `add`, `remove` with the LP binding; `observe`; `collect`; merkle root; simulator lane green | — |
| **3 · Registry** | registry singleton, pool slots, `register`; creation gate | TODO 1c (gate pool creation) |
| **4 · Off-chain** | Python driver; wallet-sdk second driver; responder gates; frontend on the registry, deployment index retired; *Markets tab fixes*; *fee sizing by pool count* | Roadmap §3, §4 |
| **5 · Internal audit** | full `clvmPuzzleAudit` routine + action-layer additions; adversarial lane green; `FORGE_SECURITY_AUDIT.md` V11 section | — |
| **6 · External audit** | scope in §9; fix, re-probe, re-audit until clean | — |
| **7 · Testnet launch** | launch matrix under V11 with registration; *WalletConnect add/remove*; *offer-only liquidity acceptance* | TODO 2, 4 |
| **8 · Post-launch** | router batching + *zap-add*; *LP-balancing deposits*; LP mining via CHIP-0051; *aggregator* and *portal arbitrage* read the registry and oracle; *perps oracle aggregator* consumes `observe` | TODO 9; Roadmap §2; Phases 8, 9, 4c |
| **9 · CHIP** | CFMM CHIP submission: the actions, the finalizer and the curve on CHIP-0050 | Phase 10 |
| **research** | concentrated pool type: NFT positions, N-asset bands, reference maths first | parking lot |

**Definition of done for V11:** external audit clean on the §9 scope; launch matrix live on
testnet11 through creation + registration; both drivers producing identical bundles; every lane
green with zero skips; `FORGE_PROTOCOL_STATUS.md` moved to V11.

---

## 12. Open items (settle in phase 1)

1. Tag encoding: `(-42 index . condition)` versus `-42 − index` opcodes. Recommended: the former.
2. LP TAIL handshake: puzzle announcement versus message. Recommended: message.
3. Config placement: curried into actions. Recommended: yes.
4. `ORACLE_WINDOW` value and `PRICE_SCALE` (proposed 2^64).
5. `observe` announcement format versus `SEND_MESSAGE` to a named consumer coin. Recommended:
   announcement (any same-bundle consumer can assert it).
6. Registry gate at testnet launch: none, fee, or NFT. Recommended: fee, small.
