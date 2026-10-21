"""Certifier v2 (single-PV best + shallow proposals + per-candidate verification) with a fake engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace

import chess
import pytest

from lostfish.certify import MATE_CP, certify_position, certify_position_v2


@dataclass
class _Line:
    move: chess.Move
    cp: int
    rank: int = 1
    pv: list[chess.Move] = field(default_factory=list)
    eval_by_depth: dict[int, int] = field(default_factory=dict)


class ScriptedEngine:
    """analyse() answers from a table keyed by (board_fen, multipv); records the calls."""

    def __init__(self, table: dict[tuple[str, int], list[_Line]], default_cp: int = 0) -> None:
        self.table = table
        self.default_cp = default_cp
        self.calls: list[tuple[str, int, int | None]] = []

    def analyse(
        self,
        board: chess.Board,
        *,
        multipv: int = 1,
        pov=None,
        nodes=None,
        depth=None,
        trajectory=False,
    ):
        self.calls.append((board.board_fen(), multipv, nodes))
        key = (board.board_fen(), multipv)
        if key in self.table:
            return self.table[key]
        legal = list(board.legal_moves)
        return [_Line(legal[0], self.default_cp, 1, [legal[0]])] if legal else []


def _cfg(mode="single_pv_verify", tol=30, **extra):
    certify = SimpleNamespace(
        tolerance_cp=tol,
        tolerance_min_cp=0,
        tighten_when_behind_cp=150,
        extra={
            "mode": mode,
            "proposal_fraction": 0.2,
            "verify_fraction": 0.5,
            "proposal_tolerance_cp": 60,
            **extra,
        },
    )
    return SimpleNamespace(certify=certify, steer=SimpleNamespace(extra={}), extra={})


def _budget(nodes=20000, k=3):
    return SimpleNamespace(
        certify_nodes=nodes, k=k, depth=None, clock_fraction=1.0, eval_nodes=5000
    )


START = chess.Board()
E4, D4, C4, NF3 = (chess.Move.from_uci(u) for u in ("e2e4", "d2d4", "c2c4", "g1f3"))


def _after(move: chess.Move) -> str:
    b = START.copy()
    b.push(move)
    return b.board_fen()


def test_v2_best_is_single_pv_and_alternatives_are_verified() -> None:
    table = {
        (START.board_fen(), 1): [_Line(E4, 30, 1, [E4], {8: 25, 10: 30})],  # full single-PV
        (START.board_fen(), 3): [
            _Line(D4, 28, 1),
            _Line(E4, 27, 2),
            _Line(C4, 20, 3),
        ],  # shallow proposals
        (_after(D4), 1): [_Line(NF3, 15, 1, [NF3])],  # d4 verifies at 15 >= 30-30
        (_after(C4), 1): [_Line(NF3, -5, 1, [NF3])],  # c4 fails: -5 < 0
    }
    eng = ScriptedEngine(table)
    cert = certify_position_v2(eng, START, chess.WHITE, _budget(), _cfg())
    assert cert.best.move == E4 and cert.best.cp == 30 and cert.eval_by_depth == {8: 25, 10: 30}
    assert [c.move for c in cert.candidates] == [E4, D4]
    assert cert.candidates[1].cp == 15 and cert.candidates[1].rank == 2
    assert cert.candidates[1].pv[:2] == [D4, NF3]
    # calls: full single-PV (20000), proposals (4000), two verifications (10000 each)
    assert [(m, n) for _, m, n in eng.calls] == [(1, 20000), (3, 4000), (1, 10000), (1, 10000)]


def test_v2_tolerance_zero_searches_once() -> None:
    eng = ScriptedEngine({(START.board_fen(), 1): [_Line(E4, 30, 1, [E4])]})
    cert = certify_position_v2(eng, START, chess.WHITE, _budget(), _cfg(tol=0))
    assert [c.move for c in cert.candidates] == [E4] and len(eng.calls) == 1


def test_v2_proposal_window_filters_shallow_losers() -> None:
    table = {
        (START.board_fen(), 1): [_Line(E4, 30, 1, [E4])],
        (START.board_fen(), 3): [
            _Line(E4, 30, 1),
            _Line(D4, 28, 2),
            _Line(C4, -50, 3),
        ],  # c4 outside 60cp window
        (_after(D4), 1): [_Line(NF3, 29, 1, [NF3])],
    }
    eng = ScriptedEngine(table)
    cert = certify_position_v2(eng, START, chess.WHITE, _budget(), _cfg())
    assert [c.move for c in cert.candidates] == [E4, D4]
    assert not any(f == _after(C4) for f, _, _ in eng.calls)  # never verified


def test_v2_mate_best_returns_only_best() -> None:
    eng = ScriptedEngine({(START.board_fen(), 1): [_Line(E4, MATE_CP - 3, 1, [E4])]})
    cert = certify_position_v2(eng, START, chess.WHITE, _budget(), _cfg())
    assert [c.move for c in cert.candidates] == [E4] and len(eng.calls) == 1


def test_v2_candidates_sorted_by_verified_eval() -> None:
    table = {
        (START.board_fen(), 1): [_Line(E4, 30, 1, [E4])],
        (START.board_fen(), 4): [
            _Line(E4, 30, 1),
            _Line(D4, 29, 2),
            _Line(C4, 28, 3),
            _Line(NF3, 27, 4),
        ],
        (_after(D4), 1): [_Line(E4, 10, 1)],
        (_after(C4), 1): [_Line(E4, 25, 1)],
        (_after(NF3), 1): [_Line(E4, 20, 1)],
    }
    cert = certify_position_v2(ScriptedEngine(table), START, chess.WHITE, _budget(k=4), _cfg())
    assert [c.move for c in cert.candidates] == [E4, C4, NF3, D4]
    assert [c.rank for c in cert.candidates] == [1, 2, 3, 4]


def test_mode_dispatch_default_is_multipv() -> None:
    table = {
        (START.board_fen(), 3): [
            _Line(E4, 30, 1, [E4]),
            _Line(D4, 20, 2, [D4]),
            _Line(C4, -40, 3, [C4]),
        ]
    }
    eng = ScriptedEngine(table)
    cert = certify_position(eng, START, chess.WHITE, _budget(), _cfg(mode="multipv"))
    assert [c.move for c in cert.candidates] == [E4, D4] and eng.calls[0][1] == 3
    eng2 = ScriptedEngine({(START.board_fen(), 1): [_Line(E4, 30, 1, [E4])]})
    cert2 = certify_position(
        eng2, START, chess.WHITE, _budget(), _cfg(mode="single_pv_verify", tol=0)
    )
    assert eng2.calls[0][1] == 1 and [c.move for c in cert2.candidates] == [E4]


def test_v2_child_checkmate_is_certified_as_mate() -> None:
    board = chess.Board("r1bqkb1r/pppp1ppp/2n2n2/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 4 4")
    qf7, other = chess.Move.from_uci("h5f7"), chess.Move.from_uci("c4b3")
    table = {
        (board.board_fen(), 1): [
            _Line(other, 200, 1, [other])
        ],  # pretend the full search missed the mate
        (board.board_fen(), 3): [_Line(other, 200, 1), _Line(qf7, 190, 2)],
    }
    cert = certify_position_v2(ScriptedEngine(table), board, chess.WHITE, _budget(), _cfg())
    assert cert.candidates[1].move == qf7 and cert.candidates[1].cp == MATE_CP


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__])
