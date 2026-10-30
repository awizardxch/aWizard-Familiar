# Skill: Chia Gaming State Channels (upstream `Chia-Network/chia-gaming`)

> The state channel puzzles, peer protocol and hub model the BOW hub builds on.
> Upstream is the source of truth; this file pins the revision we target and
> records what it guarantees. Load it before touching any channel, referee, hub
> or game code. Pair with `clvmPuzzleAudit.md` for any puzzle review.

---

## Pinned revision

| Field | Value |
| --- | --- |
| Repo | https://github.com/Chia-Network/chia-gaming (Apache-2.0) |
| Commit | `76f0fb8c646e7030c43d2f0a89dd4743445c173b` (main, 2026-10-30) |
| Last referee/unroll change | `9c3bde28` 2026-10-23 |
| Last game-puzzle change | `0a5c8b4f` 2026-10-23 |
| Chialisp dialect | `cl-26` (`(include *standard-cl-26*)`) |
| Compiler / VM | `chialisp = 0.6.0`, `clvmr = =0.21.0` (from `Cargo.toml`) |
| Status | Upstream calls it **early beta**, with unreleased app-owned formats that may change without migration |

Source sha256 at the pin (these are hashes of the `.clsp` files, not puzzle hashes):

| File | sha256 |
| --- | --- |
| `clsp/referee/onchain/referee.clsp` | `849aacffa044256b4aac90b086e7d7b05af60abc3fd5e47db357b33935bb42ab` |
| `clsp/referee/onchain/shapes.clinc` | `04fcc17173e503a069ed9d6e3f1cb834e72f572be40a3c9be618a21089c10eb4` |
| `clsp/unroll/unroll_puzzle.clsp` | `af05f136e9a1c1bb7fa4bb8585bd3c334b9a9594ab21304f4f7f9df5d87ebecf` |

**Puzzle hashes are not recorded yet.** The `.hex` files are build output
(gitignored upstream) and come from `build.rs` through `chialisp.toml`. Fill
these in from a trusted build machine, then copy them into this table:

```bash
git clone https://github.com/Chia-Network/chia-gaming && cd chia-gaming
git checkout 76f0fb8c646e7030c43d2f0a89dd4743445c173b
sha256sum clsp/referee/onchain/referee.clsp clsp/unroll/unroll_puzzle.clsp  # must match the table
cargo build                                   # build.rs compiles chialisp.toml → *.hex
# then take the tree hash of each compiled program (e.g. `opc -H` or chia-wallet-sdk's tree_hash)
```

### Re-pinning

1. `git log --format='%h %cs %s' -- clsp/referee clsp/unroll games/*/clsp` since the pin.
2. Read every commit that touches `clsp/`. Referee changes alter the puzzle hash
   and break channels opened under the old one. Never re-pin while a channel is open.
3. Update the table above, the hashes, and `docs/BOW_GAME_HUB_PLAN.md`.

### Recent puzzle changes (Oct 2026), so we know what "latest" means

- `167f2b36`: the referee slash path now **rejects non-nil atom validator results**.
  Older pins accepted malformed validator output on slash. This is a security fix,
  and the main reason not to stay on an older revision.
- `aac6e825`: every source and test moved to `cl-26`.
- `b1a51631`, `3969177a`, `c08ee583`, `9c3bde28`: on-chain records are now
  **shapes** (`defun-shape`, `make`, `pack`, `if-shape`, `get-field`; see
  `clsp/std/shapes.md`). Referee dispatch was simplified, and the shared
  referee/game shapes live in `clsp/referee/onchain/shapes.clinc`. A game
  validator written against the old positional layout **will not line up**.

---

## Coin hierarchy

```
Funding coins (one per player)
  ├── receiver offer  → settlement → one-time pre-launcher → zero-value singleton launcher
  ├── initiator offer → settlement → contribution coin (asserts launcher announcement)
  └──────────────────────────────▶ Channel coin  (2-of-2 aggregate sig)
                                       │ spend to unroll
                                       ▼
                                   Unroll coin   (unroll_puzzle.clsp)
                                       │ timeout / preemption
                             ┌─────────┴─────────┐
                             ▼                   ▼
                       Reward coins        Game coins (referee.clsp)
                                                 │ move / timeout / slash
                                                 ▼
                                      next game coin or payouts
```

- **Channel coin**: child of a standard singleton launcher. It is 2-of-2, so
  neither player spends it alone. CHIP-25 messages bind both wallet spends.
  A clean shutdown spends it directly to payouts.
- **Unroll coin**: curried `SHARED_PUBKEY`, `OLD_SEQUENCE_NUMBER` and
  `DEFAULT_CONDITIONS_HASH`. If the solution's `shatree` matches the default
  hash, the coin pays out to the last agreed state after `ASSERT_HEIGHT_RELATIVE`.
  If it doesn't match, it is a *preemption*: the spender shows a higher
  sequence number with the correct parity.
- **Referee coin**: one per live game. It adjudicates two-player turn-based
  play. Its curried args form a balanced tree (every field at most four edges
  deep). It has three actions:
  - **timeout**: the mover gets `MOVER_SHARE`, the waiter gets the rest, each
    behind `AGG_SIG_UNSAFE`.
  - **move**: advance the game.
  - **slash**: run the previous validator against the claimed move. The slash
    succeeds if the validator returns nil, if its returned
    `(next_validator_hash, new_state, max_move_size)` doesn't match the coin's
    commitments, or if it matches but returns extra conditions (a conditional
    slash).
  - `INFOHASH = sha256(validation_program_hash, shatree(state))`. `NONCE`
    prevents replay.

Detail lives upstream in `ON_CHAIN.md` (dispute path: unroll → preempt or wait →
forward-align → redo → timeout) and `INTERNALS.md`.

## Potato protocol (off-chain)

- The **potato** is the turn token. Only its holder may propose a game,
  accept or cancel a proposal, move, accept settlement, or start shutdown.
  Anyone else must request it first.
- Every pass is one `PeerMessage::Batch` that carries `actions[]` (`Propose`,
  `AcceptProposal`, `CancelProposal`, `Move`, `AcceptSettlement`) and two
  half-signatures over the resulting state: one for the channel-coin spend to
  the new unroll coin, and one for preempting a stale unroll coin.
- The upshot: after every pass, each side holds a fully co-signed latest state
  and can unroll on-chain without the other side's help.

## Hub model (what "host / join" means upstream)

- A **hub** is one server with two WebSocket channels: a matchmaking channel
  (player list and challenges) and a game relay channel (a dumb pipe for peer
  frames, encoded in Bencodex).
- A player is on **zero or one hub at a time**. Peers only talk through a hub
  (no WebRTC yet). The hub never sees keys and never signs anything.
- Hub connectivity is **independent of wallet connectivity**. Losing the wallet
  must never drop the hub.
- Matchmaking messages:
  - `join` / `leave`
  - `challenge {target_id, challenger_amount, target_amount, channel_timeout?, unroll_timeout?}`
  - `challenge_accept` / `challenge_decline` / `challenge_cancel`
  - alias messages and `keepalive`
- Relay messages:
  - `identify {session_id, busy, reasons}`, `set_busy`, `relay {to, payload}` and `close`
  - Outbound from the hub: `registered`, `advisory_start`, `delivery_failure`,
    `peer_available`, `peer_unavailable` and `alias_updated`
- Run it with `hub --self <own-url> --dir <serve-directory>` (`hub/hub-service`).
  The UI is `hub/hub-frontend`, and games load into it as iframes (`iframeAuth.ts`).
- Wire specs: `WEBSOCKET_PROTOCOL.md`, `PEER_PROTOCOL.md`, `CONNECTIVITY.md`.

## Games

`games/registry.json` → production: `calpoker`, `spacepoker`, `krunk`; test: `debug`.

Each game has three parts:

- `clsp/`: a factory, a factory probe, and on-chain validators
- `rust/`: the handler
- `ui/`: a React UI against the `games/host` API (`HandProposal`,
  `ProposalParameterCodec`, `GameIntent`, `SettlementOutcome`)

To add a game, follow upstream `GAME_WRITING_GUIDE.md` (register, CLVM rules,
factory probe, proposal codec, hand instance, play UI, import boundaries,
testing checklist).

## How this differs from the current BOW "channel"

The flow in `bowAppReference.md` §2 is **not a state channel**. One player
spends their own coin back to themselves with a `REMARK` memo. There is no
2-of-2 coin, no unroll, and no referee, so the gym server's result is final
and cannot be disputed on-chain. Treat that flow as a wager-intent marker
only. Any PvP wager must move to the upstream channel before real value is at
stake.

## Guardrails

- Never fork or patch `referee.clsp` or `unroll_puzzle.clsp` locally. A changed
  puzzle hash means our channels can't interoperate with any other hub, and
  the change goes unreviewed. Push changes upstream instead.
- Never advertise mainnet wagers while upstream is in early beta.
- Pin by commit, verify the source hashes, and record the puzzle hashes. Never
  build from `main` at deploy time.
- A hub relays and never holds keys. Don't add server-side signing to the hub.
