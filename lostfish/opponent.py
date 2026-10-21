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
import re
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


# --------------------------------------------------------------------------- Lc0 / Maia policy

# `info string` line from Lc0 with VerboseMoveStats=true, e.g.
#   "f1c4  (139 ) N:       0 (+ 0) (P: 21.89%) (WL:  -.-----) ... (Q:  0.02156) ..."
_LC0_STAT_RE = re.compile(r"^\s*(?P<move>\S+)\s+\(\s*\d+\s*\)\s+N:.*?\(P:\s*(?P<p>[0-9.]+)%\)")
_LC0_Q_RE = re.compile(r"\(Q:\s*(?P<q>-?[0-9.]+)\)")


def parse_lc0_verbose_stats(lines: Sequence[str]) -> tuple[dict[str, float], float | None]:
    """Root policy {uci: probability} and the root Q from Lc0 VerboseMoveStats info strings.

    The per-move lines carry each child's prior P; the final "node" line carries the root's Q
    (side-to-move POV, in [-1, 1]). Lines that do not match are ignored.
    """
    policy: dict[str, float] = {}
    root_q: float | None = None
    for line in lines:
        m = _LC0_STAT_RE.match(line)
        if not m:
            continue
        if m.group("move") == "node":
            q = _LC0_Q_RE.search(line)
            root_q = float(q.group("q")) if q else None
        else:
            policy[m.group("move")] = float(m.group("p")) / 100.0
    return policy, root_q


def lc0_q_to_cp(q: float) -> int:
    """Lc0's own Q -> centipawn mapping (90 * tan(1.5637541897 * q)), clamped to +-3000."""
    cp = 90.0 * math.tan(1.5637541897 * max(-0.9999, min(0.9999, q)))
    return int(max(-3000.0, min(3000.0, round(cp))))


class Lc0PolicyProxy:
    """Predicts replies from a Leela/Maia network's root policy (1 node, no search).

    This is the "human-like / net-based bot" opponent model: Maia nets are trained to predict
    the move a player of a given rating would play, so the raw policy *is* the prediction.
    One prediction costs ~1 ms on the Metal backend. `last_eval_cp` is the net's root value
    converted to centipawns (side-to-move POV) so steer.py can use it as the shallow eval.
    """

    def __init__(
        self,
        lc0_path: str,
        weights: str,
        *,
        threads: int = 1,
        backend: str | None = None,
        name: str = "lc0-proxy",
    ) -> None:
        import chess.engine

        self.weights = str(weights)
        self.name = name
        self.engine = chess.engine.SimpleEngine.popen_uci(lc0_path, timeout=180)
        opts: dict[str, object] = {
            "WeightsFile": self.weights,
            "Threads": int(threads),
            "VerboseMoveStats": True,
        }
        if backend:
            opts["Backend"] = backend
        self.engine.configure(opts)
        self.last_eval_cp: int | None = None
        self.last_policy: dict[str, float] = {}

    def root_policy(self, board: chess.Board) -> dict[str, float]:
        import chess.engine

        strings: list[str] = []
        with self.engine.analysis(board, chess.engine.Limit(nodes=1)) as analysis:
            for info in analysis:
                s = info.get("string")
                if s:
                    strings.append(str(s))
        policy, root_q = parse_lc0_verbose_stats(strings)
        legal = {m.uci() for m in board.legal_moves}
        policy = {m: p for m, p in policy.items() if m in legal}
        self.last_policy = policy
        self.last_eval_cp = lc0_q_to_cp(root_q) if root_q is not None else None
        return policy

    def predict_reply(
        self, board: chess.Board, *, top_n: int = 2
    ) -> list[tuple[chess.Move, float]]:
        self.last_eval_cp = None
        legal = list(board.legal_moves)
        if not legal:
            return []
        if len(legal) == 1:
            return [(legal[0], 1.0)]
        policy = self.root_policy(board)
        if not policy:
            raise RuntimeError(f"lc0 returned no policy for {board.fen()}")
        n = max(1, min(int(top_n), len(policy)))
        ranked = sorted(policy.items(), key=lambda kv: -kv[1])[:n]
        total = sum(p for _, p in ranked) or 1.0
        return [(chess.Move.from_uci(m), p / total) for m, p in ranked]

    def close(self) -> None:
        import contextlib

        with contextlib.suppress(Exception):  # best effort on shutdown
            self.engine.quit()
