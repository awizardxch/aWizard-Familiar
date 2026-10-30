# Love Slots — Design Spec (draft)

> A slot machine played over Chia state channels. Spins are instant and
> off-chain; the chain is used to open and close channels, hold the bankroll and
> jackpot pools, and settle any dispute through the upstream referee. LOVE is the
> first CAT; any CAT works the same way.
>
> Status: **design only.** Nothing here has been compiled or tested.
> Game math is checked by `simulate.py` in this folder.

## Roles

| Role | What it is |
| --- | --- |
| **Player** | Opens a channel with the Bank and plays hands in it. |
| **Bank** | The operator's channel node. It is the house: it stakes into each hand and is the entity a licence would name. |
| **Pot** | On-chain singleton holding the Bank's bankroll `MAIN`. It funds Bank channels and receives their settlements. |
| **Jackpot pools** | On-chain coins for Mini, Major and Grand. They can pay only jackpot claims or a successor pool. |
| **Dev** | Receives the service fee. |

## Spin protocol (a chia-gaming game, `games/lovespin`)

Built by following upstream `GAME_WRITING_GUIDE.md` (`chiaGamingStateChannels.md`
has the pinned revision). The pattern is Calpoker's commit-reveal chain
(`games/calpoker/clsp/onchain/a.clsp`–`e.clsp`). Each **hand is one spin**, and a
channel can run hands back to back.

1. **Bank commits.** The Bank proposes the hand with `H(bank_seed)`.
   `bank_seed` comes from a certifiable CSPRNG.
2. **Player moves.** The player stakes `w` and reveals a fresh `player_seed`.
3. **Bank reveals.** The Bank reveals `bank_seed`. The validator computes
   `seed = sha256(bank_seed, player_seed, game_id)`, derives the reels and any
   bonus from it, and settles the hand's split.
4. **Potion Pick only** adds three moves: the Bank commits a shuffle seed, the
   player picks a cauldron, and the Bank reveals.

Why it's fair to the player without trusting the Bank:

- The Bank commits before it sees `player_seed`, so it can't steer the result.
- The player doesn't know `bank_seed`, so they can't steer it either.
- **If the Bank stalls after the player's move, the referee timeout pays the
  player the Bank's whole stake for the hand** (`MAX_WIN × w`). Refusing to
  reveal a losing hand is always worse for the Bank than paying it.
- Every move is co-signed. Any cheating can be proved on-chain through the
  upstream referee's slash path.
- After each spin, the player can recompute the result from both seeds
  ("provably fair" history in the UI).

Hand funding: the player puts in `w`, and the Bank puts in `MAX_WIN × w`. The
validator pays the player `min(mult, MAX_WIN) × w` and returns the rest to the
Bank side. Jackpots are not paid inside the hand (see Money flow below).

## Tables and Bank capital

- A Bank channel must hold `MAX_WIN × bet` for every hand it may play, so
  players open a channel at a **table**: a bet range, such as 1–5 LOVE or
  5–20 LOVE. The Bank's deposit is sized to the table's top bet.
- The global max bet is still `MAIN / D`. As `MAIN` grows, higher tables open.
- **Exposure limit:** the total Bank deposit across open channels must stay at
  or below `EXPOSURE_BPS` of `MAIN` (e.g. 50%). When the limit is reached, new
  channels wait for a seat.

## Money flow

Per spin, tracked inside the channel state:

| Share | % of every wager | Where it ends up |
| --- | --- | --- |
| Dev service fee | 3.0% (rounded up) | dev |
| Mini / Major / Grand | 0.5% / 1.0% / 1.5% | the three jackpot pools |
| The rest | 95.5% | the Bank side of the hand, minus wins paid |

- **At channel close**, clean shutdown or unroll, the Bank's share goes to a
  splitter spend. It pays the accumulated fee to the dev and the contributions
  to the jackpot pools, and returns the remainder to `MAIN`. The accumulated
  totals are part of the co-signed channel state, so the player has signed them
  too.
- **Jackpot wins:** a winning hand's final state includes a co-signed jackpot
  claim with the pool, player puzzle hash, `w` and the max bet at that time.
  The pool coin pays `POOL × 90% × w / w_max` against a valid claim. The pool
  puzzle has no other exit except a successor pool, so contributions can't be
  withdrawn to the operator.

## Trust model

| What | Who you trust |
| --- | --- |
| Each spin's fairness to the player | Nobody (commit-reveal + referee) |
| Getting paid for a won hand | Nobody (channel + referee) |
| Jackpot contributions reaching the pools | Nobody past channel close. The totals are co-signed, and the splitter pays them out. |
| The Bank's bankroll `MAIN` | The operator. It is the house's money, and that is the structure licensing regimes expect. |
| Fair jackpot draws | The operator: a Bank colluding with a fake player could leak `bank_seed`. Mitigations are licensing, the audited CSPRNG, the public on-chain claim history, and per-claim rate limits on the pools. |

The fully trustless alternative, outcomes from on-chain drand with no
operator, is kept in git history. It means 3–5 minutes per spin, and it has no
operator to license, which makes the legal path harder.

## Game

3 reels. Strip weights: HEART 1, WIZARD 3, SPELLBOOK 5, POTION 4, STAR 12, MOON 6.

| Result | Odds per spin | Pays |
| --- | --- | --- |
| 3 ❤️ HEART | 1 in 29,800 | 💗 Major jackpot |
| 3 🧙 WIZARD | 1 in 1,100 | 80× |
| 2 ❤️ HEART | 1 in 330 | 5× |
| 3 🌙 MOON | 1 in 139 | 5× + 🌙 **Moonlit Free Spins** |
| 3 📖 SPELLBOOK | 1 in 235 | ❤️‍🔥 **Heart Lock** |
| 3 🧪 POTION | 1 in 459 | 🧪 **Potion Pick** |
| 3 ⭐ STAR | 1 in 17 | 8× |

Bonus features:

- 🌙 **Moonlit Free Spins:** 8 spins with line wins at ×2. They can't
  retrigger. A 3 HEART during free spins still wins the Major.
- ❤️‍🔥 **Heart Lock (Hold & Win):** a 15-cell grid that starts with 3 hearts and
  gives 3 respins. Hearts lock where they land, and each new heart resets the
  respins to 3. Hearts carry 2×–50× or a ✨ MINI or 💗 MAJOR jackpot. **Fill
  all 15 cells to win the 👑 GRAND.**
- 🧪 **Potion Pick:** pick one of three cauldrons (15×, 40×, ✨ MINI). The
  shuffle is committed before the pick, so the choice is real.

Published game facts (they must be fixed per release and shown in the game's help screen):

| | |
| --- | --- |
| **RTP** | ≈ 91.9% long-run (89.2% base and features, plus 2.7% returned via jackpots) |
| **Max win** | 250× bet per spin, plus any jackpot |
| Any bonus feature | ≈1 in 74 spins |
| Jackpots | Mini ≈1 in 1,000 · Major ≈1 in 8,400 · Grand ≈1 in 31,000 |
| Volatility | medium-high |

**Fixed odds.** The paytable never changes with the pot, the player, or
recent results. Earlier drafts paid a share of the pot, which a test lab
would not certify. Pot size changes only the max bet and the jackpot sizes.

## Economics (from `simulate.py`)

Planned seed: **40k LOVE**, split main 36k + Mini 500 + Major 1,000 + Grand 2,500. `D` = 2000.

| Per LOVE wagered | % |
| --- | --- |
| Dev service fee | 3.0 |
| Jackpot pools (90% returns to players) | 3.0 |
| Line and feature wins | ≈89.2 |
| **Kept in `MAIN`** (growth) | **≈4.8** |

| Players bet | After 200k spins | Max bet then | Dev fees | Lowest `MAIN` |
| --- | --- | --- | --- | --- |
| 5 LOVE | main ≈96k, Grand ≈11.6k | 47 LOVE | 30k | 34.7k |
| 20 LOVE (clamped early) | main ≈275k, Grand ≈34k | 137 LOVE | 120k | 31.5k |

Stress test, every spin at the max bet from the seed (5,000 spins × 400 runs):

| `D` | Max bet at seed | `MAIN` below half the seed | Worst dip |
| --- | --- | --- | --- |
| 1000 | 36 LOVE | 2.5% of runs | 29% of seed |
| **2000** | **18 LOVE** | **0%** | **55%** |

Re-run `python3 -I simulate.py` after any change and record its output in the PR.

## Compliance profile (built in so a licence application could pass)

The game ships with a per-jurisdiction **compliance profile**. Default to the
strictest settings, and loosen them only where a licence allows.

| Requirement | Why | Default |
| --- | --- | --- |
| Certifiable RNG: `bank_seed` from a CSPRNG, test-lab ready | GLI-19 is the RNG standard most regulators reference. BMM has certified a blockchain RNG (Chainlink VRF) under it | on |
| Fixed, published paytable, RTP and max win | game-math certification | on |
| Progressive pools can't be withdrawn; contributions are shown | progressive-jackpot rules (check GLI-12) | on, enforced by the pool puzzle |
| Minimum 2.5 s per spin cycle | UKGC remote standards | on |
| No autoplay, turbo, quick-spin or slam-stop | UKGC remote standards | on |
| No celebration when a "win" is less than the stake | UKGC (losses disguised as wins) | on |
| Session net position and time on screen | UKGC remote standards | on |
| Deposit, loss and session limits; reality checks; cool-off; self-exclusion | standard responsible-gambling requirements (e.g. Curaçao LOK) | on |
| No bonus buy | banned or contentious in several markets | not built |
| Age gate + KYC/AML before real-value play | every licence; enhanced for crypto under Curaçao LOK | required for real-value mode |
| Geofencing | most of the US allows no online casino, and sweepstakes models are being banned (California AB 831 since Jan 2026, New York Dec 2025, more in 2026) | block unlicensed regions |
| Full hand history kept (seeds, moves, channel states) | dispute resolution, audit | on (chia-gaming persistence) |
| **No real-value play inside Discord** | Discord's policy bans wagering real-world value, explicitly including virtual currency with market value, and apps removed for it can't be recreated | **slots live on the web hub only** |

What licensing still needs beyond this code: a licensed operating entity
(e.g. a Curaçao LOK B2C licence, which permits crypto with enhanced AML and has
a CGA crypto guideline due by mid-2027), test-lab certification of the RNG and
the game math, and counsel for each market. Calling the fee a service fee, or
the CAT just a unit, doesn't change the analysis, because LOVE trades against
XCH and so has real-world value.

## Attacks considered

| Attack | Mitigation |
| --- | --- |
| Bank refuses to reveal a losing hand | The referee timeout pays the player the Bank's full stake. |
| Player stalls after the Bank commits | The hand times out and both stakes return; nothing was revealed. |
| Player grinds `player_seed` | `bank_seed` is unknown until after the player moves. |
| Bank grinds `bank_seed` | It is committed before `player_seed`. |
| Bank leaks `bank_seed` to an accomplice | Operator-trust residual (see Trust model): licensing, CSPRNG audit, public claim history, pool rate limits. |
| Forged jackpot claim | Claims must carry both channel signatures and match a hand state; the pool verifies the Bank key and the claim format. |
| Fee or contribution skipped at close | Totals are in the co-signed state, and the splitter spend must pay them. A player can unroll to that state on-chain. |
| Bank over-commits capital | Per-table deposits and `EXPOSURE_BPS`. |
| Puzzle drift between Bank and players | Pin chia-gaming by commit; show the pinned revision in the UI. |

## Open decisions

1. The fee (3%), the jackpot split (0.5 / 1 / 1.5%), and the jackpot seed (planned 4k of the 40k).
2. Table bet ranges and `EXPOSURE_BPS`.
3. Where the code lives: the game in a fork of chia-gaming (`games/lovespin`),
   the pot/pool/splitter puzzles in a public `love-slots-puzzles` repo, and the
   UI on the web hub.
4. Whether the Discord Activity gets a link out to the web hub, or no mention of slots at all. Discord's ads policy also restricts promotion.

## Build order

1. `games/lovespin` against the pinned chia-gaming: validators, handler, proposal codec, play UI. Cross-check the validator against `simulate.py` on fixed seeds.
2. Simulator tests through upstream's harness: clean shutdown, Bank timeout, slash, Potion Pick moves, max-win cap.
3. Pot, jackpot-pool and splitter puzzles with `clvmPuzzleAudit.md` tests (solvency, no pool exit to the operator, claim forgery, exposure limit).
4. Bank node: CSPRNG, table manager, exposure tracking, splitter on channel close.
5. Compliance profile in the UI: spin pacing, session display, limits, geofence and KYC hooks.
6. testnet11 with a test CAT, then a security review, then the LOVE seed on mainnet.
