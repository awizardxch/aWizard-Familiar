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

## Economics (from `simulate.py`, default paytable)

| Tier (3 reels) | Odds | Pays at max wager |
| --- | --- | --- |
| 3 ❤️ HEART | 1 in 32,768 | 50% of pot |
| 3 🧙 WIZARD | 1 in 1,214 | 8% |
| 3 🧪 POTION | 1 in 152 | 2% |
| 3 ⭐ STAR | 1 in 33 | 0.6% |
| 3 🌙 MOON | 1 in 19 | 0.4% |
| 2 ❤️ HEART | 1 in 352 | 0.3% |

- Payout is proportional to **both the pot and the wager**. Without the
  wager factor, everyone would bet the minimum.
- **Solvent by construction:** each payout is at most 50% of the pot, so the
  pot can never go negative or be overdrawn.
- **Self-balancing:** the pot drifts to `P* = (1 − fee)·W_MAX / k`, where
  `k = Σ p·f` (≈1.58M LOVE at `W_MAX` = 1,000). At `P*`, the player's expected
  value is exactly −fee, so the RTP is 97%. Above `P*`, spins are +EV, which
  draws players in and pulls the pot back down. Below it, losing spins refill it.
- Seed the pot near `P*`, or players will mostly lose until it fills (the sim
  shows 96.2% RTP when starting from 10k).
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
| CLVM cost | One pairing check (2 pairs) plus `g1_map` is about 6M cost per ticket. Cap tickets per settlement. Confirm the per-pair cost (CHIP-0011 and the chialisp.com costs page disagree). |

## Open decisions

1. Dev fee (3% default), `W_MIN`/`W_MAX`, and the paytable feel (more frequent small wins vs a bigger jackpot).
2. Who seeds the first LOVE pot, and how much (≈`P*`).
3. Whether to add a settler bounty, so third parties settle when the keeper is down.
4. Where the code lives. Following the Forge split, that would be a public
   `love-slots-puzzles` repo for the Chialisp and a private UI in bow-app.
5. Legal review. This is real-value gambling, and the rules depend on where the operator and players are.

## Build order

1. drand verification puzzle alone, tested against the quicknet test vectors (simulator).
2. `slot_ticket.clsp` + `slot_pot.clsp` on the CAT2 layer, then simulator tests: solvency, ordering, expiry, and the mutation set from `clvmPuzzleAudit.md`.
3. Keeper bot (settles every round) and a BOW hub tile with reel animation (`networkGameplayUX.md`).
4. testnet11 with a test CAT, then a `clvmPuzzleAudit.md` review, then the LOVE pot on mainnet.
