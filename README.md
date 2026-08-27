# aWizard Familiar 🧙‍♂️

> **AI agent configuration and domain knowledge hub** for the Chia DeFi ecosystem.

---

## What is aWizard Familiar?

This repository contains the **agent brain** — specialized VS Code agent configuration with deep domain knowledge:

- **🧙 aWizard Agent** — custom VS Code agent mode with 40+ tools
- **📚 Skill Library** — 17+ domain reference docs (blockchain, DeFi, Discord, React, battle systems)
- **📋 Documentation** — Architecture guides, workflows, theme system, deployment maps
- **🎯 Agent Instructions** — Workspace-wide Copilot behavior and mode definitions

---

## Quick Setup

```bash
git clone https://github.com/aWizardxch/aWizard-Familiar.git
cd aWizard-Familiar
code .
```

aWizard agent appears in the VS Code agent dropdown automatically. All domain knowledge is loaded from `docs/skills/`.

---

## What's Included

### Agent Definition
- **`.github/agents/awizard.agent.md`** — custom agent with 43 built-in tools
- **`.github/copilot-instructions.md`** — workspace-wide Copilot behavior

### Skills Library

#### BOW Game
- **`docs/skills/battleKnowledge.md`** — PvE/PvP flows, state channels
- **`docs/skills/apsTierSystem.md`** — scoring, ability unlocks
- **`docs/skills/nftRewards.md`** — soulbound NFT mechanics
- **`docs/skills/aiSeedModel.md`** — deterministic AI, RNG
- **`docs/skills/bondPvpEconomy.md`** — bond escrow, player economy
- **`docs/skills/leaderboardRankings.md`** — on-chain rankings
- **`docs/skills/tournamentSystem.md`** — brackets, matchmaking
- **`docs/skills/discordActivityAuth.md`** — OAuth2, NFT gates
- **`docs/skills/deploymentInfra.md`** — Vercel/VPS architecture
- **`docs/skills/projectArchitecture.md`** — module organization
- **`docs/skills/blockchainDecentralization.md`** — Chia blockchain philosophy
- **`docs/skills/bowAppReference.md`** — WalletConnect/CHIP-0002, multi-address scanning (`chip0002_getPublicKeys`), state channel, battle protocol, Fighter types
- **`docs/skills/snesWorldEngine.md`** — SNES chunk world, biomes, procedural gen, Godot web export
- **`docs/skills/networkGameplayUX.md`** — spell-cast UX, arcane loaders, WebSocket battles, chain tx progress

#### Chia DeFi
- **`docs/skills/chiaPerpetuals.md`** — on-chain CLOB, perpetuals, liquidations, oracles
- **`docs/skills/nightspireTheme.md`** — Nightspire CSS token system, glow classes, shared palette
- **`docs/skills/sageRpc.md`** — Sage Wallet RPC: address derivation, `increase_derivation_index`, multi-address scanning, coin/CAT/NFT/offer operations, operator patterns
- **`docs/skills/chiaWalletSdk.md`** — Lower-level wallet-engine reference: spend construction, AggSig, signer behavior, `chia-wallet-sdk` (the library Sage is built on)
- **`docs/skills/chiaPrimitivesPatterns.md`** — Singleton state machines, CAT issuance, CR-CATs, secure-the-bag distribution
- **`docs/skills/chiaDevTooling.md`** — Chia docs hub, tracing tools, RPC tooling, package and ops utilities
- **`docs/skills/forgePuzzleV10.md`** — Forge's shipping pool puzzle (V10): coin layout, curried config/state, the bracketed weighted invariant, vaults, reserve and LP authorisation, the four fees, cutting a revision
- **`docs/skills/forgeLpCat.md`** — Pool-controlled LP CAT TAIL: the three-part lock (derived action-coin id, pinned mint/melt inners, CAT-parent melt rule) and the mutual handshake
- **`docs/skills/forgePoolLifecycleTesting.md`** — Forge lanes and endpoints, the guardrails that must never be bypassed, the suite index and what a green run does not prove

#### Puzzle Security
- **`docs/skills/clvmPuzzleAudit.md`** — How to audit a CLVM/Rue puzzle: probe the compiled hex, the announcement-binding taxonomy, ten recurring defect classes, harness and bundle-audit shape, test hygiene, the off-chain bearer-instrument surface. Protocol-agnostic — load it for any puzzle review

#### Warp Bridge (Cross-Chain)
- **`docs/skills/warpBridge.md`** — Complete Chia↔EVM bridge system: 4-step wizard, lockCATs/burnCATs/unlockCATs/mintCATs driver selection, EVM wagmi entry (bridgeEtherToChia/bridgeToChia/bridgeBack), all 3 wallet adapters (Sage WC, Ozone WC, Goby extension), NOSTR validator signature collection, portal singleton mechanics, key puzzle hashes, mainnet contract addresses. Source project: `C:\Users\Ricardo\Documents\Web_Connect\warp-ui-love`. Full constants: `warp-ui-love/docs/agent-swarm/IMPLEMENTATION_CONSTANTS.md`

### Architecture & Guides
- **`docs/ARCHITECTURE.md`** — Full ecosystem deployment map
- **`docs/NIGHTSPIRE_THEME.md`** — Nightspire CSS token system for all frontends
- **`docs/AWIZARD_AGENT.md`** — Agent behavior and mode documentation
- **`docs/CODE_AUDIT_REPORT.md`** — Code quality baseline and audit results
- **`docs/FORGE_PROTOCOL_STATUS.md`** — Forge protocol status: V10 shipping, why V4–V9 are unsafe
- **`docs/FORGE_SECURITY_AUDIT.md`** — Forge findings log: ten findings, severity, how each was closed
- **`docs/TODO_DEFI.md`** — DeFi build phases tracking
- **`docs/TODO_WORLD.md`** — World engine development tracking
- **`docs/QUEST_WORKFLOW.md`** — Foundation-First pattern quick reference
- **`docs/skills/questManagement.md`** — Complete quest workflow guide

---

## Using the Agent

aWizard operates as a specialized VS Code agent with deep domain knowledge:

- **aWizard mode** — Project management, architecture enforcement, domain expertise
- Auto-loads skills from `docs/skills/` based on context
- Enforces TypeScript strict, React 19 hooks, Tailwind CSS 4, Zustand for state
- References Nightspire theme tokens and architecture patterns automatically
- Suggests optimal models: **Sonnet 4** for standard work, **Opus** for complex architecture

---

## Philosophy

> Knowledge and power through transparency — security, decentralization, safety, and magic.

aWizard operates on these principles:
- **Build brick-by-brick** — foundation first, always leave the project buildable
- **Transparency breeds trust** — every decision is documented and verifiable
- **What looks magical is rigorous engineering** — the wizard's secret is discipline

---

## License

MIT