"""Shared fakes for the steering tests (certify / opponent / steer / play). No engine binaries.

The data fakes mirror the contract in docs/INTERFACES.md field for field, so the code under test
only ever sees duck-typed objects with the agreed attributes.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import chess
import yaml

REPO = Path(__file__).resolve().parents[1]


@dataclass
class FakePVLine:
    move: chess.Move
    cp: int
    rank: int
    mate: int | None = None
    depth: int = 12
    seldepth: int | None = None
    nodes: int = 1000
    pv: list[chess.Move] = field(default_factory=list)
    eval_by_depth: dict[int, int] = field(default_factory=dict)
    best_by_depth: dict[int, chess.Move] = field(default_factory=dict)


def line(
    uci: str, cp: int, rank: int, *, mate: int | None = None, ebd: dict[int, int] | None = None
) -> FakePVLine:
    move = chess.Move.from_uci(uci)
    return FakePVLine(move, cp, rank, mate=mate, pv=[move], eval_by_depth=dict(ebd or {}))


@dataclass
class FakeBudget:
    tc_class: str = "bullet"
    certify_nodes: int = 200_000
    eval_nodes: int = 50_000
    k: int = 3
    proxy_depth_cap: int = 8
    soft_ms: int = 1000
    hard_ms: int = 1500
    clock_fraction: float = 1.0
    depth: int | None = None


@dataclass
class FakeCluster:
    label: str
    centroid: list[float]
    scale: list[float]
    uplift: float
    blunder_rate: float = 0.1
    n: int = 10


@dataclass
class FakeProfile:
    name: str = "_test"
    effective_depth: int = 6
    weak_clusters: list[FakeCluster] = field(default_factory=list)


def _ns(obj: Any) -> Any:
    if isinstance(obj, dict):
        return SimpleNamespace(**{k: _ns(v) for k, v in obj.items()})
    return obj


def make_cfg() -> SimpleNamespace:
    """The real configs/lostfish.yaml as a plain attribute tree (independent of lostfish.config)."""
    with open(REPO / "configs" / "lostfish.yaml") as fh:
        return _ns(yaml.safe_load(fh))


def hash_cp(board: chess.Board, salt: str = "") -> int:
    """Deterministic pseudo-random eval in [-300, 300] for the side to move."""
    digest = hashlib.blake2b((board.fen() + salt).encode(), digest_size=4).digest()
    return int.from_bytes(digest, "big") % 601 - 300


Script = Callable[[chess.Board, chess.Color, int], list[FakePVLine]]


def ranked_script(salt: str = "") -> Script:
    """Rank every legal move by the hashed eval of the resulting position (cheap 1-ply 'search')."""

    def script(board: chess.Board, pov: chess.Color, multipv: int) -> list[FakePVLine]:
        stm = board.turn
        scored = []
        for move in board.legal_moves:
            board.push(move)
            value = -hash_cp(board, salt)  # for the side to move at the root
            board.pop()
            scored.append((value, move.uci(), move))
        scored.sort(key=lambda t: (-t[0], t[1]))
        out = []
        for i, (value, _, move) in enumerate(scored[:multipv]):
            cp = value if stm == pov else -value
            out.append(FakePVLine(move, cp, i + 1, pv=[move], eval_by_depth={}))
        if out:
            base = out[0].cp
            out[0].eval_by_depth = {d: base for d in range(1, 13)}
        return out

    return script


def static_script(salt: str = "") -> Script:
    """Evaluator stand-in: one line, cp = hashed eval of the position from pov."""

    def script(board: chess.Board, pov: chess.Color, multipv: int) -> list[FakePVLine]:
        move = next(iter(board.legal_moves))
        value = hash_cp(board, salt)
        return [FakePVLine(move, value if board.turn == pov else -value, 1, pv=[move])]

    return script


class FakeEngine:
    """Scripted stand-in for lostfish.engines.Engine. Records every analyse() call."""

    def __init__(
        self,
        script: Script | None = None,
        *,
        name: str = "fake",
        fail: Exception | None = None,
        **kwargs: Any,
    ) -> None:
        self.script = script or static_script()
        self.name = name
        self.fail = fail
        self.kwargs = kwargs
        self.calls: list[dict[str, Any]] = []
        self.new_games = 0
        self.stops = 0
        self.closed = False

    def analyse(
        self,
        board: chess.Board,
        *,
        nodes: int | None = None,
        depth: int | None = None,
        multipv: int = 1,
        pov: chess.Color | None = None,
        trajectory: bool = False,
    ) -> list[FakePVLine]:
        assert (nodes is None) != (depth is None), "exactly one of nodes/depth"
        self.calls.append(
            {
                "fen": board.fen(),
                "nodes": nodes,
                "depth": depth,
                "multipv": multipv,
                "pov": pov,
                "trajectory": trajectory,
            }
        )
        if self.fail is not None:
            raise self.fail
        if not any(board.generate_legal_moves()):
            return []
        pov = board.turn if pov is None else pov
        return self.script(board.copy(), pov, multipv)[:multipv]

    def new_game(self) -> None:
        self.new_games += 1

    def stop(self) -> None:
        self.stops += 1

    def close(self) -> None:
        self.closed = True


class ScriptedOpponent:
    """OpponentModel returning a fixed distribution per FEN (or a default callable)."""

    def __init__(
        self,
        table: dict[str, list[tuple[str, float]]] | None = None,
        default: Callable[[chess.Board], list[tuple[chess.Move, float]]] | None = None,
        fail: Exception | None = None,
    ) -> None:
        self.table = table or {}
        self.default = default
        self.fail = fail
        self.calls: list[str] = []
        self.last_eval_cp: int | None = None

    def predict_reply(
        self, board: chess.Board, *, top_n: int = 2
    ) -> list[tuple[chess.Move, float]]:
        self.calls.append(board.fen())
        if self.fail is not None:
            raise self.fail
        if board.fen() in self.table:
            return [(chess.Move.from_uci(u), w) for u, w in self.table[board.fen()]]
        if self.default is not None:
            return self.default(board)
        legal = list(board.legal_moves)
        return [(legal[0], 1.0)] if legal else []
