# Skill: Deployment & Infrastructure

> aWizard's knowledge of hosting topology, CI/CD pipelines, environment configuration, and the boundary between Vercel, VPS, and blockchain nodes.

---

## Domain

aWizard can guide:

- **Vercel deployment** — static Vite builds, serverless functions, CDN
- **VPS deployment** — PM2/Docker for bots and servers, reverse proxy
- **Environment management** — secret separation, VITE_ prefix rules
- **Discord Developer Portal** — Activity URL mappings, OAuth2 config
- **CI/CD** — GitHub Actions for build + deploy on push
- **Operational support tooling** — database provisioning, wheel publishing, package release hygiene

## Hosting Topology

```
Vercel (Static + Serverless)
  |- awizard-gui (Vite build)
  |- /api/token (OAuth2 exchange)
  \- /api/nft/gate (NFT verification)

VPS (Persistent Processes)
  |- aWizard Discord Bot (Discord.js, WebSocket)
  |- gym-server (Express, SQLite, port 3001)
  \- Chia node (blockchain daemon)

Hosted RPC (Coinset.org — no node required)
  \- https://api.coinset.org/
       Blocks, coins, fees, mempool, websocket
       Free mainnet full-node RPC — drop-in for read queries

Vercel (Separate Project)
  \- bow-app (Next.js, port 3000)

Forge (two hosts from one repo, forge-ui)
  |- forge.awizard.dev      Vercel, STATIC ONLY -- .vercelignore keeps api/ off it
  |    |- /                  the website (SPA; /(.*) rewrites to index.html)
  |    \- /sage/             the Sage app package, built into dist/sage/ by
  |                          `npm run build:site`; install URL has the trailing slash
  \- forge-responder.up.railway.app   the responder (local-test-host.mjs + Python)
       every /api/... call, every settlement; keeps its own deployment index
```

**There is no API on forge.awizard.dev.** Every `/api/...` path there falls through the
SPA rewrite and answers `200` with `index.html`. A probe that reads only the status — or
only the CORS header, which the static host also sends — reports a healthy API that does
not exist. Read the body. Likewise the responder's `/api/sage-status` answers for a local
desktop wallet a container cannot have; that is `reason: no-local-wallet` and a 200 now,
and was a 503 that got Railway called "down" twice while it was serving 32 pools.

**Sage app origins come in two spellings.** An installed app runs at
`sage-app://<uuid>.<identity>` on macOS/Linux and `https://sage-app.<uuid>.<identity>` on
Windows. The responder's `FORGE_ALLOWED_ORIGINS` entry `sage-app://` matches both since
2026-09-20; a proxy in front of it has to know both or the app works everywhere except
Windows. Deploying forge-ui also needs `vite.config.sage.ts` and
`sage-app/sage-manifest.json` in the slice, and the scripts in
`docs/subrepo/forge-ui.package.json` — the deployment repo does not use the monorepo's
`package.json`. See `sageAppLane.md` and `projects/chia-cfmm/docs/FORGE_HOSTING_SPLIT.md`.

## Deployment Pipeline

```
git push main
  |--> Vercel auto-deploys awizard-gui
  |      Static assets -> CDN
  |      Serverless functions -> edge
  \--> (Separate) VPS deploy via PM2/Docker
         aWizard bot -> persistent WebSocket
         gym-server -> Express + SQLite
```

## Secret Separation Rules

| Prefix    | Accessible from | Safe for          |
| --------- | --------------- | ----------------- |
| `VITE_`   | Client bundle   | Public values only |
| No prefix | Server only     | Secrets, keys      |

**NEVER** put `DISCORD_CLIENT_SECRET` in a `VITE_` variable.

## Operational Toolchain

### Database Manager

Chia's `database-manager` is a useful reference for declarative infra operations:
- Config-driven user and database provisioning via YAML
- `validate` command to catch config errors before applying
- `apply` command to create databases, users, and grants
- `ENV:` value expansion for secrets and deployment-time injection
- Safe default network restriction behavior that falls back to `localhost`

This is the right pattern for future shared infra services when quest systems,
leaderboards, or back-office tools need managed database access.

### Build Wheels

`build-wheels` is a release-engineering reference for Python package maintenance:
- focused on automating wheel builds for `pypi.chia.net`
- useful when internal Chia tooling needs repeatable binary/package publishing
- relevant for Windows support, packaging consistency, and CI-based artifact generation

This matters if any of our Chia helper scripts graduate into reusable internal tools.

### Python Tooling Expectations

The current Chia reference tools commonly:
- pin specific `chia-blockchain` versions
- assume isolated virtual environments
- rely on wallet or full-node RPC availability
- are safer to automate through explicit CLI phases than ad hoc scripts

## Reference Repos

| Repo | Pattern Integrated |
| ---- | ------------------- |
| chia-gaming | Mini-Eltoo state channels, potato protocol |
| ChiaRPSGame | 3-party server signing, SpendBundle construction |
| sage | WalletConnect CHIP-0002 commands and wallet RPC surface |
| secure-the-mint | NFT pre-launcher + eve spend pattern |
| chia-gaming-tracker | Room discovery, state channel tracking |
| rue | CLVM language for contract authoring |
| chia-wallet-sdk | lower-level wallet engine, spend construction, bindings Sage is built on |
| coinset.org | hosted mainnet Chia full-node RPC — blocks, coins, fees, mempool, websocket |
| database-manager | Declarative database provisioning |
| build-wheels | Python wheel release automation |

## Source References
- `arcane-battle-protocol/DEPLOYMENT.md` — full deployment guide
- `awizard-gui/docs/ARCHITECTURE.md` — hosting and auth design
- `https://www.coinset.org/docs` — hosted Chia RPC API (mainnet, free)
- `https://github.com/coinset-org/cli` — Coinset CLI utility
- `https://github.com/Chia-Network/database-manager` — config-driven database ops
- `https://github.com/Chia-Network/build-wheels` — package build automation
