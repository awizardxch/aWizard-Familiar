# Love Slots — Design Spec (draft)

> A slot machine whose bank is an on-chain pot of one CAT. LOVE is the first pot.
> Every wager goes into the pot, the dev takes a fee on intake, losing spins
> stay in the pot, and wins pay a fraction of the pot. Outcomes come from the
> drand public randomness beacon, verified on-chain, so neither the dev nor the
> player can know or steer a result.
>
> Status: **design only.** Nothing here has been compiled or tested on-chain.
> Economics are checked by `simulate.py` in this folder.

## Why this is not a chia-gaming game

chia-gaming channels are **two-player** (`chiaGamingStateChannels.md`). A slot
has one player against a shared pot that belongs to no one. Making the pot a
"player" would mean the operator signs for it, which makes the operator the
house and puts it in a position to collude. So the pot is an on-chain
singleton, and the BOW hub only lists it as a game tile. A later "instant mode"
could run as a chia-gaming channel against an operator bankroll. That would be
a separate, trusted product.

## Coins

| Coin | Puzzle | Holds |
| --- | --- | --- |
| **Pot** | singleton → CAT layer (curried TAIL hash) → `slot_pot.clsp` | the whole bank, in one CAT coin |
| **Ticket** | CAT layer → `slot_ticket.clsp` | one spin's wager until it is settled |
| Payouts | standard CAT to the player / dev puzzle hash | winnings and fees |

`slot_pot.clsp` curried config (fixed for the life of a pot; the hash is the pot's identity):

- `TAIL_HASH` — LOVE first: `70010d83542594dd44314efbae75d82b3d9ae7d946921ed981a6cd08f0549e50`
  (from `awizard_discord/awizard.js`; verify against Dexie or Spacescan before launch). Any CAT can be used by deploying another pot with a different `TAIL_HASH`.
- `DEV_PUZZLE_HASH`, `FEE_BPS` (default 300 = 3%)
- `W_MIN`, `W_MAX`
- `PAYTABLE`: reel strips plus the tier fractions in bps
- `DRAND_PUBKEY` (quicknet G2 key), `DRAND_GENESIS`, `DRAND_PERIOD` (3 s)
- `COMMIT_MARGIN` (≥ 180 s) and `SETTLE_WINDOW` (e.g. 3600 s)

## Flow

1. **Spin.** The player's wallet creates a ticket coin. The ticket curries the
   wager `w`, the player's payout puzzle hash, and a drand round `R` whose
   publish time is at least `COMMIT_MARGIN` in the future. The spend asserts
   `ASSERT_BEFORE_SECONDS_ABSOLUTE(time(R) − COMMIT_MARGIN)`, so the ticket
   must be on-chain before anyone, farmers included, can know round R. Buying
   N spins in one transaction creates N tickets with consecutive rounds. The
   pot singleton isn't touched, so spins never contend with each other.
2. **Wait for the beacon.** The UI spins the reels until round `R` is
   published (about 3–5 minutes after confirmation).
3. **Settle (anyone may do it).** One pot spend absorbs any number of tickets.
   For each ticket, in ascending coin-id order:
   - Verify drand: `bls_pairing_identity(sig_R, −G2, g1_map(sha256(R_be64), DST), DRAND_PUBKEY)`.
   - `seed = sha256(sig_R, ticket_coin_id)` gives the reel stops (rejection
     sampling over the strip weights, so there's no modulo bias), which give the tier.
   - `fee = w·FEE_BPS/10000` goes to the dev, and `pot += w − fee`.
   - If the spin won: `payout = pot · f_tier · w / (10000 · W_MAX)`, which goes
     to the player, and `pot −= payout`.
   - The pot recreates itself with the new balance. CAT ring accounting:
     pot in + tickets in = pot out + payouts + fees.
4. **Expiry.** A ticket must settle before `time(R) + SETTLE_WINDOW`. Past that,
   the pot can absorb it as a loss. Without this, a winner could hold a
   jackpot ticket while the pot grows and settle later for more. The dev's
   keeper bot settles every ticket as soon as `R` lands, and a winner can also
   settle their own ticket.

## Bonus features

Every bonus must follow the same rule as the reels: **all randomness comes from
a drand round published after the player is locked in.** That allows two
kinds of bonus:

- **Seed-driven:** the whole bonus is derived from the spin's seed
  (`sha256(seed, i)` for step `i`). The puzzle evaluates it in the same
  settlement, so there's no extra wait. Each step costs only a few `sha256` and
  compare ops; the pairing check is paid once per ticket either way. The
  animation replays exactly what the puzzle computed, and anyone can recompute it.
- **Choice-driven:** the player's choice is committed on-chain *before* the
  round that decides the prizes. This costs a second wait (≈3–5 min) but the
  choice is real. We don't do fake picks, where the result is already public
  and the pick is only an animation.

| Bonus | Trigger | Kind | What happens |
| --- | --- | --- | --- |
| 🌙 **Moonlit Free Spins** | 3 MOON (1 in 102) | seed-driven | 8 free spins at ×2. They can't retrigger. Each win is paid from the pot as it stands at that step. |
| 📖 **Wheel of Hearts** | 3 SPELLBOOK (1 in 2,717) | seed-driven | 12-segment wheel: 1%–10% of pot, plus one **Jackpot Shot** segment (1 in 4 for 50%, otherwise 3%). |
| 🧪 **Potion Pick** | 3 POTION (1 in 340) | choice-driven | Settlement creates a *pick coin* for the player. The player spends it, choosing cauldron 1–3 and naming a new round `R2` (same `COMMIT_MARGIN` rule). When `R2` lands, the cauldron contents (0.6% / 2.5% / 12%) are shuffled by `sha256(sig_R2, pick_coin_id)` and the chosen one pays. Pick coins expire under `SETTLE_WINDOW` like tickets. If the player never picks, the keeper takes a default pick (cauldron 1) after the window, so nothing gets stuck. |

Rules that keep bonuses solvent:

- **`MAX_PAYOUT_BPS` = 5000 caps every single payout, multipliers included.**
  Without the cap, a ×2 jackpot inside free spins would pay out the whole pot.
- Bonus payouts scale by `w / W_MAX`, the same as line wins.
- Each step pays from the current pot, so a long bonus can shrink the pot but
  can never empty it.

Ideas we rejected or deferred:

- **Shared "Love Meter" that triggers when full:** rejected. Everyone can see
  how full it is, so players would only bet when it's nearly full, and that
  near-full spin becomes a +EV option. This is the classic must-hit-by exploit.
- **BOW Fighter crossover:** off the table while BOW battles are paused.

## Economics (from `simulate.py`, 2M simulated spins)

Reel strip weights: HEART 1, WIZARD 3, SPELLBOOK 2, POTION 4, STAR 12, MOON 6.

| Result (3 reels) | Odds | Pays at max wager |
| --- | --- | --- |
| 3 ❤️ HEART | 1 in 23,529 | 50% of pot (jackpot) |
| 3 📖 SPELLBOOK | 1 in 2,717 | Wheel of Hearts |
| 3 🧙 WIZARD | 1 in 827 | 8% |
| 3 🧪 POTION | 1 in 340 | Potion Pick |
| 2 ❤️ HEART | 1 in 276 | 0.3% |
| 3 🌙 MOON | 1 in 102 | 0.4% + Moonlit Free Spins |
| 3 ⭐ STAR | 1 in 13 | 0.3% |

Overall, about 9.7% of spins win something, and a bonus round lands about
once every 76 spins.

- Payout is proportional to **both the pot and the wager**. Without the
  wager factor, everyone would bet the minimum.
- **Solvent by construction:** each payout is capped at 50% of the pot at that
  moment, so the pot can never go negative or be overdrawn.
- **Self-balancing:** the pot drifts to `P* = (1 − fee)·W_MAX / k`, where `k`
  is the mean pot fraction paid per max-wager spin, bonuses included
  (≈1.54M LOVE at `W_MAX` = 1,000). At `P*`, the player's expected value is
  exactly −fee, so the RTP is 97%. Above `P*`, spins are +EV, which draws
  players in and pulls the pot back down. Below it, losing spins refill it.
- Seed the pot near `P*`, or players will mostly lose until it fills (the sim
  shows 96.5% RTP when starting from 10k).
- All values above are tunable. Re-run `python3 -I simulate.py` after any
  paytable change and record the output in the PR.

## Attacks considered

| Attack | Mitigation |
| --- | --- |
| Player or dev grinds the outcome | The seed needs `sig_R`, which nobody has until after the ticket is on-chain. The dev holds no secret. |
| Farmer back-dates a ticket after seeing `R` | `COMMIT_MARGIN` ≥ 180 s, many times the tolerated timestamp skew. Tune it on testnet. |
| Winner delays settlement to wait for a bigger pot | `SETTLE_WINDOW` expiry, and the keeper settles promptly. Residual edge is bounded by pot growth inside the window. |
| Settler reorders a batch | Fixed ascending coin-id order, enforced by the puzzle. |
| Pot singleton contention | Tickets don't touch the pot, and settlement batches. The pot needs one spend per block at most. |
| drand stops publishing or colludes | Trust assumption: a threshold of the League of Entropy. Tickets would wait until rounds resume. Any refund path must not reopen grinding. |
| Wrong DST or message for quicknet | Pin against drand's published quicknet test vectors and the `drand-verify` crate before any puzzle code. |
| Forged pick coin | The pot accepts a pick coin only with a lineage proof showing the pot itself created it, and the pick coin's puzzle curries the pot's launcher ID. |
| Player waits on a pick to see the pot grow | The pick coin expires and the keeper takes the default pick. The prize is a pot fraction at stage-2 settlement, so this is the same bounded edge as delayed ticket settlement. |
| CLVM cost | One pairing check (2 pairs) plus `g1_map` is about 6M cost per ticket. Free-spin and wheel steps add only `sha256` and compare ops; the Potion Pick's second stage needs a second pairing check. Cap tickets per settlement. Confirm the per-pair cost (CHIP-0011 and the chialisp.com costs page disagree). |

## Open decisions

1. Dev fee (3% default), `W_MIN`/`W_MAX`, and the paytable feel (more frequent small wins vs a bigger jackpot).
2. Who seeds the first LOVE pot, and how much (≈`P*`).
3. Whether to add a settler bounty, so third parties settle when the keeper is down.
4. Where the code lives. Following the Forge split, that would be a public
   `love-slots-puzzles` repo for the Chialisp and a private UI in bow-app.

## Build order

1. drand verification puzzle alone, tested against the quicknet test vectors (simulator).
2. `slot_ticket.clsp` + `slot_pot.clsp` on the CAT2 layer with line wins, Moonlit Free Spins and Wheel of Hearts, then simulator tests: solvency, ordering, expiry, the payout cap, and the mutation set from `clvmPuzzleAudit.md`. Add a cross-check that the puzzle and `simulate.py` give identical results for the same seeds.
3. `slot_pick.clsp` for Potion Pick (two-stage), with its own tests: forged pick coin, expiry, default pick.
4. Keeper bot (settles every round and takes default picks) and a BOW hub tile with reel and bonus animations (`networkGameplayUX.md`).
5. testnet11 with a test CAT, then a `clvmPuzzleAudit.md` review, then the LOVE pot on mainnet.
