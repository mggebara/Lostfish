"""Per-move speed check (docs/GPU_BOX.md job 1): drive LostFish over UCI on a few middlegame positions.

    .venv/bin/python scripts/speed_check.py [config.yaml] [profile]      # default: v2_tree2_g50 + lc0-t1-n200

Prints wall time per move and the `timings_ms` of the matching line in logs/moves.jsonl (certify / steer / proxy / eval).
The first move includes the one-off engine start-up (CUDA init for an lc0 proxy); judge the rest.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import chess
import chess.engine

FENS = [
    "r2q1rk1/1p1nbppp/p2pbn2/4p3/4P3/1NN1BP2/PPPQ2PP/2KR1B1R w - - 3 11",
    "r1bq1rk1/pp2bppp/2n1pn2/3p4/2PP4/2N1PN2/PP3PPP/R1BQKB1R w KQ - 0 8",
    "r1bqr1k1/ppp2ppp/2np1n2/2b1p3/2B1P3/2NP1N2/PPP2PPP/R1BQR1K1 w - - 0 8",
    "2r2rk1/pp1bqppp/2nppn2/8/2PNP3/2N1B3/PP2QPPP/2RR2K1 w - - 0 14",
    "r1b2rk1/pp2bppp/2n1pn2/q7/2BP4/P1N1PN2/1P3PPP/R2QK2R w KQ - 0 10",
    "r2qkb1r/pb1n1ppp/1p2pn2/2pp4/3P4/1PN1PN2/PBP1BPPP/R2QK2R w KQkq - 0 8",
]


def last_telemetry(log: Path, fen: str) -> dict:
    """Last complete JSON line for `fen` (the engine may still be writing the file)."""
    for line in reversed(log.read_text().splitlines()):
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if rec.get("fen") == fen:
            return rec
    return {}


def main() -> None:
    cfg = sys.argv[1] if len(sys.argv) > 1 else "configs/variants/v2_tree2_g50.yaml"
    profile = sys.argv[2] if len(sys.argv) > 2 else "lc0-t1-n200"
    eng = chess.engine.SimpleEngine.popen_uci(["scripts/lostfish", "--config", cfg])
    eng.configure({"Steering": True, "Profile": profile, "Hash": 64, "SyzygyPath": "tb/syzygy"})
    walls: list[float] = []
    try:
        for i, fen in enumerate(FENS):
            t = time.perf_counter()
            r = eng.play(chess.Board(fen), chess.engine.Limit(nodes=20000))
            ms = (time.perf_counter() - t) * 1000
            rec = last_telemetry(Path("logs/moves.jsonl"), fen)
            tm = rec.get("timings_ms") or {}
            print(
                f"[{i}] wall {ms:6.0f} ms  move {r.move}  cands {len(rec.get('candidates') or [])}  "
                f"total {tm.get('total', 0):.0f}  certify {tm.get('certify', 0):.0f}  steer {tm.get('steer', 0):.0f}  "
                f"proxy {tm.get('proxy', 0):.0f}  eval {tm.get('eval', 0):.0f}"
            )
            if i:
                walls.append(ms)
    finally:
        eng.quit()
    if walls:
        print(
            f"moves 1..{len(FENS) - 1}: median wall {sorted(walls)[len(walls) // 2]:.0f} ms, max {max(walls):.0f} ms"
        )


if __name__ == "__main__":
    main()
