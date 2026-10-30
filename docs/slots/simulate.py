"""Love Slots pool economics: Monte Carlo of the paytable in LOVE_SLOTS_SPEC.md.

Payout for tier k on wager w with pot P (pot already includes this wager, net of fee):
    payout = P * f_k * (w / W_MAX)
so every payout is a fraction of the pot and the pot can never go negative.
Run: python3 -I simulate.py
"""
import random

REELS = 3
# symbol: weight on each reel (same strip on every reel)
STRIP = {"HEART": 1, "WIZARD": 3, "POTION": 6, "STAR": 10, "MOON": 12}
TOTAL = sum(STRIP.values())

# tier -> fraction of pot paid at max wager (basis points of the pot)
PAYTABLE_BPS = {
    "3 HEART": 5000,   # jackpot: half the pot
    "3 WIZARD": 800,
    "3 POTION": 200,
    "3 STAR": 60,
    "3 MOON": 40,
    "2 HEART": 30,
}
FEE_BPS = 300          # dev fee on every wager
W_MAX = 1_000          # LOVE (whole units for the sim)


def tier(reels):
    for s in STRIP:
        if reels.count(s) == 3:
            return f"3 {s}"
    if reels.count("HEART") == 2:
        return "2 HEART"
    return None


def exact_probs():
    syms = list(STRIP)
    probs = {}
    for a in syms:
        for b in syms:
            for c in syms:
                p = STRIP[a] * STRIP[b] * STRIP[c] / TOTAL**3
                t = tier([a, b, c])
                if t:
                    probs[t] = probs.get(t, 0) + p
    return probs


def spin(rng):
    return [rng.choices(list(STRIP), weights=STRIP.values())[0] for _ in range(REELS)]


def run(spins, pot, wager, seed):
    rng = random.Random(seed)
    paid_in = fees = paid_out = 0
    lo = pot
    for _ in range(spins):
        fee = wager * FEE_BPS // 10_000
        pot += wager - fee
        paid_in += wager
        fees += fee
        t = tier(spin(rng))
        if t:
            out = pot * PAYTABLE_BPS[t] * wager // (10_000 * W_MAX)
            pot -= out
            paid_out += out
        lo = min(lo, pot)
    return pot, paid_in, paid_out, fees, lo


if __name__ == "__main__":
    probs = exact_probs()
    k = sum(probs[t] * PAYTABLE_BPS[t] / 10_000 for t in probs)  # expected pot fraction per max-wager spin
    print("tier probabilities:")
    for t, p in sorted(probs.items(), key=lambda x: x[1]):
        print(f"  {t:9s} 1 in {1/p:8.0f}   pays {PAYTABLE_BPS[t]/100:5.2f}% of pot")
    hit = sum(probs.values())
    print(f"hit rate {hit:.2%}, expected pot fraction per max spin k = {k:.6f}")
    ss = (1 - FEE_BPS / 10_000) * W_MAX / k
    print(f"steady-state pot = (1-fee)*W_MAX/k = {ss:,.0f} LOVE  (players' EV there = -fee)")
    print(f"break-even pot (player EV = 0) = W_MAX/k = {W_MAX/k:,.0f} LOVE")
    print()
    for start in (10_000, int(ss), 1_000_000):
        pot, i, o, f, lo = run(200_000, start, W_MAX, seed=7)
        print(f"start pot {start:>9,} -> end {pot:>9,}  RTP {o/i:6.2%}  dev fees {f:,}  min pot {lo:,}")
