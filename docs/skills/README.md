# Skills Index

This file is the authoritative human-readable routing index for `docs/skills/`.

Use it to decide which 1-3 skills to load for a quest instead of duplicating large skill tables in agent docs.
For compact programmatic routing, see `docs/skills/manifest.json`.

This index maps the skill library in `docs/skills/` to the kinds of work the repo is
actually doing: Chia protocol design, DeFi product work, Nightspire frontend flows,
and quest planning.

Use this file when:
- drafting or refining backlog quests
- choosing which domain docs to read before implementation
- deciding whether a problem is protocol, product, UX, or infrastructure

---

## Fast Paths

### Chia Protocol, Contracts, and Assets

| Skill | Use it for |
| --- | --- |
| `blockchainDecentralization.md` | Core Chia primitives, trustless design, singletons, announcements, learning order |
| `chiaPrimitivesPatterns.md` | Singleton patterns, CAT issuance, CR-CATs, secure-the-bag, asset architecture |
| `chiaWalletSdk.md` | Standard lower-level wallet-engine reference for signer behavior, spend construction, and Sage-under-the-hood work |
| `chiaDevTooling.md` | Chia docs hub, tracing tools, RPC tooling, `chia-wallet-sdk`, and package and ops utilities |
| `chiaPerpetuals.md` | Perps market design, margin, funding, liquidation, oracle architecture |
| `nftRewards.md` | Chia NFT minting patterns, DID/royalties, reward collection design |
| `bondPvpEconomy.md` | Escrow, mutual signing, PvP settlement economics |

### Frontend, Wallet, and User Flows

| Skill | Use it for |
| --- | --- |
| `bowAppReference.md` | WalletConnect, CHIP-0002, state channels, tracker patterns, battle state, multi-address scanning |
| `sageRpc.md` | Sage RPC address derivations, `increase_derivation_index`, gap-limit scan, operator patterns |
| `discordActivityAuth.md` | Discord Activity auth, OAuth2, embedded app flow |
| `networkGameplayUX.md` | Loading states, spell-cast UX, network feedback, multiplayer responsiveness |
| `nightspireTheme.md` | Canonical Nightspire design language, tokens, component styling |
| `projectArchitecture.md` | File placement, naming, boundaries, module organization |
| `deploymentInfra.md` | Vercel/VPS deployment, env boundaries, DB and release tooling |

### Game Systems and World Design

| Skill | Use it for |
| --- | --- |
| `battleKnowledge.md` | Battle flow, turn systems, engine logic |
| `aiSeedModel.md` | Deterministic AI, seeded RNG, fairness model |
| `apsTierSystem.md` | Progression, ranks, unlock thresholds |
| `leaderboardRankings.md` | Ranking logic, score surfaces, trustless record planning |
| `tournamentSystem.md` | Brackets, seeding, prize logic |
| `snesWorldEngine.md` | World navigation, map systems, encounter integration |

### Warp Bridge — Cross-Chain Chia ↔ EVM

| Skill | Use it for |
| --- | --- |
| `warpBridge.md` | Full Chia↔EVM bridge system: offer lifecycle, lockCATs/burnCATs/unlockCATs/mintCATs driver selection, EVM wagmi entry (bridgeToChia/bridgeBack), NOSTR validator signatures, portal singleton mechanics, Goby/Sage/Ozone adapters, key puzzle hashes and contract addresses |

### Puzzle Security and Audit

> Load `clvmPuzzleAudit.md` before reviewing, probing, or revising **any** puzzle in the
> workspace — it is protocol-agnostic and applies to cfmm, vaults, perps, and treasure chest.

| Skill | Use it for |
| --- | --- |
| `clvmPuzzleAudit.md` | How to audit a CLVM/Rue puzzle: probe the compiled hex, the announcement-binding taxonomy (coin vs puzzle), the ten recurring defect classes, harness and bundle-audit shape, test hygiene, the off-chain bearer-instrument surface |

### Forge DeFi Primitives

> Forge-specific knowledge, distinct from generic Chia protocol patterns.
> The first three are current at **V10**, the shipping revision — pre-V10 pools are retired and
> carry critical authorisation bugs. **V11 is evaluated, not decided:** the CHIP-0050 action layer
> is recommended for it on a surface count, pending the owner's confirmation;
> `chip0050ActionLayer.md` carries the count and the candidate design.

| Skill | Use it for |
| --- | --- |
| `chip0050ActionLayer.md` | CHIP-0050 reference (action layer, finalizers, `p2_delegated_by_singleton`, slots, pinned hashes), the V10-versus-V11 exploit-surface count, the V11 candidate design, the multi-reserve finalizer spec, action-layer audit additions, open items |
| `forgePuzzleV10.md` | The shipping puzzle set: coin layout, curried config and state, the bracketed weighted invariant, swap/mint/burn, vaults, reserve and LP authorisation, the four fees, modes, cutting a revision, version history |
| `forgeLpCat.md` | The pool-controlled LP CAT TAIL: the three-part lock (derived action-coin id, pinned mint/melt inners, CAT-parent melt rule), the mutual handshake and message format, genesis trust |
| `forgePoolLifecycleTesting.md` | Lanes and endpoints, the guardrails that must never be bypassed (freshness, snapshot round trip, revision filtering, offer redaction), the suite index and what a green run does not prove |

### External Liquidity and DEX Integrations

| Skill | Use it for |
| --- | --- |
| `chiaDexieRouting.md` | Dexie quote flow, offer submission, route selection, token normalization, external execution boundaries |
| `chiaTibetAmm.md` | Tibet router and pair model, XCH/CAT LP flows, offer-settled swap/add/remove behavior, reserve handling |
| `tibetUiFrontend.md` | Tibet UI repo patterns for pair discovery, request caching, wallet UX, and external route presentation |

### Quest and Planning Workflow

| Skill | Use it for |
| --- | --- |
| `questManagement.md` | Backlog workflow, foundation-first delivery, enhancement quest pattern |

---

## Suggested Reading by Quest Type

### DeFi / Protocol Quest
- `blockchainDecentralization.md`
- `chiaPrimitivesPatterns.md`
- `forgePuzzleV10.md` — if the quest touches the Forge puzzle set
- `chiaDevTooling.md` — only if tooling/Sage internals are in scope
- `deploymentInfra.md` — only if deployment is in scope

### Puzzle Security / Audit Quest
- `clvmPuzzleAudit.md` — load first, always; the method is protocol-agnostic
- `forgePuzzleV10.md` — if the target is a Forge pool
- `forgeLpCat.md` — if the target is LP supply, the TAIL, or either pinned inner
- `forgePoolLifecycleTesting.md` — to know which suite already covers the surface
- `chiaPrimitivesPatterns.md` — only if the quest reaches into singleton or CAT fundamentals

Applies to any puzzle review, not only Forge: reviewing an authorisation path, writing
adversarial probes, cutting a revision, or judging whether a fix actually closed the hole.
Two of the ten Forge findings were **introduced by the fix for an earlier one**, so a
revision is never done until it has been re-probed.

### External Liquidity / Aggregator Quest
- `chiaDexieRouting.md`
- `chiaTibetAmm.md`
- `tibetUiFrontend.md` — only if frontend or wallet UX is in scope
- `forgePuzzleV10.md` — only if local Forge pool behaviour or routing lanes are also in scope

### Wallet / Signing / Multisig Quest
- `bowAppReference.md` — WalletConnect, CHIP-0002, multi-address scanning
- `sageRpc.md` — operator/backend address derivation, gap-limit expansion
- `chiaWalletSdk.md` — only when dropping below the Sage/WC layer into signer behavior

Use `bowAppReference.md` first for all WalletConnect and CHIP-0002 UI flows, including `chip0002_getPublicKeys` multi-address patterns.
Use `sageRpc.md` for backend/operator flows that call Sage RPC directly (`/get_derivations`, `/increase_derivation_index`).
Use `chiaWalletSdk.md` only when the quest requires raw spend construction or wallet engine internals below Sage.
Only add `blockchainDecentralization.md` + `chiaPrimitivesPatterns.md` if the quest also touches protocol design or asset architecture.

Use `chiaDexieRouting.md` when the wallet flow must end in a Chia offer submitted to an external venue.
Use `chiaTibetAmm.md` when comparing Forge pool logic to an existing XCH/CAT AMM implementation on Chia.
Use `tibetUiFrontend.md` when the main problem is external route UX, pair discovery, or frontend request behavior.

### NFT / Rewards / Collections Quest
- `nftRewards.md`
- `blockchainDecentralization.md`
- `chiaPrimitivesPatterns.md`
- `deploymentInfra.md`

### Game / Nightspire Quest
- `battleKnowledge.md`
- `networkGameplayUX.md`
- `nightspireTheme.md`
- `discordActivityAuth.md`

### Warp Bridge / Cross-Chain Quest
- `warpBridge.md` — load first; covers all 4 bridge directions, all 3 wallet adapters, driver selection, NOSTR, EVM contracts
- `chiaPrimitivesPatterns.md` — only if the quest also touches raw Chia singleton or CAT puzzle design
- `bowAppReference.md` — only if the quest also involves WalletConnect state channel or multi-address scanning alongside bridging

### Architecture / Refactor Quest
- `projectArchitecture.md`
- `deploymentInfra.md`
- `bowAppReference.md`

---

## Indexes and Companion Docs

- `docs/ARCHITECTURE_INDEX.md` — where to find the right architecture document
- `docs/ARCHITECTURE.md` — ecosystem-level product and subdomain map
- `docs/QUEST_WORKFLOW.md` — quest lifecycle and backlog movement rules
- `docs/FORGE_PROTOCOL_STATUS.md` — Forge protocol status (V10) and why V4–V9 are unsafe
- `docs/FORGE_SECURITY_AUDIT.md` — the findings log the audit skill generalises from

## Skills Must Stand Alone

This repo publishes standalone: `.github/`, `docs/`, `docs/skills/`, `.vscode/`, `README.md`.
`projects/`, `tests/`, `scripts/`, `docs/quests/` and `memories/` are gitignored and never ship.

A skill therefore carries its knowledge **inline**. A path into `projects/…` is a pointer for
someone with the monorepo open — never the place the knowledge lives. When a project doc holds
something the agent needs, summarise it into `docs/` (as `docs/FORGE_SECURITY_AUDIT.md` does)
instead of linking out to it.

## Backlog Wiring Rule

New backlog quests should include:
- a short `Reference Indexes` section linking this file and `docs/ARCHITECTURE_INDEX.md`
- a short `Relevant Skills` section listing the few skills that matter most for the quest

This keeps planning docs actionable instead of becoming disconnected idea dumps.