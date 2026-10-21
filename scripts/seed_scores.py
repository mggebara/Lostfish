"""Per-seed scores vs the field (and vs each opponent) from a gauntlet's run.log, with crude 95% CIs.

    .venv/bin/python scripts/seed_scores.py experiments/<name> [--seeds A,B,C]
Seeds default to the engines that appear on both sides against everyone else (fastchess -seeds).
"""

from __future__ import annotations

import collections
import math
import re
import sys
from pathlib import Path

PAT = re.compile(r"^Finished game \d+ \((\S+) vs (\S+)\): (1-0|0-1|1/2-1/2)")


def main() -> None:
    exp = Path(sys.argv[1])
    seeds: set[str] | None = None
    if len(sys.argv) > 3 and sys.argv[2] == "--seeds":
        seeds = set(sys.argv[3].split(","))
    games = []
    for line in (exp / "run.log").open():
        m = PAT.match(line)
        if m:
            w, b, r = m.groups()
            games.append((w, b, {"1-0": 1.0, "0-1": 0.0, "1/2-1/2": 0.5}[r]))
    if seeds is None:  # engines that appear against >= 2 distinct opponents are seeds
        opps = collections.defaultdict(set)
        for w, b, _ in games:
            opps[w].add(b)
            opps[b].add(w)
        seeds = {
            e for e, o in opps.items() if len(o) >= 2 and e.startswith(("LostFish", "Stockfish"))
        }
    vs = collections.defaultdict(lambda: [0.0, 0])
    pair = collections.defaultdict(lambda: [0.0, 0])
    h2h = collections.defaultdict(lambda: [0.0, 0])
    for w, b, pw in games:
        if w in seeds and b in seeds:
            h2h[(w, b)][0] += pw
            h2h[(w, b)][1] += 1
            h2h[(b, w)][0] += 1 - pw
            h2h[(b, w)][1] += 1
            continue
        for s, o, p in ((w, b, pw), (b, w, 1 - pw)):
            if s in seeds:
                vs[s][0] += p
                vs[s][1] += 1
                pair[(s, o)][0] += p
                pair[(s, o)][1] += 1
    print(f"{exp.name}: {len(games)} games")
    print(f"{'seed':18s} {'vs field':>10s} {'±95%':>6s}")
    for s in sorted(vs, key=lambda k: -vs[k][0] / max(1, vs[k][1])):
        p, n = vs[s]
        print(f"{s:18s} {100 * p / n:9.1f}% {100 * 1.96 * math.sqrt(0.15 / n):5.1f}  (n={n})")
    for o in sorted({o for _, o in pair}):
        row = "  ".join(
            f"{s}: {100 * pair[(s, o)][0] / max(1, pair[(s, o)][1]):5.1f}%" for s in sorted(vs)
        )
        print(f"  vs {o:14s} {row}")
    if h2h:
        print("seed vs seed (row scores vs column):")
        for a in sorted(vs):
            print(
                f"  {a:18s} "
                + "  ".join(
                    f"{b[:10]:>10s}={100 * h2h[(a, b)][0] / max(1, h2h[(a, b)][1]):5.1f}%"
                    for b in sorted(vs)
                    if b != a
                )
            )


if __name__ == "__main__":
    main()
