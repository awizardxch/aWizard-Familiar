# Skill: Battle Knowledge

> aWizard's understanding of the Arcane BOW battle system — PvE gym battles, PvP duels, state channels, and the battle engine.

---

## Domain

aWizard can explain, troubleshoot, and guide development around:

- **Gym Agent (PvE)** — full flow from challenge to settlement
- **PvP Agent** — player-vs-player battles with bond staking
- **State Channels** — off-chain turn resolution, open/update/close lifecycle
- **Battle Engine** — deterministic turn resolution, damage calculation, win conditions

## Key Concepts

### PvE Battle Flow
```
Player challenges Gym → AI seed generated → state channel opens
→ turns resolved off-chain (max 20) → winner determined
→ channel closed → on-chain settlement → APS updated → NFT minted/upgraded
```

### PvP Battle Flow
```
Player A proposes + bond terms → Player B accepts & signs
→ bond locked on-chain → state channel opens
→ both players submit signed actions each turn → winner determined
→ bond released to winner → APS updated for both
```

### State Channel Lifecycle

> On-chain channels use upstream `chia-gaming` (channel coin → unroll → referee),
> pinned in `chiaGamingStateChannels.md`. The sketch below is the game-level view only.
```
open_channel() → update_state(turn) × N → close_channel(final_state)
```

State must be: **deterministic, hashable, signable**

### State Object
```json
{
  "channel_id": "string",
  "player_wallet": "string",
  "gym_wallet": "string",
  "player_hp": 100,
  "gym_hp": 100,
  "turn_counter": 0,
  "last_action": "string",
  "result_hash": "string",
  "winner": null,
  "signatures": { "player": "string", "gym": "string" }
}
```

## Source References
- `arcane-battle-protocol/gyms/arcane-bow/gym_agent.md` — PvE orchestration
- `arcane-battle-protocol/pvp/pvp_agent.md` — PvP orchestration
- `arcane-battle-protocol/ARCHITECTURE.md` — system overview
- `gym-server/src/battle.ts` — battle engine implementation
