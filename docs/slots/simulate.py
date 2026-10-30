"""Love Slots pool economics: Monte Carlo of the paytable and bonus features in LOVE_SLOTS_SPEC.md.

Every payout is a fraction of the pot *at that moment*, scaled by wager / W_MAX
and capped at MAX_PAYOUT_BPS, so the pot can never be drained.
Bonus rounds pay from the pot one step at a time, like the puzzle would.
Run: python3 -I simulate.py
"""
import random

REELS = 3
# symbol -> weight (the same strip on every reel)
STRIP = {"HEART": 1, "WIZARD": 3, "SPELLBOOK": 2, "POTION": 4, "STAR": 12, "MOON": 6}
SYMS = list(STRIP)
WEIGHTS = list(STRIP.values())

# base line wins: tier -> bps of pot at max wager
LINE_BPS = {
    "3 HEART": 5000,     # jackpot
    "3 WIZARD": 800,
    "3 STAR": 30,
    "2 HEART": 30,
    "3 MOON": 40,        # also triggers Moonlit Free Spins
    "3 POTION": 0,       # triggers Potion Pick (value comes from the pick)
    "3 SPELLBOOK": 0,    # triggers Wheel of Hearts
}

FREE_SPINS = 8
FREE_SPIN_MULT = 2
# Potion Pick: three cauldrons, shuffled after the pick is locked in
CAULDRONS_BPS = [60, 250, 1200]
# Wheel of Hearts: 12 equal segments; "SHOT" is a 1-in-4 jackpot shot, else 300 bps
WHEEL_BPS = [100, 100, 150, 150, 200, 200, 300, 300, 500, 500, 1000, "SHOT"]

MAX_PAYOUT_BPS = 5000  # cap on any single payout, multipliers included
FEE_BPS = 300
W_MAX = 1_000


def line_tier(r):
    for s in SYMS:
        if r.count(s) == 3:
            return f"3 {s}"
    if r.count("HEART") == 2:
        return "2 HEART"
    return None


class Pot:
    def __init__(self, amount):
        self.amount = amount
        self.paid = 0

    def pay(self, bps, wager, mult=1):
        bps = min(bps * mult, MAX_PAYOUT_BPS)
        out = self.amount * bps * wager // (10_000 * W_MAX)
        self.amount -= out
        self.paid += out
        return out


def spin_reels(rng):
    return rng.choices(SYMS, weights=WEIGHTS, k=REELS)


def play(rng, pot, wager, stats):
    t = line_tier(spin_reels(rng))
    if not t:
        return
    stats[t] = stats.get(t, 0) + 1
    pot.pay(LINE_BPS[t], wager)
    if t == "3 MOON":                      # free spins: no retrigger
        for _ in range(FREE_SPINS):
            ft = line_tier(spin_reels(rng))
            if ft and LINE_BPS[ft]:
                pot.pay(LINE_BPS[ft], wager, FREE_SPIN_MULT)
    elif t == "3 POTION":                  # the pick is fair: contents shuffled after the commit
        pot.pay(rng.choice(CAULDRONS_BPS), wager)
    elif t == "3 SPELLBOOK":
        seg = rng.choice(WHEEL_BPS)
        if seg == "SHOT":
            pot.pay(5000 if rng.random() < 0.25 else 300, wager)
        else:
            pot.pay(seg, wager)


def expected_fraction(trials, seed):
    """k: mean pot fraction paid per max-wager spin (pot held at 1e12 so rounding is negligible)."""
    rng = random.Random(seed)
    big = 10**12
    total, stats = 0, {}
    for _ in range(trials):
        pot = Pot(big)
        play(rng, pot, W_MAX, stats)
        total += pot.paid
    return total / big / trials, stats


def run(spins, start, wager, seed):
    rng = random.Random(seed)
    pot, paid_in, fees, lo = Pot(start), 0, 0, start
    for _ in range(spins):
        fee = wager * FEE_BPS // 10_000
        pot.amount += wager - fee
        paid_in += wager
        fees += fee
        play(rng, pot, wager, {})
        lo = min(lo, pot.amount)
    return pot.amount, paid_in, pot.paid, fees, lo


if __name__ == "__main__":
    n = 2_000_000
    k, stats = expected_fraction(n, seed=1)
    print(f"over {n:,} spins:")
    for t, c in sorted(stats.items(), key=lambda x: x[1]):
        print(f"  {t:12s} 1 in {n/c:8.0f}")
    bonus = sum(stats.get(t, 0) for t in ("3 MOON", "3 POTION", "3 SPELLBOOK"))
    print(f"hit rate {sum(stats.values())/n:.2%}, bonus round 1 in {n/bonus:.0f}")
    ss = (1 - FEE_BPS / 10_000) * W_MAX / k
    print(f"k = {k:.6f}; steady-state pot ~ {ss:,.0f} LOVE (player EV there = -fee)")
    print()
    for start in (10_000, int(ss), 5_000_000):
        end, i, o, f, lo = run(300_000, start, W_MAX, seed=7)
        print(f"start pot {start:>9,} -> end {end:>9,}  RTP {o/i:6.2%}  dev fees {f:,}  min pot {lo:,}")
