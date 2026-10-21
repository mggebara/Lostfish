"""Game-length metric for ceiling-limited gauntlets: when every seed beats an opponent, who wins faster?

    .venv/bin/python scripts/game_length.py experiments/<name> [opponent-name-substring]

Per seed vs the opponent: games, score, mean plies in decisive games, mean plies in won games.
"""

from __future__ import annotations

import collections
import statistics
import sys
from pathlib import Path

import chess.pgn


def main() -> None:
    exp = Path(sys.argv[1])
    opp_sub = sys.argv[2] if len(sys.argv) > 2 else None
    rows: dict[str, list[tuple[float, int]]] = collections.defaultdict(list)
    with (exp / "games.pgn").open() as f:
        while (g := chess.pgn.read_game(f)) is not None:
            w, b, r = g.headers["White"], g.headers["Black"], g.headers["Result"]
            if r not in ("1-0", "0-1", "1/2-1/2"):
                continue
            names = (w, b)
            opp = next((n for n in names if opp_sub and opp_sub in n), None)
            if opp_sub and opp is None:
                continue
            seed = b if opp == w else w if opp == b else None
            if seed is None:
                continue
            pw = {"1-0": 1.0, "0-1": 0.0, "1/2-1/2": 0.5}[r]
            p = pw if seed == w else 1 - pw
            rows[seed].append((p, len(list(g.mainline_moves()))))
    print(f"{'seed':18s} {'n':>4s} {'score':>6s} {'plies(dec)':>10s} {'plies(won)':>10s}")
    for seed, v in sorted(rows.items()):
        dec = [n for p, n in v if p != 0.5]
        won = [n for p, n in v if p == 1.0]
        print(
            f"{seed:18s} {len(v):4d} {100 * sum(p for p, _ in v) / len(v):5.1f}% "
            f"{statistics.mean(dec) if dec else float('nan'):10.1f} {statistics.mean(won) if won else float('nan'):10.1f}"
        )


if __name__ == "__main__":
    main()
