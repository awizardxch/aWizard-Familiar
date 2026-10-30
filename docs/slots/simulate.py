"""Love Slots economics: Monte Carlo of the model in LOVE_SLOTS_SPEC.md.

Every wager is split into: dev fee, jackpot contributions, and the main pot.
Line and bonus wins pay fixed multiples of the wager from the main pot.
The max wager scales with the pot (pot / D), so prizes grow as the pot grows,
and no payout may exceed MAX_PAYOUT_BPS of the pot at that moment.
Jackpots pay from their own pools, scaled by wager / max wager.
Run: python3 -I simulate.py
"""
import random

# ── reels ───────────────────────────────────────────────────────────────────
STRIP = {"HEART": 1, "WIZARD": 3, "SPELLBOOK": 2, "POTION": 4, "STAR": 12, "MOON": 6}
SYMS, WEIGHTS = list(STRIP), list(STRIP.values())

# line wins: multiples of the wager (paid from the main pot)
LINE_X = {"3 WIZARD": 140, "3 STAR": 6, "2 HEART": 5, "3 MOON": 5}
# "3 HEART" wins the Major jackpot; 3 POTION / 3 SPELLBOOK start bonuses

FREE_SPINS, FREE_SPIN_MULT = 8, 2
CAULDRONS_X = [15, 50, "MINI"]                   # Potion Pick: one cauldron holds the Mini
WHEEL = [15, 15, 20, 20, 25, 25, 40, 40, 60, 80, 120, "GRAND"]  # Wheel of Hearts

# ── wager split (basis points of every wager) ───────────────────────────────
FEE_BPS = 300                                   # dev service fee
JACKPOT_BPS = {"MINI": 50, "MAJOR": 100, "GRAND": 150}  # 3% total to jackpot pools
# the remaining 94% goes to the main pot; line + bonus RTP (~87.5%) pays out of it
# and the rest (~6.5%) is kept, which is what grows the pot

JACKPOT_PAYS_BPS = 9000   # a max-wager jackpot pays 90% of its pool; the rest re-seeds it
D = 2000                  # max wager = main pot / D
MOJO = 1_000              # CAT amounts are in mojos: 1 LOVE = 1,000 mojos
W_MIN = 1 * MOJO
MAX_PAYOUT_BPS = 5000     # no single payout above 50% of the main pot


def line_tier(r):
    for s in SYMS:
        if r.count(s) == 3:
            return f"3 {s}"
    return "2 HEART" if r.count("HEART") == 2 else None


class Machine:
    def __init__(self, main, mini=0, major=0, grand=0):
        self.main = main
        self.jp = {"MINI": mini, "MAJOR": major, "GRAND": grand}
        self.paid = self.fees = self.wagered = 0
        self.jp_hits = {"MINI": 0, "MAJOR": 0, "GRAND": 0}

    def max_wager(self):
        return max(W_MIN, self.main // D)

    def pay_x(self, mult, w):
        out = min(int(mult * w), self.main * MAX_PAYOUT_BPS // 10_000)
        self.main -= out
        self.paid += out

    def pay_jackpot(self, name, w, wmax):
        out = self.jp[name] * JACKPOT_PAYS_BPS * min(w, wmax) // (10_000 * wmax)
        self.jp[name] -= out
        self.paid += out
        self.jp_hits[name] += 1

    def spin(self, rng, w):
        wmax = self.max_wager()
        w = min(w, wmax)                         # excess over the cap is refunded
        fee = -(-w * FEE_BPS // 10_000)          # fee rounds up, so it is never 0
        jps = {k: w * b // 10_000 for k, b in JACKPOT_BPS.items()}
        self.fees += fee
        self.wagered += w
        for k, v in jps.items():
            self.jp[k] += v
        self.main += w - fee - sum(jps.values())

        t = line_tier(rng.choices(SYMS, weights=WEIGHTS, k=3))
        if t is None:
            return
        if t == "3 HEART":
            self.pay_jackpot("MAJOR", w, wmax)
        elif t in LINE_X:
            self.pay_x(LINE_X[t], w)
        if t == "3 MOON":
            for _ in range(FREE_SPINS):
                ft = line_tier(rng.choices(SYMS, weights=WEIGHTS, k=3))
                if ft in LINE_X:
                    self.pay_x(LINE_X[ft] * FREE_SPIN_MULT, w)
        elif t == "3 POTION":
            c = rng.choice(CAULDRONS_X)
            if c == "MINI":
                self.pay_jackpot("MINI", w, wmax)
            else:
                self.pay_x(c, w)
        elif t == "3 SPELLBOOK":
            seg = rng.choice(WHEEL)
            if seg == "GRAND":
                self.pay_jackpot(seg, w, wmax)
            else:
                self.pay_x(seg, w)


def main_rtp(trials, seed):
    """Expected line + bonus return per unit wagered (main pot only, no caps binding)."""
    m = Machine(main=10**15)
    rng = random.Random(seed)
    for _ in range(trials):
        m.spin(rng, 1_000 * MOJO)
    return m.paid / m.wagered


def stress(d, spins, trials):
    """Every spin at max wager: how often does the main pot fall below half the seed?"""
    global D
    old, D = D, d
    busts = 0
    worst = 1.0
    for t in range(trials):
        rng = random.Random(1000 + t)
        m = Machine(36_000 * MOJO, 500 * MOJO, 1_000 * MOJO, 2_500 * MOJO)
        lo = m.main
        for _ in range(spins):
            m.spin(rng, m.max_wager())
            lo = min(lo, m.main)
        worst = min(worst, lo / (36_000 * MOJO))
        busts += lo < 18_000 * MOJO
    D = old
    return busts / trials, worst


if __name__ == "__main__":
    rtp = main_rtp(2_000_000, seed=1)
    jp_share = sum(JACKPOT_BPS.values()) / 10_000
    keep = 1 - FEE_BPS / 10_000 - jp_share - rtp
    print(f"per LOVE wagered: fee {FEE_BPS/100:.1f}%  jackpots {jp_share:.1%}  "
          f"line+bonus RTP {rtp:.2%}  kept in pot {keep:.2%}")
    print(f"player RTP over time ~ {rtp + jp_share * JACKPOT_PAYS_BPS / 10_000:.2%} "
          f"(jackpot pools pay back as they hit)\n")

    for bet in (5, 20):
        rng = random.Random(7)
        m = Machine(36_000 * MOJO, 500 * MOJO, 1_000 * MOJO, 2_500 * MOJO)
        lo = m.main
        print(f"players bet {bet} LOVE per spin (capped at pot/{D}); seed 40k = main 36k + jackpots 4k")
        for i in range(1, 200_001):
            m.spin(rng, bet * MOJO)
            lo = min(lo, m.main)
            if i in (10_000, 50_000, 100_000, 200_000):
                L = lambda v: v // MOJO
                print(f"  {i:>7,} spins: main {L(m.main):>9,}  max bet {L(m.max_wager()):>4,}  "
                      f"mini {L(m.jp['MINI']):>6,}  major {L(m.jp['MAJOR']):>6,}  grand {L(m.jp['GRAND']):>7,}  "
                      f"dev fees {L(m.fees):>7,}  (LOVE)")
        print(f"  lowest main pot {lo // MOJO:,} LOVE; jackpot hits {m.jp_hits}; RTP {m.paid/m.wagered:.2%}\n")

    print("stress test: every spin at max bet, 5,000 spins from the 40k seed, 400 runs")
    for d in (500, 1000, 2000):
        p, worst = stress(d, 5_000, 400)
        print(f"  D={d:>4} (max bet {36_000//d:>2} LOVE at seed): pot fell below half the seed in "
              f"{p:.1%} of runs; worst dip to {worst:.0%} of seed")
