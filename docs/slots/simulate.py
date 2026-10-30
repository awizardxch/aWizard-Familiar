"""Love Slots game math: Monte Carlo of the model in LOVE_SLOTS_SPEC.md.

5 reels x 3 rows, 20 paylines. The player picks lines (1/5/10/15/20), coins per
line (1-5) and a coin value; total bet = lines x coins x coin value.
Line wins pay multiples of the line bet; scatter and feature wins pay multiples
of the total bet. Each spin's wins are capped at MAX_WIN x total bet (the Bank
stakes that much into each hand). Jackpots are not on the reels: every spin
enters the Love Draw, with odds scaled by bet / global max bet; the Grand needs
max lines and max coins.
All amounts are in mojos (1 LOVE = 1,000 mojos).
Run: python3 -I simulate.py
"""
import random

# ── reels ───────────────────────────────────────────────────────────────────
# One strip per reel, built from these weights and shuffled with a fixed seed.
# A spin picks a stop on each strip; the 3 visible rows are consecutive stops.
WEIGHTS = {
    "HEART": 3,      # wild: substitutes for line symbols, pays the top award
    "WIZARD": 5, "OWL": 7, "CRYSTAL": 10, "CANDLE": 14, "STAR": 18, "LEAF": 22,
    "MOON": 2,       # scatter: 3+ anywhere pays and starts Moonlit Free Spins
    "POTION": 2,     # scatter: 3+ anywhere starts Potion Pick
    "SPELLBOOK": 12, # 6+ anywhere starts Heart Lock
}
SCATTERS = {"MOON", "POTION", "SPELLBOOK"}


def build_strip(reel):
    strip = [s for s, w in WEIGHTS.items() for _ in range(w)]
    random.Random(1000 + reel).shuffle(strip)
    return strip


STRIPS = [build_strip(r) for r in range(5)]

LINES = [
    [1, 1, 1, 1, 1], [0, 0, 0, 0, 0], [2, 2, 2, 2, 2], [0, 1, 2, 1, 0], [2, 1, 0, 1, 2],
    [0, 0, 1, 2, 2], [2, 2, 1, 0, 0], [1, 0, 0, 0, 1], [1, 2, 2, 2, 1], [1, 0, 1, 0, 1],
    [1, 2, 1, 2, 1], [0, 1, 0, 1, 0], [2, 1, 2, 1, 2], [1, 1, 0, 1, 1], [1, 1, 2, 1, 1],
    [0, 1, 1, 1, 0], [2, 1, 1, 1, 2], [0, 2, 0, 2, 0], [2, 0, 2, 0, 2], [0, 0, 2, 0, 0],
]
LINE_CHOICES = (1, 5, 10, 15, 20)
MAX_COINS = 5

# line pays, x line bet, for 3 / 4 / 5 of a kind (left to right)
PAYS = {
    "HEART": (100, 500, 2000), "WIZARD": (60, 250, 1000), "OWL": (35, 120, 450),
    "CRYSTAL": (25, 70, 230), "CANDLE": (12, 35, 140), "STAR": (7, 23, 90), "LEAF": (5, 12, 45),
}
TOP_AWARD_MAX_COINS = 5000      # 5 HEART at max coins pays this instead of 2000
MOON_PAYS = {3: 5, 4: 20, 5: 100}  # x total bet, plus free spins
FREE_SPINS, FREE_SPIN_MULT = 12, 3
CAULDRONS = [10, 25, 60]        # Potion Pick, x total bet

# Heart Lock (Hold & Win): the 6+ spellbooks lock as hearts; 3 respins; each
# new heart resets them to 3; filling all 15 cells pays FULL_GRID x total bet
HL_TRIGGER, HL_CELLS, HL_RESPINS, HL_LAND = 6, 15, 3, 0.06
HL_VALUES = [(1, 35), (2, 25), (3, 18), (5, 12), (10, 7), (25, 3)]
HL_FULL_GRID = 250

# ── money ───────────────────────────────────────────────────────────────────
FEE_BPS = 300                                   # dev service fee
JACKPOT_BPS = {"MINI": 50, "MAJOR": 100, "GRAND": 150}
# Love Draw odds per spin at the global max bet, scaled by bet / max bet
DRAW_ODDS = {"MINI": 1 / 1_000, "MAJOR": 1 / 10_000, "GRAND": 1 / 50_000}
JACKPOT_PAYS_BPS = 9000                         # winner takes 90%; 10% re-seeds
MAX_WIN = 500                                   # published max win per spin, x total bet
D = 2000                                        # global max total bet = MAIN / D
MOJO = 1_000
COIN_VALUES = (100, 250, 500, 1_000)            # 0.1 / 0.25 / 0.5 / 1 LOVE
W_MIN = COIN_VALUES[0]                          # 1 line x 1 coin x 0.1 LOVE


def spin_grid(rng):
    grid = []
    for strip in STRIPS:
        stop = rng.randrange(len(strip))
        grid.append([strip[(stop + r) % len(strip)] for r in range(3)])
    return grid  # grid[reel][row]


def line_win(symbols, coins):
    """Multiple of the line bet for one payline."""
    target = next((s for s in symbols if s != "HEART"), "HEART")
    if target in SCATTERS:
        target = "HEART"
    run = 0
    for s in symbols:
        if s == target or s == "HEART":
            run += 1
        else:
            break
    wild_run = 0
    for s in symbols:
        if s == "HEART":
            wild_run += 1
        else:
            break
    best = 0
    if target != "HEART" and run >= 3:
        best = PAYS[target][run - 3]
    if wild_run >= 3:
        top = PAYS["HEART"][wild_run - 3]
        if wild_run == 5 and coins == MAX_COINS:
            top = TOP_AWARD_MAX_COINS
        best = max(best, top)
    return best


def count(grid, sym):
    return sum(row == sym for reel in grid for row in reel)


def lines_win(grid, lines, coins):
    """Sum of line multiples (x line bet) over the active lines."""
    return sum(line_win([grid[r][LINES[i][r]] for r in range(5)], coins) for i in range(lines))


def heart_lock(rng, start):
    hearts = [rng.choices(*zip(*HL_VALUES))[0] for _ in range(start)]
    respins = HL_RESPINS
    while respins and len(hearts) < HL_CELLS:
        landed = sum(rng.random() < HL_LAND for _ in range(HL_CELLS - len(hearts)))
        if landed:
            hearts += [rng.choices(*zip(*HL_VALUES))[0] for _ in range(landed)]
            respins = HL_RESPINS
        else:
            respins -= 1
    hearts = hearts[:HL_CELLS]
    return sum(hearts) + (HL_FULL_GRID if len(hearts) == HL_CELLS else 0)


def play(rng, lines, coins, stats):
    """Returns the spin's win as a multiple of the total bet (before the cap)."""
    grid = spin_grid(rng)
    per_line = 1 / lines                       # line bet as a share of total bet
    win = lines_win(grid, lines, coins) * per_line
    moons, potions, books = count(grid, "MOON"), count(grid, "POTION"), count(grid, "SPELLBOOK")
    if moons >= 3:
        stats["FREE SPINS"] = stats.get("FREE SPINS", 0) + 1
        win += MOON_PAYS[min(moons, 5)]
        for _ in range(FREE_SPINS):            # no retrigger
            win += lines_win(spin_grid(rng), lines, coins) * per_line * FREE_SPIN_MULT
    if potions >= 3:
        stats["POTION PICK"] = stats.get("POTION PICK", 0) + 1
        win += rng.choice(CAULDRONS)
    if books >= HL_TRIGGER:
        stats["HEART LOCK"] = stats.get("HEART LOCK", 0) + 1
        win += heart_lock(rng, books)
    if win >= MAX_WIN:
        stats["MAX WIN"] = stats.get("MAX WIN", 0) + 1
    return win


def base_rtp(trials, lines, coins, seed):
    rng = random.Random(seed)
    stats, total = {}, 0.0
    for _ in range(trials):
        total += min(play(rng, lines, coins, stats), MAX_WIN)
    return total / trials, stats


class Bank:
    def __init__(self, main, mini=0, major=0, grand=0):
        self.main = main
        self.jp = {"MINI": mini, "MAJOR": major, "GRAND": grand}
        self.paid = self.fees = self.wagered = 0
        self.jp_hits = {"MINI": 0, "MAJOR": 0, "GRAND": 0}

    def max_bet(self):
        return max(W_MIN, self.main // D)

    def spin(self, rng, lines, coins, coin_value):
        bet = lines * coins * coin_value
        if bet > self.max_bet():
            return False                        # the UI only offers bets under the cap
        fee = -(-bet * FEE_BPS // 10_000)       # rounds up, never 0
        self.fees += fee
        self.wagered += bet
        contrib = {k: bet * b // 10_000 for k, b in JACKPOT_BPS.items()}
        for k, v in contrib.items():
            self.jp[k] += v
        self.main += bet - fee - sum(contrib.values())

        win = int(min(play(rng, lines, coins, {}), MAX_WIN) * bet)
        self.main -= win
        self.paid += win

        scale = bet / self.max_bet()            # Love Draw: odds scale with bet
        for k, odds in DRAW_ODDS.items():
            if k == "GRAND" and not (lines == 20 and coins == MAX_COINS):
                continue
            if rng.random() < odds * scale:
                out = self.jp[k] * JACKPOT_PAYS_BPS // 10_000
                self.jp[k] -= out
                self.paid += out
                self.jp_hits[k] += 1
        return True


def choose_bet(bank, lines, coins):
    """Largest coin value that keeps the bet under the cap; None if none fits."""
    for cv in reversed(COIN_VALUES):
        if lines * coins * cv <= bank.max_bet():
            return cv
    return None


if __name__ == "__main__":
    n = 300_000
    jp_share = sum(JACKPOT_BPS.values()) / 10_000
    print("base game + features RTP by bet shape (300k spins each):")
    for lines, coins in ((1, 1), (10, 1), (20, 1), (20, MAX_COINS)):
        rtp, stats = base_rtp(n, lines, coins, seed=1)
        grand = lines == 20 and coins == MAX_COINS
        jp_back = (jp_share if grand else jp_share - JACKPOT_BPS["GRAND"] / 10_000) * JACKPOT_PAYS_BPS / 10_000
        print(f"  {lines:>2} lines x {coins} coins: base {rtp:6.2%}  + jackpots ~{jp_back:.2%}"
              f"  = player RTP ~{rtp + jp_back:6.2%}   "
              + ", ".join(f"{k} 1 in {n/v:,.0f}" for k, v in sorted(stats.items())))
    print()

    for label, lines, coins in (("20 lines x 1 coin", 20, 1), ("max bet: 20 lines x 5 coins", 20, MAX_COINS)):
        rng = random.Random(7)
        b = Bank(36_000 * MOJO, 500 * MOJO, 1_000 * MOJO, 2_500 * MOJO)
        lo = b.main
        print(f"{label}, biggest coin value under the cap; seed 40k = main 36k + jackpots 4k")
        for i in range(1, 100_001):
            cv = choose_bet(b, lines, coins)
            if cv:
                b.spin(rng, lines, coins, cv)
            lo = min(lo, b.main)
            if i in (10_000, 50_000, 100_000):
                L = lambda v: v / MOJO
                print(f"  {i:>7,} spins: main {L(b.main):>9,.0f}  max bet {L(b.max_bet()):>5,.1f}  "
                      f"mini {L(b.jp['MINI']):>6,.0f}  major {L(b.jp['MAJOR']):>6,.0f}  "
                      f"grand {L(b.jp['GRAND']):>7,.0f}  dev fees {L(b.fees):>7,.0f}  (LOVE)")
        print(f"  lowest main pot {lo / MOJO:,.0f} LOVE; jackpot hits {b.jp_hits}; "
              f"RTP {b.paid / b.wagered:.2%}\n")
