# Skill: Sage App Lane

How the Forge UI is packaged, published, installed and debugged as a **Sage app** —
the same bundle that serves the website, wrapped for the wallet's bridge. This is a
different thing from `sageRpc.md` (calling the wallet's RPC from a backend); here the app
runs *inside* Sage and reaches the wallet through `sage-app-sdk`.

Everything below was learned on 2026-09-19/20 against Sage 0.13.1 and SDK 0.13.1, and
each rule names the failure that produced it.

## Domain

- `projects/chia-cfmm/sage-app/` — manifests and packaging; the app itself is `src/`
- `vite.config.sage.ts` — relative `base`, three modes: default (`sage-app/dist`),
  `sagelocal` (loopback responder), `sagesite` (into the website's `dist/sage/`)
- `src/lib/walletTransport.ts` — the WalletConnect/bridge seam; `sageApiBase.ts` — the
  `/api` fetch shim and the runtime responder override
- `local-test-host.mjs` — the responder; `scripts/https-responder.mjs` — TLS proxy for
  the loopback lane

## Publishing

- **The package must be a real file tree the host serves.** `npm run build:site` builds
  the website into `dist/`, then the Sage bundle into `dist/sage/` and finalizes the
  manifest there. Vercel serves real files before its catch-all rewrite, which is why
  `/sage/…` works and why `/sage-manifest.json` at the root never did — Sage fetched
  the SPA's HTML and reported *failed to parse manifest JSON*.
- **Install from `https://forge.awizard.dev/sage/` — with the slash.** Sage resolves
  `sage-manifest.json` relative to the URL; `/sage` would look at the site root.
  `vercel.json` 307s `/sage` → `/sage/` (targeted, not global `trailingSlash`, which
  would rewrite the SPA's own routes).
- **The deployment repo builds from its own `package.json`**
  (`docs/subrepo/forge-ui.package.json`) and its slice must carry
  `vite.config.sage.ts` and `sage-app/sage-manifest.json`. A `vercel.json` change that
  references either without the slice carrying them fails the Vercel build outright.
- Sage keys updates off the finalized manifest's hash, not `version`; any file change
  is an update.

## The manifest (what the guides get wrong)

- Network whitelist entries are **origin strings** (`"https://api-testnet.dexie.space"`).
  `{scheme, host}` is the *bridge runtime* type used by `requestNetworkWhitelistGrant`;
  Sage's own built-in apps ship strings. Chain-specific hosts go under
  `whitelistByNetwork`. `https`/`wss` only — no loopback `http`, even though `http`
  loopback is fine as an *install* URL.
- The required host is whatever `VITE_FORGE_API` names at build time (Railway), never
  the code's fallback constant and never `forge.awizard.dev` (no API there).
- `sageVersion.testedMax` is the release actually tested; `99.0.0` permanently
  silences the warning the field exists for. `min` moves only for a real dependency.
- `finalize-manifest` rejects any `donation.address` whose bech32m prefix is not `xch` —
  no testnet donation, whatever the guide says.
- `sage:package:local` finalizes `sage-manifest.local.json`; it used to finalize the
  hosted manifest over the loopback bundle, so the local manifest was never used.

## SDK

- `isSageRuntimeAvailable()` is literally `!!globalThis.__TAURI__`; the hand-rolled
  check is equivalent and stays because the SDK is imported dynamically to keep Tauri
  out of the browser bundle. Not `hasSageBridge()`/`isSageBridgeInitialized()` — both
  are false during a normal startup.
- 0.13.1: `wallet.getKey()` takes **no argument** (breaking); `requestPermissionGrants`
  replaces the two single-grant calls (keep the deprecated one as fallback so `min` can
  stay 0.13.0); `--exclude` globs in `finalize-manifest`.
- A responder set at runtime (`forge.sage.apiBase`) cannot be in a manifest finalized
  before it was typed — `setSageApiBase()` requests the grant.

## The loopback lane

`npm run sage:package:local` + `npm run responder:tls` (https://localhost:4443 →
127.0.0.1:4184). **WebView2 uses the Windows certificate store**: import
`.certs/localhost.cer` into `Cert:\CurrentUser\Root` (no elevation, one prompt) or every
fetch dies in the TLS handshake as "Failed to fetch" while the proxy logs nothing.
`curl -k` will *not* reproduce this — drop `-k` and see exit 60. The `.pfx` passphrase is
whatever `RESPONDER_TLS_PASSPHRASE` is set to (the script's default is in
`scripts/https-responder.mjs`); the cert is dev-only and `.certs/` is excluded from
every sync.

## Debugging inside Sage

- **Read the body, not the status.** `forge.awizard.dev/api/*` is `200 index.html`; the
  responder's `/api/sage-status` reports a missing *local wallet* (200,
  `reason: no-local-wallet`) — neither means what the code alone suggests.
- **Origins have two spellings**: `sage-app://…` and, on Windows, `https://sage-app.…`.
  The responder matches both off one `sage-app://` allowlist entry; a proxy must too.
- **Consecutive trades**: the client drops cached reserves at push time now. A quote
  inside the old ≤5-minute confirmation window priced pre-trade reserves and was refused
  as "route releases X, trader asks Y" — the router had persisted the successor already.
- The app's trades settle through the **hosted** responder, so the local
  `.awizard/deployment-index.json` drifts behind chain; resync before reading local
  suite failures as defects (see `forgePoolLifecycleTesting.md`).

## Reference

`projects/chia-cfmm/sage-app/README.md`, `docs/FORGE_HOSTING_SPLIT.md`, the
fancybudgie.com Sage guides (accurate on shape, wrong on `txch` donations), and
`xch-dev/sage` `builtin-apps/*/sage-manifest.json` for ground truth on manifest format.
