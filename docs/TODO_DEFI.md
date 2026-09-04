# TODO — aWizard Protocol (DeFi Ecosystem)

> Master quest log for the full aWizard DeFi build.
> Start with `docs/ARCHITECTURE_INDEX.md` for architecture routing, then use `docs/ARCHITECTURE.md` for the full subdomain map + product specs.
> Start with `docs/skills/README.md` for skill routing before opening individual domain skills.
> Projects live in `projects/` — `projects/chia-cfmm/`, `projects/chia-treasure-chest/`, `projects/chia-perps/`
>
> **Subdomain targets:** `forge.awizard.dev` (CFMM + NFT vaults), `portal.awizard.dev` (arbitrage),
> `bank.awizard.dev` (portfolio hub), `craft.awizard.dev` (emoji asset creation),
> `map.awizard.dev` (open world), `build.awizard.dev` (dev expansion), `stats.awizard.dev` (analytics)
>
> Goal: prove out the full DeFi OS on Chia testnet11, then write CHIPs for each primitive.
>
> **Quest Index:** [docs/quests/INDEX.md](quests/INDEX.md) — unified main + side quest routing  
> **Side Quests:** [docs/quests/sidequests/](quests/sidequests/) — parallel innovation lane (patent incubator)

---

## 📊 Progress Summary

**✅ Completed Frontends (6 phases):**
- Phase 0: Theme Unification — Nightspire CSS across all projects ✅
- Phase 5: **Emoji Market** ([craft.awizard.dev](http://localhost:5183)) — 6 core tokens ✅
- Phase 6: **Bank of Wizards** ([bank.awizard.dev](http://localhost:5184)) — Portfolio aggregation MVP ✅
- Phase 7: **Analytics Hub** ([stats.awizard.dev](http://localhost:5185)) — Ecosystem metrics ✅
- Phase 10: **Liquidity Manager** ([vaults.awizard.dev](http://localhost:5178)) — Foundation complete; optional post-launch liquidity-management layer ✅

**✅ Just Completed:**
- **🔒 Forge V10 — internal security audit closed, protocol re-shipped** (2026-08-27) — ten findings, all fixed; two were third-party-reachable fund loss. **LP burn was unauthenticated (V4–V8)** and **reserves were not bound to their pool (V4–V9)**, so every pre-V10 pool was retired and the deployment index now rejects superseded revisions in both directions. V10 curries `launcher_id` into the reserve, authorises it with a puzzle announcement rebuilt in-puzzle, pins the successor with `AssertMyPuzzleHash`, derives the LP action coin id, pins the mint/melt inners, and requires a CAT parent on a melt. Method and defect classes captured in [docs/skills/clvmPuzzleAudit.md](skills/clvmPuzzleAudit.md); shipping shape in [docs/skills/forgePuzzleV10.md](skills/forgePuzzleV10.md). Status: [docs/FORGE_PROTOCOL_STATUS.md](FORGE_PROTOCOL_STATUS.md).
- **🔀 Forge V4 Protocol — create/add/remove/swap all confirmed on testnet11** — the T6/T11 V4 pool (`geometric-invariant-v1`, launcher `d666d3fe...c9ac4f324`) has confirmed on-chain evidence for create-pool, add-liquidity, remove-liquidity, and swap (both directions). All four actions route through one shared server-side responder (`api/_forgeV4Responder.js`) enforcing a singleton-freshness guard before every transition. A background poller now auto-discovers and auto-fills open Dexie offers matching an indexed V4 pool. Quest moved to done/: [build-forge-swap-execution-path.md](quests/done/build-forge-swap-execution-path.md) — resolved via V4 protocol, not the originally planned `swap_engine.rue` boundary. See [projects/chia-cfmm/docs/LP_LIFECYCLE_STATUS.md](../projects/chia-cfmm/docs/LP_LIFECYCLE_STATUS.md) for the current status table.
- **� Forge Swap Aggregator Foundation** — quest complete, moved to done/
  - Sessions 1-2: 7-file aggregator module, adapter interface, multi-hop execution, SwapPanel replaced
  - Session 3: Blocker analysis — puzzle reveals ✅, pool state mock fallback ✅
  - Session 4: `bootstrapAmounts` added to STATIC_KNOWN_POOLS (T1.6: 10B TXCH + 1000 TEST1; T1.7: 100B TXCH + 100 each CAT), deterministic reserves, full data flow verified
  - Enhancement backlog created: [enhance-forge-swap-aggregator.md](quests/backlog/enhance-forge-swap-aggregator.md)
- **�🚀 CFMM Infrastructure Quest** — Sage RPC + 6 contracts + 3 pools + deployment pipeline ✅
- **🧾 Forge Fee + Env Alignment** — on-chain protocol fee curried into the canonical n-asset pool, fee UI/env defaults aligned, `.env` restored as the single active operator config ✅
- **🎉 T1.6 Pool Fully Live on testnet11** — Stage 1 + Stage 2 completed via Sage RPC two-phase pipeline; LP CAT `cff471f8...3af` confirmed visible in Sage wallet ✅

**🚧 In Progress:**
- **Forge is on V10 with zero live pools** — the index was cleared when the old pools were retired. Next up, in dependency order: deploy the 16-row launch matrix through the real creation path, gate pool creation to an NFT or allowlist, rebuild the 6 suites still skipping against V10, then LP-balancing deposits and the Markets tab fixes. See [docs/skills/forgePoolLifecycleTesting.md](skills/forgePoolLifecycleTesting.md) for what each suite proves.
- **🔀 Build Forge Swap Execution Path** — [docs/quests/done/build-forge-swap-execution-path.md](quests/done/build-forge-swap-execution-path.md) — **COMPLETE** — resolved via the V4 protocol (`pool_singleton_v4` swap mode), not the originally planned `swap_engine.rue` boundary.
- **🔥 Build Pool-Controlled TAIL** — [docs/quests/build-forge-pool-controlled-tail.md](quests/build-forge-pool-controlled-tail.md) — foundation completed but security model superseded by the V3 hardening quest; announcement-only authorization is replayable and must not ship to mainnet.
- **🧊 Forge LP NFT Standard Migration** — [docs/quests/done/forge-lp-nft-standard-migration.md](quests/done/forge-lp-nft-standard-migration.md) — frozen prototype; retain as reusable wallet-visible NFT receipt/container infrastructure for Treasure Chest only
- **🔐 Cloud Vault + Multisig Pivot** — optional future strategy layer; not required for initial Forge CFMM launch
- Phase 1: Wallet Connect — integration ready, awaiting testnet wallet testing  
- **📦 Deployment Quest** — [docs/quests/backlog/deploy-testnet-infrastructure.md](quests/backlog/deploy-testnet-infrastructure.md) — backlogged; infra follow-through remains useful but is not the current Forge ownership lane
- **🧩 Forge Bootstrap Protocol Reconciliation** — [docs/quests/backlog/reconcile-forge-bootstrap-protocol.md](quests/backlog/reconcile-forge-bootstrap-protocol.md) — backlogged architectural ledger; no longer a separate active implementation lane
- **🖥️ Forge GUI Truth Lane** — [docs/quests/backlog/frontend-gui-pool-deployment.md](quests/backlog/frontend-gui-pool-deployment.md) — backlogged post-deploy UX verification lane
- **🧭 Forge Pool Launch Flow Enhancements** — [docs/quests/backlog/enhance-forge-pool-launch-and-create-flow-redesign.md](quests/backlog/enhance-forge-pool-launch-and-create-flow-redesign.md) — post-foundation polish for asset search, live metrics, review-step flow, and real burn-initial-LP wiring
- **🧪 LP Puzzle + Router Balanced/Range Liquidity** — [docs/quests/backlog/enhance-forge-lp-puzzle-router-balanced-and-range-lp.md](quests/backlog/enhance-forge-lp-puzzle-router-balanced-and-range-lp.md) — keep WalletConnect create-offer UX while router handles single-sided balancing and range-style LP strategies on testnet
- Phase 4: Perpetuals — frontend complete, awaiting contracts

**📦 Ready to Deploy:**
- `chia-treasure-chest` → localhost:5180
- `chia-cfmm` → localhost:5182
- `chia-craft` → localhost:5183
- `chia-bank` → localhost:5184
- `chia-stats` → localhost:5185

**📋 Planning Backlog:**
- Future quests moved to `docs/quests/backlog/` (full Bank build, Aggregator DEX, Portal, Multisig, upgradeable treasury wallet)
- Near-term treasury operations can continue on a simple Sage address until the treasury wallet quest is activated

## 🔮 Next Session Focus

1. **🔒 LP CAT TAIL audit** — ✅ DONE (2026-08-27). The replay concern was real and worse than
   suspected: through V8 the TAIL was announcement-only and the pool accepted a solution-supplied
   action coin id, so reserves could be withdrawn with **no LP destroyed at all**. Closed in V9/V10
   by the three-part lock — derived action-coin id, pinned mint/melt inners, and a CAT parent
   required on a melt. See [docs/skills/forgeLpCat.md](skills/forgeLpCat.md).
1a. **🔐 Forge V11 — CHIP-0050 action layer, weighted full range** (HIGH — adopted 2026-09-04, build after V10 tests)
  - rule met: more secure with fewer points of exploit long term; surface count and design in
    [docs/skills/chip0050ActionLayer.md](skills/chip0050ActionLayer.md). Conditions: upstream-grade
    review of the finalizer; audit the final multi-action puzzle once (no in-puzzle guard)
  - [x] owner confirms adoption (2026-09-04)
  - [x] pool type: weighted N-asset full range; V10 curve, fees and LP CAT unchanged; three actions
  - [x] **concentrated liquidity off scope** (2026-09-04) — returns as a second pool type with NFT
        positions so wallets and other DEXes identify them; per-band asset ids and a position layer
        were both rejected; the N-asset band derivation stays in the skill as the research record
  - [ ] cheap future-proofing only: finalizer tested at N=2 and N=10, fixed tag/state conventions,
        reserved slot nonces, pool-type field in the router registry
  - keep the V10 curve, fees and LP CAT; replace the pool inner and the custom reserve puzzle with
    the action layer, `p2_delegated_by_singleton` reserves, and a Forge-written multi-reserve
    finalizer (none exists upstream — the reserve finalizer is the template)
  - [ ] settle the open items in the skill (tag encoding, LP TAIL handshake, protocol fee placement, config placement)
  - [ ] port the curve functions into a shared Rue module; three action puzzles: `swap`, `add`, `remove`
  - [ ] `multi_reserve_finalizer.rue` from `reserve_finalizer.rue` at the CHIP's pinned commit
  - [ ] integrity pins for the upstream action-layer, `p2_delegated_by_singleton` and slot hashes
  - [ ] action-layer audit additions (finalizer, multi-action, reserve probes) as named suites that exit 2 on skip
  - [ ] second driver via `chia-wallet-sdk` `ActionLayer` + `Reserve`; bundles must match the Python driver
  - [ ] re-run the launch matrix under V11; V10 pools retire like V4–V9 did
  - [ ] multi-action suites are launch scope: every ordered pair and triple in one spend, two adds, two removes, add+remove
  - one action per spend at launch as **router policy**; batching (and zap-add) switched on later with no puzzle change
1b. **🚀 Deploy the V10 launch matrix** (HIGH — NEXT QUEST)
  - 16 pools across the routing surface, vaults, weighted, N-asset, and fee edges
  - every row already deploys through the real creation path in a dry run before coins are spent
  - re-probe per [docs/skills/clvmPuzzleAudit.md](skills/clvmPuzzleAudit.md) before any pool is minted
1c. **🛡️ Gate pool creation to an NFT or allowlist** (HIGH)
  - a pool is permanent, appears beside every audited one, and its creator picks fees and weights
  - correct default for testnet, wrong one for launch
2. **🔀 Wire WalletConnect Add/Remove Liquidity** (HIGH)
   - Step 2 reusable path: any user can add/remove liquidity via WalletConnect
   - Same code path for all future deposits and withdrawals
   - Mints LP CAT on deposit, melts LP CAT on withdraw — pool-controlled
3. **🔀 Forge Swap Execution** — ✅ DONE (2026-08-10). V4 swap confirmed both directions on
   testnet11 through the shared responder + singleton-freshness guard. See
   [quests/done/build-forge-swap-execution-path.md](quests/done/build-forge-swap-execution-path.md).
4. **🧺 Validate Offer-Only Liquidity Flow** (HIGH — V3 ACCEPTANCE)
  - user signs one standard offer for deposit or withdrawal
  - any keyless responder assembles the deterministic on-chain transition
  - no separate wallet signature, Sage taker, or trusted responder metadata
5. **🔀 Forge Swap Aggregator — live on-chain testing** (MEDIUM)
  - connect Sage wallet and validate the routed swap path after the execution quest lands
  - mock reserves continue to support UI/quote testing without full node
6. **📦 Verify TM10 pool on-chain** (MEDIUM)
   - Confirm Stage 2 bundle included in block, target coin exists
   - Test swap execution against the live pool state
7. **🔀 Forge Swap Aggregator — Phase 2 external DEX adapters** (LOW)
   - `tibetAdapter.ts`, `dexieAdapter.ts`, `splashAdapter.ts`
   - Each adapter = one new file implementing `LiquiditySource`
8. **Stage-2 pipeline hardening** (LOW)
   - eliminate remaining false-failure edge cases in progress display
9. **LP puzzle v2 hardening + router zap add** (HIGH)
  - version LP announcements for router-balanced operations
  - ship zap-add-liquidity action using WalletConnect create-offer as user entry
  - add strategy abstraction for v3-like range LP behavior on top of current pool primitives

## 🏁 Completed

- ✅ **2026-08-27** — Forge internal security audit closed; V10 is the shipping revision
  - 10 findings, all fixed; 2 were third-party-reachable fund loss (unauthenticated LP burn V4–V8, unbound reserves V4–V9)
  - every pre-V10 pool retired, deployment index cleared, revision filtering applied on the way in as well as out
  - creation offers redacted at the HTTP boundary — they read standalone as "pay one mojo, take the genesis reserve"
  - four independent implementations of the curve pinned to the puzzle's own numbers; three had been weight-blind
  - skills rewritten to V10: `clvmPuzzleAudit.md` (new), `forgePuzzleV10.md` (new), `forgeLpCat.md`, `forgePoolLifecycleTesting.md`

- ✅ **2026-07-23** — Forge keyless router: create-pool now fully keyless (quest: `quests/forge-keyless-router-quest.md`)
  - New `contracts/forge_create_pool_keyless.py`: builds launcher + P1→P2 + CAT reserves + LP CAT genesis in one atomic bundle from the user's pre-signed offer; pushes via coinset.org — zero server keys (Tibet router parity)
  - `api/router-create-pool-taker.js` rewritten keyless-only; Sage take/cancel workarounds removed
  - Historical frontend offer carried `lp_out + 2` XCH; corrected path needs 2 mojos (launcher + LP CAT eve coin)
  - Two pools deployed on testnet11: launchers `8784f7d3…` (blk 4450051), `a24468c9…` (blk 4450073) — full router e2e PASS
  - Deploy configs added: Procfile, railway.toml, nixpacks.toml, requirements.txt, ecosystem.config.cjs, setup-oracle-arm.sh
- ⚠️ **2026-08-09** — Forge V2 trust-boundary audit completed
  - Existing offers protect user-requested minimums, but V2 puzzles do not enforce exact successor reserve outputs
  - Announcement-only LP TAIL authorization is replayable; `july23` also has a one-mojo LP supply mismatch
  - Mainnet design moved to direct singleton↔LP action handshake, canonical reserve IDs, exact reserve plans, and signed launch intent
  - Architecture: [forge-puzzle-architecture.md](quests/diagrams/forge-puzzle-architecture.md)
  - Quest: [harden-forge-offer-only-v3.md](quests/backlog/harden-forge-offer-only-v3.md)
- ✅ **2026-03-22** — Forge Swap Aggregator foundation + multi-hop execution delivered
  - Aggregator module: `types.ts`, `forgeAdapter.ts`, `quoteEngine.ts`, `index.ts` — adapter pattern with `LiquiditySource` interface
  - UI: `AggregatorSwap.tsx` (swap tab), `RoutePreview.tsx` (route visualization), `swapStore.ts` (Zustand state)
  - Multi-hop execution: sequential hop runner with progress tracking, 3s settle delay, pool state refresh between hops
  - Partial-failure recovery: user informed they hold intermediate asset if later hop fails
  - Fixed 7 TypeScript errors from parallel SwapPanel→AggregatorSwap migration
  - Clean build: `tsc --noEmit` 0 errors, `vite build` 1.77MB bundle
  - **Session 3-4: Blocker analysis + bootstrapAmounts fix**
  - Puzzle reveals confirmed populated from compiled CLVM hex
  - `decodeMockPoolState()` confirmed implemented at poolIndexer.ts:535
  - `bootstrapAmounts` added to STATIC_KNOWN_POOLS: T1.6 `['10000000000', '1000']`, T1.7 `['100000000000', '100', '100', '100']`
  - Deterministic reserves now flow through: App mount → loadAllPools → decodeMockPoolState → forgeAdapter.setPoolState → quoteEngine.findRoutes
  - Quest moved to done/, enhancement backlog created at `backlog/enhance-forge-swap-aggregator.md`
  - INDEX.md cleaned: no active quests remaining; aggregator added to completed foundations
  - Remaining: live on-chain testing (needs full node or Sage bridge), Phase 2 external DEX adapters
- ✅ **2026-03-29** — TM10 (10-asset pool) Stage 2 bootstrap submitted on testnet11, operator LP CAT `FLPTM10` minted (1100 mojos, asset_id `418c18a5...`). Production architecture decision: LP = CAT with pool-controlled TAIL (elastic supply, mint/burn gated by singleton announcements). New active quest: [build-forge-pool-controlled-tail.md](quests/build-forge-pool-controlled-tail.md)
- ✅ **2026-03-22** — T1.6 pool fully deployed on testnet11 — Stage 1 + Stage 2 via Sage RPC two-phase pipeline validated end-to-end
  - Pool launcher: `34ac7576174cff3c4aa7899b62b6fe91d55fc061892d05b8afca233f7e1338f2`
  - Target coin: `e8ec7eb63f3a92480abb74d15d6140fae08a3bc92e973bf37e28687bcc445720`
  - LP CAT: `cff471f832a20343e921b3f5229adf94070295e77dedee69899d0ef22c1973af` — confirmed visible in Sage wallet
  - Assets: TXCH + TEST 1 (50/50, 30bps fee, 50ppm protocol fee)
  - Fix applied: Stage 1 routes through `sage_stage1_submit.py` (no WalletConnect approval); Stage 2 waits up to 90s for sync instead of hard-failing
  - Fix applied: TypeScript `submitResultSucceeded({})` empty-object guard added; Sage always returns `{}` on success
  - T1.5 and T1.6 registered in `STATIC_KNOWN_POOLS` in `poolIndexer.ts`; pools now survive `localStorage.clear()`
  - T1.5 LP CAT ID still outstanding — locate from Sage and fill `poolIndexer.ts` TODO comment
- ✅ **2026-03-22** — Pool inline detail + pool launch workspace UX hardened
  - Redundant "Load Live Pool Anchor" lane removed from `PoolLaunchWorkspace.tsx`
  - Smart `PoolInlineDetail` now uses `effectiveLpCat = historyBatch?.lpCatAssetId || pool.lpCatAssetId` fallback
  - Sync-block errors distinguished from real failures; amber/green/red badges based on actual failure mode
  - "Continue Bootstrap" gated on absence of LP CAT from any source
- ✅ **2026-03-20** — Forge Sage RPC lane foundation + WalletConnect liquidity audit
  - Subagents traced the new Sage RPC quest and audited the current add/remove liquidity path before code changes.
  - Forge now has an expert-only Sage RPC preparation lane with a local `/api/sage-deploy` bridge, host/port inputs, and truthful `Prepared` launcher history records.
  - Liquidity audit outcome: add/remove liquidity on already-deployed pools remains the correct WalletConnect-first public path; the creation curse stays isolated to combined deploy + first LP CAT genesis.
- ✅ **2026-03-20** — Forge Sage/operator and Stage-2 quests moved to done as foundations
  - Quest moved to done: [forge-sage-rpc-deploy-and-walletconnect-liquidity.md](quests/done/forge-sage-rpc-deploy-and-walletconnect-liquidity.md)
  - Enhancement backlog: [enhance-forge-sage-rpc-deploy-and-walletconnect-liquidity.md](quests/backlog/enhance-forge-sage-rpc-deploy-and-walletconnect-liquidity.md)
  - Quest moved to done: [forge-stage2-execution-flow.md](quests/done/forge-stage2-execution-flow.md)
  - Enhancement backlog: [enhance-forge-stage2-execution-flow.md](quests/backlog/enhance-forge-stage2-execution-flow.md)
- ✅ **2026-03-21** — Independent subagent research slices completed for LP CAT authority + Forge create flow
  - LP CAT identity research locked the recommended pool-scoped TAIL direction around deterministic launcher-derived asset identity plus explicitly recorded `lp_cat_asset_id` in pool state.
  - Authority lifecycle research locked the requirement that launch, deposit, and withdraw all include a recreated persistent authority coin.
  - Builder mapping research identified the concrete launch, deposit, and withdraw touchpoints in [projects/chia-cfmm/src/lib/spendBundles.ts](projects/chia-cfmm/src/lib/spendBundles.ts) and the canonical announcement changes needed in [projects/chia-cfmm/contracts/pool_singleton_n_fixed.rue](projects/chia-cfmm/contracts/pool_singleton_n_fixed.rue).
  - Frontend flow research reduced the redesign to a smallest viable slice: stepper shell + pool-type step + persistent summary card, with [projects/chia-cfmm/src/components/PoolCreationPanel.tsx](projects/chia-cfmm/src/components/PoolCreationPanel.tsx) kept as the temporary integration shell.
- ✅ **2026-03-21** — Next implementation quests launched in subagents
  - Protocol implementation prep chose a narrow first coding slice: deterministic LP CAT TAIL + authority bootstrap contracts, canonical singleton announcement payloads, and launcher-side identity helpers before full deposit/withdraw authority wiring.
  - Frontend implementation prep chose a narrow first coding slice: create-pool store, stepper shell, pool-type step, and persistent summary card before the heavier coin-picker and deployment-step work.
- ✅ **2026-03-21** — LP CAT identity + authority bootstrap foundation landed in code
  - Forge now ships compiled `forge_lp_cat_tail.rue` and `lp_cat_authority_coin.rue` foundation contracts.
  - The combined launcher + exact Stage 2 path now derives authoritative LP CAT identity metadata and creates a 1-mojo authority anchor coin during bootstrap.
  - The pool singleton now emits canonical LP announcements with `new_total_lp_supply` while preserving legacy announcements for current bridge compatibility.
  - Current truth remains explicit: the live eve CAT spend is still on the temporary `genesis_by_coin_id` lane until repeated pool-authoritative mint/burn is wired.
- ✅ **2026-04-01** — Forge CFMM pool testnet11 deployment foundation complete
  - Quest moved to done: `deploy-forge-pool-testnet.md` → Stage 1 + Stage 2 confirmed
  - `launcher_id`: `1d17a51c21200e687efa180dbba02764ba973600fdfb0b20afd7873bdc4dc83b`
  - Stage 1 confirmed at h=3926044 (~91s). Stage 2 (P2 bootstrap) submitted, mempool=0.
  - Key fix: bypassed `send_xch` entirely — reads Sage SQLite directly (WAL persists pending txs across restart)
  - Enhancement backlog: [enhance-forge-reserve-coin-deposits.md](quests/backlog/enhance-forge-reserve-coin-deposits.md)
- ✅ **2026-04-08** — Forge swap execution architecture clarified for the next implementation slice
  - `swap_engine` locked as the canonical swap settlement boundary; `pool_singleton_v2` remains LP-only
  - routed external offers may execute through wallet-native take-offer methods or the local Sage offer bridge where truthful
  - Forge-native swap-engine routes remain quote-only until a pool-aware responder or submission lane is present and validated
  - live proper-tail pool `e35984cd...20cf` has confirmed add/remove lifecycle evidence and remains the truthful swap-validation target
- ✅ **2026-03-21** — Forge LP CAT ownership pivot moved to done as a foundation quest
  - Quest moved to done: [forge-lp-cat-ownership-pivot.md](quests/done/forge-lp-cat-ownership-pivot.md)
  - Enhancement backlog: [enhance-forge-lp-cat-mint-and-burn-authority.md](quests/backlog/enhance-forge-lp-cat-mint-and-burn-authority.md)
- ✅ **2026-03-21** — Forge pool launch flow redesign moved to done as a frontend foundation quest
  - Quest moved to done: [forge-pool-launch-and-create-flow-redesign.md](quests/done/forge-pool-launch-and-create-flow-redesign.md)
  - Enhancement backlog: [enhance-forge-pool-launch-and-create-flow-redesign.md](quests/backlog/enhance-forge-pool-launch-and-create-flow-redesign.md)

---

## 🎯 Active Quests

### Phase 0 — Theme Unification (cross-project) ✅ COMPLETE
- [x] Add Nightspire CSS token block + glow utility classes to `chia-treasure-chest/src/App.css`
- [x] Add Nightspire CSS token block + glow utility classes to `chia-cfmm/src/App.css`
- [x] Update treasure-chest header / footer selectors to use `--accent`, `--border-color`, glow vars
- [x] Update CFMM header to use `--accent`, `--bg-deep`, glow shadows; `.rt-Card:hover` uses `--border-color`
- [x] Create `chia-perps/` project scaffold from `chia-cfmm/` as template
- [x] Verify all 3 sites render with `.glow-card`, `.glow-text`, `.glow-btn` classes ✅

---

### Phase 1 — Sage Wallet Connect (all frontends)

- [x] `chia-treasure-chest` — full `useChiaWallet` + `lib/walletConnect.ts` already wired (testnet11)
- [x] `chia-cfmm` — replaced mock stub with real WalletConnect Sign Client implementation
- [x] `chia-cfmm` — created `lib/walletConnect.ts` with CHIP-0002 contract methods:
  - `getAssetCoins` — query spendable CAT/NFT/DID coins
  - `getAssetBalance` — query confirmed/spendable balances
  - `signCoinSpends` — sign Rue-compiled CLVM puzzles via Sage
  - `sendTransaction` — broadcast SpendBundle to mempool
  - `signAndSend` — convenience: sign + broadcast in one call
- [x] Both projects default to `chia:testnet11` ✅
- [x] Create `chia-perps/src/` scaffold with wallet hook
- [x] Add `VITE_WC_PROJECT_ID` reminder to each `.env.example` ✅ STANDARDIZED
- [ ] Test: connect Sage wallet → address displays in header

---

### Phase 2 — Treasure Chest Frontend

Connect the existing `chia-treasure-chest` contracts to the UI.

- [ ] Read `chia-treasure-chest/contracts/` — understand deployed testnet11 singleton
- [ ] Build `ChestViewer.tsx` — displays current chest state (listings, owner, balance)
- [ ] Build `ListItemForm.tsx` — owner can list XCH, CAT, or NFT
- [ ] Build `PurchaseFlow.tsx` — buyer: view listing → confirm → submit spend bundle
- [ ] Wire spend bundle signing via `WalletConnectProvider.signCoinSpends()`
- [ ] Display Spacescan link to chest singleton coin

---

### Phase 3 — CFMM Backend Library

Implement all TypeScript back-end modules the CFMM frontend depends on.

**Math library** (`src/lib/cfmm.ts`) ✅
- [x] `powFrac(baseScaled, p, q)` — Newton-Raphson x^(p/q), 16 iterations, mirrors `pow_frac()` in swap_engine.rue
- [x] `calcSwapOut` / `calcSwapIn` — weighted CFMM with fee
- [x] `spotPrice`, `priceImpactBps`
- [x] `calcLpOut(pool, amounts)` — geometric mean (first deposit) / proportional (thereafter)
- [x] `calcWithdrawAmounts(pool, lpShare)` — proportional withdrawal
- [x] `buildSwapQuote`, `buildDepositQuote`, `buildWithdrawQuote`

**Coin utilities** (`src/lib/coinUtils.ts`) ✅
- [x] `puzzleHashToAddress` / `addressToPuzzleHash` — bech32m encode/decode (xch / txch)
- [x] `mojosToXch` / `xchToMojos`, `mojosToCat` / `catToMojos`
- [x] `coinId(parent, puzzleHash, amount)` — async SHA-256 coin ID
- [x] `bigintToChiaBytes` — Chia minimal-length big-endian integer encoding
- [x] `treeHashCons` / `treeHashAtom` — CLVM tree hash primitives
- [x] `clvmAtom`, `clvmCons`, `clvmList`, `clvmInt`, `clvmHash` — CLVM serialization

**Spend bundle builders** (`src/lib/spendBundles.ts`) ✅
- [x] `buildSwapBundle` — pool singleton Swap mode + input CAT coin spend
- [x] `buildMultiAssetDepositBundle` — MultiAssetDeposit mode + N CAT coin spends
- [x] `buildSingleAssetDepositBundle` — SingleAssetDeposit mode + 1 CAT coin spend
- [x] `buildWithdrawBundle` — Withdraw mode + LP NFT Burn mode
- [x] `buildSplitLpBundle` — LP NFT Split mode
- [x] CLVM solution serialization for all Rue struct modes (tagged-union encoding)
- [x] `PUZZLE_REVEALS` registry with clear "compile first" error messages

**Pending (connect frontend)** — ⚠️ **BLOCKED:** Rue contracts need compilation fixes
- [ ] **Compile Rue contracts** — `rue build contracts/pool_singleton_n_fixed.rue` + `lp_nft.rue`; fill `PUZZLE_REVEALS` in spendBundles.ts
- [ ] Build `PoolStats.tsx` — reserves, K invariant, current price, 24h volume
- [ ] Build `SwapForm.tsx` — token in/out with estimated output and price impact; wire `buildSwapBundle`
- [ ] Build `LiquidityForm.tsx` — add/remove liquidity, show LP NFT balance; wire deposit/withdraw bundles
- [ ] Build `SplitLpModal.tsx` — split LP position; wire `buildSplitLpBundle`
- [ ] Real `poolIndexer.ts` — replace mock with WalletConnect getPublicKeys → pool coin fetch; populate `currentPuzzleReveal` + `lineageProof`
  - proven locally: `bootstrapTargetCoinId` / `bootstrapTargetPuzzleHash` can be the spent Stage-2 singleton, not the live child coin
  - helper lane now derives the real post-bootstrap child coin id + puzzle hash from the captured Stage-2 payload
  - remaining blocker: source of truth for the live child `currentPuzzleReveal` is still missing from checked-in app state
- [ ] Display pool singleton coin on Spacescan testnet11

### Forge Focus — Stage 2 Bootstrap

- [x] Truthful Stage-1 launcher deployment flow in Forge
- [x] Adaptive Stage-2 batch planner in the GUI
- [x] Persist batch launcher history across refreshes
- [x] Persist launcher parent coin info and render launcher history outside the planner card
- [x] First-pass CLVM benchmark: adaptive 5x2 route vs single 10-asset `pool_singleton_n_fixed` candidate
- [x] Simulator-first end-to-end launcher-to-bootstrap probe for `pool_singleton_n_fixed` across 2-10 assets
- [x] Direct launcher path prototype targeting `pool_singleton_n_fixed`
- [x] Freeze one canonical Stage-2 target before reopening adjacent Forge quests

---

### Phase 4 — Chia Perpetuals (`chia-perps`)

Build the Aftermath-equivalent perpetuals exchange on Chia. Start from testnet11.

#### 4a. Contracts (Rue/CLVM)
- [ ] Design `market_singleton.rue` — CLOB state, open interest, funding accumulator
- [ ] Design `account_singleton.rue` — per-user collateral + position map (isolated margin)
- [ ] Design `oracle_aggregator.rue` — multi-source price aggregation (3+ signed oracle coins)
- [ ] Design `insurance_fund.rue` — market-isolated insurance pool
- [ ] Design `liquidation_engine.rue` — permissionless liquidation logic
- [ ] Design `aflp_vault.rue` — community LP market-making vault

#### 4b. Math (TypeScript reference) ✅ COMPLETE
- [x] `src/lib/perpsmath.ts` — mark price median: `median(bookPrice, fundingPrice, TWAP)`
- [x] `src/lib/perpsmath.ts` — unrealized PnL: `(markPrice - entryPrice) × size`
- [x] `src/lib/perpsmath.ts` — margin ratio check for liquidation trigger
- [x] `src/lib/perpsmath.ts` — partial liquidation: minimum size to restore health
- [x] `src/lib/perpsmath.ts` — funding rate computation (premium × clamp)

#### 4c. Frontend Components
- [x] `MarketsTab.tsx` — ✅ COMPLETE list of perpetual markets with mark price, 24h change, OI
- [x] `TradingPanel.tsx` — open long/short, size, leverage input, estimated liquidation price
- [x] `PositionPanel.tsx` — open positions: size, entry price, PnL, margin ratio, close button
- [x] `LiquidationPanel.tsx` — permissionless liquidator view: underwater positions + liquidate btn
- [x] `VaultTab.tsx` — afLP-equivalent vault: deposit/withdraw, TVL, APY estimate
- [x] `OracleStatusBar.tsx` — show current oracle prices + staleness indicator

#### 4d. Testnet Deployment
- [ ] Deploy `oracle_aggregator` singleton on testnet11
- [ ] Deploy `market_singleton` for XCH-PERP on testnet11
- [ ] Deploy `insurance_fund` singleton
- [ ] Open test positions via UI, verify on Spacescan
- [ ] Run a test liquidation (open undercollateralised position, trigger liquidator)
- [ ] Document coin IDs for CHIP submission evidence

---

### Phase 5 — Emoji Market (craft.awizard.dev) ✅ COMPLETE

Create and launch the 6 core emoji token CATs on testnet11 via `craft.awizard.dev`.

- [ ] Design `emoji_cat_launcher.rue` — standard CAT launcher with emoji metadata
- [ ] Mint 6 genesis emoji tokens on testnet11:
  - [ ] ❤️  LOVE — Love / social capital
  - [ ] 🌱 SPROUT — Growth / ecological
  - [ ] 🔮 CASTER — Magic / creative power
  - [ ] ✨ SPELL — Utility / action fuel
  - [ ] ⚡ POWER — Energy / compute
  - [ ] 💎 HODL — Store of value / conviction
- [ ] Create Forge pools: LOVE/XCH, SPROUT/XCH, CASTER/XCH, SPELL/XCH, POWER/XCH, HODL/XCH
- [x] Build `craft.awizard.dev` UI ✅ **COMPLETE**
  - [x] `EmojiTokenGrid.tsx` — 6 token cards with emoji, symbol, rarity glow
  - [x] `TokenCreator.tsx` — minting interface with cost calculation
  - [x] `TokenMetadata.tsx` — full token details with backstory + use cases
  - [x] Core token definitions with rich metadata (emotion, backstory, useCase)
  - [x] Dev server running on **localhost:5183**
- [ ] Add emoji token metadata standard to CHIP submission queue

---

### Phase 6 — Bank of Wizards (bank.awizard.dev) ✅ MVP COMPLETE

**Quest:** [docs/quests/done/build-bank-of-wizards.md](quests/done/build-bank-of-wizards.md) ✅  
**Enhancements:** [docs/quests/backlog/enhance-bank-of-wizards.md](quests/backlog/enhance-bank-of-wizards.md) (backlog)  
**Status:** Foundation delivered (60%), enhancements deferred

Portfolio hub — aggregates everything a user owns across all wizard protocols.

**✅ Delivered (MVP Foundation):**
- [x] Scaffold `projects/chia-bank/` from `chia-cfmm` template ✅
- [x] `PortfolioOverview.tsx` — total net worth in XCH + USD, breakdown by category ✅
- [x] `AssetList.tsx` — all CAT/emoji tokens with balance, price, value ✅
- [x] `LpPositionList.tsx` — LP NFT positions with share %, fees earned, manage links ✅
- [x] Core types: `AssetBalance`, `LpPosition`, `TreasureChest`, `EmojiTokenBalance` ✅
- [x] `bankAggregator.ts` — net worth calculation, price formatting ✅
- [x] Mock data integration (ready for real WalletConnect queries) ✅
- [x] Dev server running on **localhost:5184** ✅

**📦 Deferred to Backlog (Enhancements):**
- Tab structure (Assets, Liquidity, Perps, Chests, Vaults)
- Charts & visualizations (Recharts pie/line/bar charts)
- Quick action modals (swap, send, deposit)
- Oracle price integration (Dexie, Tibetswap, CFMM fallback)
- Testnet11 deployment to bank.awizard.dev

---

### Phase 7 — Analytics Hub (stats.awizard.dev) ✅ COMPLETE

Unified analytics dashboard — ecosystem observability layer with metrics, charts, and rankings.

- [x] Scaffold `projects/chia-stats/` from `chia-bank` template ✅
- [x] Install Recharts charting library ✅
- [x] Mock analytics data layer with realistic ecosystem metrics ✅
- [x] `EcosystemOverview.tsx` ✅
  - [x] Hero TVL card (125.75 XCH total ecosystem)
  - [x] 7-day TVL growth chart with Recharts
  - [x] Metric cards: 24h volume, protocol revenue, active users, protocol count
- [x] `ForgeAnalytics.tsx` — CFMM pool rankings table ✅
  - [x] Pool list sorted by TVL
  - [x] Display: weights, TVL, 24h volume, APR
  - [x] 6 pools (XCH/LOVE leads with 45 XCH + 14.2% APR)
- [x] `TokenAnalytics.tsx` — emoji token market cap leaderboard ✅
  - [x] Token cards with rank, emoji, mcap, 24h change
  - [x] Price, supply, holder count stats
  - [x] LOVE #1 (100 XCH mcap), HODL #2 (80 XCH mcap)
- [x] Recharts integration with Nightspire theme (accent colors, glow effects) ✅
- [x] Dev server running on **localhost:5185** ✅
- [ ] Build Python indexer service (FastAPI + SQLite)
- [ ] Poll chain state every 60s (pool coins, CAT balances, NFT listings)
- [ ] REST API for real-time data (`/api/tvl`, `/api/pools`, `/api/tokens`)
- [ ] Replace mock data with live testnet11 queries

---

### 🚀 Deployment Quest — Testnet11 Infrastructure 📦 BACKLOG

**Quest Doc:** [docs/quests/backlog/deploy-testnet-infrastructure.md](quests/backlog/deploy-testnet-infrastructure.md)  
**Deployment Map:** [docs/DEPLOYMENT_MAP.md](DEPLOYMENT_MAP.md)  
**Setup Guides:** [WALLETCONNECT_SETUP.md](WALLETCONNECT_SETUP.md) | [VERCEL_SETUP.md](VERCEL_SETUP.md) | [RAILWAY_SETUP.md](RAILWAY_SETUP.md) | [ENV_VARS_REFERENCE.md](ENV_VARS_REFERENCE.md)

Deploy all 11 projects to testnet11 with production CI/CD:

- [x] **Step 1: Domain & Hosting Setup** ✅ COMPLETE
  - [x] Inventory all projects → 11 total (9 Vite frontends + gym-server + bow-app)
  - [x] Map subdomains: forge/craft/bank/chest/perps/vaults/stats/faucet/map/gym.awizard.dev
  - [x] Create `vercel.json` for all 8 Vite frontends
  - [x] Document `.env.example` files (production-ready)
  - [x] Create WalletConnect Cloud setup guide
- [x] **Step 2: Environment Configuration** ✅ COMPLETE
  - [x] Create **WALLETCONNECT_SETUP.md** — 7-step guide to WalletConnect Cloud project setup
  - [x] Create **VERCEL_SETUP.md** — Complete Vercel config for all 8 frontends
  - [x] Create **RAILWAY_SETUP.md** — gym-server deployment with persistent SQLite
  - [x] Create **ENV_VARS_REFERENCE.md** — Master reference for 37 environment variables
- [ ] **Step 3: CI/CD Pipeline Setup** *(backlog — do after local testing validates the UI)*
  - [x] `chia-cfmm` production-ready: SPA rewrites, chunk splitting, forge.awizard.dev metadata ✅ **2026-03-06**
  - [ ] **Deploy forge.awizard.dev** — connect Vercel project to `projects/chia-cfmm/`, set `VITE_WC_PROJECT_ID` + `VITE_CHIA_NETWORK=testnet11` env vars
  - [ ] Install Vercel GitHub App → link remaining 7 frontend projects
  - [ ] Configure Railway auto-deploy for gym-server
  - [ ] Enable preview deployments for PR branches
  - [ ] Test deployment flow (push to main → auto-deploy)
- [ ] **Step 4: Testnet11 Wallet Infrastructure**
  - [ ] Generate deployment wallets (1 per contract project)
  - [ ] Fund via testnet11 faucet (1000 XCH each)
  - [ ] Document fingerprints + mnemonics in 1Password
  - [ ] Deploy gym-server wallet for battle signing
- [ ] **Step 5: Monitoring & Logging**
  - [ ] Enable Vercel Analytics (all frontends)
  - [ ] Configure Sentry error tracking
  - [ ] Set up UptimeRobot monitoring (5-min pings)
  - [ ] Railway metrics dashboard (gym-server CPU/memory)
- [ ] **Step 6: Deployment Documentation**
  - [ ] Write DEPLOYMENT.md runbook
  - [ ] Update project READMEs with production URLs
  - [ ] Create troubleshooting guide
- [ ] **Step 7: Testing & Validation**
  - [ ] Smoke test all frontends (wallet connect, UI loads)
  - [ ] Backend health checks (gym-server /health endpoint)
  - [ ] Cross-service integration tests
  - [ ] Lighthouse benchmarks (performance audit)
- [ ] **Step 8: Production Readiness Checklist**
  - [ ] HTTPS verification (all subdomains)
  - [ ] CORS configuration (gym-server → map.awizard.dev)
  - [ ] Error boundaries on all React roots
  - [ ] Testnet disclaimers on every frontend

---

### Phase 8 — Aggregator DEX (swap.awizard.dev)

Unified swap interface — aggregates liquidity from all major Chia DEXs.

- [ ] Scaffold `projects/chia-aggregator/` from `chia-cfmm` template
- [ ] **Dexie Integration:** Parse offer book API, calculate swap routes via orderbook matching
- [ ] **Tibetswap Integration:** Import pool configs, calculate AMM swap rates
- [ ] **Splash Integration:** Fetch pool state, calculate swap quotes via their SDK
- [ ] **Our CFMM Integration:** Use existing `cfmm.ts` math library with fetched pool state
- [ ] **Smart Router:** `findBestRoute(tokenIn, tokenOut, amountIn)` — compares rates across all DEXs
- [ ] **Atomic Splitting:** Route large swaps across multiple DEXs to minimize slippage
- [ ] `AggregatorSwapForm.tsx` — unified UI showing best rate + selected route
- [ ] `LiquidityCompare.tsx` — side-by-side TVL, APR, volume comparison across DEXs
- [ ] **Revenue Sharing:** 0.05% protocol fee on aggregated swaps → insurance fund
- [ ] Deploy on `swap.awizard.dev` with unified brand

### Phase 9 — Portal Arbitrage (portal.awizard.dev)

Market balancer — detects price mismatches, routes arbitrage bundles.

- [ ] `priceMonitor.ts` — poll Forge pool prices + Dexie offer book prices
- [ ] `arbDetector.ts` — compute profitable arbitrage routes
- [ ] `buildArbBundle()` — construct atomic spend bundle (swap Forge → capture spread)
- [ ] `portal.awizard.dev` UI — display active opportunities, historical captures
- [ ] Feed arb revenue to insurance fund singleton

---

### Phase 10 — Liquidity Manager (Auto-Rebalancing Strategy Layer) ✅ FOUNDATION COMPLETE

**Quest:** [docs/quests/done/build-liquidity-manager-system.md](quests/done/build-liquidity-manager-system.md) ✅  
**Enhancements:** [docs/quests/backlog/enhance-liquidity-manager-system.md](quests/backlog/enhance-liquidity-manager-system.md) (backlog)  
**Project:** [projects/chia-vaults/](../projects/chia-vaults/)  
**Status:** Foundation delivered (30%), contracts + frontend deferred

**Current sequencing:** defer active liquidity-manager implementation until LP deployment quests are complete, then use live pool behavior to decide the remaining balancing mechanics.

Automated liquidity management strategies for CFMM pools and Treasure Chests — Chia's equivalent
of Aftermath afLP strategy UX. This is an optional post-launch layer for automated balancing,
not a required custody system for initial CFMM launch.

**✅ Delivered (Foundation Complete):**
- [x] Quest specification with full Aftermath afLP reference (900+ lines) ✅
- [x] Contract flow diagrams (Mermaid: deposit, withdraw, rebalance, oracle) ✅
- [x] Math library: `src/lib/vaultBalancer.ts` ✅ COMPLETE (18 KB, 600+ lines)
  - Share calculations (deposit/withdraw)
  - Rebalance trigger detection & optimal action computation
  - APY tracking, impermanent loss calculations
  - Oracle price aggregation (median of 3+ sources)
  - Risk metrics (VaR, Sharpe ratio)
- [x] Project scaffold: `projects/chia-vaults/` fully scaffolded ✅
- [x] README.md with comprehensive documentation ✅
- [x] Dev server ready on **localhost:5178** ✅

**📦 Deferred to Backlog (70% remaining):**
- Optional shared-strategy deposit accounting
- Frontend UI (VaultDashboard, DepositFlow, WithdrawFlow, RebalanceMonitor)
- Spend bundle builders for manager interactions
- Oracle integration (Dexie, Tibetswap, CFMM price feeds)
- Manager indexer for live state queries
- Testnet deployment for XCH/LOVE liquidity manager
- CHIP documentation & submission if the pattern proves reusable

**Re-entry condition:** return here after LP deployment quests finish and the team has real pool-state feedback about drift, keeper cadence, and which balancing actions should be automatic.

---

### Phase 10 — CHIP Submissions

After testnet proofs are live:

- [ ] Treasure Chest CHIP — NFT programmable vault standard (Informational)
- [ ] CFMM CHIP — weighted multi-CAT AMM primitive (Standards Track); built on CHIP-0050 from V11, so the submission covers the actions, the multi-reserve finalizer and the curve, not the glue
- [ ] Emoji Token CHIP — emoji metadata standard for CATs
- [ ] Perps CHIP-A: On-Chain CLOB Standard
- [ ] Perps CHIP-B: Perpetual Futures Position Standard
- [ ] Perps CHIP-C: Oracle Aggregation Standard
- [ ] Perps CHIP-D: Permissionless Vault Standard
- [ ] Liquidity Manager CHIP — Auto-Rebalancing Strategy Standard (Informational)

---

## 🏁 Completed

- ✅ **2026-08-09** — Forge V4-alpha unbalanced joins and full-position withdrawal implemented
  - Fresh pools accept one or both reserve CATs on add; no synthetic counterpart deposit
  - LP mint is the exact floor of 50/50 geometric-invariant growth and remains XCH-backed
  - Remove continues to return all reserve CATs pro rata
  - V4 locks `1 LP` mojo at creation; legacy pool `8926` safely burned `1999/2000` LP and returned `1 LP` as change in confirmed transaction `b9d6d640...`

- ✅ **2026-03-05** — `docs/skills/chiaPerpetuals.md` created (full Aftermath-equivalent protocol spec)
- ✅ **2026-03-05** — `docs/skills/nightspireTheme.md` created (canonical Nightspire CSS design system)
- ✅ **2026-03-05** — `awizard.agent.md` updated with Chia DeFi ecosystem, Nightspire theme convention, skills table
- ✅ **2026-03-05** — Phase 0: Nightspire glow tokens + utility classes added to both `App.css` files ✅ THEME VALIDATION COMPLETE
- ✅ **2026-03-05** — Phase 1: `chia-cfmm/lib/walletConnect.ts` created with full CHIP-0002 contract methods ✅ WIRE CFMM COMPLETE  
- ✅ **2026-03-05** — Phase 1: `chia-cfmm/hooks/useChiaWallet.ts` rewritten (mock → real WalletConnect) 
- ✅ **2026-03-05** — Phase 4b: `chia-perps/src/lib/perpsmath.ts` complete with all perpetuals math functions ✅ PERPS MATH COMPLETE
- ✅ **2026-03-05** — Phase 4c: `chia-perps/MarketsTab.tsx` built with markets display ✅ MARKETS TAB COMPLETE
- ✅ **2026-03-05** — World Engine: `awizard-gui/` Phaser 3 tile renderer + world foundation ✅ BOOTSTRAP WORLD COMPLETE
- ✅ **2026-03-05** — Sage CHIP-0002 method list documented in `/memories/chia-ecosystem.md`
- ✅ **2026-03-05** — Phase 10: Liquidity Manager Foundation (Phases 1-2) ✅ MATH LIBRARY + QUEST DOC COMPLETE
  - Quest: `build-liquidity-manager-system.md` (900+ lines, contract flows, full spec)
  - Math library: `chia-vaults/src/lib/vaultBalancer.ts` (600+ lines, all liquidity-manager math)
  - Project scaffold: `chia-vaults/` ready for contract development
- ✅ **2026-03-06** — Phase 6: Bank of Wizards MVP ✅ FOUNDATION COMPLETE
  - Quest: [build-bank-of-wizards.md](quests/done/build-bank-of-wizards.md) moved to done/
  - Core aggregation engine (60% complete) — net worth, assets, LP positions
  - Enhancements backlogged: [enhance-bank-of-wizards.md](quests/backlog/enhance-bank-of-wizards.md)
- ✅ **2026-03-06** — Phase 10: Liquidity Manager Foundation ✅ COMPLETE (30%)
  - Quest: [build-liquidity-manager-system.md](quests/done/build-liquidity-manager-system.md) moved to done/
  - Math library complete (`vaultBalancer.ts` — 18 KB with all liquidity-manager math)
  - Project scaffold ready (`projects/chia-vaults/` on localhost:5178)
  - Enhancements backlogged: [enhance-liquidity-manager-system.md](quests/backlog/enhance-liquidity-manager-system.md)
- ✅ **2026-03-07** — Forge GUI testnet deployment: stage-1 launcher spell cast
  - Quest: [frontend-gui-pool-deployment.md](quests/backlog/frontend-gui-pool-deployment.md) moved to backlog after the LP CAT ownership pivot reprioritized CFMM work
  - Sage WalletConnect accepted the launcher with `status: 1, error: null`
  - Launcher id recorded: `0104a3cb0cee7221294cf5028140a112aaf61cd580bfb7825ab438f65be6e297`
  - Derived singleton eve coin ids recorded for pool and DAO shells
  - Follow-up spell backlogged: [enhance-forge-liquidity-bootstrap.md](quests/backlog/enhance-forge-liquidity-bootstrap.md)
- ✅ **2026-03-07** — Forge Stage 2 Bootstrap foundation complete
  - Quest: [forge-stage2-bootstrap.md](quests/done/forge-stage2-bootstrap.md) moved to done/
  - Canonical target frozen on `pool_singleton_n_fixed` for 2-10 assets
  - Standard singleton launcher path, persistent launcher history, and launcher parent metadata all wired through Forge
  - Follow-up spell activated: [forge-stage2-execution-flow.md](quests/done/forge-stage2-execution-flow.md)
- ✅ **2026-03-08** — Forge LP NFT standard-migration comparison path crossed the Sage-native mint boundary
  - Quest: [forge-lp-nft-standard-migration.md](quests/forge-lp-nft-standard-migration.md) is now frozen as prototype-complete infrastructure for Treasure Chest and future NFT-native lanes
  - Active CFMM ownership pivot: [forge-lp-cat-ownership-pivot.md](quests/forge-lp-cat-ownership-pivot.md)
  - Quest: [forge-lp-nft-standard-migration.md](quests/forge-lp-nft-standard-migration.md) remains active
  - `chia_bulkMintNfts` is now wired through Forge with explicit DID configuration and a Sage-acceptable minimal payload
  - Sage successfully minted a wallet-visible native LP receipt on testnet11 and returned `nftIds`
  - Forge now preserves Sage `nftIds`, records native LP wallet ids in adaptive Stage-2 history, and shows a recovered fallback LP card instead of dropping the position
  - Remaining blocker: the native receipt still lacks collection/metadata richness, so Forge has not yet upgraded that fallback card into a fully wallet-indexed LP position
- ✅ **2026-03-17** — Forge protocol fee + operator env cleanup foundation delivered
  - `pool_singleton_n_fixed.rue` now retains LP fee in reserves correctly and curries `protocol_fee_ppm` plus `protocol_puzzle_hash` into the pool state
  - Forge frontend quote and stats surfaces now distinguish LP fee, protocol fee, DAO fee, and frontend platform fee
  - Network-aware treasury defaults now exist in code for mainnet and testnet11, while `.env` remains the single active local operator config
  - `.env.example` was updated into a real placeholder template and `.env.testnet` now reflects the current fee-routing story
  - Next proof spell: fresh testnet11 pool replay against the new canonical pool hash, then one post-deploy pool action
- ✅ **2026-03-20** — Forge deployment strategy reprioritized around Sage RPC and public-user liquidity
  - New active quest: [forge-sage-rpc-deploy-and-walletconnect-liquidity.md](quests/done/forge-sage-rpc-deploy-and-walletconnect-liquidity.md)
  - Pair deployment is now explicitly treated as an expert/operator action first
  - Public-user scope is now add/remove liquidity on already-deployed pools through WalletConnect + Sage-friendly flows
  - Tibet-style backend operator service remains the fallback lane after Sage RPC mode, not the first implementation spell
- ✅ **2026-01-15** — 🚀 CFMM Infrastructure Quest ✅ COMPLETE (100%)
  - Quest: [cfmm-deployment-infrastructure.md](quests/done/cfmm-deployment-infrastructure.md) moved to done/
  - Sage RPC integration: Live Sage wallet connection (mTLS on 127.0.0.1:9257) 
  - Contract compilation: 6/6 Rue contracts compiled to CLVM (17KB total)
  - Pool configuration: 3 pools prepared (TXCH/Test1, Test1/Test2, TXCH+Test1+Test2+Test3)
  - Deployment pipeline: 4 deployment approaches + live transaction demonstration
  - Status doc: [DEPLOYMENT_STATUS.md](../projects/chia-cfmm/DEPLOYMENT_STATUS.md) with full infrastructure summary

---

## 🎨 Frontend Enhancement Queue — "Juice Up UI/UX"

### Three.js Integration (chia-cfmm) — 3D DeFi Experience
**Status:** BACKLOG  
**Prerequisites:** Current chia-cfmm foundation ✅ COMPLETE
**Target:** Future-proof for Arcane BOW in-game integration

**Phase 1: Foundation Setup**
- [ ] Install Three.js ecosystem: `three @types/three @react-three/fiber @react-three/drei @react-three/postprocessing`
- [ ] Create `src/components/three/` — 3D component library
- [ ] Configure Vite for Three.js optimization (bundle splitting, WASM support)

**Phase 2: Strategic Implementation**  
- [ ] **LP NFT Visualization** (LpNftCard.tsx) — 3D rotating NFT cards with depth/lighting
- [ ] **Pool Statistics** (PoolStats.tsx) — 3D bar/pie charts, animated asset flows
- [ ] **Background Ambience** — Subtle 3D particles matching Radix UI theme
- [ ] **Pool Creation Preview** (PoolCreationPanel.tsx) — 3D asset weight visualization

**Phase 3: Gaming Integration Prep**
- [ ] **Asset-Game Bridge** — Shared 3D models for DeFi ↔ Arcane BOW  
- [ ] **Battle-Worthy Assets** — LP positions as 3D weapons/artifacts
- [ ] **Performance Optimization** — Mobile-first 3D with 2D fallbacks
- [ ] **Cross-App Library** — Share components with bow-app project

**Implementation Strategy:** Toggle 2D/3D modes, progressive enhancement, maintain current UX

---

## 💡 Ideas Parking Lot

- **Concentrated pool type (post-V11)** — second merkle root on the same action layer, finalizer and
  reserves; positions as NFTs carrying `(band_id, share)`; N-asset "bands" per the research record in
  `docs/skills/chip0050ActionLayer.md`; gated on off-chain reference maths (homothety, two-threshold
  result, re-entry rule) matched to V3 at N=2 and V10 at zero offsets

- **Cross-collateral margin**: use CFMM LP NFTs as collateral in the perps account singleton
- **Insurance fund mining**: emit reward CATs to liquidators proportional to bad debt covered
- **Referral codes**: builder fee split (like Aftermath's builder codes) — route % to a referrer coin
- **Multi-manager strategies**: strategy-of-strategies that allocates to multiple liquidity managers based on APY
- **Yield tokenization**: split vault shares into principal + yield tokens (Pendle-style)

---

_Last updated: 2026-03-20_
