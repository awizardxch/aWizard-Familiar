# Architecture Index

This index tells you which architecture document to open based on the question you are
trying to answer.

Use this file when:
- scoping a backlog quest
- deciding where a new system belongs in the wizard ecosystem
- figuring out whether a problem is protocol, frontend, deployment, or workflow

---

## Primary Architecture Docs

> **Published vs workspace.** This repo ships standalone on GitHub: `.github/`, `docs/`,
> `docs/skills/`, `.vscode/`, `README.md`. Rows below pointing into `projects/` or `docs/quests/`
> are **workspace only** — they exist for someone with the monorepo open, and anything the agent
> must be able to rely on lives in `docs/`.


| Document | Scope | Open this when |
| --- | --- | --- |
| `docs/ARCHITECTURE.md` | Ecosystem-wide product map | You need the high-level subdomain model, project-to-product mapping, or world metaphor |
| `projects/arcane-battle-protocol/ARCHITECTURE.md` | On-chain game and protocol architecture | You need battle, contract, state-channel, or reward protocol structure |
| `projects/awizard-gui/docs/ARCHITECTURE.md` | Discord Activity and GUI architecture | You need Nightspire frontend, auth, client structure, or activity integration details |
| `docs/quests/diagrams/forge-puzzle-architecture.md` | Forge weighted CFMM puzzle and offer protocol | You need pool, reserve, LP CAT, offer-only, or responder trust-boundary details |

## Support Architecture Docs

| Document | Scope | Open this when |
| --- | --- | --- |
| `projects/arcane-battle-protocol/DEPLOYMENT.md` | Protocol deployment details | You need deployment topology for contracts or battle infrastructure |
| `docs/DEPLOYMENT_MAP.md` | Deployment surface map | You need to understand what runs where |
| `docs/ENV_VARS_REFERENCE.md` | Environment variable contract | You need env var names, ownership, or secret boundaries |
| `docs/WALLETCONNECT_SETUP.md` | Wallet connection setup | You need WalletConnect setup details |
| `docs/VERCEL_SETUP.md` | Vercel deployment setup | You are deploying frontend or serverless surfaces |
| `docs/RAILWAY_SETUP.md` | Railway deployment setup | You are using Railway-hosted services |

## Structural and Workflow References

| Document | Scope | Open this when |
| --- | --- | --- |
| `docs/skills/projectArchitecture.md` | File/module architecture rules | You are deciding where code or docs should live |
| `docs/skills/README.md` | Skill system index | You need domain references before implementing |
| `docs/QUEST_WORKFLOW.md` | Quest lifecycle architecture | You are moving work between backlog, active, and done |
| `docs/skills/questManagement.md` | Detailed quest workflow | You need the rationale and rules behind the backlog system |

## Architecture by Work Type

### Ecosystem / Product Surface
- Start with `docs/ARCHITECTURE.md`
- Then open `docs/DEPLOYMENT_MAP.md` if deployment boundaries matter

### Chia Protocol / Contract System
- Start with `projects/arcane-battle-protocol/ARCHITECTURE.md`
- Then open `projects/arcane-battle-protocol/DEPLOYMENT.md`
- Pair with `docs/skills/chiaPrimitivesPatterns.md` and `docs/skills/blockchainDecentralization.md`

### Forge CFMM / Offer-Only Execution
- Start with `docs/skills/forgePuzzleV10.md` — the shipping revision
- Pair with `docs/skills/forgeLpCat.md`, `docs/skills/forgePoolLifecycleTesting.md`, and `docs/skills/chiaTibetAmm.md`
- For any review, probe, or revision of the puzzles: `docs/skills/clvmPuzzleAudit.md` first
- Current status: `docs/FORGE_PROTOCOL_STATUS.md` (V10; pre-V10 pools retired and unsafe)
- Next revision: `docs/FORGE_V11_SPEC.md` (build spec and phase plan) with `docs/skills/chip0050ActionLayer.md` (rationale: CHIP-0050 action layer, weighted full range, oracle, registry; concentrated liquidity descoped, future via NFT positions)
- Findings: `docs/FORGE_SECURITY_AUDIT.md` — ten, all fixed, two third-party-reachable fund loss
- `docs/quests/diagrams/forge-puzzle-architecture.md` (workspace only) predates V10 — read it as history
- Treat routers and indexes as replaceable liveness infrastructure, never protocol authority

### Nightspire / GUI / Activity
- Start with `projects/awizard-gui/docs/ARCHITECTURE.md`
- Then open `docs/WALLETCONNECT_SETUP.md` and `docs/ENV_VARS_REFERENCE.md`
- Pair with `docs/skills/bowAppReference.md`, `docs/skills/discordActivityAuth.md`, and `docs/skills/nightspireTheme.md`

### Repo Layout / New Module Planning
- Start with `docs/skills/projectArchitecture.md`
- Then open `docs/ARCHITECTURE.md`

## Backlog Wiring Rule

Backlog quests should usually link:
- `docs/ARCHITECTURE_INDEX.md`
- `docs/skills/README.md`
- one or two specific architecture docs
- a small set of quest-relevant skills

This keeps each backlog quest grounded in the correct source of truth.