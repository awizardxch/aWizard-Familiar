# aWizard Protocol Architecture

> **Tagline:** A gamified DeFi operating system on Chia.
>
> Every subdomain is a room in the wizard's world. Walking into a building opens a protocol UI.

---

## Ecosystem Map

```
awizard.dev  (landing / lore)
│
├── bank.awizard.dev      Bank of Wizards    — portfolio hub
├── forge.awizard.dev     The Forge          — liquidity engine (CFMM + NFT vaults)
├── lock.awizard.dev      The Lock           — multisig / vault custody (splitting out of Forge's 🔐 tab)
├── portal.awizard.dev    The Portal         — arbitrage / market balancer
├── craft.awizard.dev     The Craft Table    — token + NFT + emoji asset creation
├── build.awizard.dev     The Build Registry — developer expansion protocol
├── map.awizard.dev       The Open World     — visual world interface
├── cast.awizard.dev      Cast               — DEX swap routing
├── warp.awizard.dev      Warp               — bridge from Base / EVM → Chia
└── nightspire.awizard.dev  The Nightspire   — Discord Activity (Arcane BOW)
```

---

## 🏦 bank.awizard.dev — Bank of Wizards

The **main dashboard and portfolio hub**. Think wizard inventory screen — everything you own across all wizard protocols in one place.

### Sections

```
Bank of Wizards
├── Portfolio      — total value, assets, PnL
├── Vaults         — LP positions (token vaults), NFT vault chests
├── Liquidity      — active LP positions on Forge
├── Leverage       — open perpetual positions (from Portal or Forge)
├── Chests         — owned Treasure Chest NFTs with contents
└── Rewards        — farming rewards, fee accruals, referral earnings
```

### Data Sources
- Wallet coins via `chip0002_getAssetCoins`
- LP NFT positions via `chip0002_getNFTs` filtered by collection after the LP NFT standard-migration quest lands; current Forge LP ownership remains on a legacy custom position path and is not yet wallet-standard
- Forge pool state via pool singleton coin reads
- Perpetuals positions via account singleton reads

---

## 🔨 forge.awizard.dev — The Forge (CFMM Liquidity Protocol)

The **core liquidity engine** — where value is forged. Handles two vault archetypes:

### Forge's own path-domains

`forge.awizard.dev` is a single site, but it's client-side-routed (`TAB_TO_PATH` /
`PATH_TO_TAB` in `projects/chia-cfmm/src/App.tsx`) into eight real, deep-linkable paths, each a
distinct enough surface to work on as its own parallel workstream — the same "parallel-work
boundary" principle a full subdomain split gets (see Philosophy, below), just at path scope
instead of DNS scope:

| Path | Tab | Component | What it is |
|---|---|---|---|
| `/swap` | Swap | `SwapPanel` | token swap quote + route execution (default landing tab) |
| `/liquidity` | Liquidity | `LiquidityPanel` | add / remove liquidity |
| `/deploy` | ⚒️ Deploy Pool | `PoolLaunchWorkspace` + `DeploymentStatusPanel` | pool creation |
| `/holdings` | Holdings | `HoldingsPortfolio` + `LpPositions` + `OfferRelayPanel` | per-wallet position view — this overlaps Bank of Wizards' stated purpose the same way `chia-stats` overlapped Markets; not yet resolved, worth the same scrutiny later |
| `/multisig` | 🔐 | `MultisigPanel` | M-of-N safes + vault-puzzle locks — **the one path being externalized**, to `lock.awizard.dev` (see below); everything else here stays a Forge path. **Planned to gate `/balancer`'s automation** — see below |
| `/offers` | Offers | `OfferRelayPanel` | offer indexing/relay, take/cancel, deep-linkable at `/offers/<id>` |
| `/markets` | Markets | `MarketsPanel` | pool rows, spread, volume — the surface that absorbed `chia-stats`' `ForgeAnalytics.tsx` scope when that subdomain was retired |
| `/balancer` | Balancer | `BalancerPanel` (`lib/balancer/{equilibrium,arbCycle,catCycles}.ts`) | arb-cycle discovery + equilibrium planning across pools — **already built**, and already does most of what the `chia-vaults` autobalancer idea was for. Confirmed in its own source comment: "there is no keeper yet, so each one is a deliberate click rather than an automatic response to a spread opening." That sentence names the exact remaining gap precisely — a scheduled/automatic trigger, not the arb-cycle logic itself, which already exists here |

The `/balancer` finding sharpens the `docs/TODO_DEFI.md` Phase 10 note: it isn't only that
Forge's *passive* split-routing balances pools as a side effect of ordinary flow — Forge already
has an *active* rebalancer UI too. The only undone piece of the original vault-autobalancer idea
is automating `/balancer`'s click, not building rebalancing logic from scratch.

**Planned, future work after phase 8 — not current focus (2026-09-05, not yet built): `/multisig`
gates `/balancer`'s automation.** Current focus is phase 8 (V10 parity on V11); this is documented
direction, not a near-term task. Assets sit in
a vault lock; the balancer keeper holds a signing view scoped to one delegated-puzzle shape (the
arb-cycle spend), authorized to fire only when a criterion clears before signing — at minimum,
that the cycle's realized output is not less than what the vault's own offer/quote already
committed to (received units ≥ the offer's stated output). This is the concrete first instance of
`forgeMultisig.md`'s "vault actions" direction: a keeper that can only ever produce a trade at
least as good as one the owner already agreed to the shape of, and never holds a key that can do
anything else.

### 1. Token Vault — LP Pools

Fungible LP representation. Standard weighted CFMM.

| Property | Detail |
|---|---|
| Pool type | N-asset weighted CFMM (Balancer-style), 1–10 assets; shipping revision = **V10** |
| LP token | Fungible CAT, ticker `ASSET1ASSET2-FORGE` |
| Fee | Configurable per-pool (e.g. 0.3%) |
| Math | `calcSwapOut`, `calcSwapIn`, `powFrac` — implemented in `cfmm.ts` |
| Contracts | `pool_singleton_FORGE` (state + all three modes), `forge_reserve_FORGE` (curried with the pool's `launcher_id`), `forge_lp_cat_tail_FORGE` plus the pinned `forge_lp_{mint,melt}_inner_FORGE`; all built via `contracts/forge_stdin.py`. Superseded revisions live in `contracts/development/` |
| Invariant | `prod(reserve_i ** weight_i)`, integer weights, **verified by bracketing** rather than solved — no fractional exponents on chain |
| Single-asset pools | A vault: cannot swap, so wrapping and redeeming its LP is its only trade, and the liquidity fee applies to that crossing |

Forge's execution boundary:

- the pool singleton is the LP authority and the state-transition lane; a router assembles the
  bundle from a signed Offer and **never holds a key**, so it cannot alter what the trader signed
- external routed offers may be accepted through wallet-native take-offer methods, or the local
  Sage RPC bridge when the browser session does not advertise them
- Forge maintains a local offer relay/indexer for uploaded offer files and router-created pending
  matches; router order is AMM-first, then Forge-owned indexed offers, with Dexie retained as an
  external fallback rather than the primary dependency
- **creation offers are bearer instruments** and are redacted at the HTTP boundary — never logged,
  mirrored to a public venue, or rendered with a copy button

Lanes: direct (`swap` / `add` / `remove`), multi-hop, split, and vault-route (swap then redeem).
A redemption may end a route but never open one; a wrap leg has no settling lane and is dropped
at quote time.

**V10 semantics** (see [docs/skills/forgePuzzleV10.md](skills/forgePuzzleV10.md)):

- creation commits the creator-selected bootstrap amounts, which set the initial ratios, and locks
  a genesis LP mojo at an unspendable destination so a holder can burn their whole position
- adds may be balanced, imbalanced or single-sided; the imbalance fee falls on `(K - k_i)/K` of the
  excess, so an unbalanced add followed by a pro-rata remove is not a fee-free swap
- LP CAT issuance requires equal XCH mojo backing, because CAT value cannot be created without
  base-coin value
- removes are exactly proportional and free for every multi-asset pool, with `burn < total_lp`
- **a reserve moves only on a puzzle announcement from its own pool**, rebuilt in-puzzle from the
  reserve's curried `launcher_id`; and LP supply moves only through the derived action coin id,
  the pinned inner, and a CAT-parent melt
- every transition passes a singleton-freshness guard (`api/_forgeResponder.js`) — exact unspent
  coin, matching puzzle hash, no pending mempool spend — and the successor snapshot it persists is
  the only source of the pool's next state
- **pre-V10 pools are retired and unsafe**; the deployment index rejects superseded revisions in
  both directions. See [docs/FORGE_PROTOCOL_STATUS.md](FORGE_PROTOCOL_STATUS.md)

### 2. NFT Vault — Treasure Chests

Non-fungible vault representation. Each chest is an on-chain container.

```
Treasure Chest #381
Contains:
  - 1,200 CAT tokens
  - 50 XCH
  - 3 NFTs
Properties:
  - NFT ownership controls withdrawal
  - Transferable (sell chest = transfer all contents)
  - Composable in games / other protocols
```

| Property | Detail |
|---|---|
| Vault type | Singleton NFT container |
| Ownership | NFT holder controls withdrawal |
| Contracts | `treasure_chest.rue`, `nft_lock.rue`, `cat_vault.rue` |
| CHIP | Standards Track — Informational (programmable vault NFTs) |

### Why Two Vault Types?

| | Token Vault | NFT Vault |
|---|---|---|
| LP token | Fungible CAT | Non-fungible NFT |
| Use case | AMM liquidity, yield farming | Composable containers, game loot, OTC |
| Transferability | Split/merge freely | Sell chest = transfer all contents |
| Game integration | Show LP percentage | Open chest in-world on `map.awizard.dev` |

---

## 🔐 lock.awizard.dev — The Lock (Multisig / Vault Custody)

**Not yet its own site.** Today this is the `🔐` tab inside `forge.awizard.dev` (`chia-cfmm`); the
plan is to split it into its own subdomain since it is a distinct custody primitive, not a Forge
pool feature — see the "three things called vault" note in
[docs/skills/README.md](skills/README.md#forge-defi-primitives).

| Property | Detail |
|---|---|
| Puzzle | Legacy: CNI's `p2_m_of_n_delegate_direct`. Current: CNI's vault puzzle (singleton + `m_of_n` merkle root of `bls_member` leaves) |
| Contracts | `contracts/multisig_tool.py`, `contracts/vault_tool.py`, `contracts/multisig_profile.py` (all in `chia-cfmm`, not yet their own project) |
| Frontend | `src/lib/multisig.ts`, `src/components/MultisigPanel.tsx` (in `chia-cfmm`) |
| Status | 🟡 logic and UI exist and work on testnet; not split into a standalone project/subdomain yet |
| Skill | [docs/skills/forgeMultisig.md](skills/forgeMultisig.md) |

### Functions
- Create or observe an M-of-N safe (or a vault-puzzle lock); on-chain self-describing manifest, no server-side registry of truth
- Propose → sign (partial Sage signatures via signing views) → assemble → execute
- Rekey as a vote on the current lock, not a unilateral mint
- **Direction:** the intended custody layer under other subdomains' held assets — e.g. Bank's
  vault positions, or a future Liquidity Manager strategy balance — via scoped "vault actions"
  that hold even for a 1-of-1 safe. Not yet wired to any of them.

---

## 🌀 portal.awizard.dev — The Portal (Arbitrage Engine)

The **market balancer**. Detects price mismatches between Forge pools and external DEXes, executes arbitrage, and captures spread for protocol revenue.

```
Mismatch detected:
  XCH/CAT price on Forge ≠ XCH/CAT price on Dexie
  ↓
Portal opens
  ↓
Arbitrage bundle submitted
  ↓
Markets balance, protocol earns spread
```

### Functions
- Monitor Forge pool prices vs. Dexie / other on-chain prices
- Execute atomic arbitrage spend bundles
- Route proceeds to insurance fund or stakers
- Stabilise prices → better UX for regular traders

---

## 🧩 craft.awizard.dev — The Craft Table

**Asset creation studio.** Where new tokens, NFTs, and emoji market assets originate.

### Products
- **Token Forge** — create a new CAT with name, ticker, supply
- **NFT Mint** — mint collections with on-chain metadata
- **Emoji Assets** — create emoji-backed on-chain tokens (see Emoji Market below)
- **Chest Templates** — define reusable Treasure Chest layouts

### Emoji Market
Each emoji token is a CAT representing a symbolic value unit:

| Emoji | Token | Meaning |
|---|---|---|
| ❤️ | LOVE | Love / social capital |
| 🌱 | SPROUT | Growth / ecological |
| 🔮 | CASTER | Magic / creative power |
| ✨ | SPELL | Utility / action fuel |
| ⚡ | POWER | Energy / compute |
| 💎 | HODL | Store of value / conviction |

Traded on Forge pools. Created via `craft.awizard.dev`.

---

## 🏗 build.awizard.dev — Developer Expansion Protocol

**The self-expanding world registry.** Developers register their own wizard modules.

```
build.awizard.dev
  ↓
Register Project
  - GitHub repo URL
  - Smart contract addresses
  - Protocol services
  - World location (map coordinates)
  ↓
Deploy wizard module
  ↓
Appears on map.awizard.dev
```

Modules can be:
- New AMM pools on Forge
- Games that integrate Treasure Chests
- Tools that consume emoji tokens
- Community-built world locations

---

## 🗺 map.awizard.dev — The Open World

**The visual interface** — all protocols as walkable world locations.

```
Wizard Continent
├── 🏦 Bank of Wizards     (north)
├── 🔨 The Forge           (east, industrial district)
├── 🌀 Portal Gate         (west, shimmering vortex)
├── 🧩 Craft Table         (south market)
├── 🗺 Cartographer        (center)
└── 🏘 Community Builds    (expandable edges)
```

Walking into a location loads that subdomain's UI in an iframe/panel. Entering The Forge opens `forge.awizard.dev`. Powered by `map.awizard.dev` — for skill routing start with `docs/skills/README.md`, then use `docs/skills/snesWorldEngine.md` for the world-engine specifics.

---

## ⚡ cast.awizard.dev — Cast (DEX Swap Router)

Fast-path swap UI. Routes through Forge pools, finds best price, and settles through Chia offer flows.  
Simple: pick two tokens, enter amount, cast the swap.

---

## 🌉 warp.awizard.dev — Warp (EVM → Chia Bridge)

Bridge from Base / EVM chains into the Chia ecosystem.  
Lock on Base → mint CAT on Chia. Burn CAT on Chia → release on Base.

---

## 🏰 nightspire.awizard.dev — The Nightspire

Discord Activity — Arcane BOW game. The wizard's realm inside Discord.  
Built on `projects/awizard-gui/`. Start with `docs/ARCHITECTURE_INDEX.md` for architecture routing and `docs/skills/README.md` for skill routing, then open `docs/skills/discordActivityAuth.md` for the auth-specific flow.

---

## Tech Stack (all projects)

| Layer | Technology |
|---|---|
| Frontend | Vite + React 19 + TypeScript |
| Styling | Tailwind CSS 4 / Radix UI Themes + Nightspire CSS tokens |
| State | Zustand |
| Wallet | WalletConnect CHIP-0002 + Sage wallet |
| Network | Chia testnet11 → mainnet |
| Contracts | Rue (compiles to CLVM) |
| Standards | CHIP submissions for each primitive |

---

## Project → Subdomain Mapping

| Project folder | Subdomain | Status |
|---|---|---|
| `projects/chia-cfmm/` | `forge.awizard.dev` | 🟡 Phase 3 |
| `projects/chia-treasure-chest/` | `forge.awizard.dev` (NFT vaults tab) | 🟡 Phase 2 |
| `projects/chia-perps/` | `forge.awizard.dev` (leverage tab) | 🔴 Planned |
| `projects/chia-cfmm/` (Multisig tab) | `lock.awizard.dev` | 🟡 Working, embedded in Forge — split planned |
| `projects/awizard-gui/` | `nightspire.awizard.dev` | 🟡 In dev |
| `projects/bow-app/` | `nightspire.awizard.dev` (game backend) | 🟡 In dev |
| `projects/awizard-bot/` | Discord bot (supports all subdomains) | 🟡 In dev |
| bank (planned) | `bank.awizard.dev` | 🔴 Planned |
| portal (planned) | `portal.awizard.dev` | 🔴 Planned |
| craft (planned) | `craft.awizard.dev` | 🔴 Planned |
| build (planned) | `build.awizard.dev` | 🔴 Planned |
| map (planned) | `map.awizard.dev` | 🔴 Planned |
| warp (planned) | `warp.awizard.dev` | 🔴 Planned |

---

## Philosophy

> A gamified DeFi operating system on Chia — where every protocol is a room in the wizard's world, every asset is a magical instrument, and every on-chain action is a spell cast.

- **Transparency** — all contracts verifiable on-chain, all prices deterministic
- **Composability** — Treasure Chest NFTs usable in games, Forge LP positions collateralisable
- **Self-expansion** — `build.awizard.dev` lets anyone add a room to the world
- **Lore-first** — the metaphor is not decoration, it's the product
- **Subdomains are a parallel-work boundary, not proof of separate product scope.** A feature can
  conceptually belong inside another product's domain and still ship from its own subdomain if
  that unblocks working on it independently — Lock splitting out of Forge is exactly this, not a
  claim that custody is unrelated to Forge. The inverse also holds: `stats.awizard.dev` was
  retired and folded into Forge's Markets tab + Bank precisely because it had no independent
  workstream left to justify the separate site once its scope was redundant.
