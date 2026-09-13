# aWizard Ecosystem — Testnet11 Deployment Map

**Last Updated:** March 6, 2026  
**Network:** Chia testnet11  
**Domain:** awizard.dev

---

## 🌐 Subdomain Deployment Matrix

> `chia-faucet` was cut — not being built. `stats.awizard.dev` (`chia-stats`) was retired
> 2026-09-05: its pool-ranking piece duplicated Forge's own in-app Markets tab, and the
> cross-protocol TVL rollup piece folds into `bank.awizard.dev` instead. Both removed from this
> matrix and every setup guide below.

| Subdomain | Project Folder | Purpose | Stack | Status |
|-----------|----------------|---------|-------|---------|
| **forge.awizard.dev** | `projects/chia-cfmm/` | The Forge — Weighted multi-CAT CFMM + LP NFTs | Vite + React 19 + Rue/CLVM | 🟡 Ready to deploy |
| **craft.awizard.dev** | `projects/chia-craft/` | The Craft Table — Emoji + CAT token creation | Vite + React 19 + Rue/CLVM | 🟡 Ready to deploy |
| **bank.awizard.dev** | `projects/chia-bank/` | Bank of Wizards — Portfolio hub + analytics | Vite + React 19 | 🟡 Ready to deploy |
| **chest.awizard.dev** | `projects/chia-treasure-chest/` | Treasure Chest — On-chain kiosk storefront | Vite + React 19 + Rue/CLVM | 🟡 Ready to deploy |
| **perps.awizard.dev** | `projects/chia-perps/` | The Perps Exchange — On-chain perpetuals DEX | Vite + React 19 + Rue/CLVM | 🟡 Ready to deploy |
| **lock.awizard.dev** | `projects/chia-cfmm/` (Multisig tab, not split out yet) | The Lock — M-of-N safes + vault-puzzle custody | Vite + React 19 + Rue/CLVM | 🔴 Planned split (working today as Forge's `🔐` tab; see `docs/skills/forgeMultisig.md`) |
| **vaults.awizard.dev** | `projects/chia-vaults/` | Liquidity Manager idea (Aftermath afLP-style auto-rebalancing) — no longer about "vaults" at all: Forge now owns both vault meanings (🫙 pool primitive, 🔐 custody lock), so this project's only remaining differentiator is the rebalancing/strategy automation, not vault creation or custody | Vite + React 19 | 🟠 Purpose needs restating — likely merges into `chest.awizard.dev` (Treasure Chest) as a strategy feature, not a standalone product |
| **map.awizard.dev** | `projects/awizard-gui/` | The Nightspire — Discord Activity (SNES world) | Vite + React 19 + Discord SDK | 🟡 Ready to deploy |
| **gym.awizard.dev** | `projects/gym-server/` | Gym Battle Server — PvE battle backend | Express + SQLite + TypeScript | 🟡 Ready to deploy |
| **bow.awizard.dev** | `projects/bow-app/` | Battle of Wizards — Main game frontend | Next.js 16 + React 19 | 🟢 Already deployed |

---

## 🏗️ Hosting Infrastructure

### Vercel (Static + Serverless)
All Vite frontends deploy to Vercel with automatic GitHub integration:
- forge, craft, bank, chest, perps, lock, vaults, map
- Build command: `npm run build`
- Output directory: `dist`
- Framework preset: Vite
- Monorepo root directory: Set per project (e.g., `projects/chia-cfmm/`)

### Railway/Render (Backend Services)
- **gym.awizard.dev** — gym-server (Express + SQLite)
  - Build: `cd projects/gym-server && npm install && npm run build`
  - Start: `node dist/index.js`
  - Persistent volume: `/data` for SQLite database

### Discord Activity Hosting
- **map.awizard.dev** — awizard-gui (Discord CDN)
  - Special deployment via Discord Developer Portal
  - See: https://discord.com/developers/docs/activities/hosting

---

## 🔐 Environment Variables

### Shared Across All Frontends
```env
VITE_WC_PROJECT_ID=xxx          # WalletConnect Cloud project ID
VITE_CHIA_NETWORK=testnet11     # Enforce testnet
```

### Project-Specific Variables

#### forge.awizard.dev (chia-cfmm)
```env
VITE_DEFAULT_POOL_ID=xxx        # Deployed pool singleton coin ID
VITE_ENABLE_MOCK_DATA=false     # Disable mocks in production
```

#### craft.awizard.dev (chia-craft)
```env
# Cost multipliers already hardcoded in emojiTokens.ts ✅
```

#### bank.awizard.dev (chia-bank)
```env
VITE_FORGE_API_URL=https://forge.awizard.dev/api  # CFMM integration
VITE_CHEST_API_URL=https://chest.awizard.dev/api  # Kiosk integration
# Ecosystem-wide TVL/analytics (formerly stats.awizard.dev, now retired — folds in here) reads
# directly from VITE_FORGE_API_URL / VITE_CHEST_API_URL rather than a separate stats API
```

#### perps.awizard.dev (chia-perps)
```env
VITE_ORACLE_ENDPOINT=xxx        # Testnet11 price oracle
VITE_INSURANCE_FUND=xxx         # Insurance fund singleton
```

#### map.awizard.dev (awizard-gui)
```env
VITE_DISCORD_CLIENT_ID=xxx      # Discord application ID
VITE_WORLD_API_URL=xxx          # World server endpoint (when deployed)
VITE_GYM_SERVER_URL=https://gym.awizard.dev
VITE_BOW_APP_URL=https://bow.awizard.dev
```

#### gym.awizard.dev (gym-server)
```env
PORT=3001                       # Railway auto-assigns
TRACKER_URL=https://bow.awizard.dev/api/tracker
FRONTEND_URL=https://map.awizard.dev  # CORS allowlist
GYM_FINGERPRINT=xxx             # Testnet11 wallet for gym battles
GITHUB_TOKEN=xxx                # GitHub Models API for wizard AI
DATABASE_PATH=/data/gym.db      # Persistent volume
```

---

## 📦 Vercel Configuration Template

Each frontend needs a `vercel.json`:

```json
{
  "buildCommand": "npm run build",
  "outputDirectory": "dist",
  "framework": "vite",
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        {
          "key": "X-Frame-Options",
          "value": "DENY"
        },
        {
          "key": "X-Content-Type-Options",
          "value": "nosniff"
        }
      ]
    }
  ]
}
```

**Discord Activity (awizard-gui) needs CSP for iframes:**
```json
{
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        {
          "key": "Content-Security-Policy",
          "value": "frame-ancestors https://discord.com https://*.discord.com https://*.discordapp.com https://*.discordsays.com"
        }
      ]
    }
  ]
}
```

---

## 🚀 CI/CD Pipeline

### GitHub → Vercel
1. Install Vercel GitHub App on `aWizardxch/aWizard-Familiar`
2. Link projects:
   - `projects/chia-cfmm/` → forge.awizard.dev
   - `projects/chia-craft/` → craft.awizard.dev
   - `projects/chia-bank/` → bank.awizard.dev
   - `projects/chia-treasure-chest/` → chest.awizard.dev
   - `projects/chia-perps/` → perps.awizard.dev
   - `projects/awizard-gui/` → map.awizard.dev
3. Configure root directory detection (monorepo)
4. Enable preview deployments for PR branches
5. Set production branch to `main`

### GitHub → Railway (gym-server)
1. Create Railway project linked to GitHub
2. Configure:
   - Root directory: `projects/gym-server/`
   - Build: `npm install && npm run build`
   - Start: `node dist/index.js`
   - Volume: `/data` for SQLite
3. Enable auto-deploys on `main` push

---

## 📊 Monitoring Stack

| Service | Tool | Purpose |
|---------|------|---------|
| Vercel Analytics | Built-in | Real User Monitoring (Core Web Vitals) |
| Sentry | Frontend error tracking | React error boundaries + runtime errors |
| Railway Metrics | Built-in | gym-server CPU/memory/logs |
| UptimeRobot | External pings | 5-min uptime checks on all subdomains |

---

## 🧪 Testnet11 Wallet Infrastructure

All contract deployments require funded testnet11 wallets:

1. Generate deployment wallets:
   ```bash
   chia keys generate
   chia keys show --show-mnemonic-seed
   # Save fingerprint + mnemonic securely
   ```

2. Fund via faucet:
   - https://testnet11-faucet.chia.net/
   - Request minimum 1000 XCH per deployment wallet

3. Document in 1Password:
   - Wallet name: "aWizard Testnet11 — [Project Name]"
   - Fingerprint
   - Mnemonic (secure notes)
   - First receive address

4. Deployment wallets needed:
   - ✅ forge.awizard.dev — CFMM pool launcher
   - ✅ craft.awizard.dev — Emoji token factory
   - ✅ chest.awizard.dev — Kiosk singleton
   - ✅ perps.awizard.dev — Perps exchange
   - ✅ gym.awizard.dev — Gym battle server wallet (for signing battle outcomes)

---

## 🔒 Security Checklist

- [ ] HTTPS enabled on all subdomains (automatic via Vercel/Railway)
- [ ] CORS properly configured (gym-server → map.awizard.dev only)
- [ ] No secrets in VITE_ environment variables (client-safe only)
- [ ] Discord Activity CSP allows only Discord domains
- [ ] Error boundaries on all React roots
- [ ] Testnet disclaimers on every frontend
- [ ] WalletConnect Project ID rate-limited per domain
- [ ] Database backups scheduled (Railway volumes → S3)

---

## 📖 Deployment Runbook

See [docs/quests/backlog/deploy-testnet-infrastructure.md](docs/quests/backlog/deploy-testnet-infrastructure.md) for the parked step-by-step deployment guide.

**Status Tracker:**
- ✅ Step 1: Domain & Hosting Setup (Planning complete)
- ⬜ Step 2: Environment Configuration
- ⬜ Step 3: CI/CD Pipeline Setup
- ⬜ Step 4: Testnet11 Wallet Infrastructure
- ⬜ Step 5: Monitoring & Logging
- ⬜ Step 6: Deployment Documentation
- ⬜ Step 7: Testing & Validation
- ⬜ Step 8: Production Readiness

---

**Next Steps:**
1. Create `vercel.json` for all 8 frontend projects
2. Generate WalletConnect Cloud project ID
3. Set up Railway project for gym-server
4. Document `.env.example` files
