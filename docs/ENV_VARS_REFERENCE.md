# Environment Variables — Master Reference

**Purpose:** Comprehensive reference for all environment variables across aWizard ecosystem.  
**Date:** March 6, 2026  
**Network:** Chia testnet11

---

## 🔐 Security Guidelines

### VITE_ Prefix Rules
| Prefix | Exposure | Use Cases | Security Level |
|--------|----------|-----------|----------------|
| `VITE_` | **Client-side** (bundled in JS) | Network IDs, API URLs, public keys | ⚠️ Public — never put secrets here |
| No prefix | **Server-side only** | Private keys, tokens, fingerprints | ✅ Secret — never exposed to client |

**Critical Rule:** Never use `VITE_` for Discord client secrets, wallet mnemonics, or API keys.

---

## 🌐 Shared Variables (All Projects)

These variables are **identical across all frontends**:

| Variable | Value (Production) | Purpose |
|----------|-------------------|---------|
| `VITE_WC_PROJECT_ID` | `your_project_id_from_walletconnect_cloud` | WalletConnect v2 relay connection |
| `VITE_CHIA_NETWORK` | `testnet11` | Prevents accidental mainnet transactions |

**Source:** Get `VITE_WC_PROJECT_ID` from [cloud.walletconnect.com](https://cloud.walletconnect.com) (see [WALLETCONNECT_SETUP.md](./WALLETCONNECT_SETUP.md))

---

## 🎨 Frontend Projects (Vite)

### forge.awizard.dev (chia-cfmm)

**Subdomain:** https://forge.awizard.dev  
**Project Folder:** `projects/chia-cfmm/`  
**Hosting:** Vercel

| Variable | Example Value | Required | Purpose |
|----------|---------------|----------|---------|
| `VITE_WC_PROJECT_ID` | `a1b2c3d4e5f6...` | ✅ Yes | WalletConnect project ID |
| `VITE_CHIA_NETWORK` | `testnet11` | ✅ Yes | Network enforcement |
| `VITE_DEFAULT_POOL_ID` | `0xabc123...` | ⬜ Optional | Pre-select default AMM pool |
| `VITE_ENABLE_MOCK_DATA` | `false` | ⬜ Optional | Disable mock data in production |
| `VITE_GYM_SERVER_URL` | `http://localhost:3001` | ⬜ Dev only | Local gym server (dev env) |
| `VITE_WORLD_API_URL` | `http://localhost:3002` | ⬜ Dev only | Local world API (dev env) |

**`.env.example` Status:** ✅ Up to date

---

### craft.awizard.dev (chia-craft)

**Subdomain:** https://craft.awizard.dev  
**Project Folder:** `projects/chia-craft/`  
**Hosting:** Vercel

| Variable | Example Value | Required | Purpose |
|----------|---------------|----------|---------|
| `VITE_WC_PROJECT_ID` | `a1b2c3d4e5f6...` | ✅ Yes | WalletConnect project ID |
| `VITE_CHIA_NETWORK` | `testnet11` | ✅ Yes | Network enforcement |
| `VITE_DEFAULT_SUPPLY` | `1000000000000` | ⬜ Optional | Default token supply (mojos) |
| `VITE_MIN_MINT_AMOUNT` | `1000` | ⬜ Optional | Min tokens per mint |
| `VITE_MAX_MINT_AMOUNT` | `1000000` | ⬜ Optional | Max tokens per mint |

**Note:** Cost multipliers are **hardcoded** in `emojiTokens.ts` (intentional design).

**`.env.example` Status:** ✅ Up to date

---

### bank.awizard.dev (chia-bank)

**Subdomain:** https://bank.awizard.dev  
**Project Folder:** `projects/chia-bank/`  
**Hosting:** Vercel

| Variable | Example Value | Required | Purpose |
|----------|---------------|----------|---------|
| `VITE_WC_PROJECT_ID` | `a1b2c3d4e5f6...` | ✅ Yes | WalletConnect project ID |
| `VITE_CHIA_NETWORK` | `testnet11` | ✅ Yes | Network enforcement |
| `VITE_FORGE_API_URL` | `https://forge.awizard.dev/api` | ✅ Yes | CFMM pool data API |
| `VITE_CHEST_API_URL` | `https://chest.awizard.dev/api` | ✅ Yes | Kiosk listing data |

**`.env.example` Status:** ✅ Up to date

---

### chest.awizard.dev (chia-treasure-chest)

**Subdomain:** https://chest.awizard.dev  
**Project Folder:** `projects/chia-treasure-chest/`  
**Hosting:** Vercel

| Variable | Example Value | Required | Purpose |
|----------|---------------|----------|---------|
| `VITE_WC_PROJECT_ID` | `a1b2c3d4e5f6...` | ✅ Yes | WalletConnect project ID |
| `VITE_CHIA_NETWORK` | `testnet11` | ✅ Yes | Network enforcement |
| `VITE_VAULT_INDEXER_URL` | `https://vaults.awizard.dev/api/vaults` | ⬜ Optional | Frontend vault catalog endpoint |
| `VAULT_INDEXER_UPSTREAM_URL` | `https://vault-indexer.awizard.dev/api/vaults` | ⬜ Server | Server-side merged vault singleton + oracle feed |
| `VAULT_REGISTRY_URL` | `https://vault-indexer.awizard.dev/api/vault-registry` | ⬜ Server | Deployed vault singleton registry feed |
| `VAULT_ORACLE_URL` | `https://oracle.awizard.dev/api/prices` | ⬜ Server | Oracle price feed merged by `/api/vaults` |
| `VAULT_SIMPLE_MODE` | `true` | ⬜ Server | Serve a simple preview XCH/LOVE vault from `/api/vaults` when no live backend is configured |

**`.env.example` Status:** ✅ Up to date

**Backend note:** `projects/chia-vaults/api/vaults.ts` first prefers a real upstream source: either `VAULT_INDEXER_UPSTREAM_URL`, or both `VAULT_REGISTRY_URL` and `VAULT_ORACLE_URL`. If none are set and `VAULT_SIMPLE_MODE` is not `false`, the route serves a simple preview vault payload with signer-policy metadata. Set `VAULT_SIMPLE_MODE=false` to force a `503` instead.

---

### perps.awizard.dev (chia-perps)

**Subdomain:** https://perps.awizard.dev  
**Project Folder:** `projects/chia-perps/`  
**Hosting:** Vercel

| Variable | Example Value | Required | Purpose |
|----------|---------------|----------|---------|
| `VITE_WC_PROJECT_ID` | `a1b2c3d4e5f6...` | ✅ Yes | WalletConnect project ID |
| `VITE_CHIA_NETWORK` | `testnet11` | ✅ Yes | Network enforcement |
| `VITE_ORACLE_ENDPOINT` | `https://oracle.awizard.dev/api/prices` | ⬜ Future | Price oracle feed |
| `VITE_INSURANCE_FUND` | `0xdef456...` | ⬜ Future | Insurance fund singleton |

**`.env.example` Status:** ✅ Up to date

---

### vaults.awizard.dev (chia-vaults)

**Purpose under review:** Forge now owns both meanings of "vault" (the 🫙 pool primitive and,
via Multisig, the 🔐 custody lock), and Forge's own split-routing balancer already covers most of
what this project's autobalancer was meant to do — see the note in `docs/TODO_DEFI.md` Phase 10.
Current direction: merges into Treasure Chest rather than staying standalone. Chest's own env
vars below already reference `vaults.awizard.dev` for a vault catalog endpoint, which is existing
evidence the two were meant to integrate.

**Subdomain:** https://vaults.awizard.dev  
**Project Folder:** `projects/chia-vaults/`  
**Hosting:** Vercel

| Variable | Example Value | Required | Purpose |
|----------|---------------|----------|---------|
| `VITE_WC_PROJECT_ID` | `a1b2c3d4e5f6...` | ✅ Yes | WalletConnect project ID |
| `VITE_CHIA_NETWORK` | `testnet11` | ✅ Yes | Network enforcement |

**`.env.example` Status:** ✅ Up to date

---

### map.awizard.dev (awizard-gui)

**Subdomain:** https://map.awizard.dev  
**Project Folder:** `projects/awizard-gui/`  
**Hosting:** Discord Activity (or Vercel with CSP headers)

| Variable | Example Value | Required | Purpose |
|----------|---------------|----------|---------|
| `VITE_DISCORD_CLIENT_ID` | `123456789012345678` | ✅ Yes | Discord application ID |
| `VITE_AWIZARD_BOT_URL` | `https://bot.yourdomain.com` | ✅ Yes | aWizard bot REST API |
| `VITE_GYM_SERVER_URL` | `https://gym.awizard.dev` | ✅ Yes | Gym battle server |
| `VITE_BOW_APP_URL` | `https://bow.awizard.dev` | ✅ Yes | Main BOW game client |
| `VITE_WORLD_API_URL` | `https://world-api.awizard.dev` | ⬜ Future | SNES world server API |

**Special Note:** Discord Activity hosting requires CSP headers (already configured in `vercel.json`).

**`.env.example` Status:** ✅ Up to date

---

## 🖥️ Backend Projects

### gym.awizard.dev (gym-server)

**Subdomain:** https://gym.awizard.dev  
**Project Folder:** `projects/gym-server/`  
**Hosting:** Railway (or Render)

| Variable | Example Value | Required | Purpose |
|----------|---------------|----------|---------|
| `PORT` | `3001` | ✅ Yes | Server port (Railway auto-assigns) |
| `NODE_ENV` | `production` | ✅ Yes | Environment mode |
| `FRONTEND_URL` | `https://map.awizard.dev,https://bow.awizard.dev` | ✅ Yes | CORS allowed origins |
| `TRACKER_URL` | `https://bow.awizard.dev/api/tracker` | ✅ Yes | Battle tracker API |
| `DATABASE_PATH` | `/data/gym.db` | ✅ Yes | SQLite persistent volume path |
| `GYM_FINGERPRINT` | `1234567890` | ✅ Yes | Testnet11 wallet fingerprint |
| `GITHUB_TOKEN` | `ghp_abc123...` | ✅ Yes | GitHub Models API key |
| `DEBUG` | `gym:*` | ⬜ Optional | Debug logging namespace |

**Security Notes:**
- `GITHUB_TOKEN` must be **server-side only** (never `VITE_`)
- `GYM_FINGERPRINT` should be documented in 1Password
- Database backups required weekly

**`.env.example` Status:** ✅ Up to date

---

### bow.awizard.dev (bow-app)

**Subdomain:** https://bow.awizard.dev  
**Project Folder:** `projects/bow-app/`  
**Hosting:** Vercel (Next.js)

| Variable | Example Value | Required | Purpose |
|----------|---------------|----------|---------|
| `NEXT_PUBLIC_WC_PROJECT_ID` | `a1b2c3d4e5f6...` | ✅ Yes | WalletConnect project ID |
| `NEXT_PUBLIC_CHIA_NETWORK` | `testnet11` | ✅ Yes | Network enforcement |
| `UPSTASH_REDIS_REST_URL` | `https://xxx.upstash.io` | ✅ Yes | Tracker Redis URL |
| `UPSTASH_REDIS_REST_TOKEN` | `xxx` | ✅ Yes | Tracker Redis token |

**Note:** Next.js uses `NEXT_PUBLIC_` prefix instead of `VITE_` for client-exposed vars.

**`.env.example` Status:** ✅ Already deployed (no changes needed)

---

## 📦 1Password Documentation Template

For storing secrets in 1Password vault:

### WalletConnect Project
- **Title:** aWizard DeFi — WalletConnect Cloud
- **Username:** (your GitHub email)
- **Password:** n/a
- **Project ID:** `your_walletconnect_project_id_here`
- **URL:** https://cloud.walletconnect.com
- **Notes:** Shared across all frontends (forge, craft, bank, etc.)

### GitHub Personal Access Token
- **Title:** Railway gym-server — GitHub Models API
- **Token:** `ghp_...`
- **Scopes:** No special scopes needed
- **Created:** March 6, 2026
- **Expires:** 90 days
- **URL:** https://github.com/settings/tokens

### Testnet11 Wallet (gym-server)
- **Title:** aWizard Testnet11 — Gym Server
- **Fingerprint:** `1234567890`
- **Mnemonic:** (24-word seed phrase)
- **First Address:** `txch1abc...`
- **Balance:** 1000 XCH (funded via testnet faucet)
- **Notes:** Used for gym battle outcome signing

---

## 🔄 Environment Variable Checklist

### Development (Local .env files)
- [ ] All projects have `.env` files (copied from `.env.example`)
- [ ] `VITE_WC_PROJECT_ID` set in all frontend `.env` files
- [ ] `VITE_CHIA_NETWORK=testnet11` in all projects
- [ ] gym-server `.env` has `GITHUB_TOKEN` and `GYM_FINGERPRINT`
- [ ] No `.env` files committed to Git (verified in `.gitignore`)

### Production (Vercel/Railway Dashboards)
- [ ] Vercel: `VITE_WC_PROJECT_ID` set for all 8 frontend projects
- [ ] Vercel: Environment scopes set to **Production + Preview**
- [ ] Railway: All gym-server variables configured
- [ ] Railway: Persistent volume mounted at `/data`
- [ ] All secrets documented in 1Password

---

## 🧪 Verification Script

Run this to verify all `.env.example` files are production-ready:

```bash
cd aWizard-Familiar

# Check for VITE_ prefix violations (should return empty)
grep -r "DISCORD_CLIENT_SECRET" projects/*/\.env.example
grep -r "GITHUB_TOKEN" projects/*/\.env.example | grep "VITE_"

# Verify all frontends have VITE_WC_PROJECT_ID
grep -r "VITE_WC_PROJECT_ID" projects/chia-*/\.env.example

# Expected: 8 matches (all frontend projects)
```

---

## 📚 Reference Documentation

- [WALLETCONNECT_SETUP.md](./WALLETCONNECT_SETUP.md) — Get WalletConnect Project ID
- [VERCEL_SETUP.md](./VERCEL_SETUP.md) — Configure Vercel environment variables
- [RAILWAY_SETUP.md](./RAILWAY_SETUP.md) — Configure Railway environment variables
- [DEPLOYMENT_MAP.md](./DEPLOYMENT_MAP.md) — Full ecosystem deployment matrix

---

**Last Updated:** March 6, 2026  
**Maintained By:** aWizard 🧙  
**Review Schedule:** Monthly or before major deployments
