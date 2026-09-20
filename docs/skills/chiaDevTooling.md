# Skill: Chia Dev Tooling

> aWizard's practical reference for the Chia developer docs, debugging tools,
> wallet RPC utilities, packaging infrastructure, and operator workflows that support
> current quests and future backlog work.

---

## Domain

aWizard can guide use of:

- **Developer Guides hub** — where to start and what to read next
- **Tool repos** — what each Chia-maintained utility is good for
- **Wallet and node RPC tooling** — when a synced wallet or full node is required
- **Debugging lineage** — tracing parents, children, and announcements
- **Ops automation** — config-driven database and packaging workflows

## Recommended Reading Order

Use the Chia docs in this order when shaping a new quest or protocol backlog item:

1. `https://docs.chia.net/dev-guides-home/`
   - crash course for state, signatures, inner puzzles, smart coins
2. `https://docs.chia.net/guides/primitives/`
   - NFTs, CATs, offers, DataLayer, clawback, DAOs, VCs, gaming
3. `https://docs.chia.net/guides/tutorials/`
   - simulator, custom puzzles, RPC spend flows, WalletConnect, app structure

This sequence is better than jumping straight into implementation repos with no context.

## Tool Map

### Coinset.org (Hosted Chia RPC API)

Endpoint: `https://api.coinset.org/`
Docs: `https://www.coinset.org/docs`
CLI: `https://github.com/coinset-org/cli`

Purpose:
- free, fast, reliable hosted Chia full-node RPC API
- eliminates the need to run and sync a local full node for mainnet queries
- supports blocks, coins, fees, full-node, mempool, and websocket endpoints
- same RPC shape as a local Chia full node — drop-in replacement for read operations

Available endpoint groups:
- **Blocks** — `get_block`, `get_block_record`, `get_block_spends`, `get_additions_and_removals`, etc.
- **Coins** — coin record lookups, puzzle solutions
- **Fees** — fee estimation
- **Full node** — blockchain state, network info
- **Mempool** — pending transaction inspection
- **WebSocket** — real-time coin and block subscriptions

Use it when:
- querying mainnet coin state, block data, or mempool from a frontend or script
- verifying on-chain pool state without a local full node
- building read-side dashboards, explorers, or monitoring tools
- testing mainnet RPC integration before running own infrastructure

Do not use it for:
- broadcasting spend bundles (use wallet RPC or Sage for signing + broadcast)
- wallet-private operations (coin selection, key management)

### `chia-wallet-sdk`

Purpose:
- lower-level wallet and dApp development SDK for Chia
- useful when a quest needs wallet internals, spend-driver behavior, binding surfaces, or signer logic below the WalletConnect UI layer

Important boundary:
- it is not a prebuilt wallet
- Sage is the more relevant end-user wallet and RPC surface for current Forge quests
- use this SDK as the reference layer when the question is about how Sage likely constructs or signs spends under the hood

Practical value for this repo:
- Rust-first reference for coin interaction and wallet application structure
- WASM / JS / Python binding surface for future tooling experiments
- useful when debugging clear-signing behavior, AggSig handling, coin spend construction, or building a local operator path outside the browser wallet session

Use it when:
- a WalletConnect or Sage flow fails and the next question is about signer internals rather than session plumbing
- a quest needs a non-UI wallet/operator service or local spend-builder reference
- a future project wants more direct wallet logic than CHIP-0002 alone exposes

Do not treat it as:
- the first reference for frontend WalletConnect integration
- a substitute for Sage session behavior or CHIP-0002 method support

For frontend wallet quests, start with `bowAppReference.md`.
For signer or wallet-engine quests, load `chiaWalletSdk.md` and combine it with `chiaPrimitivesPatterns.md` and the Sage repo.

### `chia-toolbox`

Status:
- archived, but still useful as a lightweight reference

Most concrete current value:
- offer operations tooling
- cancel offers by CAT asset ID, NFT launcher ID, or all offers
- wallet RPC pagination via `get_all_offers`
- dry-run support before cancellation

Use it when:
- testing marketplace cleanup flows
- operating a wallet with many pending offers
- building small wallet-ops utilities around existing RPC endpoints

### `coin-tracing-scripts`

Purpose:
- trace direct and indirect coin parents and children by inspecting announcement conditions

What it teaches:
- how `CREATE_COIN_ANNOUNCEMENT` pairs with `ASSERT_COIN_ANNOUNCEMENT`
- how `CREATE_PUZZLE_ANNOUNCEMENT` pairs with `ASSERT_PUZZLE_ANNOUNCEMENT`
- how to reconstruct related spends in the same transaction block
- how to read lineage from actual chain data instead of guessing

Operational constraints:
- requires a synced full node on the same machine
- uses Python condition parsing that is less hardened than the Rust path
- malicious spends may cause excessive memory use, so treat it as a developer/debug tool

Use it when:
- a quest spend has confusing inputs or outputs
- a singleton or CAT unwind needs forensic review
- a contract interaction must be explained coin-by-coin

### `database-manager`

Purpose:
- manage users and databases in a cluster from YAML config

Useful patterns:
- `validate` before `apply`
- `ENV:` prefix expansion for deployment-time secrets
- explicit user/database definitions with config validation
- host restriction defaults that fall back to `localhost`
- separate creation of databases, users, read grants, and write grants

Use it when:
- a quest service needs repeatable database setup
- shared staging/prod access must be auditable
- infra should be config-driven instead of manually clicked together

### `build-wheels`

Purpose:
- automate Python wheel building for `pypi.chia.net`

Useful patterns:
- package build automation in CI
- Windows-aware wheel handling
- consistent release artifact generation for Chia-related Python tooling

Use it when:
- internal scripts need to become maintained packages
- quest tooling must be installed reproducibly across machines

## Working Rules

When using Chia tooling, assume:
- wallet RPC tools need a running synced wallet
- tracing tools need a running synced full node
- Python helpers often pin specific `chia-blockchain` versions
- simulator-first validation is the safest path before testnet or mainnet use
- Coinset's testnet11 API returns `403` to a bare `urllib` request; send a `User-Agent`.
  `chia_rs` 0.27 raises `TypeError: 12` where 0.48 raises
  `ValueError("ValidationError", 12, ...)` — normalise at one funnel, not per suite.

Verification rules that cost a night to learn (2026-09-19/20):
- **Never verify with a flag that disables the check under test.** `curl -k` passed a
  self-signed certificate the webview was failing; every "the lane works" was false.
- **Read the body, not the status.** A `200` was an SPA's `index.html`; a `503` was our
  own wallet probe. Print `head -c 300` and the `Content-Type` before judging a host.
- **`$?` after a pipe is the last stage's exit.** Use `${PIPESTATUS[0]}`.
- **In this Windows workspace `/tmp` is two places** — Git Bash's and what Windows
  Python opens — so a file written by one is missing to the other. Use the project or
  scratchpad directory. And Bash-heredoc Python corrupts backslashes (`\v` in a path
  became a vertical tab, twice): use the Write tool or raw-string files for any patch
  containing one.
- **Check what produced a number before explaining it.** A probe's `--pools` default of 8
  was explained as index drift; a "6-mojo" gap was the whole 0.5% router fee.

## Quick Decision Guide

- Need conceptual grounding: start at the docs hub
- Need asset primitive details: use the primitives index
- Need app flow examples: use the tutorials index
- Need to inspect weird spend relationships: use coin tracing scripts
- Need to cancel or inspect many offers: use `chia-toolbox`
- Need reproducible DB setup: use `database-manager`
- Need repeatable package publishing: use `build-wheels`
- Need mainnet coin/block queries without a local node: use Coinset.org API

## Source References
- `https://www.coinset.org/docs` — hosted Chia RPC API (mainnet)
- `https://github.com/coinset-org/cli` — Coinset CLI utility
- `https://github.com/xch-dev/chia-wallet-sdk`
- `https://github.com/Chia-Network/chia-toolbox`
- `https://github.com/Chia-Network/coin-tracing-scripts`
- `https://github.com/Chia-Network/build-wheels`
- `https://github.com/Chia-Network/database-manager`
- `https://docs.chia.net/dev-guides-home/`
- `https://docs.chia.net/guides/primitives/`
- `https://docs.chia.net/guides/tutorials/`