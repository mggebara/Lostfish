"""Opponent models: softmax weighting, proxy search parameters, edge cases."""

from __future__ import annotations

import math

import chess
import pytest

from lostfish.certify import MATE_CP
from lostfish.opponent import (
    OpponentModel,
    StockfishDepthProxy,
    UniformRandomOpponent,
    softmax_weights,
)
from tests.steer_fakes import FakeEngine, line, ranked_script

STALEMATE = "7k/5Q2/6K1/8/8/8/8/8 b - - 0 1"
CHECKMATE = "7k/6Q1/6K1/8/8/8/8/8 b - - 0 1"


def test_softmax_100cp_gap_gives_about_27_percent():
    w = softmax_weights([50, -50], 100.0)
    assert w[1] == pytest.approx(math.exp(-1) / (1 + math.exp(-1)))
    assert 0.26 < w[1] < 0.28
    assert sum(w) == pytest.approx(1.0)


def test_softmax_equal_scores_and_mate_gaps_are_stable():
    assert softmax_weights([10, 10], 100.0) == pytest.approx([0.5, 0.5])
    w = softmax_weights([MATE_CP - 3, 0], 100.0)
    assert w[0] == pytest.approx(1.0) and w[1] >= 0.0 and all(math.isfinite(x) for x in w)
    assert softmax_weights([], 100.0) == []
    assert softmax_weights([5, 9, 9], 0.0) == [0.0, 0.5, 0.5]


def test_proxy_searches_at_depth_with_side_to_move_pov():
    engine = FakeEngine(ranked_script("p"))
    proxy = StockfishDepthProxy(engine, 7)
    board = chess.Board()
    board.push_uci("e2e4")
    dist = proxy.predict_reply(board, top_n=2)
    call = engine.calls[-1]
    assert call["depth"] == 7 and call["nodes"] is None
    assert call["multipv"] == 2 and call["pov"] == chess.BLACK
    assert len(dist) == 2 and sum(w for _, w in dist) == pytest.approx(1.0)
    assert dist[0][1] >= dist[1][1]
    assert all(m in board.legal_moves for m, _ in dist)
    assert proxy.last_eval_cp == ranked_script("p")(board.copy(), chess.BLACK, 1)[0].cp


def test_proxy_weights_follow_scores():
    lines = [line("e7e5", 30, 1), line("c7c5", -70, 2)]
    proxy = StockfishDepthProxy(FakeEngine(lambda b, p, k: lines), 5)
    board = chess.Board()
    board.push_uci("e2e4")
    (m1, w1), (m2, w2) = proxy.predict_reply(board)
    assert (m1.uci(), m2.uci()) == ("e7e5", "c7c5")
    assert w2 == pytest.approx(0.2689, abs=1e-3) and w1 + w2 == pytest.approx(1.0)


def test_proxy_single_legal_move_skips_search():
    board = chess.Board("k7/8/8/8/8/8/1q6/K7 w - - 0 1")  # Kxb2 is the only legal move
    assert board.legal_moves.count() == 1
    engine = FakeEngine(ranked_script())
    proxy = StockfishDepthProxy(engine, 6)
    assert proxy.predict_reply(board) == [(chess.Move.from_uci("a1b2"), 1.0)]
    assert engine.calls == [] and proxy.last_eval_cp is None


@pytest.mark.parametrize("fen", [STALEMATE, CHECKMATE])
def test_proxy_no_legal_moves_returns_empty(fen):
    board = chess.Board(fen)
    assert board.legal_moves.count() == 0
    engine = FakeEngine(ranked_script())
    assert StockfishDepthProxy(engine, 6).predict_reply(board) == []
    assert engine.calls == []


def test_proxy_top_n_capped_by_legal_moves_and_rejects_bad_depth():
    board = chess.Board("k7/8/8/8/8/8/8/K6R b - - 0 1")
    engine = FakeEngine(ranked_script())
    dist = StockfishDepthProxy(engine, 4).predict_reply(board, top_n=10)
    assert engine.calls[-1]["multipv"] == board.legal_moves.count() == len(dist)
    with pytest.raises(ValueError):
        StockfishDepthProxy(engine, 0)


def test_proxy_empty_engine_answer_raises():
    with pytest.raises(RuntimeError):
        StockfishDepthProxy(FakeEngine(lambda b, p, k: []), 4).predict_reply(chess.Board())


def test_uniform_random_opponent():
    opp = UniformRandomOpponent(seed=3)
    assert isinstance(opp, OpponentModel)
    board = chess.Board()
    dist = opp.predict_reply(board, top_n=3)
    assert len({m for m, _ in dist}) == 3 and all(m in board.legal_moves for m, _ in dist)
    assert sum(w for _, w in dist) == pytest.approx(1.0)
    assert UniformRandomOpponent(seed=3).predict_reply(board, top_n=3) == dist
    assert opp.predict_reply(chess.Board(CHECKMATE)) == []
    assert isinstance(StockfishDepthProxy(FakeEngine(), 3), OpponentModel)
