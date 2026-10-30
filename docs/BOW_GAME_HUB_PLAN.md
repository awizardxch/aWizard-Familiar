# BOW as a Chia Gaming Hub — Plan

> Status: **plan, not started in code.** The bow-app source is not on GitHub yet
> (it lives at `C:\Users\Ricardo\Documents\discord\bow\bow-app`). Push it to a
> repo first, then work through these phases there.
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
- [ ] Push bow-app (and the awizard-gui Discord Activity, if it's separate) to GitHub.
- [ ] Build the pinned chia-gaming on a trusted machine. Record the referee and
      unroll puzzle hashes in `chiaGamingStateChannels.md`.
- [ ] Get the upstream simulator tests passing locally (`SIMULATOR_TESTING.md`).

### Phase 1: Retire the fake channel
- [ ] Relabel the current `/channel` flow (REMARK + CREATE_COIN to self) as a
      "wager intent". It is not a channel, so it must not hold an opponent's funds.
- [ ] Gate PvP wagers off until Phase 3 lands. PvE gym battles can stay as they are.

### Phase 2: Run a BOW hub
- [ ] Deploy `hub/hub-service` (Node, Express plus two WebSocket servers) next
      to the gym server: `hub --self https://hub.awizard.dev --dir <hub-frontend build>`.
- [ ] Map the hub's WebSocket paths in the Discord Developer Portal (Activity
      URL mappings) so the Activity can reach them through Discord's proxy.
- [ ] Map Discord identity to the hub `alias` only. The hub `id` and `session_id`
      stay hub-generated, because routing IDs must not be rebound without peer auth.

### Phase 3: Embed the game client in BOW
- [ ] Vendor `front-end` + `wasm` + `games/{calpoker,spacepoker,krunk}` at the pinned
      commit (a git submodule or a build-time fetch by commit, never `main`).
- [ ] Replace `lobbyStore`'s Redis lobbies with a hub client (`useHubSocket`
      pattern). Keep the Redis tracker for stats and leaderboards only.
- [ ] Wire BOW's existing WalletConnect / CHIP-0002 provider into the
      chia-gaming wallet layer. Keep hub and wallet connectivity independent
      (`CONNECTIVITY.md` cascade rules).
- [ ] Add a hub picker: the BOW hub by default, plus user-added upstream hub URLs.
- [ ] Map upstream `SettlementOutcome` values to BOW's arcane loaders and toasts
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
