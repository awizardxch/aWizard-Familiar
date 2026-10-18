# FLPCR — Forge Liquidity Pool Campaign Rewards — Specification

> Incentive campaigns for Forge liquidity and Chia CATs. Anyone can fund a reward budget on a
> Forge pool or a CAT over a block range. Holders earn from it every block, and an on-chain
> distributor pays them out.
> **FLPCR is the working name.** It appears in identifiers (`flpcr`, `flpcr-*-v1` tags), so a
> rename is a find-and-replace until something is deployed. Merkl is the reference design, not a
> dependency; nothing here uses Merkl's name, contracts or API.
> Status: **draft v0.1, 2026-10-18.** Engine slice built and tested; distributor puzzles specified
> but not yet written. Not audited. Testnet first.

---

## 1. What Merkl does, and what we keep

Merkl ([docs](https://docs.merkl.xyz/merkl-mechanisms/incentive-mechanisms),
[developers](https://developers.merkl.xyz), contracts `AngleProtocol/merkl-contracts`) is
the incentive layer most EVM DEXs use. It has four parts:

| Merkl | How it works there | FLPCR |
|---|---|---|
| `DistributionCreator.createCampaign(CampaignParameters)` | `{creator, rewardToken, amount, campaignType, startTimestamp, duration, campaignData}`; fee taken (~3%); min amount per hour per token | `create` leaf on a **distributor singleton**; campaign struct hashed into a campaign id; the creation fee goes to the treasury; campaigns are scheduled by block height |
| Off-chain engine | Every few hours it scores positions (time-weighted liquidity; for CLAMMs, fees/token0/token1 weights, in-range only, boosts, blacklists, forwarders for ALMs) and builds a tree of **cumulative** `(user, token, amount)` | Same model, deterministic and exact (§6). Scores LP and CAT holders from chain data, using the Forge replay that already exists |
| `Distributor.updateTree(root)` + dispute | Root posted by an updater; becomes claimable after a dispute period; a bonded disputer can freeze it; governance resolves or revokes | `post_epoch` leaf, then a **dispute window in blocks** before it pays out; a guardian can `veto`; the same leaf also enforces each campaign's **emission ceiling** on chain (§5.3), which Merkl does not have |
| `Distributor.claim(users, tokens, amounts, proofs)` | Leaf `keccak(user, token, cumulative)`; pays `cumulative − claimed[user][token]`; operators may claim for users | `payout` leaf: **anyone** can trigger it, and it can only pay the entry's puzzle hash. Rewards land in the holder's wallet as a hinted coin, so Sage shows them without a claim page (§5.4) |
| API `api.merkl.xyz/v4` (`/opportunities`, `/campaigns`, `/users/{addr}/rewards`) | Read side for apps and wallets | `/v1/...` with the same three resources (§8) |

Merkl's incentive models carried over:

- **Variable rate (default).** A fixed budget per unit of time, split by time-weighted share.
  APR falls as liquidity grows. This is the only model in v1.
- **Fixed rate / capped APR.** Rewards per unit of liquidity, with the budget as a ceiling.
  Phase 2, because it needs a price (§6.6).
- **ERC20 holding campaigns.** These map to `CAT_HOLD`.
- **Concentrated liquidity (fees / token0 / token1 / in-range).** Only partly applies, because a
  Forge pool is a weighted CFMM with **fungible** LP. Every LP has the same range and the same
  per-reserve mix. So token0/token1 weights and in-range filters have nothing to act on. The
  **fee weight** still matters: it rewards liquidity that was present when the pool was actually
  used (§6.3).
- **Forwarders (ALMs, wrappers).** LP held by a Forge vault pool's nested LP reserve is passed
  through to that vault's LP holders (§6.4).
- **Blacklist / whitelist / minimum balance.** Kept, and committed into the campaign id.

What we drop: Merkl's per-campaign overrides (editable live campaigns), its signed terms-of-service
gate, and governance reallocation of a user's rewards. A campaign cannot be edited once
created. That is the same rule as a Forge pool's leaf set.

### Why not CHIP-0051 (Reward Distributor)

CHIP-0051 is the native Chia option on the same action layer. Forge evaluated it before
(`chip0050ActionLayer.md`) and declined it for trading fees, because holders must **stake**
(lock entries in the distributor) or a manager must set shares by hand. FLPCR's point is
that LP and CATs **stay in the holder's wallet** and keep working: routable, offerable, usable
as collateral. That needs an off-chain scorer. The trade is explicit: correctness of the split
rests on a reproducible engine plus a dispute window, not on the puzzle. The *amount* that can
leave rests on the puzzle (§5.3). A CHIP-0051-backed "staked campaign" can be added later as a
second campaign kind for creators who want a split the puzzle itself enforces.

---

## 2. Vocabulary

| Term | Meaning |
|---|---|
| **Campaign** | A reward budget on one target (a Forge pool or a CAT) over `[start, end)` blocks |
| **Distributor** | The singleton that holds one reward asset (XCH or one CAT) for every campaign paying in it |
| **Engine** | The off-chain scorer (`flpcr/`); its output is an epoch |
| **Epoch** | One posted payout tree covering `[start, end)` blocks: entries `(index, puzzle_hash, amount)` |
| **Operator** | The key allowed to post epochs (a coin at `ENGINE_PH` sends a message) |
| **Guardian** | The key (intended to be a Forge multisig safe) allowed to veto a pending epoch and rotate the operator |
| **Keeper** | Anyone who submits `payout` spends; no permission needed |

---

## 3. Campaign kinds

| Kind | `target` | Tracked asset | Fee weighting |
|---|---|---|---|
| `LP_HOLD` (1) | Forge pool launcher id | the pool's LP CAT | yes |
| `CAT_HOLD` (2) | CAT asset id | that CAT | no (time only) |

Phase 2 candidates, each a new `Kind` with its own scoring function and none needing a puzzle change:
`SWAP_VOLUME` (pay traders by routed volume, from the same replay), `VAULT_DEPOSIT`
(Greenwood/vault positions), `NFT_HOLD` (collection holders, e.g. BOW soulbound tiers as a
**boost** instead of a kind).

### 3.1 The campaign struct (what the id commits to)

```
campaign = ["flpcr-campaign-v1", distributor_id, creator_ph, reward_asset, amount,
            start, end, kind, target, params_hash, nonce]
campaign_id = sha256tree(campaign)
params = [time_bps, fees_bps, min_balance, sorted(blacklist), sorted(whitelist), forward]
params_hash = sha256tree(params)
```

Rules (checked by both the engine, `model.py`, and the `create` leaf):
`amount > 0`, `end > start`, `start >= h_create` (no retroactive campaigns),
`end - start <= MAX_DURATION`, `time_bps + fees_bps = 10000`, `CAT_HOLD ⇒ fees_bps = 0`,
`blacklist ∩ whitelist = ∅`. The full `params` value is in the `create` solution, so it is on
chain and anyone can recover it from the hash.

---

## 4. Architecture

```
 creator ──offer──▶ responder ──create──▶ ┌──────────────────────────────┐
                                          │ Distributor singleton        │
 chain ──▶ Engine ──epoch manifest──▶ IPFS│  action layer, 8 leaves      │
            │                             │  reserve (upstream finalizer)│
            └──post_epoch (operator)────▶ │  state: campaigns, epochs    │
 guardian ──veto / rotate───────────────▶ └──────────┬───────────────────┘
 keeper ──payout(entries, proofs)───────────────────▶ │ CREATE_COIN to holder, hinted
                                                      ▼
                                                 holder's wallet (Sage)
```

**One distributor per reward asset.** The distributor is
`singleton(action_layer(reserve_finalizer, leaves_root, state))` with **one** reserve. That is the
upstream CHIP-0050 reserve finalizer **unmodified**. Forge needed a multi-reserve finalizer; this
doesn't, which keeps it out of the audit scope. Every campaign paying in, say, wUSDC goes to the
wUSDC distributor. Discovery is by a registry like Forge's (key = reward asset id, sorted slots,
one distributor per asset), so wallets and the API find a distributor cold.

---

## 5. The distributor (on chain)

Rue, CHIP-0050 action layer, upstream puzzles hash-pinned exactly as in `contracts/v14/pins.json`.
Leaf-by-leaf detail is in [`PUZZLES.md`](PUZZLES.md); this section sets out the properties.

### 5.1 Config (curried, so the leaf root commits to it) and state

```
Config  = { distributor_id, reward_asset, treasury_ph, fee_bps, guardian_ph,
            dispute_blocks, payout_window, max_campaigns, max_live_epochs, max_entries }
State   = { engine_ph, campaigns: List<Campaign>, epochs: List<LiveEpoch>,
            last_epoch_id, last_epoch_end, fees_owed, reserve_total }
Campaign (in state) = (campaign_id, creator_ph, amount, start, end, allocated)
LiveEpoch = (epoch_id, root, entry_count, remaining, paid_bitmap, activates_at, expires_at)
```

`reserve_total = Σ (amount − allocated) over campaigns + Σ remaining over epochs + fees_owed`.
The reserve finalizer sizes the reserve coin from it. Conservation is the reserve's job;
honesty about this sum is each leaf's job (the Forge rule, `chip0050ActionLayer.md`).

### 5.2 Leaves (fixed forever per distributor)

| Leaf | Who | Does |
|---|---|---|
| `create` | anyone | Binds a settlement of `amount + fee` (V14 `settlement_binding`: parent + amount + `ASSERT_CONCURRENT_SPEND`), validates the struct, appends `(id, creator, amount, start, end, 0)`, accrues `fee` to `fees_owed`. Refuses a duplicate id or a full list |
| `post_epoch` | operator (mode-23 message from a coin at `engine_ph`) | Appends a pending epoch. Checks §5.3. `activates_at = h + dispute_blocks` |
| `veto` | guardian (mode-23 message from `guardian_ph`) | Removes a **pending** epoch and gives its allocations back to each campaign |
| `payout` | anyone | For an **active** epoch: verifies each `(index, ph, amount)` against the root, checks and sets bit `index`, decrements `remaining`, emits reserve `CREATE_COIN ph amount (ph)` |
| `expire` | anyone, after `expires_at` | Drops an epoch. Its unpaid `remaining` goes back into the creators' unallocated pool, pro rata by the epoch's allocation vector (§5.5) |
| `reclaim` | anyone, after `end` and once no live epoch covers the campaign | Pays `amount − allocated` to `creator_ph` and removes the campaign |
| `collect` | anyone | Pays `fees_owed` to `treasury_ph` |
| `rotate` | guardian | Replaces `engine_ph` |

There is no upgrade leaf and no "withdraw everything" leaf. A compromised operator and a
compromised guardian *together* can still only pay out up to each campaign's emission schedule
(§5.3), and only after a dispute window.

### 5.3 The emission ceiling (the on-chain guarantee)

`post_epoch`'s solution carries `(epoch_id, start, end, root, entry_count, allocations[], manifest_hash)`
where `allocations[i]` is the mojos of campaign `i` placed in this tree. The leaf asserts:

```
epoch_id == last_epoch_id + 1            start == last_epoch_end      end <= h   (ASSERT_HEIGHT_ABSOLUTE end)
entry_count in 1..max_entries            len(epochs) < max_live_epochs
for each campaign i:   allocated_i + allocations[i] <= amount_i * (min(end, end_i) - start_i) / (end_i - start_i)
remaining = Σ allocations[i]
```

The right-hand side is `Campaign.emittable(end)` in `model.py`, which the engine checks itself
before it posts. So **no key can move a campaign's money faster than its schedule, or more than
its amount**, whatever tree it posts. The puzzle cannot check that the tree's entries add up to
`remaining`, but it doesn't need to: `payout` decrements `remaining` and refuses to go below
zero. A tree whose entries add up to more than `remaining` simply cannot pay its last entries.

What the puzzle does **not** guarantee: that the split between holders is correct. That is the
engine's job, made checkable by determinism (§6) and enforceable by the dispute window (§7).

### 5.4 Payouts: push, not pull

A Merkl claim needs a per-user `claimed` mapping. On Chia that means a slot per user plus
a sorted-list non-existence proof for the first claim (the registry pattern): one shared neighbor
coin per insert, and every first-time claimer contends for it. FLPCR avoids the mapping
entirely:

- Each epoch pays only the **deltas** for its window (not cumulative), so an entry is paid once.
- "Paid once" is a **bit** in the live epoch's `paid_bitmap` (`entry_count ≤ max_entries`, e.g.
  2048 bits = 256 bytes in state).
- The payout goes to the entry's own puzzle hash, hinted with it. So **anyone** can submit it,
  and a keeper bot pushes every entry shortly after activation (~20–40 entries per spend within
  the cost limit). Holders see rewards appear in Sage. A user can also push their own entry
  from the UI with a Sage offer that pays the network fee.
- Cost per entry: one merkle proof (~11 hashes at 2048 entries) and one `CREATE_COIN`.

### 5.5 Unpaid entries

If an epoch reaches `expires_at` (`payout_window`, e.g. 30 days) with entries unpaid, `expire`
returns its `remaining` to the campaigns pro rata by the epoch's allocation vector. This
reduces each campaign's `allocated` (the vector is stored with the live epoch). The engine
reads the final bitmap from chain and marks those holders' amounts **unallocated** again, so
they are re-earned into the next epoch. Nothing is lost. Expiry exists only so state cannot grow
without bound.

---

## 6. The engine (off chain) — normative scoring

Implemented in `flpcr/engine.py`. Any second implementation must produce byte-identical
roots. All arithmetic is exact rational; the only rounding is a floor of a holder's cumulative
accrual.

### 6.1 Inputs, all from chain

- **Holder timeline** of the tracked asset: every CAT coin creation (+amount) and spend (−amount)
  attributed to its inner puzzle hash via the CHIP-0020 hint (Forge LP coins are hinted). A change
  at height `h` is in force on `[h, …)`.
- **Exclusions:** pool reserve puzzle hashes, OFFER_MOD settlement coins (transient, created and
  spent within a route), the zero hash (the `LOCKED_BURN` floor), the protocol treasury. Derived
  from the Forge registry, never configured by hand.
- **Fee events** for `LP_HOLD`: each pool generation is replayed with `forge_v14_resync`
  (resolve each action's leaf through its selector, not `zip(puzzles, solutions)` —
  `forgePuzzleV14.md` §5). Each `swap` action yields `(h, weight)`, where weight = the LP fee it
  paid, valued in XCH at the pool's **pre-spend** spot price (the same price the oracle
  accumulates in the prologue).
- **Forwarders:** Forge vault pools whose reserves include this pool's LP, mapped to the vault's own
  LP asset.

### 6.2 Time weighting (variable rate)

Within an epoch window `[a, b)` clipped to the campaign, cut at every balance change into segments
`[s, t)`. For each segment, with `E(h) = campaign.emittable(h)` and eligible balances `B_u`:

```
budget(s,t) = (E(t) − E(s)) · time_bps / 10000
credit_u   += budget(s,t) · B_u / Σ B
```

This is per-block share of eligible supply, the same as Merkl's variable rate and MasterChef.
A segment with no eligible holder credits no one; its budget stays unallocated and the creator
reclaims it.

### 6.3 Fee weighting (`LP_HOLD` only)

```
fee_budget  = (E(b) − E(a)) · fees_bps / 10000
credit_u   += fee_budget · Σ_e w_e · B_u(h_e)/ΣB(h_e)  /  Σ_e w_e
```

over fee events `e` in the window with at least one eligible holder. If the window has **no** such
event, the fee share is spent on time weighting instead, so a quiet pool doesn't strand the budget.
This is the fungible-LP version of Merkl's `propFees`: an LP's fee share in a block *is* their LP
share, so weighting by fees concentrates rewards on the blocks where the liquidity was used.
Because the fallback is decided per window, epoch boundaries are part of the result. They are
posted on chain (`start`, `end`), so a replay uses the same ones.

### 6.4 Forwarding

A wrapper's balance `W` at height `h` is credited to its share holders `p` as `W · S_p / ΣS` (the
share asset's own exclusions apply). It is one level deep; a wrapper of a wrapper is credited to the
inner wrapper's puzzle hash. Disabled per campaign with `forward = 0`.

### 6.5 Accrual, deltas and payout

```
accrued[c][u]   += credit_u                 (exact)
delta[c][u]      = floor(accrued[c][u]) − allocated[c][u]
entry[u]         = Σ_c delta[c][u]         if ≥ min_payout, or any c has ended
allocated[c][u] += delta[c][u]             for included entries
```

Entries are sorted by puzzle hash; `index` is the position. The leaf is

```
sha256tree(["flpcr-entry-v1", distributor_id, epoch_id, index, puzzle_hash, amount])
```

in a Chia `merkle_utils` tree (leaf prefix `0x01`, node `0x02`, midpoint split, proof
`(path, hashes)`), which is what `simplify_merkle_proof` verifies on chain. Floors guarantee
`Σ_u allocated[c][u] ≤ E(end)`, so the engine can never ask for more than §5.3 allows. An epoch
with nothing to pay is not posted, and the next one covers the longer window, so posted epochs
tile the timeline.

### 6.6 Valuation (display only in v1)

APR and TVL in the API use the pools' oracle accumulators (`observe` snapshots and the cumulative
price in state) for a TWAP, rather than a spot price that can be moved. In v1 no reward amount
depends on a price except fee weights (§6.3), which use the pre-spend spot of the pool that paid
them. Fixed-rate / capped-APR campaigns would make price load-bearing and must use the TWAP only.

### 6.7 Anti-gaming

Time weighting per block makes flash deposits worth one block's share. The minimum balance
and blacklist apply. Self-trading to farm fee weight costs the trader the full pool fee for a
share of a **fixed** budget, so it only pays if the fee weight per mojo of fee is worth more
than the fee. Creators who worry about this keep `fees_bps` low. Campaign creators should see that
trade-off in the UI.

---

## 7. Trust model and disputes

| Party | Can | Cannot |
|---|---|---|
| Operator | Post a wrong split | Exceed any campaign's schedule; post for the future; skip or repeat an epoch; pay before the dispute window |
| Guardian | Veto a pending epoch; rotate the operator | Post epochs; move funds; touch active epochs |
| Creator | Fund; reclaim the unallocated remainder after end | Cancel or edit; reclaim allocated rewards |
| Keeper | Trigger payouts | Choose the recipient or amount |

**Disputes, v1:** a watcher (`flpcr` run in replay mode by anyone) recomputes each pending
root from chain data. On mismatch it alerts the guardian, which vetoes within `dispute_blocks`
(e.g. 1,152 ≈ 6 h). **v2:** a public `dispute` leaf. Anyone posts a bond in the reward asset, which
freezes activation until the guardian resolves it (bond returned on a valid dispute, kept otherwise),
like Merkl's `Disputer`.

---

## 8. HTTP API (read side mirrors Merkl v4)

See [`API.md`](API.md). Resources: `GET /v1/opportunities`, `GET /v1/campaigns[/{id}]`,
`GET /v1/users/{address}/rewards`, `GET /v1/epochs/{distributor}/{epoch_id}`; write side
`POST /v1/campaigns/quote` (returns the offer to sign) and `POST /v1/payouts/build`. Addresses
accept `xch1…` or a hex puzzle hash.

---

## 9. Interface

A **🔥 Campaigns** tab in forge-ui (or on whichever site this lands), three views:

1. **Opportunities.** Every pool and CAT with a live campaign, with APR (TWAP-valued), daily emission, time left, and
   a "provide liquidity" deep link into the existing add flow.
2. **Create.** Pick a target (pool search or CAT asset id), reward asset, amount, duration (with the
   date shown, at about 18.75 s per block), and weighting slider (time ↔ fees, `LP_HOLD` only).
   Advanced: min balance, lists. A preview shows the fee, the per-day emission and an estimated APR at
   current TVL. Signing is one Sage offer: give `amount + fee` and request nothing. The responder
   builds the `create` spend around it, the same keyless pattern as Forge's offer lane
   (`forge_v14_offer.py`).
3. **My rewards.** Accrued (engine, unposted), pending (in a disputed window), paid. Pending entries
   show "arrives in about N blocks"; a "push now" button submits the user's own payout.

Spellbook / agent API: `flpcr.quote`, `flpcr.create`, `flpcr.rewards` as tools beside the
existing swap quote/build/settle.

---

## 10. Phases

| Phase | Deliverable | Gate |
|---|---|---|
| **0 — this slice** | Spec; engine (`model`, `engine`, `merkle`, `manifest`, CLI) with tests | 26 tests green, hashing cross-checked against `clvm` |
| **1 — engine on real data** | Live `Source` for testnet11 (coinset / full node + `forge_v14_resync`); run against the 32 V14 pools; publish manifests | Replay of a week of testnet produces stable roots twice from scratch |
| **2 — distributor puzzles** | `contracts/flpcr/` rue project: 8 leaves, registry, pins; driver; suites in the V14 style (integrity, before/after, mutation with UNREACHED reporting) | `clvmPuzzleAudit.md` pass; every leaf refusal probed in a simulator |
| **3 — testnet lane** | Operator bot (post + keeper), watcher, API, forge-ui tab | One campaign end to end on testnet11: create → epochs → payouts → reclaim |
| **4 — hardening** | Public dispute leaf, guardian as a Forge multisig safe, external review | No mainnet before external review |

---

## 11. Open questions

1. **Reward assets allowed.** Any CAT, or an allowlist? Merkl keeps a min-amount-per-hour list
   per token. Proposal: any CAT, plus a `MIN_RATE` per distributor fixed at launch.
2. **Fee level.** Merkl charges about 3%. Proposal: `fee_bps = 100` (1%), sent to the same treasury as
   the Forge protocol fee.
3. **Operator decentralization.** One operator key in v1. Later: M-of-N operator messages, or several
   engines that must post the same root.
4. **Where it lives.** Its own repo, `flpcr` (engine + API), with the puzzles either in
   `forge-puzzles` (one audit surface) or `flpcr-puzzles` (the `sync-subrepos.ps1` split).
