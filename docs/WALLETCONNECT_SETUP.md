# WalletConnect Cloud Setup Guide

**Purpose:** Configure WalletConnect v2 for production deployment across all aWizard DeFi frontends.  
**Date:** March 6, 2026  
**Network:** Chia testnet11

---

## 🌐 What is WalletConnect Cloud?

WalletConnect Cloud provides the relay infrastructure for connecting dApps to Chia wallets (like Sage) via the **CHIP-0002** standard. Each project needs a unique **Project ID** to use the WalletConnect SDK.

**Dashboard:** https://cloud.walletconnect.com

---

## 📋 Step 1: Create a WalletConnect Cloud Account

1. Navigate to https://cloud.walletconnect.com
2. Sign up with GitHub (recommended) or email
3. Verify your email address
4. Skip the onboarding questionnaire (optional)

---

## 🔑 Step 2: Create a New Project

1. Click **"Create Project"** from the dashboard
2. **Project Name:** `aWizard DeFi — Testnet11`
3. **Project Description:** `Chia DeFi ecosystem on testnet11 — CFMM, perps, NFT vaults, token creation`
4. **Homepage URL:** `https://awizard.dev`
5. Click **"Create"**

---

## 📱 Step 3: Configure Allowed Domains

To prevent unauthorized usage, whitelist your production domains:

1. Open your project settings
2. Navigate to **"Allowed Domains"**
3. Add the following domains:
   ```
   forge.awizard.dev
   lock.awizard.dev
   craft.awizard.dev
   bank.awizard.dev
   chest.awizard.dev
   perps.awizard.dev
   vaults.awizard.dev
   map.awizard.dev
   localhost:5173
   localhost:5174
   localhost:5175
   localhost:5176
   localhost:5177
   localhost:5178
   localhost:5179
   localhost:5180
   ```
4. Save changes

---

## 🔐 Step 4: Copy Your Project ID

1. From the project dashboard, locate **"Project ID"**
2. Copy the ID (format: `xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`)
3. Save this securely — you'll need it for all `.env` files

**Example Project ID:**
```
a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
```

---

## 🚀 Step 5: Configure Environment Variables

Add the Project ID to **all frontend projects**:

### Production (Vercel Environment Variables)

Navigate to each Vercel project → **Settings** → **Environment Variables**:

| Project | Variable | Value |
|---------|----------|-------|
| forge.awizard.dev | `VITE_WC_PROJECT_ID` | `your_project_id_here` |
| craft.awizard.dev | `VITE_WC_PROJECT_ID` | `your_project_id_here` |
| bank.awizard.dev | `VITE_WC_PROJECT_ID` | `your_project_id_here` |
| chest.awizard.dev | `VITE_WC_PROJECT_ID` | `your_project_id_here` |
| perps.awizard.dev | `VITE_WC_PROJECT_ID` | `your_project_id_here` |
| vaults.awizard.dev | `VITE_WC_PROJECT_ID` | `your_project_id_here` |

**Scope:** Production + Preview

### Local Development

Copy `.env.example` to `.env` in each project:
```bash
cd projects/chia-cfmm
cp .env.example .env
# Edit .env and add:
VITE_WC_PROJECT_ID=your_project_id_here
VITE_CHIA_NETWORK=testnet11
```

Repeat for all projects that use WalletConnect.

---

## 📊 Step 6: Monitor Usage

WalletConnect Cloud provides analytics:

1. **Relay Requests** — Number of connection attempts
2. **Active Connections** — Currently paired wallets
3. **Bandwidth** — Data transferred via relay

**Free Tier Limits:**
- 1 million relay requests/month
- 100 GB bandwidth/month

If you exceed limits, upgrade to Pro tier ($49/month) or create additional projects per subdomain.

---

## 🧪 Step 7: Test WalletConnect Integration

After deploying, test the connection flow:

1. Visit any deployed frontend (e.g., https://forge.awizard.dev)
2. Click **"Connect Wallet"**
3. Scan QR code with **Sage wallet** (testnet11 mode)
4. Approve connection
5. Verify wallet address displays correctly

**Expected Behavior:**
- QR code appears instantly (relay connection successful)
- Sage wallet detects testnet11 network
- Connection persists across page refreshes

---

## 🔍 Troubleshooting

### Issue: "Invalid Project ID"
**Solution:** Verify you copied the full Project ID (32 characters) and set it as `VITE_WC_PROJECT_ID`.

### Issue: "Domain not allowed"
**Solution:** Add your domain to **Allowed Domains** in WalletConnect Cloud settings.

### Issue: QR code doesn't appear
**Solution:** Check browser console for errors. Verify you're using WalletConnect v2.x SDK (not v1.x).

### Issue: "Network mismatch" in Sage
**Solution:** Ensure Sage wallet is set to testnet11 mode. Check `VITE_CHIA_NETWORK=testnet11` in `.env`.

---

## 📚 Reference Documentation

- **WalletConnect Docs:** https://docs.walletconnect.com/
- **CHIP-0002 Spec:** https://github.com/Chia-Network/chips/blob/main/CHIPs/chip-0002.md
- **Sage Wallet:** https://github.com/xch-dev/sage
- **aWizard Deployment Map:** [docs/DEPLOYMENT_MAP.md](./DEPLOYMENT_MAP.md)

---

## ✅ Checklist

- [ ] Create WalletConnect Cloud account
- [ ] Create new project: "aWizard DeFi — Testnet11"
- [ ] Configure allowed domains (all subdomains + localhost)
- [ ] Copy Project ID
- [ ] Add `VITE_WC_PROJECT_ID` to Vercel environment variables (all projects)
- [ ] Add to local `.env` files for development
- [ ] Test connection flow on forge.awizard.dev
- [ ] Monitor usage in WalletConnect Cloud dashboard

---

**Next Steps:**
- Deploy all frontends to Vercel
- Test wallet connections across all subdomains
- Monitor relay usage (should stay within free tier)
- Document Project ID in 1Password vault
