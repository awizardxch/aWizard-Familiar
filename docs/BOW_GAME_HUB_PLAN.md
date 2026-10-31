# BOW as a Chia Gaming Hub — Plan

> **BOW is The Nightspire** ([awizardxch/The-Nightspire](https://github.com/awizardxch/The-Nightspire)).
> The separate `bow-app` is retired. The hub work lives there: the Games tab,
> the patched chia-gaming client build (`game-client/`) and its docs
> (`docs/GAME_HUB.md`). Merged to `main` in PR #1.
>
> Reference skill: `docs/skills/chiaGamingStateChannels.md`, which pins
> `Chia-Network/chia-gaming@76f0fb8c`.

## Decisions taken

| Question | Decision |
| --- | --- |
| State channel puzzles | Use upstream `chia-gaming` **unmodified**, pinned by commit. No local referee or unroll fork. |
| Hub model | **Upstream-compatible hub.** BOW runs `hub-service` with the upstream protocol, so any compatible client or hub frontend can host or join there, and BOW players can take their wallet to any other upstream hub. No federated relay between hubs: upstream allows zero or one hub per player, and federation would need a new protocol. |
| First games | Upstream production set: **Calpoker, Spacepoker, Krunk** (`games/registry.json`), plus **Love Slots** (`docs/slots/LOVE_SLOTS_SPEC.md`) as an on-chain tile. |
| BOW battles | **Paused** until a later date. No battle port, and no Fighter tie-ins in other games. |
| Later | Port Chellyz as a chia-gaming game (`GAME_WRITING_GUIDE.md`). Not in this plan. |

## What "join or host across hubs" means under this model

- **Host**: a player in the BOW hub's lobby issues a `challenge` with stakes
  and timeouts. Anyone in that lobby can accept.
- **Join**: the player picks a challenge from the lobby of whichever hub they
  are connected to.
- **Other hubs**: the BOW client keeps a hub list (BOW plus any community
  upstream hub URLs). Switching hubs leaves the wallet connected, and channels
  are hub-independent at the puzzle level, because every hub runs the same
  pinned referee. Players on two different hubs cannot match each other until
  one of them switches.

## Phases

### Phase 0: Prerequisites
- [x] BOW code on GitHub: The Nightspire is the BOW project.
- [ ] Build the pinned chia-gaming on a trusted machine. Record the referee and
      unroll puzzle hashes in `chiaGamingStateChannels.md`.
- [ ] Get the upstream simulator tests passing locally (`SIMULATOR_TESTING.md`).

### Phase 1: Retire the fake channel
- [x] Battles paused: the Battle tab is out of The Nightspire's nav, so its PvP
      "channel" (REMARK + CREATE_COIN to self) is no longer reachable there.
- [ ] Chellyz still uses `stateChannel.ts` / `channelOpen.ts`. Port it to a
      chia-gaming game rather than extending them; until then it must not hold
      an opponent's funds.

### Phase 2: Run a BOW hub
- [ ] Deploy `hub/hub-service` (Node, Express plus two WebSocket servers) next
      to the gym server: `hub --self https://hub.awizard.dev --dir <hub-frontend build>`.
- [ ] Map the hub's WebSocket paths in the Discord Developer Portal (Activity
      URL mappings) so the Activity can reach them through Discord's proxy.
- [ ] Map Discord identity to the hub `alias` only. The hub `id` and `session_id`
      stay hub-generated, because routing IDs must not be rebound without peer auth.

### Phase 3: Embed the game client in The Nightspire
Changed from the original plan: rather than vendoring the client into BOW and
rewiring BOW's wallet into it, The Nightspire embeds the upstream client (which
owns its wallet, channel engine, lobby and relay) and carries one patch.
- [x] Games tab with game catalog and hub picker (BOW hub default, user-added hubs on the web).
- [x] Client built at the pinned commit by `game-client/build.sh`, never from `main`.
- [x] Client patch: hubs under a path (needed for Discord URL mappings) and
      `?hub=` prefill. Tested behind a prefix-stripping proxy (`game-client/e2e/run.sh`).
- [ ] GitHub Actions build of the client and hub (in progress).
- [ ] Client's WalletConnect relay inside Discord (same rewrite as The Nightspire's `index.html`).
- [ ] Map upstream `SettlementOutcome` values to arcane loaders and toasts
      (`networkGameplayUX.md`).

### Phase 4: Testnet
- [ ] testnet11 only. Play each game to clean shutdown, timeout, and slash in
      the simulator, then on testnet11.
- [ ] Interop check: a BOW client on the BOW hub plays a stock upstream
      client on the same hub.
- [ ] Interop check: a BOW client on a stock upstream hub.

### Phase 5: Mainnet gate
- [ ] Upstream leaves early beta, or we accept the risk in writing.
- [ ] Puzzle hashes re-verified against the pin. `clvmPuzzleAudit.md` pass on the referee and each game's validators.

## Risks to check early

- **Discord and wagering.** Discord's policy bans wagering anything of
  real-world value, including virtual currency with a market value. The
  Discord UI therefore wagers only a dedicated no-value game CAT (LOVE is a
  stand-in during development). The token must not be buyable, sellable or
  redeemable, so no DEX pools and no swaps; if that changes, the Discord
  build drops wagering. The web UI runs the same games.
- **Nested iframes.** Discord Activities already run in an iframe, and the
  upstream hub frontend loads games in iframes too. Check the CSP and
  `postMessage` origins inside Discord before building on this.
- **WebSocket through the Discord proxy.** Check that the relay's binary Bencodex
  frames survive Discord's URL mappings.
- **Format churn.** Upstream says unreleased app-owned formats can change
  without migration. Pin, and never upgrade with live channels.
- **Puzzle drift.** If either peer runs a different pin, the referee hashes
  won't match and the channel can't open. Show the pinned commit in the UI and
  in the hub's `registered` metadata.
