# Love Slots — Design Spec (draft)

> A slot machine whose bank is an on-chain pot of one CAT. LOVE is the first pot.
> Every wager is split four ways: a dev service fee, contributions to three
> jackpot pools, a share kept in the pot so it grows and sustains itself, and
> the share that funds regular wins. The max bet scales with what the pot
> holds, so prizes grow as the pot grows. Outcomes come from the drand public
> randomness beacon, verified on-chain, so neither the dev nor the player can
> know or steer a result.
>
> Status: **design only.** Nothing here has been compiled or tested on-chain.
> Economics are checked by `simulate.py` in this folder.

## Why this is not a chia-gaming game

chia-gaming channels are **two-player** (`chiaGamingStateChannels.md`). A slot
has one player against a shared pot that belongs to no one. Making the pot a
"player" would mean the operator signs for it, which makes the operator the
house and puts it in a position to collude. So the pot is an on-chain
singleton, and the BOW hub only lists it as a game tile.

## Coins

| Coin | Puzzle | Holds |
| --- | --- | --- |
| **Pot** | singleton → CAT layer (curried TAIL hash) → `slot_pot.clsp` | the main pot **and** the three jackpot pools, in one CAT coin |
| **Ticket** | CAT layer → `slot_ticket.clsp` | one spin's wager until it is settled |
| **Pick** | `slot_pick.clsp` (curries the pot launcher ID) | a pending Potion Pick |
| Payouts | standard CAT to the player / dev puzzle hash | winnings and fees |

The pot singleton's state is `(MAIN, MINI, MAJOR, GRAND)`. The CAT coin's
amount is always their sum, and the puzzle asserts this on every spend. Keeping
the jackpots in the same coin avoids four singletons contending for spends.

`slot_pot.clsp` curried config (fixed for the life of a pot; the hash is the pot's identity):

- `TAIL_HASH` — LOVE first: `70010d83542594dd44314efbae75d82b3d9ae7d946921ed981a6cd08f0549e50`
  (from `awizard_discord/awizard.js`; verify against Dexie or Spacescan before launch). Any CAT can be used by deploying another pot with a different `TAIL_HASH`.
- `DEV_PUZZLE_HASH`, `FEE_BPS` = 300
- `JACKPOT_BPS` = Mini 50, Major 100, Grand 150 (3% in total); `JACKPOT_PAYS_BPS` = 9000
- `D` = 2000 (max bet = `MAIN / D`), `W_MIN` = 1 LOVE (1,000 mojos)
- `MAX_PAYOUT_BPS` = 5000
- `PAYTABLE`: reel strips, line multipliers, bonus tables
- `DRAND_PUBKEY` (quicknet G2 key), `DRAND_GENESIS`, `DRAND_PERIOD` (3 s)
- `COMMIT_MARGIN` (≥ 180 s) and `SETTLE_WINDOW` (e.g. 3600 s)

## Flow

1. **Spin.** The player's wallet creates a ticket coin. The ticket curries the
   wager `w`, the player's payout puzzle hash, and a drand round `R` whose
   publish time is at least `COMMIT_MARGIN` in the future. The spend asserts
   `ASSERT_BEFORE_SECONDS_ABSOLUTE(time(R) − COMMIT_MARGIN)`, so the ticket
   must be on-chain before anyone, farmers included, can know round R. Buying
   N spins in one transaction creates N tickets with consecutive rounds.
   Tickets don't touch the pot, so spins never contend with each other. The UI
   suggests bets at or below the current max.
2. **Wait for the beacon.** The UI spins the reels until round `R` is
   published (about 3–5 minutes after confirmation).
3. **Settle (anyone may do it).** One pot spend absorbs any number of tickets.
   For each ticket, in ascending coin-id order:
   - Verify drand: `bls_pairing_identity(sig_R, −G2, g1_map(sha256(R_be64), DST), DRAND_PUBKEY)`.
   - **Clamp the bet:** `w_max = max(W_MIN, MAIN / D)` and `w_eff = min(w, w_max)`.
     The excess `w − w_eff` is refunded in full to the player. The pot can move
     between spin and settlement, so the cap is applied at settlement.
   - **Split the wager** (all in mojos):
     - `fee = ceil(w_eff · FEE_BPS / 10000)` goes to the dev. Rounding up means
       the fee is never 0 on small bets.
     - `w_eff · JACKPOT_BPS[k] / 10000` goes to each jackpot pool.
     - The rest goes to `MAIN`.
   - `seed = sha256(sig_R, ticket_coin_id)` gives the reel stops (rejection
     sampling over the strip weights, so there's no modulo bias), which give the result.
   - **Line and bonus wins:** `payout = min(mult · w_eff, MAIN · MAX_PAYOUT_BPS / 10000)`,
     paid from `MAIN`.
   - **Jackpots:** `payout = POOL · JACKPOT_PAYS_BPS · w_eff / (10000 · w_max)`,
     paid from that pool. A max bet takes 90% of the pool and the other 10%
     re-seeds it. A smaller bet takes a proportional share, and the rest stays
     in the pool for the next winner.
   - The pot recreates itself with the new state. CAT ring accounting:
     pot in + tickets in = pot out + payouts + fees + refunds.
4. **Expiry.** A ticket must settle before `time(R) + SETTLE_WINDOW`. Past that,
   the pot can absorb it as a loss. Without this, a winner could hold a
   jackpot ticket while the pool grows and settle later for more. The dev's
   keeper bot settles every ticket as soon as `R` lands, and a winner can also
   settle their own ticket.

## Paytable

Reel strip weights (all three reels): HEART 1, WIZARD 3, SPELLBOOK 2, POTION 4, STAR 12, MOON 6.

| Result | Odds | Pays |
| --- | --- | --- |
| 3 ❤️ HEART | 1 in 23,500 | 💗 **Major jackpot** |
| 3 📖 SPELLBOOK | 1 in 2,700 | **Wheel of Hearts** bonus |
| 3 🧙 WIZARD | 1 in 830 | 140× |
| 3 🧪 POTION | 1 in 340 | **Potion Pick** bonus |
| 2 ❤️ HEART | 1 in 280 | 5× |
| 3 🌙 MOON | 1 in 100 | 5× + **Moonlit Free Spins** bonus |
| 3 ⭐ STAR | 1 in 13 | 6× |

## Bonus features

Every bonus follows the same rule as the reels: **all randomness comes from a
drand round published after the player is locked in.** That allows two kinds
of bonus:

- **Seed-driven:** the whole bonus is derived from the spin's seed
  (`sha256(seed, i)` for step `i`). The puzzle evaluates it in the same
  settlement, so there's no extra wait. Each step costs only a few `sha256` and
  compare ops; the pairing check is paid once per ticket either way. The
  animation replays exactly what the puzzle computed, and anyone can recompute it.
- **Choice-driven:** the player's choice is committed on-chain *before* the
  round that decides the prizes. This costs a second wait (≈3–5 min) but the
  choice is real. We don't do fake picks, where the result is already public
  and the pick is only an animation.

| Bonus | Kind | What happens |
| --- | --- | --- |
| 🌙 **Moonlit Free Spins** | seed-driven | 8 free spins with line wins at ×2. They can't retrigger. |
| 📖 **Wheel of Hearts** | seed-driven | 12 segments: 15×, 15×, 20×, 20×, 25×, 25×, 40×, 40×, 60×, 80×, 120×, and 👑 **GRAND jackpot**. |
| 🧪 **Potion Pick** | choice-driven | Settlement creates a pick coin for the player. The player spends it, choosing cauldron 1–3 and naming a new round `R2` (same `COMMIT_MARGIN` rule). When `R2` lands, the contents (15×, 50×, ✨ **MINI jackpot**) are shuffled by `sha256(sig_R2, pick_coin_id)` and the chosen cauldron pays. Pick coins expire under `SETTLE_WINDOW`. If the player never picks, the keeper takes cauldron 1 after the window, so nothing gets stuck. |

## Jackpot pools

| Pool | Funded by | Won by | Odds per spin |
| --- | --- | --- | --- |
| ✨ Mini | 0.5% of every wager | Potion Pick cauldron | ≈1 in 1,100 |
| 💗 Major | 1.0% of every wager | 3 HEART | ≈1 in 23,500 |
| 👑 Grand | 1.5% of every wager | Wheel of Hearts GRAND segment | ≈1 in 32,600 |

- The Major and Grand grow over many thousands of spins, so their pools get
  large. The Mini hits often, so it stays small and frequent.
- A win pays a share scaled by bet size, so a max-bet player takes 90% of the
  pool. That rewards max bets without letting a minimum-bet spin empty it.
- The UI shows all three pools live, read from the pot's on-chain state.

Ideas we rejected or deferred:

- **Shared "Love Meter" that triggers when full:** rejected. Everyone can see
  how full it is, so players would only bet when it's nearly full, and that
  near-full spin becomes a +EV option. The jackpot pools above avoid this,
  because their hits are random and don't depend on how full they are.
- **BOW Fighter crossover:** off the table while BOW battles are paused.

## Economics (from `simulate.py`)

Where each LOVE wagered goes, on average:

| Share | % | Notes |
| --- | --- | --- |
| Dev service fee | 3.0% | paid on every spin |
| Jackpot pools | 3.0% | 90% of it returns to players as jackpots hit |
| Line + bonus wins | ≈90.2% | paid from the main pot |
| **Kept in the main pot** | ≈3.8% | what makes the pot grow and sustain itself |

- **Player return over time is about 93%.**
- **Self-sustaining:** the kept 3.8% grows `MAIN` in proportion to everything
  bet. A bigger `MAIN` raises the max bet, which raises prize sizes, so the
  pot and prizes compound as people play.
- **Solvent by construction:** no win can exceed half of `MAIN`, and jackpots
  only pay out of their own pools.

Simulated from the planned seed of **40k LOVE**, split main 36k + Mini 500 +
Major 1,000 + Grand 2,500, with `D` = 2000:

| Players bet | After 200k spins | Max bet | Dev fees | Lowest main pot |
| --- | --- | --- | --- | --- |
| 5 LOVE | main ≈79k, Major ≈6k, Grand ≈11k | 39 LOVE | 30k | 34k |
| 20 LOVE (clamped while the max is lower) | main ≈205k, Major ≈16k, Grand ≈31k | 102 LOVE | 120k | 29k |

In both runs, players got back about 91.5% of what they bet. That's below
the 93% long-run figure because the Major and Grand pools were still filling.

Stress test: every spin at the max bet, 5,000 spins from the 40k seed, 400 runs:

| `D` | Max bet at seed | Runs where the main pot fell below half the seed | Worst dip |
| --- | --- | --- | --- |
| 500 | 72 LOVE | 46% | 2% of seed |
| 1000 | 36 LOVE | 11% | 18% |
| **2000** | **18 LOVE** | **0.2%** | **45%** |

**Launch with `D` = 2000.** The max bet starts at 18 LOVE and grows on its own
as the pot fills. Because `D` is curried, a looser `D` later means deploying a
new pot.

All values are tunable. Re-run `python3 -I simulate.py` after any paytable
change and record the output in the PR.

## Attacks considered

| Attack | Mitigation |
| --- | --- |
| Player or dev grinds the outcome | The seed needs `sig_R`, which nobody has until after the ticket is on-chain. The dev holds no secret. |
| Farmer back-dates a ticket after seeing `R` | `COMMIT_MARGIN` ≥ 180 s, many times the tolerated timestamp skew. Tune it on testnet. |
| Winner delays settlement to wait for a bigger pool | `SETTLE_WINDOW` expiry, and the keeper settles promptly. Residual edge is bounded by pool growth inside the window. |
| Settler reorders a batch to change `w_max` or pool sizes for a ticket | Fixed ascending coin-id order, enforced by the puzzle. |
| Oversized ticket | It's clamped to `w_max` at settlement and the excess refunded, so oversizing gains nothing. |
| Dust bets that skip the fee | The fee rounds up, and `W_MIN` = 1 LOVE. |
| State/amount mismatch | The puzzle asserts coin amount = `MAIN + MINI + MAJOR + GRAND` on every spend. |
| Pot singleton contention | Tickets don't touch the pot, and settlement batches. The pot needs one spend per block at most. |
| drand stops publishing or colludes | Trust assumption: a threshold of the League of Entropy. Tickets would wait until rounds resume. Any refund path must not reopen grinding. |
| Wrong DST or message for quicknet | Pin against drand's published quicknet test vectors and the `drand-verify` crate before any puzzle code. |
| Forged pick coin | The pot accepts a pick coin only with a lineage proof showing the pot itself created it. |
| CLVM cost | One pairing check (2 pairs) plus `g1_map` is about 6M cost per ticket. Free-spin and wheel steps add only `sha256` and compare ops; the Potion Pick's second stage needs a second pairing check. Cap tickets per settlement. Confirm the per-pair cost (CHIP-0011 and the chialisp.com costs page disagree). |

## Open decisions

1. The fee (3%), the jackpot split (0.5 / 1 / 1.5%), and how much of the seed
   goes to the jackpots (planned: 4k of the 40k).
2. Whether to add a settler bounty, so third parties settle when the keeper is down.
3. Where the code lives. Following the Forge split, that would be a public
   `love-slots-puzzles` repo for the Chialisp and a private UI in bow-app.

## Build order

1. drand verification puzzle alone, tested against the quicknet test vectors (simulator).
2. `slot_ticket.clsp` + `slot_pot.clsp` on the CAT2 layer with line wins, jackpot pools, Moonlit Free Spins and Wheel of Hearts, then simulator tests: solvency, the state/amount invariant, bet clamping and refunds, ordering, expiry, the payout cap, and the mutation set from `clvmPuzzleAudit.md`. Add a cross-check that the puzzle and `simulate.py` give identical results for the same seeds.
3. `slot_pick.clsp` for Potion Pick (two-stage), with its own tests: forged pick coin, expiry, default pick.
4. Keeper bot (settles every round and takes default picks) and a BOW hub tile with reels, bonus animations, and live jackpot meters (`networkGameplayUX.md`).
5. testnet11 with a test CAT, then a `clvmPuzzleAudit.md` review, then the LOVE pot on mainnet with the 40k seed.
