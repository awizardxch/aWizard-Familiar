# Vercel Deployment Setup Guide

**Purpose:** Deploy all 8 aWizard frontend projects to Vercel with monorepo support.  
**Date:** March 6, 2026  
**Repository:** aWizardxch/aWizard-Familiar

---

## 📋 Prerequisites

- GitHub account with access to `aWizardxch/aWizard-Familiar` repository
- Vercel account (free tier works, Pro recommended for team collaboration)
- WalletConnect Project ID (see [WALLETCONNECT_SETUP.md](./WALLETCONNECT_SETUP.md))

---

## 🚀 Part 1: Install Vercel GitHub App

### 1. Sign Up / Sign In to Vercel
1. Go to https://vercel.com
2. Click **"Sign Up"** or **"Log In"**
3. Choose **"Continue with GitHub"**
4. Authorize Vercel to access your GitHub account

### 2. Import Repository
1. From Vercel dashboard, click **"Add New..."** → **"Project"**
2. In the repository list, find **"aWizardxch/aWizard-Familiar"**
3. Click **"Import"**

---

## 🎯 Part 2: Configure Individual Projects

You'll create **8 separate Vercel projects** for the monorepo. Each project targets a specific folder.

### Project 1: forge.awizard.dev (chia-cfmm)

**Import Settings:**
- **Project Name:** `awizard-forge`
- **Framework Preset:** Vite
- **Root Directory:** `projects/chia-cfmm/`
- **Build Command:** `npm run build`
- **Output Directory:** `dist`
- **Install Command:** `npm install --legacy-peer-deps`

**Environment Variables (Production):**
```env
VITE_WC_PROJECT_ID=your_walletconnect_project_id_here
VITE_CHIA_NETWORK=testnet11
VITE_ENABLE_MOCK_DATA=false
```

**Custom Domain:**
1. Go to **Settings** → **Domains**
2. Add `forge.awizard.dev`
3. Configure DNS CNAME record pointing to Vercel

---

### Project 2: craft.awizard.dev (chia-craft)

**Import Settings:**
- **Project Name:** `awizard-craft`
- **Framework Preset:** Vite
- **Root Directory:** `projects/chia-craft/`
- **Build Command:** `npm run build`
- **Output Directory:** `dist`
- **Install Command:** `npm install --legacy-peer-deps`

**Environment Variables (Production):**
```env
VITE_WC_PROJECT_ID=your_walletconnect_project_id_here
VITE_CHIA_NETWORK=testnet11
```

**Custom Domain:** `craft.awizard.dev`

---

### Project 3: bank.awizard.dev (chia-bank)

**Import Settings:**
- **Project Name:** `awizard-bank`
- **Framework Preset:** Vite
- **Root Directory:** `projects/chia-bank/`
- **Build Command:** `npm run build`
- **Output Directory:** `dist`
- **Install Command:** `npm install --legacy-peer-deps`

**Environment Variables (Production):**
```env
VITE_WC_PROJECT_ID=your_walletconnect_project_id_here
VITE_CHIA_NETWORK=testnet11
VITE_FORGE_API_URL=https://forge.awizard.dev/api
VITE_CHEST_API_URL=https://chest.awizard.dev/api
```

**Custom Domain:** `bank.awizard.dev`

---

### Project 4: chest.awizard.dev (chia-treasure-chest)

**Import Settings:**
- **Project Name:** `awizard-chest`
- **Framework Preset:** Vite
- **Root Directory:** `projects/chia-treasure-chest/`
- **Build Command:** `npm run build`
- **Output Directory:** `dist`
- **Install Command:** `npm install --legacy-peer-deps`

**Environment Variables (Production):**
```env
VITE_WC_PROJECT_ID=your_walletconnect_project_id_here
VITE_CHIA_NETWORK=testnet11
```

**Custom Domain:** `chest.awizard.dev`

---

### Project 5: perps.awizard.dev (chia-perps)

**Import Settings:**
- **Project Name:** `awizard-perps`
- **Framework Preset:** Vite
- **Root Directory:** `projects/chia-perps/`
- **Build Command:** `npm run build`
- **Output Directory:** `dist`
- **Install Command:** `npm install --legacy-peer-deps`

**Environment Variables (Production):**
```env
VITE_WC_PROJECT_ID=your_walletconnect_project_id_here
VITE_CHIA_NETWORK=testnet11
VITE_ORACLE_ENDPOINT=https://oracle.awizard.dev/api/prices
```

**Custom Domain:** `perps.awizard.dev`

---

### Project 6: vaults.awizard.dev (chia-vaults)

**Import Settings:**
- **Project Name:** `awizard-vaults`
- **Framework Preset:** Vite
- **Root Directory:** `projects/chia-vaults/`
- **Build Command:** `npm run build`
- **Output Directory:** `dist`
- **Install Command:** `npm install --legacy-peer-deps`

**Environment Variables (Production):**
```env
VITE_WC_PROJECT_ID=your_walletconnect_project_id_here
VITE_CHIA_NETWORK=testnet11
```

**Custom Domain:** `vaults.awizard.dev`

---


## 🔐 Part 3: Configure Environment Variables (All Projects)

### Adding Environment Variables in Vercel:

1. Open project in Vercel dashboard
2. Go to **Settings** → **Environment Variables**
3. For each variable:
   - **Key:** Variable name (e.g., `VITE_WC_PROJECT_ID`)
   - **Value:** Secret value (paste from 1Password or WalletConnect dashboard)
   - **Environments:** Check both **Production** and **Preview**
4. Click **"Save"**

### Critical Variables to Set:

**All Frontend Projects Need:**
- `VITE_WC_PROJECT_ID` — WalletConnect Cloud project ID (same for all)
- `VITE_CHIA_NETWORK` — Set to `testnet11` (prevents accidental mainnet use)

**Project-Specific Variables:**
- See individual project sections above

---

## 🌍 Part 4: DNS Configuration

For each custom domain, configure DNS records:

### Option A: Using Vercel DNS (Recommended)
1. Transfer domain to Vercel DNS
2. Automatic SSL certificate provisioning
3. Edge network optimization

### Option B: External DNS Provider
1. Add CNAME record:
   ```
   Host: forge
   Type: CNAME
   Value: cname.vercel-dns.com
   ```
2. Repeat for each subdomain (craft, bank, chest, etc.)
3. SSL certificates auto-issued via Let's Encrypt

**Verify DNS:**
```bash
# Check DNS propagation
nslookup forge.awizard.dev

# Expected output:
# Name: cname.vercel-dns.com
# Addresses: 76.76.21.21 (Vercel edge IP)
```

---

## 🔄 Part 5: Enable Auto-Deploy

### Git Integration Settings (Per Project):
1. Go to **Settings** → **Git**
2. **Production Branch:** `main`
3. **Preview Deployments:** Enable for all branches
4. **Deploy Hooks:** Optionally create webhook for manual triggers

### Deployment Triggers:
- ✅ Push to `main` → Production deployment
- ✅ Push to PR branch → Preview deployment
- ✅ Path filter: Only redeploy when files in `projects/[project-name]/` change

**Enable Ignored Build Step (Monorepo Optimization):**

Create `vercel-ignore-build-step.sh` in each project root (optional):
```bash
#!/bin/bash
# Only build if files in this project changed

git diff HEAD^ HEAD --quiet projects/chia-cfmm/
```

---

## 📊 Part 6: Configure Analytics & Monitoring

### Enable Vercel Analytics:
1. Open project → **Analytics** tab
2. Click **"Enable Analytics"**
3. Choose **Core Web Vitals** tracking
4. Free tier: 100k events/month

### Optional: Speed Insights
1. **Settings** → **Speed Insights**
2. Enable Real User Monitoring (RUM)
3. Track FCP, LCP, CLS, FID metrics

---

## 🧪 Part 7: Test Deployment Flow

### Trigger First Deployment:
1. Make a small change to a project (e.g., update README.md)
2. Commit and push to `main`:
   ```bash
   cd projects/chia-cfmm
   echo "# Test deployment" >> README.md
   git add README.md
   git commit -m "test: trigger Vercel deployment"
   git push origin main
   ```
3. Watch deployment in Vercel dashboard
4. Verify site loads at `https://forge.awizard.dev`

### Verify Environment Variables:
1. Open deployed site
2. Open browser devtools → Console
3. Check WalletConnect initialization:
   ```javascript
   // Should see testnet11 network config
   console.log(import.meta.env.VITE_CHIA_NETWORK);
   // Output: "testnet11"
   ```

---

## 🎯 Deployment Status Checklist

- [ ] **forge.awizard.dev** — Vercel project created, env vars set, domain configured
- [ ] **craft.awizard.dev** — Vercel project created, env vars set, domain configured
- [ ] **bank.awizard.dev** — Vercel project created, env vars set, domain configured
- [ ] **chest.awizard.dev** — Vercel project created, env vars set, domain configured
- [ ] **perps.awizard.dev** — Vercel project created, env vars set, domain configured
- [ ] **vaults.awizard.dev** — Vercel project created, env vars set, domain configured
---

## 🐛 Troubleshooting

### Build Fails: "Cannot find module"
**Solution:** Check `Root Directory` setting — must include trailing slash for monorepo detection.

### Environment Variables Not Loading
**Solution:** Ensure variables start with `VITE_` prefix (required for Vite to expose them to client).

### Domain Not Resolving
**Solution:** DNS propagation takes 10-60 minutes. Use `nslookup` to verify CNAME record.

### Build Succeeds But Site Shows 404
**Solution:** Verify `Output Directory` is set to `dist` (not `build` or `out`).

---

## 📚 Reference Links

- **Vercel Docs:** https://vercel.com/docs
- **Monorepo Guide:** https://vercel.com/docs/concepts/git/monorepos
- **Environment Variables:** https://vercel.com/docs/concepts/projects/environment-variables
- **Custom Domains:** https://vercel.com/docs/concepts/projects/domains

---

**Next Steps:**
- Complete [WALLETCONNECT_SETUP.md](./WALLETCONNECT_SETUP.md) to get Project ID
- Complete [RAILWAY_SETUP.md](./RAILWAY_SETUP.md) for gym-server backend
- Update [docs/quests/backlog/deploy-testnet-infrastructure.md](./quests/backlog/deploy-testnet-infrastructure.md) with completion status when the deployment lane is reactivated
