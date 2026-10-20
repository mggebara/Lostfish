"""Offline check of the opponent proxy: did the opponent actually play the reply we predicted?

Joins each LostFish move in an experiment's games.pgn with its telemetry record (by FEN + profile) and
reports, per experiment: top-1/top-2 accuracy of the predicted reply, how often steering deviated from
Stockfish's best, the certified cp given up when it did, and whether the chosen candidate's "expected eval"
edge over the best candidate was real (eval after the *actual* reply is not logged, so we report the
predicted edge and the realised score of games instead).

    .venv/bin/python scripts/proxy_accuracy.py experiments/oracle_d8 experiments/oracle_d10 ...
"""

from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

import chess
import chess.pgn

LOG = Path("logs/moves.jsonl")


def load_telemetry() -> dict[tuple[str, str], dict]:
    out: dict[tuple[str, str], dict] = {}
    with LOG.open() as f:
        for line in f:
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            if d.get("player") != "steering":
                continue
            out[(d.get("profile") or "", d["fen"])] = d  # later records win; deterministic anyway
    return out


def analyse(exp: Path, tele: dict[tuple[str, str], dict]) -> None:
    pgn_path = exp / "games.pgn"
    stats = collections.Counter()
    cp_given = []
    pred_edge = []
    with pgn_path.open() as f:
        while True:
            game = chess.pgn.read_game(f)
            if game is None:
                break
            white, black = game.headers["White"], game.headers["Black"]
            if white.startswith("LostFish"):
                us, name = chess.WHITE, white
            elif black.startswith("LostFish"):
                us, name = chess.BLACK, black
            else:
                continue
            profile = name.replace("LostFish-oracle-", "sf-") if "oracle" in name else "_generic"
            board = game.board()
            moves = list(game.mainline_moves())
            for i, mv in enumerate(moves):
                if board.turn == us:
                    rec = tele.get((profile, board.fen()))
                    if rec is None:
                        stats["no_telemetry"] += 1
                    else:
                        stats["moves"] += 1
                        if rec["chosen"] != mv.uci():
                            stats["chosen_mismatch"] += 1
                        cands = rec["candidates"]
                        best = cands[0]
                        chosen = next((c for c in cands if c["move"] == rec["chosen"]), None)
                        if rec.get("reason") == "steer":
                            stats["steer_decisions"] += 1
                            if chosen is not None and chosen["move"] != best["move"]:
                                stats["deviated"] += 1
                                cp_given.append(best["cp"] - chosen["cp"])
                                pred_edge.append(chosen.get("expected_eval", 0) - best.get("expected_eval", 0))
                        if chosen is not None and chosen.get("replies") and i + 1 < len(moves):
                            actual = moves[i + 1].uci()
                            preds = sorted(chosen["replies"], key=lambda r: -r["weight"])
                            stats["reply_checked"] += 1
                            if preds[0]["move"] == actual:
                                stats["reply_top1"] += 1
                            if any(p["move"] == actual for p in preds[:2]):
                                stats["reply_top2"] += 1
                board.push(mv)
    n = stats["moves"] or 1
    rc = stats["reply_checked"] or 1
    print(f"\n== {exp.name} ==")
    print(f"LostFish moves matched: {stats['moves']} (no telemetry: {stats['no_telemetry']}, chosen mismatch: {stats['chosen_mismatch']})")
    print(f"steer decisions: {stats['steer_decisions']}  deviated from SF best: {stats['deviated']} ({100*stats['deviated']/n:.1f}% of moves)")
    if cp_given:
        cp_given.sort()
        print(f"certified cp given up when deviating: mean {sum(cp_given)/len(cp_given):.1f}, median {cp_given[len(cp_given)//2]}, max {cp_given[-1]}")
        print(f"predicted expected-eval edge of chosen over best: mean {sum(pred_edge)/len(pred_edge):+.1f} cp")
    print(f"predicted reply accuracy: top-1 {100*stats['reply_top1']/rc:.1f}%  top-2 {100*stats['reply_top2']/rc:.1f}%  (n={stats['reply_checked']})")


def main() -> None:
    tele = load_telemetry()
    print(f"telemetry steering records: {len(tele)}")
    for arg in sys.argv[1:]:
        analyse(Path(arg), tele)


if __name__ == "__main__":
    main()
