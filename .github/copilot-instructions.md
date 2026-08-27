# Workspace Copilot Instructions — aWizard Familiar

> Loaded automatically for all Copilot interactions in this workspace.

## Two views of this repo

**In the workspace**, aWizard Familiar is the monorepo and single source of truth: every project
lives under `projects/`, agent skills in `docs/skills/`, test suites in `tests/`, deploy scripts in
`scripts/`.

**On GitHub** ([awizardxch/aWizard-Familiar](https://github.com/awizardxch/aWizard-Familiar)) it is
a **standalone agent repo** — `.github/` (agent, prompts, these instructions), `docs/`,
`docs/skills/`, `.vscode/`, and `README.md`, and nothing else. `projects/`, `tests/`, `scripts/`,
`docs/quests/` and `memories/` are gitignored; project code ships separately to the Forge repo.

**What follows from that:** a skill or doc must carry its knowledge *inline*. A path into
`projects/…` is a pointer for someone with the workspace open, never the place the knowledge
lives — anyone reading the published repo cannot follow it. When a project doc holds something the
agent needs, summarise it into `docs/` (as `docs/FORGE_SECURITY_AUDIT.md` does) rather than
linking out to it.

## Projects (workspace only)

| Folder                                  | Stack                       | Purpose                                          |
| --------------------------------------- | --------------------------- | ------------------------------------------------ |
| `projects/arcane-battle-protocol`       | Chialisp, Python, TS        | Protocol spec, contracts, battle engine          |
| `projects/bow-app`                      | Next.js 16, React 19        | Game client (wallet, battles, NFTs)              |
| `projects/gym-server`                   | Express, SQLite, TS         | PvE gym battle server (port 3001)                |
| `projects/awizard-gui`                  | Vite, React 19, Discord SDK | Discord Activity GUI (The Nightspire)            |
| `projects/awizard-bot`                  | Discord.js, Node            | aWizard Discord bot                              |
| `projects/chia-cfmm` (Forge)            | Vite, React 19, Rue/CLVM    | N-asset weighted CFMM, pool-scoped LP CAT, vaults |
| `projects/chia-treasure-chest`          | Vite, React 19, Rue/CLVM    | On-chain singleton kiosk storefront              |
| `projects/chia-perps` *(planned)*       | Vite, React 19, Rue/CLVM    | On-chain perpetuals exchange (Aftermath equiv.)  |

## Skill routing

Domain knowledge lives in `docs/skills/`. Load **1–2 skills per task**, not the whole library.

- `docs/skills/README.md` — the authoritative routing index, with a reading path per quest type
- `docs/skills/manifest.json` — the same routing, compact, for programmatic lookup

## Coding Conventions

- **TypeScript strict** across all projects. No untyped `any` without explicit `@ts-expect-error`.
- **Tailwind CSS 4** for styling in `bow-app` and `awizard-gui`.
- **Functional React** — hooks only, no class components.
- **Zustand** for client state in React apps.
- File naming: `PascalCase.tsx` for components, `camelCase.ts` for everything else.
- Keep imports explicit — no barrel files / `index.ts` re-exports unless a folder has 5+ modules.
- Chia contracts are written in **Rue** (compiles to CLVM), never Chialisp directly.

## Architecture Awareness

- The **tracker** (Upstash Redis) is accessed via `projects/bow-app`'s API routes at `/api/tracker/`.
- The **gym-server** runs on port 3001 and serves `/gym/*` endpoints.
- The **aWizard bot** lives in `projects/awizard-bot/` — `awizard-gui` connects to it via REST.
- Chia wallet interaction goes through **WalletConnect (CHIP-0002)** and the **Sage** wallet.
- Discord Activity authentication uses the **Embedded App SDK** + OAuth2 token exchange.
- **Forge (chia-cfmm)** ships at **V10**. V4–V9 carry critical authorisation bugs, those pools are
  retired, and superseded revisions must never be re-enabled for creation. See
  `docs/FORGE_PROTOCOL_STATUS.md`.

## Puzzle work is audit work

Any change that touches a CLVM/Rue puzzle, its builders, or its quoting mirrors follows
`docs/skills/clvmPuzzleAudit.md`. The rules that cost real findings:

- **Probe the compiled puzzle, never the source.** Reading it and reasoning produces confident
  wrong answers.
- **Every adversarial probe ships beside its honest case** — a negative probe proves nothing if the
  harness rejects everything, and a failure for the wrong reason (an arity error) looks exactly
  like a fix.
- **A skip that exits 0 is a lie.** Skips exit 2.
- **Never accept an identity from a solution.** A coin announcement keyed on a solution-supplied
  coin id authorises anyone; a satellite coin asserts a *puzzle* announcement rebuilt from its own
  curried launcher id.
- **Duplicated consensus arithmetic diverges.** Pin every mirror to the puzzle's own numbers.
- **The off-chain surface is in scope** — offers are bearer instruments.
- A revision is not done until it has been re-probed: two of ten Forge findings were introduced by
  the fix for an earlier one.

## Documentation

Repo-resident (published, and the agent's own memory):
- `docs/ARCHITECTURE.md` / `docs/ARCHITECTURE_INDEX.md` — ecosystem map and where to look
- `docs/FORGE_PROTOCOL_STATUS.md`, `docs/FORGE_SECURITY_AUDIT.md` — Forge state and findings
- `docs/TODO_DEFI.md`, `docs/TODO_WORLD.md` — phase and quest tracking
- `docs/skills/` — domain knowledge

Workspace only (not published):
- `projects/arcane-battle-protocol/ARCHITECTURE.md` — protocol-level architecture
- `projects/bow-app/STATUS.md` — game client status tracker
- `projects/awizard-gui/docs/` — TODO, IN_DEVELOPMENT, IDEAS, ARCHITECTURE, AWIZARD_AGENT
- `projects/chia-cfmm/docs/` — Forge puzzle reference, full audit log, launch matrix, roadmap

When modifying architecture, update the relevant doc alongside the code change — and if the change
matters to the agent, make sure the durable part lands in `docs/`, which is what actually ships.
