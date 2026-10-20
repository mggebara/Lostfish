"""PassthroughPlayer: plays Stockfish's best move at `budget.certify_nodes` (MultiPV=1).

The Phase 0 baseline and the fallback whenever steering is off or unavailable.
"""

from __future__ import annotations

import time

import chess

from lostfish.config import Config
from lostfish.engines import Engine
from lostfish.timeman import Budget


class PassthroughPlayer:
    """Implements the Player protocol (see docs/INTERFACES.md) with one persistent Stockfish."""

    def __init__(self, cfg: Config) -> None:
        self.cfg = cfg
        self.engine = Engine(
            cfg.engines.stockfish,
            hash_mb=cfg.engines.hash_mb,
            threads=1,
            syzygy_path=cfg.engines.syzygy_path,
            name="passthrough",
        )
        self.opponent: tuple[str | None, int | None] = (None, None)

    def new_game(self) -> None:
        self.engine.new_game()

    def set_opponent(self, name: str | None, rating: int | None) -> None:
        self.opponent = (name, rating)

    def choose(self, board: chess.Board, budget: Budget) -> tuple[chess.Move, dict]:
        t0 = time.perf_counter()
        if budget.depth is not None:
            lines = self.engine.analyse(board, depth=budget.depth, multipv=1)
        else:
            lines = self.engine.analyse(board, nodes=max(1, budget.certify_nodes), multipv=1)
        if not lines:
            raise ValueError(f"no legal moves in {board.fen()}")
        best = lines[0]
        search_ms = round((time.perf_counter() - t0) * 1000.0, 1)
        cand = {
            "move": best.move.uci(),
            "cp": best.cp,
            "rank": best.rank,
            "mate": best.mate,
            "depth": best.depth,
            "seldepth": best.seldepth,
            "nodes": best.nodes,
            "pv": [m.uci() for m in best.pv],
        }
        telemetry = {
            "player": "passthrough",
            "candidates": [cand],
            "chosen": best.move.uci(),
            "reason": "passthrough",
            "timings": {"certify_ms": search_ms},
        }
        return best.move, telemetry

    def stop(self) -> None:
        """End the current search early (called from the UCI thread on `stop`)."""
        self.engine.stop()

    def close(self) -> None:
        self.engine.close()
