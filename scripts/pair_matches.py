"""Pair two 2-engine fastchess matches by opening (Round) and report the seed-vs-seed difference.

    .venv/bin/python scripts/pair_matches.py experiments/A experiments/B [--opponent lc0]

Both matches must use the same openings (same srand/order), so round r of A and round r of B share an opening. In each
match the "seed" is the engine whose name does not contain --opponent. Games are paired by (Round, seed colour); the
independent unit for the error bar is the round (its two games share an opening). Output: each seed's W/D/L and score,
the paired difference A - B in percentage points with SE and 95% CI, and rounds where A did better / worse / the same.
"""

from __future__ import annotations

import argparse
import collections
import math
import statistics
from pathlib import Path

import chess.pgn

SCORE = {"1-0": 1.0, "0-1": 0.0, "1/2-1/2": 0.5}


def load(exp: Path, opp_sub: str) -> tuple[str, dict[tuple[str, str], float]]:
    """Return (seed name, {(round, seed colour): seed score})."""
    games: dict[tuple[str, str], float] = {}
    seed_name = ""
    with (exp / "games.pgn").open(encoding="utf-8", errors="replace") as f:
        while (g := chess.pgn.read_game(f)) is not None:
            h = g.headers
            if h.get("Result") not in SCORE:
                continue
            w, b = h["White"], h["Black"]
            if opp_sub in w and opp_sub not in b:
                seed, colour, s = b, "black", 1 - SCORE[h["Result"]]
            elif opp_sub in b and opp_sub not in w:
                seed, colour, s = w, "white", SCORE[h["Result"]]
            else:
                continue
            seed_name = seed
            games[(h.get("Round", "?"), colour)] = s
    return seed_name, games


def summary(name: str, games: dict[tuple[str, str], float]) -> str:
    n = len(games)
    w = sum(1 for s in games.values() if s == 1.0)
    d = sum(1 for s in games.values() if s == 0.5)
    pct = 100 * sum(games.values()) / n if n else float("nan")
    by_col = {}
    for c in ("white", "black"):
        v = [s for (_, col), s in games.items() if col == c]
        by_col[c] = 100 * sum(v) / len(v) if v else float("nan")
    return f"{name:28s} {n:4d} games  {w}W {d}D {n - w - d}L  {pct:5.1f}%  (W {by_col['white']:.1f} / B {by_col['black']:.1f})"


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("a", type=Path)
    ap.add_argument("b", type=Path)
    ap.add_argument(
        "--opponent", default="lc0", help="substring of the common opponent's engine name"
    )
    args = ap.parse_args()
    name_a, ga = load(args.a, args.opponent)
    name_b, gb = load(args.b, args.opponent)
    print(summary(f"A {name_a}", ga))
    print(summary(f"B {name_b}", gb))
    common = sorted(set(ga) & set(gb), key=lambda k: (int(k[0]) if k[0].isdigit() else k[0], k[1]))
    if not common:
        print("no paired games (different Rounds?)")
        return
    per_round: dict[str, list[float]] = collections.defaultdict(list)
    for k in common:
        per_round[k[0]].append(ga[k] - gb[k])
    m = [sum(v) / len(v) for v in per_round.values()]  # per-round mean per-game difference
    r = len(m)
    mean = 100 * statistics.fmean(m)
    se = 100 * statistics.stdev(m) / math.sqrt(r) if r > 1 else float("nan")
    better = sum(1 for x in m if x > 0)
    worse = sum(1 for x in m if x < 0)
    print(
        f"paired A - B: {mean:+.1f} points (SE {se:.1f}, 95% [{mean - 1.96 * se:+.1f}, {mean + 1.96 * se:+.1f}], "
        f"z={mean / se if se else float('nan'):.2f}) over {len(common)} games in {r} rounds; "
        f"A better in {better}, worse in {worse}, same in {r - better - worse}"
    )


if __name__ == "__main__":
    main()
