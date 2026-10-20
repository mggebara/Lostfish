"""Opponent models: predict the reply distribution of a specific opponent.

`StockfishDepthProxy` models a bot as "Stockfish at its fingerprinted depth" (PLAN.md §6,
Phase 2). It searches the position with `go depth d` and MultiPV = top_n on a dedicated
small-hash engine, then turns the MultiPV scores into weights with a softmax over centipawns:

    w_i = exp(cp_i / T) / Σ_j exp(cp_j / T),   T = temperature_cp (default 100 cp)

so a second move 100 cp worse than the first gets e^-1 / (1 + e^-1) ≈ 27 % of the weight, one
200 cp worse ≈ 12 %, one 400 cp worse ≈ 2 %. Scores are from the side to move (the opponent).
"""

from __future__ import annotations

import math
import random
from collections.abc import Sequence
from typing import TYPE_CHECKING, Protocol, runtime_checkable

import chess

if TYPE_CHECKING:
    from lostfish.engines import Engine

DEFAULT_TEMPERATURE_CP = 100.0


@runtime_checkable
class OpponentModel(Protocol):
    def predict_reply(
        self, board: chess.Board, *, top_n: int = 2
    ) -> list[tuple[chess.Move, float]]:
        """Reply distribution for the side to move; weights sum to 1. [] if no legal moves."""
        ...


def softmax_weights(cps: Sequence[int | float], temperature_cp: float) -> list[float]:
    """Numerically stable softmax over centipawns. T <= 0 means argmax (all weight on the best)."""
    if not cps:
        return []
    top = max(cps)
    if temperature_cp <= 0:
        winners = [i for i, c in enumerate(cps) if c == top]
        return [1.0 / len(winners) if i in winners else 0.0 for i in range(len(cps))]
    exps = [math.exp((c - top) / temperature_cp) for c in cps]
    total = sum(exps)
    return [e / total for e in exps]


class StockfishDepthProxy:
    """Predicts replies with a depth-limited Stockfish search (the opponent's effective depth)."""

    def __init__(
        self, engine: Engine, depth: int, *, temperature_cp: float = DEFAULT_TEMPERATURE_CP
    ) -> None:
        if int(depth) < 1:
            raise ValueError(f"proxy depth must be >= 1, got {depth}")
        self.engine = engine
        self.depth = int(depth)
        self.temperature_cp = float(temperature_cp)
        # Side-to-move (opponent) POV eval of the top reply from the last search, or None when
        # the last call did not search (0 or 1 legal moves). steer.py uses it as eval_shallow.
        self.last_eval_cp: int | None = None

    def predict_reply(
        self, board: chess.Board, *, top_n: int = 2
    ) -> list[tuple[chess.Move, float]]:
        self.last_eval_cp = None
        legal = list(board.legal_moves)
        if not legal:
            return []
        if len(legal) == 1:
            return [(legal[0], 1.0)]
        n = max(1, min(int(top_n), len(legal)))
        lines = self.engine.analyse(board, depth=self.depth, multipv=n, pov=board.turn)
        if not lines:
            raise RuntimeError(f"proxy returned no lines for {board.fen()}")
        lines = sorted(lines, key=lambda ln: ln.rank)[:n]
        self.last_eval_cp = int(lines[0].cp)
        weights = softmax_weights([ln.cp for ln in lines], self.temperature_cp)
        return [(ln.move, w) for ln, w in zip(lines, weights, strict=True)]


class UniformRandomOpponent:
    """Test model: top_n distinct random legal moves, equal weights. Seedable."""

    def __init__(self, seed: int | None = None) -> None:
        self._rng = random.Random(seed)

    def predict_reply(
        self, board: chess.Board, *, top_n: int = 2
    ) -> list[tuple[chess.Move, float]]:
        legal = list(board.legal_moves)
        if not legal:
            return []
        chosen = self._rng.sample(legal, max(1, min(int(top_n), len(legal))))
        return [(m, 1.0 / len(chosen)) for m in chosen]
