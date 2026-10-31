# Love Slots — Design Spec (draft)

> A decentralized, provably fair 5-reel video slot. Spins are instant hands in a
> Chia state channel between the player and a Bank. Jackpots come from the
> **Love Draw**, an on-chain draw decided by the drand public beacon, so nobody,
> the Bank included, can steer money that belongs to other players. Anyone can
> run a Bank, and jackpot pools are shared across hubs.
>
> LOVE stands in for the play token. The production token will be a dedicated
> game CAT with no market value; the mechanics are identical.
>
> Status: **design only.** Nothing here has been compiled or tested.
> Game math is checked by `simulate.py` in this folder.

## Roles

| Role | What it is |
| --- | --- |
| **Player** | Opens a channel with a Bank and plays hands. |
| **Bank** | Anyone who deploys a pot and runs a Bank node. It is the house for its own channels and stakes into each hand. |
| **Pot** | The Bank's on-chain bankroll singleton (`MAIN`). It funds the Bank's channels and receives their settlements. |
| **Jackpot pools** | Network-wide Mini, Major and Grand pools, shared by every Bank on every hub. Funds leave only through a winning Love Draw claim. |
| **Dev** | Receives the service fee. |

## Fairness

| Money | Decided by | Who can steer it |
| --- | --- | --- |
| Line, scatter and feature wins | commit-reveal between the Bank and the player, inside their channel | **Nobody.** The Bank commits first, the player can't see its seed, and a stalled Bank loses its whole stake by timeout. |
| Jackpots | the Love Draw, decided by drand on-chain | **Nobody**, including a Bank colluding with a player |

A Bank colluding with a fake player can only move its own bankroll around in
their shared channel. Every coin that belongs to someone else (other players'
channels, the jackpot pools) is protected by the referee or the drand draw.

## Bets

| Control | Options |
| --- | --- |
| Lines | 1, 5, 10, 15, 20 (fixed paylines on a 5×3 grid) |
| Coins per line | 1–5 |
| Coin value | set by the table, e.g. 0.1 / 0.25 / 0.5 / 1 |
| **Total bet** | lines × coins × coin value |
| **Min bet** | 1 line × 1 coin × the smallest coin value (0.1 at the default table) |
| Max bet | the smaller of the table's top bet and the global cap `MAIN / D` (`D` = 2000) |

Line wins pay multiples of the **line bet** (coins × coin value). Scatter and
feature wins pay multiples of the **total bet**. More lines means more ways
to win, at the same expected return per unit bet.

### Why max bet pays more (as in real slots)

1. **Top award premium:** five ❤️ wilds on a line pay 2,000× the line bet, but
   **5,000× at max coins**, the way video-poker paytables boost the top award.
2. **Grand eligibility:** the 👑 Grand is drawn only for spins at **20 lines and
   5 coins**, as with Megabucks-style progressives. Any coin value qualifies.
3. **Draw odds scale with bet:** Mini and Major (and the Grand, when eligible)
   use odds × `bet / global max bet`.

RTP is published per bet shape (see Game facts), so players can see the benefit.

## Spin protocol (a chia-gaming game, `games/lovespin`)

Built by following upstream `GAME_WRITING_GUIDE.md`, against the revision pinned
in `chiaGamingStateChannels.md`. The pattern is Calpoker's commit-reveal chain
(`games/calpoker/clsp/onchain/a.clsp`–`e.clsp`). **One hand is one spin**, and
a channel plays hands back to back.

1. The Bank proposes the hand with `H(bank_seed)`.
2. The player stakes the total bet, sets lines and coins, and reveals a fresh `player_seed`.
3. The Bank reveals `bank_seed`. The validator computes
   `seed = sha256(bank_seed, player_seed, game_id)`, picks the 5 reel stops
   (rejection sampling, no modulo bias), evaluates the active lines, scatters
   and features, and splits the hand.
4. Potion Pick adds three moves: the Bank commits a shuffle seed, the player picks a cauldron, and the Bank reveals.

Hand funding: the player puts in the bet, and the Bank puts in `MAX_WIN × bet`.
If the Bank stalls after the player's move, the referee timeout gives the player the whole hand.

## The Love Draw (jackpots)

Every spin also gets a draw ticket: `ticket = sha256(channel_id, hand_nonce)`.

1. **Batch.** About once a minute, each Bank posts an on-chain batch spend. It
   pays that minute's jackpot contributions into the shared pools and records
   a Merkle root of its tickets (ticket, player payout puzzle hash, bet,
   global max bet, Grand eligibility). It also names a drand round `R` at least
   `COMMIT_MARGIN` in the future, asserted with `ASSERT_BEFORE_SECONDS_ABSOLUTE`.
2. **Reimbursement.** The Bank pays the contributions on-chain up front. The
   channel reimburses it only for tickets the player has an inclusion proof
   for, so a Bank that leaves a ticket out isn't paid for it, and the player's
   contribution stays with the player. The player's client asks for the proof
   before the next hand.
3. **Draw.** When round `R` is published, each ticket wins tier `k` if
   `sha256(sig_R, ticket, k) < odds_k × bet / max_bet × 2^256`.
4. **Claim.** The winner (or a bot on their behalf) presents `sig_R` and the
   Merkle proof. The pool verifies drand on-chain
   (`bls_pairing_identity` + `g1_map`, quicknet) and pays 90% of the pool.
   Several winners in one round are paid in ticket order, each from what's
   left. Claims expire after a fixed window.

Results show in the UI as the **Love Draw ticker**, a few minutes after the
spin. Tickets can't be dropped after `R` is known, because the batch is
on-chain before `R` exists.

| Pool | Funded by | Odds per spin at max bet | Equilibrium size if every spin were at max bet |
| --- | --- | --- | --- |
| ✨ Mini | 0.5% of every bet | 1 in 1,000 | ≈ 5.6 × global max bet |
| 💗 Major | 1.0% | 1 in 10,000 | ≈ 111 × global max bet |
| 👑 Grand | 1.5% | 1 in 50,000 (20 lines × 5 coins only) | ≈ 833 × global max bet |

## Game

5 reels × 3 rows, 20 paylines. Each reel has one strip of 95 stops (weights:
❤️ wild 3, 🧙 Wizard 5, 🦉 Owl 7, 💎 Crystal 10, 🕯️ Candle 14, ⭐ Star 18,
🍃 Leaf 22, 🌙 Moon 2, 🧪 Potion 2, 📖 Spellbook 12). The 3 visible rows are
consecutive stops, as on a physical reel.

Line pays (× line bet, 3 / 4 / 5 of a kind from the left, wild substitutes):

| Symbol | 3 | 4 | 5 |
| --- | --- | --- | --- |
| ❤️ Heart (wild) | 100 | 500 | 2,000 (**5,000 at max coins**) |
| 🧙 Wizard | 60 | 250 | 1,000 |
| 🦉 Owl | 35 | 120 | 450 |
| 💎 Crystal | 25 | 70 | 230 |
| 🕯️ Candle | 12 | 35 | 140 |
| ⭐ Star | 7 | 23 | 90 |
| 🍃 Leaf | 5 | 12 | 45 |

Features:

| Feature | Trigger | Odds | What happens |
| --- | --- | --- | --- |
| 🌙 **Moonlit Free Spins** | 3+ Moon anywhere | 1 in 242 | Pays 5× / 20× / 100× the total bet, then 12 free spins on the same lines with all wins ×3. They can't retrigger. |
| ❤️‍🔥 **Heart Lock** (Hold & Win) | 6+ Spellbook anywhere | 1 in 333 | The spellbooks lock as hearts worth 1×–25× the total bet. 3 respins, reset by each new heart. **Fill all 15 cells for +250×.** |
| 🧪 **Potion Pick** | 3+ Potion anywhere | 1 in 465 | Pick one of 3 cauldrons: 10× / 25× / 60× the total bet. The choice is real (committed before the shuffle). |

### Game facts (published per release)

| Bet shape | Base + features | + Love Draw | **Player RTP** |
| --- | --- | --- | --- |
| 1 line | 90.9% | 1.35% | ≈ 92.3% |
| 10 lines | 91.0% | 1.35% | ≈ 92.4% |
| 20 lines × 1–4 coins | 91.2% | 1.35% | ≈ 92.5% |
| **20 lines × 5 coins (max bet)** | 91.2% | 2.70% | **≈ 93.9%** |

Base figures are long-run means from `simulate.py`, 6 × 500k spins per shape.
An earlier version of this table used single 300k-spin runs and understated
the return by about 1.5 points: at 1 line, single runs swing from 86% to 91%,
because rare large wins dominate. Quote long-run means only.

- **Max win:** 500× total bet per spin, plus any Love Draw jackpot. The cap
  binds more often at 1 line, which lowers its return slightly (90.9% vs 91.2%).
- **Fixed odds:** the paytable never changes with the pot, the player, or
  recent results. Pot size changes only the max bet and the jackpot sizes.
- Volatility: medium-high. A feature lands about once in 108 spins.

## Money flow

| Share of every bet | % | Where it goes |
| --- | --- | --- |
| Dev service fee | 3.0 (rounded up) | dev, from the Bank's side at channel close |
| Love Draw pools | 3.0 | shared pools, paid on-chain by the batch |
| Wins | ≈ 91 | the player, inside the hand |
| **Kept in the Bank's `MAIN`** | ≈ 3 | grows the Bank, which raises its max bet |

`simulate.py`, Bank seeded with 40k (main 36k + jackpots 4k), `D` = 2000, the
biggest coin value that fits under the cap, 100k spins:

| Players play | `MAIN` after 100k | Max bet then | Dev fees | Lowest `MAIN` | Realized RTP |
| --- | --- | --- | --- | --- | --- |
| 20 lines × 1 coin | 116k | 58 | 58k | 35k | 91.2% |
| 20 lines × 5 coins | 47k | 24 | 30k | 26k | 95.5% (two Grands hit) |

The max-bet run is a reminder that the Bank's `MAIN` also has to absorb
variance from its own players. The jackpot pools absorb only their own draws.

## Tables and Bank capital

- A table fixes the coin values and so the top bet. The Bank's channel
  deposit is `MAX_WIN × top bet` per open hand.
- **Exposure limit:** a Bank's total channel deposits must stay at or below
  `EXPOSURE_BPS` of its `MAIN` (e.g. 50%). When the limit is reached, new
  seats wait.
- More Banks means more seats, and the hub lists every Bank with its on-chain
  bankroll, open seats and uptime.

## Compliance profile (so a licensed deployment remains possible)

The game ships with a per-jurisdiction profile. It defaults to the strictest
settings, and an operator may loosen them only where its licence allows.

| Requirement | Default |
| --- | --- |
| `bank_seed` from a CSPRNG a test lab can certify (GLI-19); provably fair history per spin | on |
| Fixed, published paytable, per-bet RTP and max win | on |
| Jackpot pools can't be withdrawn; contributions shown | on, enforced by the pool puzzle |
| Minimum 2.5 s per spin; no autoplay, turbo or slam-stop | on (UKGC baseline) |
| No celebration when a win is less than the stake; session net position and time on screen | on |
| Deposit, loss and session limits; reality checks; cool-off; self-exclusion | on |
| No bonus buy | not built |
| Age gate, KYC and geofencing hooks | off for the no-value game token; required for any real-value deployment |

**Discord and web UIs.** Both run the same game. The no-value game token is
what keeps the Discord build within Discord's gambling policy, which counts
virtual currency with a market value as real value. The token must not be
buyable, sellable or redeemable for anything of value (for example no DEX
pools, and no swaps to LOVE or XCH). If that ever changes, the Discord build
has to drop wagering.

## Attacks considered

| Attack | Mitigation |
| --- | --- |
| Bank refuses to reveal a losing hand | The referee timeout gives the player the whole hand. |
| Either side grinds its seed | Commit-reveal ordering; neither knows the other's seed in time. |
| Bank colludes with a fake player to win jackpots | The draw uses drand, which is unknown until after the batch is on-chain, so collusion can't change the odds. |
| Bank drops losing tickets after the draw | Batches are on-chain before round `R` exists. |
| Bank leaves a ticket out | It isn't reimbursed for that contribution, and the player's client stops before the next hand without an inclusion proof. |
| Forged or replayed claim | Merkle proof against an on-chain batch, drand verified on-chain, and each ticket can be claimed once (claimed-ticket set or accumulator in the pool state). |
| Farmer back-dates a batch after seeing `R` | `COMMIT_MARGIN` ≥ 180 s. |
| Bank over-commits capital | Per-table deposits and `EXPOSURE_BPS`. |
| Puzzle drift between Bank and players | Pin chia-gaming by commit, and show the pinned revision in the UI. |
| drand stalls | Batches wait for the next round; no refund path that reopens grinding. |

## Open decisions

1. Fee (3%) and Love Draw split (0.5 / 1 / 1.5%).
2. Table coin values, `D`, `MAX_WIN` and `EXPOSURE_BPS`.
3. The game token's TAIL: how it's issued to players, and how the no-value rule is kept (no DEX pools, no swaps).
4. Where the code lives: `games/lovespin` in a chia-gaming fork; the pot, Love
   Draw and splitter puzzles in a public `love-slots-puzzles` repo; the UI in
   The Nightspire (the BOW project), shared by its web and Discord builds.

## Build order

1. drand verification puzzle, tested against the quicknet test vectors (simulator).
2. `games/lovespin`: validators, handler, proposal codec and play UI. Cross-check the validator against `simulate.py` on fixed seeds.
3. Channel tests through upstream's harness: clean shutdown, Bank timeout, slash, Potion Pick moves, max-win cap.
4. Love Draw puzzles: batch, pools, claims. Tests: inclusion, replay, ordering, expiry, and the `clvmPuzzleAudit.md` mutation set.
5. Bank node: CSPRNG, tables, exposure tracking, batch poster, splitter at channel close.
6. UI: bet controls (lines, coins, coin value, max bet), Love Draw ticker, provably fair history, compliance profile. Ship to web and Discord.
7. testnet11 with the game token, then a security review, then mainnet.
