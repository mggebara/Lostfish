"""Victim-play line search (steer.line_value / exploit_eval with line_depth > 1), with fakes."""

from __future__ import annotations

from dataclasses import dataclass

import chess
import pytest

from lostfish.engines import MATE_CP
from lostfish.steer import exploit_eval, line_value


@dataclass
class _Line:
    move: chess.Move
    cp: int
    rank: int = 1


class FakeEvaluator:
    """Returns (first legal move, cp) where cp comes from a FEN->cp table or a default."""

    def __init__(self, table: dict[str, int] | None = None, default: int = 10) -> None:
        self.table = table or {}
        self.default = default
        self.calls: list[tuple[str, int]] = []

    def analyse(
        self, board: chess.Board, *, nodes: int, pov: chess.Color, **_: object
    ) -> list[_Line]:
        self.calls.append((board.fen(), nodes))
        legal = list(board.legal_moves)
        if not legal:
            return []
        cp = self.table.get(board.board_fen(), self.default)
        return [_Line(legal[0], cp)]


class FakeOpponent:
    """Plays the move from a FEN->uci table, else the last legal move. Weight 1."""

    def __init__(self, table: dict[str, str] | None = None) -> None:
        self.table = table or {}
        self.last_eval_cp = None

    def predict_reply(self, board: chess.Board, *, top_n: int = 2):
        legal = list(board.legal_moves)
        if not legal:
            return []
        uci = self.table.get(board.board_fen())
        mv = chess.Move.from_uci(uci) if uci else legal[-1]
        return [(mv, 1.0)]


START_AFTER_E4 = chess.Board("rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1")


def test_depth1_matches_single_eval() -> None:
    ev = FakeEvaluator(default=25)
    ex = exploit_eval(START_AFTER_E4.copy(), chess.WHITE, FakeOpponent(), ev, eval_nodes=1000)
    assert ex.expected_eval == 25
    assert ex.lines == [[ex.replies[0][0].uci()]] and ex.line_evals == [[25]]
    assert ev.calls and ev.calls[0][1] == 1000


def test_depth2_line_has_three_plies_and_two_evals() -> None:
    ev = FakeEvaluator(default=40)
    ex = exploit_eval(
        START_AFTER_E4.copy(),
        chess.WHITE,
        FakeOpponent(),
        ev,
        eval_nodes=1000,
        line_depth=2,
        line_nodes=300,
    )
    (line,) = ex.lines
    assert len(line) == 3  # reply, our move, predicted reply
    assert ex.line_evals == [[40, 40]]  # one intermediate (line_nodes) + one leaf (eval_nodes)
    assert [n for _, n in ev.calls] == [300, 1000]
    assert ex.expected_eval == 40


def test_line_stops_at_checkmate_delivered_by_us() -> None:
    # Scholar's mate position: White to move, Qxf7# available; evaluator "best move" = first legal,
    # so steer the fake to pick the mate by making it the only move in the table.
    board = chess.Board("r1bqkb1r/pppp1ppp/2n2n2/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 4 4")

    class MateEvaluator(FakeEvaluator):
        def analyse(self, b, *, nodes, pov, **_):
            self.calls.append((b.fen(), nodes))
            return [_Line(chess.Move.from_uci("h5f7"), 500)]

    val, moves, evals = line_value(
        board,
        chess.WHITE,
        FakeOpponent(),
        MateEvaluator(),
        replies_left=2,
        line_nodes=10,
        eval_nodes=10,
    )
    assert val == MATE_CP and moves == ["h5f7"] and evals == [500]


def test_line_stops_early_when_decisive() -> None:
    ev = FakeEvaluator(default=900)
    val, moves, evals = line_value(
        chess.Board(),
        chess.WHITE,
        FakeOpponent(),
        ev,
        replies_left=3,
        line_nodes=10,
        eval_nodes=10,
        decisive_cp=600,
    )
    assert val == 900 and moves == [] and evals == [900] and len(ev.calls) == 1


def test_line_terminal_stalemate_is_zero() -> None:
    # Black to move and stalemated after our move: use a known stalemate position with White to move
    # where every White move stalemates? Simpler: position already stalemate for side to move.
    board = chess.Board("7k/5Q2/6K1/8/8/8/8/8 b - - 0 1")  # Black stalemated
    val, moves, evals = line_value(
        board,
        chess.BLACK,
        FakeOpponent(),
        FakeEvaluator(),
        replies_left=2,
        line_nodes=10,
        eval_nodes=10,
    )
    assert val == 0 and moves == [] and evals == []


def test_min_gain_fallback() -> None:
    from lostfish.certify import Candidate, Certified
    from lostfish.steer import Scored, _choose

    best = Candidate(chess.Move.from_uci("e2e4"), 20, 1, [])
    alt = Candidate(chess.Move.from_uci("d2d4"), 15, 2, [])
    cert = Certified(best, [best, alt], 30, {})
    scored = [Scored(best, 20, 0.0, 20.0), Scored(alt, 25, 0.0, 25.0)]
    assert _choose(scored, cert)[0] == alt.move  # default: 5 cp better -> steer
    assert _choose(scored, cert, min_gain_cp=10)[0] == best.move  # needs +10 -> fallback
    assert _choose(scored, cert, min_gain_cp=10)[1] == "fallback_best"


@pytest.mark.parametrize("depth", [1, 2, 3])
def test_expected_eval_is_weighted_mean(depth: int) -> None:
    class TwoReplies(FakeOpponent):
        def predict_reply(self, board, *, top_n=2):
            legal = list(board.legal_moves)
            if top_n == 1 or len(legal) < 2:
                return [(legal[0], 1.0)]
            return [(legal[0], 0.75), (legal[1], 0.25)]

    ev = FakeEvaluator(default=100)
    ex = exploit_eval(
        START_AFTER_E4.copy(), chess.WHITE, TwoReplies(), ev, eval_nodes=100, line_depth=depth
    )
    assert ex.expected_eval == 100 and len(ex.replies) == 2 and len(ex.lines) == 2
    assert all(len(line) == 2 * depth - 1 for line in ex.lines)
