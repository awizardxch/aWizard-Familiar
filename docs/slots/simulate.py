"""Love Slots game math: Monte Carlo of the model in LOVE_SLOTS_SPEC.md.

Play happens in a state channel between the player and the Bank. Every wager is
split into a dev fee, jackpot contributions, and the Bank's main pot. Line and
bonus wins pay fixed multiples of the wager, capped at MAX_WIN per spin (the
Bank stakes MAX_WIN x wager into each hand). The max wager scales with the main
pot (MAIN / D). Jackpots pay from their own pools, scaled by wager / max wager.
All amounts are in mojos (1 LOVE = 1,000 mojos).
Run: python3 -I simulate.py
"""
import random

# ── reels ───────────────────────────────────────────────────────────────────
STRIP = {"HEART": 1, "WIZARD": 3, "SPELLBOOK": 5, "POTION": 4, "STAR": 12, "MOON": 6}
SYMS, WEIGHTS = list(STRIP), list(STRIP.values())

# line wins: multiples of the wager
LINE_X = {"3 WIZARD": 80, "3 STAR": 8, "2 HEART": 5, "3 MOON": 5}
# 3 HEART wins the Major; 3 MOON / 3 POTION / 3 SPELLBOOK start bonuses

FREE_SPINS, FREE_SPIN_MULT = 8, 2               # Moonlit Free Spins
CAULDRONS = [15, 40, "MINI"]                    # Potion Pick (a real choice)

# Heart Lock (Hold & Win): 15 cells, starts with 3 hearts, 3 respins,
# every new heart resets the respins to 3; filling all 15 wins the Grand
HL_CELLS, HL_START, HL_RESPINS, HL_LAND = 15, 3, 3, 0.07
HL_VALUES = [(2, 40), (3, 25), (5, 15), (8, 10), (15, 6), (50, 3), ("MINI", 0.8), ("MAJOR", 0.2)]

# ── money ───────────────────────────────────────────────────────────────────
FEE_BPS = 300                                   # dev service fee
JACKPOT_BPS = {"MINI": 50, "MAJOR": 100, "GRAND": 150}
JACKPOT_PAYS_BPS = 9000                         # max bet takes 90%; the rest re-seeds
MAX_WIN = 250                                   # published max win per spin, x wager
D = 2000                                        # max wager = MAIN / D
MOJO = 1_000
W_MIN = 1 * MOJO


def line_tier(r):
    for s in SYMS:
        if r.count(s) == 3:
            return f"3 {s}"
    return "2 HEART" if r.count("HEART") == 2 else None


def heart_value(rng):
    vals, weights = zip(*HL_VALUES)
    return rng.choices(vals, weights=weights)[0]


def heart_lock(rng):
    """Returns (total multiplier, list of jackpots won)."""
    hearts = [heart_value(rng) for _ in range(HL_START)]
    respins = HL_RESPINS
    while respins and len(hearts) < HL_CELLS:
        landed = sum(rng.random() < HL_LAND for _ in range(HL_CELLS - len(hearts)))
        if landed:
            hearts += [heart_value(rng) for _ in range(landed)]
            respins = HL_RESPINS
        else:
            respins -= 1
    hearts = hearts[:HL_CELLS]
    mult = sum(v for v in hearts if isinstance(v, int))
    jps = [v for v in hearts if isinstance(v, str)]
    if len(hearts) == HL_CELLS:
        jps.append("GRAND")
    return mult, jps


class Bank:
    def __init__(self, main, mini=0, major=0, grand=0):
        self.main = main
        self.jp = {"MINI": mini, "MAJOR": major, "GRAND": grand}
        self.paid = self.jp_paid = self.fees = self.wagered = 0
        self.hits = {"FREE SPINS": 0, "POTION PICK": 0, "HEART LOCK": 0, "MAX WIN": 0,
                     "MINI": 0, "MAJOR": 0, "GRAND": 0}

    def max_wager(self):
        return max(W_MIN, self.main // D)

    def jackpot(self, name, w, wmax):
        out = self.jp[name] * JACKPOT_PAYS_BPS * min(w, wmax) // (10_000 * wmax)
        self.jp[name] -= out
        self.paid += out
        self.jp_paid += out
        self.hits[name] += 1

    def spin(self, rng, w):
        wmax = self.max_wager()
        w = min(w, wmax)                         # stakes over the cap are refused
        fee = -(-w * FEE_BPS // 10_000)          # rounds up, never 0
        jps = {k: w * b // 10_000 for k, b in JACKPOT_BPS.items()}
        self.fees += fee
        self.wagered += w
        for k, v in jps.items():
            self.jp[k] += v
        self.main += w - fee - sum(jps.values())

        mult, won = 0, []
        t = line_tier(rng.choices(SYMS, weights=WEIGHTS, k=3))
        if t == "3 HEART":
            won.append("MAJOR")
        elif t in LINE_X:
            mult += LINE_X[t]
        if t == "3 MOON":
            self.hits["FREE SPINS"] += 1
            for _ in range(FREE_SPINS):
                ft = line_tier(rng.choices(SYMS, weights=WEIGHTS, k=3))
                if ft == "3 HEART":
                    won.append("MAJOR")
                elif ft in LINE_X:
                    mult += LINE_X[ft] * FREE_SPIN_MULT
        elif t == "3 POTION":
            self.hits["POTION PICK"] += 1
            c = rng.choice(CAULDRONS)
            if c == "MINI":
                won.append("MINI")
            else:
                mult += c
        elif t == "3 SPELLBOOK":
            self.hits["HEART LOCK"] += 1
            m, j = heart_lock(rng)
            mult += m
            won += j

        if mult >= MAX_WIN:
            self.hits["MAX WIN"] += 1
        out = min(mult, MAX_WIN) * w
        self.main -= out
        self.paid += out
        for name in won:
            self.jackpot(name, w, wmax)


def base_rtp(trials, seed):
    """Line + bonus return per unit wagered, excluding jackpots."""
    b = Bank(main=10**15)
    rng = random.Random(seed)
    for _ in range(trials):
        b.spin(rng, 1_000 * MOJO)
    return (b.paid - b.jp_paid) / b.wagered, b.hits, trials


def stress(d, spins, trials):
    """Every spin at max wager: how often does the main pot fall below half the seed?"""
    global D
    old, D = D, d
    busts, worst = 0, 1.0
    for t in range(trials):
        rng = random.Random(1000 + t)
        b = Bank(36_000 * MOJO, 500 * MOJO, 1_000 * MOJO, 2_500 * MOJO)
        lo = b.main
        for _ in range(spins):
            b.spin(rng, b.max_wager())
            lo = min(lo, b.main)
        worst = min(worst, lo / (36_000 * MOJO))
        busts += lo < 18_000 * MOJO
    D = old
    return busts / trials, worst


if __name__ == "__main__":
    rtp, hits, n = base_rtp(2_000_000, seed=1)
    jp_share = sum(JACKPOT_BPS.values()) / 10_000
    keep = 1 - FEE_BPS / 10_000 - jp_share - rtp
    print(f"per LOVE wagered: fee {FEE_BPS/100:.1f}%  jackpots {jp_share:.1%}  "
          f"line+bonus RTP {rtp:.2%}  kept in pot {keep:.2%}")
    print(f"player RTP over time ~ {rtp + jp_share * JACKPOT_PAYS_BPS / 10_000:.2%}")
    print("frequency per spin: " + ", ".join(f"{k} 1 in {n/v:,.0f}" for k, v in hits.items() if v))
    print()

    for bet in (5, 20):
        rng = random.Random(7)
        b = Bank(36_000 * MOJO, 500 * MOJO, 1_000 * MOJO, 2_500 * MOJO)
        lo = b.main
        print(f"players bet {bet} LOVE per spin (capped at MAIN/{D}); seed 40k = main 36k + jackpots 4k")
        for i in range(1, 200_001):
            b.spin(rng, bet * MOJO)
            lo = min(lo, b.main)
            if i in (10_000, 50_000, 100_000, 200_000):
                L = lambda v: v // MOJO
                print(f"  {i:>7,} spins: main {L(b.main):>9,}  max bet {L(b.max_wager()):>4,}  "
                      f"mini {L(b.jp['MINI']):>6,}  major {L(b.jp['MAJOR']):>6,}  grand {L(b.jp['GRAND']):>7,}  "
                      f"dev fees {L(b.fees):>7,}  (LOVE)")
        print(f"  lowest main pot {lo // MOJO:,} LOVE; RTP {b.paid/b.wagered:.2%}\n")

    print("stress test: every spin at max bet, 5,000 spins from the 40k seed, 400 runs")
    for d in (1000, 2000):
        p, worst = stress(d, 5_000, 400)
        print(f"  D={d:>4} (max bet {36_000//d:>2} LOVE at seed): pot fell below half the seed in "
              f"{p:.1%} of runs; worst dip to {worst:.0%} of seed")
