# Skill: bow-app Reference — State Channel & Frontend Patterns

> Extracted from the live `bow-app` (Next.js 16) codebase at
> `C:\Users\Ricardo\Documents\discord\bow\bow-app`.
>
> This is the **ground truth** source for WalletConnect/CHIP-0002 integration,
> state channel lifecycle, fighter types, the battle commit-reveal protocol,
> the tracker client, and the Zustand store shape.
>
> When building `awizard-gui` or any Chia frontend, treat these patterns as canonical.

---

## Project Quick Reference

```
bow-app/
  app/
    providers/WalletConnectProvider.tsx  ← CHIP-0002 full integration
    store/bowStore.ts                    ← Zustand: battle, channel, room state
    lib/fighters.ts                      ← Fighter types, damage calc, collections
    lib/tiers.ts                         ← 5 gym tiers with bosses + badge data
    lib/trackerClient.ts                 ← Upstash Redis tracker HTTP client
    gym/page.tsx                         ← Gym challenge flow (announce → poll → channel)
    channel/page.tsx                     ← Channel open: fund coin, sign SpendBundle
    battle/page.tsx                      ← Commit-reveal battle protocol
    lobby/page.tsx                       ← PvP lobby: create/join room, poll tracker
  docs/protocol/                         ← Protocol spec copies
```

---

## 1. WalletConnect / CHIP-0002 Provider

### Environment Variables

```ts
NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID=  // required — from cloud.walletconnect.com
NEXT_PUBLIC_CHIA_CHAIN=chia:testnet11  // or chia:mainnet
```

Both `chia:mainnet` and `chia:testnet11` are always declared in the session request
so Sage can match whichever network the user is running.

### Context Value Shape

```ts
interface WalletConnectContextValue {
  session:        SessionTypes.Struct | null;   // null = disconnected
  pairingUri:     string | null;                // QR-code URI while pairing
  fingerprint:    string | null;                // session-level numeric ID
  walletAddress:  string | null;                // BLS public key hex (stable on-chain identity)
  connect:        () => Promise<void>;
  disconnect:     () => Promise<void>;
  signCoinSpends: (coinSpends: CoinSpend[], partial?: boolean) => Promise<string>;
  sendTransaction:(spendBundle: SpendBundle) => Promise<{ status: string; error?: string }>;
  getAssetCoins:  () => Promise<SpendableCoin[]>;
  getNFTs:        () => Promise<WalletNft[]>;
  isConnecting:   boolean;
  error:          string | null;
}
```

### Key Types

```ts
interface SpendableCoin {
  coin: { parent_coin_info: string; puzzle_hash: string; amount: number };
  coinName: string;       // hex coin ID (no 0x prefix) — sha256(parent+ph+amount)
  puzzle: string;         // puzzle reveal hex
  confirmedBlockIndex: number;
  locked: boolean;
}

interface CoinSpend {
  coin: { parent_coin_info: string; puzzle_hash: string; amount: number };
  puzzle_reveal: string;
  solution: string;
}

interface SpendBundle {
  coin_spends: CoinSpend[];
  aggregated_signature: string;
}

interface WalletNft {
  nftId?:        string;
  launcherId?:   string;
  encodedId?:    string;
  address?:      string;         // bech32m nft1… address
  collectionId?: string;         // col1… on-chain collection ID
  name?:         string;
  attributes?:   { trait_type: string; value: string | number }[];
  imageUri?:     string;
  thumbnailUri?: string;
  metadata?:     Record<string, unknown>;
  [key: string]: unknown;
}
```

### SignClient Init Metadata

```ts
SignClient.init({
  projectId: WC_PROJECT_ID,
  relayUrl:  'wss://relay.walletconnect.org',
  metadata: {
    name:        'Bank of Wizards',
    description: 'Battle of Wizards — StateChannel Chia battles',
    url:         window.location.origin,
    icons:       [`${window.location.origin}/logo.png`],
  },
})
```

### connect() — Session Request

```ts
const { uri, approval } = await client.connect({
  requiredNamespaces: {
    chia: {
      methods: [
        'chip0002_signCoinSpends',
        'chip0002_sendTransaction',
        'chip0002_getAssetCoins',
        'chip0002_getNFTs',
        'chip0002_getPublicKeys',
      ],
      chains:  ['chia:mainnet', 'chia:testnet11'],
      events:  [],
    },
  },
});
if (uri) setPairingUri(uri);    // display QR code
const session = await approval();
```

### signCoinSpends

```ts
const aggregatedSignature = await client.request<string>({
  topic:   session.topic,
  chainId: session.namespaces.chia.chains[0],
  request: {
    method: 'chip0002_signCoinSpends',
    params: { coinSpends, partialSign: false },
  },
});
// Returns BLS aggregated signature hex string only — NOT the full SpendBundle.
// Assemble SpendBundle yourself: { coin_spends, aggregated_signature }
```

### sendTransaction — Status Normalisation ⚠️

```ts
// Sage may return numeric 1 (ok) or string 'SUCCESS' — normalise both:
const ok = result.status === 1 || result.status === 'SUCCESS';
return { status: ok ? 'SUCCESS' : String(result.status), error: result.error };
```

### getNFTs — Two-Method Fallback

```ts
// Try chip0002_getNFTs first (returns full objects with metadata)
// Fallback: chip0002_getAssetCoins with type: 'nft'
const approvedMethods = session.namespaces?.chia?.methods ?? [];
if (approvedMethods.includes('chip0002_getNFTs')) { /* primary path */ }
// else fallback to getAssetCoins(type: 'nft')
```

### Stale Session Cleanup (run on init)

```ts
// Purge expired sessions to prevent relay errors
const staleSessions = c.session.getAll().filter(s => s.expiry <= Date.now() / 1000);
for (const s of staleSessions) {
  c.session.delete(s.topic, { code: 6000, message: 'Session expired' }).catch(() => null);
}
// Also purge stale pairings with no active session
```

### WalletConnect Error Objects ⚠️

WalletConnect throws plain objects, not `Error` instances:
```ts
function wcErr(e: unknown): string {
  if (e instanceof Error) return e.message;
  if (e && typeof e === 'object') {
    const o = e as Record<string, unknown>;
    if (typeof o.message === 'string') return `${o.message}${o.code ? ` (code ${o.code})` : ''}`;
    return JSON.stringify(o);
  }
  return String(e);
}
```

### Multi-Address Scanning via `chip0002_getPublicKeys`

Chia HD wallets derive a fresh address for every receive. A single wallet may hold
coins across 50–200+ derived puzzle hashes. The three patterns below cover the most
common surface area.

#### Key Insight: When Sage aggregates automatically

`chip0002_getAssetCoins` and `chip0002_getNFTs` already aggregate across **all**
synced derived addresses internally — you do NOT need to enumerate addresses for
basic asset queries. Sage handles the scan window for you.

Use `chip0002_getPublicKeys` when you need the actual address list for:
- Displaying a per-address balance breakdown (portfolio view)
- Deriving puzzle hashes to build spends targeting a specific address
- Verifying off-chain that a coin belongs to the connected wallet
- Scanning beyond the wallet's auto-derived window (see gap-limit note)

#### `chip0002_getPublicKeys` — Call Pattern

```ts
// Fetch unhardened derived public keys (returns hex G1 elements, 96 chars each)
// offset + limit walk the derivation path in windows
async function fetchAllWalletKeys(
  client: SignClient,
  session: SessionTypes.Struct,
  windowSize = 20,
): Promise<string[]> {
  const chainId = session.namespaces.chia.chains[0];
  const allKeys: string[] = [];
  let offset = 0;

  while (true) {
    const batch = await client.request<string[]>({
      topic:   session.topic,
      chainId,
      request: {
        method: 'chip0002_getPublicKeys',
        params: { limit: windowSize, offset },
      },
    });
    if (!batch || batch.length === 0) break;
    allKeys.push(...batch);
    if (batch.length < windowSize) break;
    offset += windowSize;
  }
  return allKeys; // ['0xabc...', '0xdef...', …]
}
```

#### Puzzle Hash Derivation from a Public Key (greenwebjs)

```ts
import { fromHex, hash256 } from '@rigidnetwork/clvm-lib';
// Or via greenwebjs StandardPuzzle:
import { Puzzles } from '@greenweb/chia-blockchain-utils';

// Derive the standard p2 puzzle hash for a given G1 public key hex:
function pubkeyToPuzzleHash(pubkeyHex: string): string {
  const puzzles = new Puzzles();
  // stripHex: 0x-prefixed or raw both accepted by greenwebjs
  return puzzles.standardPuzzleHash(pubkeyHex); // returns 0x-prefixed 64-char hex
}

// Batch derivation:
const addressMap = allKeys.map((pk, i) => ({
  index:      i,
  publicKey:  pk,
  puzzleHash: pubkeyToPuzzleHash(pk),
}));
```

#### Gap-Limit Awareness

Chia wallets track a **derivation window** (default ~20 unhardened indices).
If coins were sent to index > window, `getAssetCoins` may miss them until
`increase_derivation_index` is called (Sage RPC — see `sageRpc.md`).

```ts
// Defensive: after session connect, request enough keys to cover expected usage
// 50 keys covers most practical wallets; increase for high-volume users
const keys = await fetchAllWalletKeys(client, session, 50);
// If the wallet returned fewer than requested, the window is auto-capped by Sage
```

#### Identifying Coin Ownership from a Coin Set

```ts
// Given a SpendableCoin, verify it belongs to the connected wallet:
function coinBelongsToWallet(coin: SpendableCoin, knownPuzzleHashes: Set<string>): boolean {
  const ph = coin.coin.puzzle_hash.replace(/^0x/, '').toLowerCase();
  return knownPuzzleHashes.has(ph);
}

// Build the set once after connecting:
const walletKeys   = await fetchAllWalletKeys(client, session);
const puzzleHashes = new Set(walletKeys.map(k => pubkeyToPuzzleHash(k).replace(/^0x/, '').toLowerCase()));
```

#### Context Value Extension (multi-address variant)

```ts
interface WalletConnectContextValue {
  // … existing fields …
  getPublicKeys: (limit?: number, offset?: number) => Promise<string[]>;
  // returns G1 hex array for the given window
}
```

---

## 2. State Channel Lifecycle

> ⚠️ **Not a state channel.** The flow below spends one player's coin back to
> themselves with a REMARK memo. There's no 2-of-2 coin, no unroll and no
> referee, so results can't be disputed on-chain. Treat it as a wager-intent
> marker only. The real channel is upstream `chia-gaming`: see
> `chiaGamingStateChannels.md` and `docs/BOW_GAME_HUB_PLAN.md`.

```
[Lobby] Player announces room → tracker creates RoomRecord (status: pending)
   ↓
[Lobby] Gym server polls tracker → joins room as player2 (status: pending)
   ↓
[Channel] Player fetches spendable XCH coin from wallet via getAssetCoins()
   ↓
[Channel] Builds CLVM standard coin solution with greenwebjs (REMARK + CREATE_COIN)
   ↓
[Channel] signCoinSpends([channelSpend], false) → aggregated BLS signature
   ↓
[Channel] sendTransaction(spendBundle) → broadcasts SpendBundle on-chain
   ↓
[Channel] Derive coinName from Sage → stateChannelCoinId on tracker (status: active)
   ↓
[Battle] Commit-reveal rounds × N (off-chain against gym server)
   ↓
[Channel] Settle / close channel → final SpendBundle → tracker (status: settled)
```

### Channel State (Zustand)

```ts
interface ChannelState {
  channelId:   string | null;
  coinId:      string | null;         // 0x-prefixed coin ID
  partyRole:   'player1' | 'player2' | null;
  isOpen:      boolean;
  wagerAmount: number;                // mojos
}
```

### Building the Channel Open SpendBundle

```ts
// Build standard p2 solution: REMARK (memo) + CREATE_COIN (self, full amount)
// Uses greenwebjs for CLVM encoding
function buildStandardSolution(
  senderPuzzleHashHex: string,
  totalAmount: number,
  memo: string,  // e.g. "BoW open 100mj abc123456789abcd"
): string { /* returns 0x-prefixed hex */ }

// Derive coin ID (client-side, matches Sage's coinName)
async function deriveCoinName(coin: SpendableCoin['coin']): Promise<string> {
  // sha256(parent_coin_info_bytes + puzzle_hash_bytes + amount_be64)
  // returns '0x' + hex
}
```

### Explorer Links

```ts
const EXPLORER_URL = (coinId: string) => {
  const hex = coinId.replace(/^0x/, '');
  const isTestnet = process.env.NEXT_PUBLIC_CHIA_CHAIN === 'chia:testnet11';
  return isTestnet
    ? `https://testnet11.spacescan.io/coin/0x${hex}`
    : `https://xchscan.com/txns/0x${hex}`;
};
```

---

## 3. Battle Commit-Reveal Protocol

### Concept

Both sides hash their chosen move before revealing it — prevents cheating by peeking:
```
Player:   commitHash = sha256(move + ":" + revealKey)   ← unique UUID per battle
GymServer: gymCommitHash = sha256(gym_move + salt)
Both submit hashes → both reveal → server resolves damage
```

### Implementation

```ts
// Commit phase
const revealKey = crypto.randomUUID();  // stable per battle
const commitHash = await sha256hex(`${selectedMove}:${revealKey}`);
// POST /gym/round/commit  { roomId, commitHash }
// Server returns: { gymCommitHash, taunt? }

// Reveal phase
// POST /gym/round/reveal  { roomId, move, salt: revealKey }
// Server returns: { gymMove, playerDmg, gymDmg, playerHp, gymHp, gameOver, winner }
```

### Battle State Machine

```
status: 'idle'   → battle starts
status: 'commit' → waiting for player to commit a move hash
status: 'reveal' → hash submitted, waiting to reveal
status: 'settle' → battle over, channel needs closing
status: 'done'   → winner determined
```

`have_potato` = `true` means it is your turn (you hold the "potato").

### Moves & Damage Matrix

```ts
type MoveKind = 'SCRATCH' | 'EMBER' | 'BUBBLE' | 'VINE' | 'THUNDER' | 'SHADOW' | 'BLIZZARD' | 'SHIELD' | null;

const MOVES = [
  { kind: 'SCRATCH',  label: 'Arcane Strike', type: 'Arcane',   baseDmg: 10 },
  { kind: 'EMBER',    label: 'Fireball',      type: 'Fire',     baseDmg: 20 },
  { kind: 'BUBBLE',   label: 'Frost Wave',    type: 'Water',    baseDmg: 15 },
  { kind: 'VINE',     label: 'Vine Snare',    type: 'Nature',   baseDmg: 15 },
  { kind: 'THUNDER',  label: 'Thunder Hex',   type: 'Electric', baseDmg: 18 },
  { kind: 'SHADOW',   label: 'Void Strike',   type: 'Shadow',   baseDmg: 20 },
  { kind: 'BLIZZARD', label: 'Blizzard',      type: 'Ice',      baseDmg: 15 },
  { kind: 'SHIELD',   label: 'Divine Shield', type: 'Holy',     baseDmg: 0  },
];

// DAMAGE[attackerMove][defenderMove] = base damage dealt
// SHIELD blocks everything (attacker does 0 vs SHIELD; SHIELD deals 0)
// Type matchups: EMBER beats VINE/BLIZZARD (25), BUBBLE beats EMBER/THUNDER (25), etc.
```

### Draw Condition

Both HP → 0 simultaneously = **draw** — both HP reset to max for a rematch round. The round counter increments and status returns to `'commit'` without ending the battle.

---

## 4. Fighter System

### Core Types

```ts
interface FighterStats {
  hp:  number;  // e.g. 90
  atk: number;  // attack modifier
  def: number;  // defense modifier
  spd: number;  // speed (determines turn priority)
}

type ElementType =
  | 'Spirit' | 'Exile' | 'Nature' | 'Fire'
  | 'Water' | 'Electric' | 'Shadow' | 'Ice'
  | 'Corruption' | 'None';

type RarityTier = 'Common' | 'Uncommon' | 'Rare' | 'Legendary';

interface Fighter {
  source:       'user' | 'nft';
  name:         string;
  stats:        FighterStats;
  strength:     ElementType;   // deals bonus damage vs matching weakness
  weakness:     ElementType;   // takes bonus damage from matching strength
  rarity:       RarityTier;
  effect?:      string;        // special ability text from NFT metadata
  faction?:     string;
  nftId?:       string;
  collectionId?: string;
  imageUri?:    string;
}

const DEFAULT_FIGHTER: Fighter = {
  source: 'user', name: 'Wizard',
  stats: { hp: 100, atk: 15, def: 10, spd: 10 },
  strength: 'None', weakness: 'None', rarity: 'Common',
};
```

### NFT-to-Fighter Trait Mapping

```ts
interface TraitMapping {
  hp: string; atk: string; def: string; spd: string;
  strength: string; weakness: string; rarity: string;
  effect?: string; faction?: string; name?: string;
}

interface ApprovedCollection {
  collectionId: string;
  name:         string;
  traitMapping: TraitMapping;
  statCaps?:    Partial<FighterStats>;  // prevent overpowered NFTs
  minRarity?:   RarityTier;
}
// APPROVED_COLLECTIONS is the registry — only listed collections are usable as fighters.
```

### calculateFighterDamage

```ts
// From bow-app/app/lib/fighters.ts
// Takes base damage from the damage matrix + fighter stats + elemental matchup
// Returns final integer damage after ATK/DEF modifiers and strength/weakness bonus
calculateFighterDamage(baseDmg: number, attacker: Fighter, defender: Fighter): number
```

---

## 5. Tier System

Five tiers with static fallback data (used when gym server is unreachable):

| Tier | Name | Boss | AI Difficulty | Badge |
|------|------|------|--------------|-------|
| 1 | Apprentice | Grimshaw the Flicker | easy | Apprentice Badge |
| 2 | Adept | Vyrenna Shadowveil | medium | Adept Badge |
| 3 | Master | Thalrok Ironhex | hard | Master Badge |
| 4 | Archmage | Xelaris the Unbound | brutal | Archmage Badge |
| 5 | Overlord | Malachar, the Ashen King | nightmare | Overlord Badge |

```ts
interface TierInfo {
  tier:          number;
  name:          string;
  title:         string;
  bossName:      string;
  description:   string;
  requiredBadge: string | null;       // null = no prerequisite (tier 1)
  bossStats:     FighterStats;
  bossStrength:  string;
  bossWeakness:  string;
  bossRarity:    string;
  bossEffect?:   string;              // special ability (tiers 4–5)
  playerStatCaps: FighterStats;       // max allowed player stats for this tier
  aiDifficulty:  string;
  badge:         { name: string; tier: number; imageUri: string; description: string };
  color:         string;              // Tailwind gradient class
  emoji:         string;
}

function getTierInfo(tier: number): TierInfo | undefined
```

**Badge progression** — each tier requires the previous tier's badge. Player must have `'tier-N-badge'` to challenge tier `N+1`.

---

## 6. Tracker Client

### Room Record

```ts
interface RoomRecord {
  id:                   string;
  ownerFingerprint:     string;
  name?:                string;
  wagerAmount:          number;               // mojos
  stateChannelCoinId:   string | null;        // on-chain coin ID once funded
  stateChannelStatus:   'pending' | 'locked' | 'active' | 'settling' | 'settled' | 'cancelled';
  player1Fingerprint:   string | null;
  player2Fingerprint:   string | null;        // 'GYM-BOSS-0001' for gym battles
  player1Balance:       number;
  player2Balance:       number;
  totalLockedAmount:    number;
  updatedAt:            number;               // unix ms
  _source?:             'own' | 'crate.ink'; // set server-side by proxy
}
```

### Battle Record

```ts
interface BattleRecord {
  id:                   string;
  playerFingerprint:    string;
  opponentFingerprint:  string;               // 'GYM-BOSS-0001' for gym
  opponentType:         'gym' | 'pvp';
  result:               'win' | 'loss' | 'draw' | 'forfeit';
  playerPokemonId:      number;
  wagerAmount:          number;
  playerHpFinal:        number;
  opponentHpFinal:      number;
  settleTxId:           string | null;        // on-chain tx hash
  settledAt:            number;               // unix ms
}
```

### TrackerClient Usage

```ts
const trackerClient = new TrackerClient('/api/tracker');  // always use Next.js proxy path

// Announce / update a room
await trackerClient.announceRoom({ ownerFingerprint, wagerAmount, stateChannelStatus: 'pending' });

// List open rooms (optionally filtered)
const rooms = await trackerClient.listRooms({ stateChannelStatus: 'pending', minWager: 100 });

// Record battle result
await trackerClient.recordBattle({ playerFingerprint, opponentFingerprint, opponentType: 'gym', result: 'win', ... });

// Get battle history
const history = await trackerClient.getHistory(fingerprint, 20);
```

**Always proxy through `/api/tracker`** — avoids CORS and keeps server credentials out of the browser.

---

## 7. Zustand Store (`bowStore`)

```ts
// Full persisted shape
interface BowStore {
  walletFingerprint: string | null;      // from WC session
  currentRoom:       RoomRecord | null;  // active lobby/gym room
  channel:           ChannelState;       // open state channel
  battle:            BattleState | null; // active battle
  testMode:          boolean;            // practice mode (no wallet)
  selectedFighter:   Fighter | null;     // persisted NFT fighter choice
  selectedTier:      number;             // 1–5
  activePage:        string;             // for nav highlighting
}
```

### BattleState Full Shape

```ts
interface BattleState {
  channel_id:                   string;
  player_hp:                    number;
  gym_hp:                       number;
  current_state_number:         number;       // increments each half-round
  have_potato:                  boolean;      // true = your turn
  wager_amount:                 number;       // mojos
  player_allocated_balance:     number;
  opponent_allocated_balance:   number;
  player_out_of_game_balance:   number;
  opponent_out_of_game_balance: number;
  live_games:                   LiveGame[];
  committed_move_hash:          string | null;
  revealed_move:                MoveKind;
  opponent_move:                MoveKind;
  round_number:                 number;
  status:                       'idle' | 'commit' | 'reveal' | 'settle' | 'done';
  opponentType:                 'local' | 'gym' | 'pvp';
  playerPokemonId:              number;       // freezes at battle start
  playerFighter?:               Fighter;      // snapshot — stable across reloads
  gymFighter?:                  Fighter;
  tier?:                        number;
  bossName?:                    string;
  aiGreeting?:                  string;       // AI-generated boss intro
  aiTaunt?:                     string;
}
```

**Persistence** — `persist` middleware saves: `walletFingerprint`, `channel`, `activePage`, `battle`, `currentRoom`, `selectedFighter`, `selectedTier` to localStorage under key `'bow-store'`.

---

## 8. Gym Challenge Flow

```ts
// 1. Announce room to tracker (player1 = challenger)
const room = await trackerClient.announceRoom({
  ownerFingerprint:   fingerprint,
  name:               `[GYM] ${fingerprint.slice(0, 8)}'s challenge`,
  wagerAmount:        wagerMojos,
  stateChannelStatus: 'pending',
});
setCurrentRoom(room);

// 2. Poll tracker every 3s for gym server to join (player2 = 'GYM-BOSS-0001')
const iv = setInterval(async () => {
  const rooms = await trackerClient.listRooms();
  const found = rooms.find(r => r.id === room.id);
  if (found?.player2Fingerprint === 'GYM-BOSS-0001') {
    clearInterval(iv);
    setCurrentRoom(found);
    router.push('/channel');
  }
}, 3_000);

// Timeout after 30s if gym server doesn't respond
setTimeout(() => { clearInterval(iv); setError('Gym server unreachable'); }, 30_000);
```

---

## 9. Test / Practice Mode

Any page can be reached without a wallet via `testMode = true`:

```ts
const handleTestBattle = () => {
  setTestMode(true);
  setBattle({
    channel_id:    'test-gym-' + Date.now(),
    player_hp:     activeFighter.stats.hp,
    gym_hp:        gymBoss.stats.hp,
    opponentType:  'local',             // uses client-side random AI, no server
    status:        'commit',
    have_potato:   true,
    wager_amount:  0,
    // …zero-out all balance fields
  });
  router.push('/battle');
};
```

`opponentType: 'local'` uses the DAMAGE matrix + random AI client-side — no gym server or wallet needed.

---

## 10. Key Gotchas & Lessons Learned

| Issue | Fix |
|-------|-----|
| Sage `sendTransaction` returns `{ status: 1 }` not `"SUCCESS"` | Normalise: `ok = status === 1 \|\| status === 'SUCCESS'` |
| `chip0002_getPublicKeys` not in session methods → crashes | Guard with `approvedMethods.includes(...)` before calling |
| `chip0002_getNFTs` missing on older Sage → silent failure | Two-method fallback: try `getNFTs` → catch → `getAssetCoins(type: 'nft')` |
| WalletConnect throws `{ code, message }` objects not `Error` | Use `wcErr(e)` helper to stringify safely |
| Stale WC sessions + pairings → relay console spam | Purge expired sessions/pairings on `SignClient.init()` |
| Coin ID mismatch between client and Sage | Use `realCoin.coinName` from `getAssetCoins()` — it IS the coin ID |
| State channel coin ID needs `0x` prefix for explorer links | Always prefix: `'0x' + coinName` |
| Fighter snapshots must be frozen at battle start | Store `playerFighter` + `gymFighter` in `BattleState` — never recompute mid-battle |
| Tracker `503` when no URL configured | Treat same as empty list — not a hard error |
| PvP commit: sign mock state coin spend to simulate off-chain step | Use `signCoinSpends([stateCoinSpend], true)` with `partialSign: true` |

---

## Source References

- `bow-app/app/providers/WalletConnectProvider.tsx` — full CHIP-0002 implementation
- `bow-app/app/store/bowStore.ts` — Zustand store with all battle/channel/room state
- `bow-app/app/lib/fighters.ts` — Fighter types, approved collections, damage calc
- `bow-app/app/lib/tiers.ts` — 5-tier system with boss data and badge definitions
- `bow-app/app/lib/trackerClient.ts` — Redis tracker HTTP client class
- `bow-app/app/channel/page.tsx` — SpendBundle assembly, channel fund/settle flow
- `bow-app/app/battle/page.tsx` — commit-reveal protocol, damage matrix, move types
- `bow-app/app/gym/page.tsx` — gym announce + poll flow
- `bow-app/STATUS.md` — current working features and known issues
