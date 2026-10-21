"""Lc0/Maia policy proxy: parser (fast) and a real-engine check (slow, needs lc0 + maia weights)."""

from __future__ import annotations

import shutil
from pathlib import Path

import chess
import pytest

from lostfish.opponent import Lc0PolicyProxy, lc0_q_to_cp, parse_lc0_verbose_stats

SAMPLE = [
    "   e1e8  (177 ) N:       0 (+ 0) (P:  0.01%) (WL:  -.-----) (D: -.---) (Q:  0.02156) (U: 0.00019) ",
    "   f1c4  (139 ) N:       0 (+ 0) (P: 21.89%) (WL:  -.-----) (D: -.---) (Q:  0.02156) (U: 0.38195) ",
    "   f1b5  (140 ) N:       0 (+ 0) (P: 18.00%) (WL:  -.-----) (D: -.---) (Q:  0.02156) (U: 0.30000) ",
    "   node  (  27) N:       1 (+ 0) (P:  0.00%) (WL:  0.02061) (D: 0.040) (M:  0.0) (Q:  0.02061) (V:  0.0216)",
    "garbage line",
]
WEIGHTS = Path("engines/maia/maia-1500.pb.gz")


def test_parse_policy_and_q() -> None:
    policy, q = parse_lc0_verbose_stats(SAMPLE)
    assert policy == {"e1e8": 0.0001, "f1c4": 0.2189, "f1b5": 0.18}
    assert q == pytest.approx(0.02061)
    assert lc0_q_to_cp(0.0) == 0
    assert lc0_q_to_cp(0.5) > 50 and lc0_q_to_cp(-0.5) < -50
    assert lc0_q_to_cp(1.0) == 3000 and lc0_q_to_cp(-1.0) == -3000


def test_parse_empty() -> None:
    assert parse_lc0_verbose_stats([]) == ({}, None)


class _FakeAnalysis:
    def __init__(self, strings: list[str]) -> None:
        self._strings = strings

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def __iter__(self):
        return iter([{"string": s} for s in self._strings])


class _FakeEngine:
    def __init__(self, strings: list[str]) -> None:
        self.strings = strings

    def analysis(self, board, limit):
        return _FakeAnalysis(self.strings)

    def quit(self) -> None:
        pass


def test_predict_reply_from_policy_filters_illegal_and_normalises() -> None:
    proxy = Lc0PolicyProxy.__new__(Lc0PolicyProxy)
    proxy.weights, proxy.name, proxy.nodes = "fake", "fake", 1
    proxy.engine = _FakeEngine(SAMPLE)  # type: ignore[assignment]
    proxy.last_eval_cp, proxy.last_policy, proxy.last_visits, proxy.last_bestmove = (
        None,
        {},
        {},
        None,
    )
    board = chess.Board("r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3")
    replies = proxy.predict_reply(board, top_n=2)
    assert [m.uci() for m, _ in replies] == ["f1c4", "f1b5"]
    assert sum(w for _, w in replies) == pytest.approx(1.0)
    assert replies[0][1] > replies[1][1]
    assert (
        "h1g1" not in proxy.last_policy
    )  # illegal here (king on e1 blocks? no: h1g1 is illegal, g1 empty) -> filtered
    assert proxy.last_eval_cp == lc0_q_to_cp(0.02061)


@pytest.mark.slow
def test_real_maia_policy_proxy() -> None:
    if shutil.which("lc0") is None or not WEIGHTS.exists():
        pytest.skip("lc0 binary or maia weights not available")
    import time

    proxy = Lc0PolicyProxy("lc0", str(WEIGHTS.resolve()))
    try:
        board = chess.Board("r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3")
        proxy.predict_reply(board)  # warm-up (backend init)
        t = time.perf_counter()
        replies = proxy.predict_reply(board, top_n=2)
        dt = time.perf_counter() - t
        assert len(replies) == 2 and all(board.is_legal(m) for m, _ in replies)
        assert sum(w for _, w in replies) == pytest.approx(1.0)
        assert dt < 0.2, f"policy prediction took {dt * 1000:.0f} ms"
        assert proxy.last_eval_cp is not None
    finally:
        proxy.close()


def test_parse_visits_and_victim_mode_prefers_bestmove() -> None:
    lines = [
        "   f1c4  (139 ) N:      120 (+ 0) (P: 21.89%) (WL:  0.1) (D: 0.1) (Q:  0.05) (U: 0.3) ",
        "   f1b5  (140 ) N:       70 (+ 0) (P: 18.00%) (WL:  0.1) (D: 0.1) (Q:  0.04) (U: 0.3) ",
        "   node  (  27) N:      200 (+ 0) (P:  0.00%) (WL:  0.02) (D: 0.040) (M:  0.0) (Q:  0.02) (V:  0.02)",
    ]
    visits: dict[str, int] = {}
    policy, _q = parse_lc0_verbose_stats(lines, visits=visits)
    assert visits == {"f1c4": 120, "f1b5": 70} and policy["f1c4"] == 0.2189

    class _Eng:
        def analysis(self, board, limit):
            return _FakeAnalysis(lines)

        def quit(self) -> None:
            pass

    proxy = Lc0PolicyProxy.__new__(Lc0PolicyProxy)
    proxy.weights, proxy.name, proxy.nodes = "fake", "fake", 200
    proxy.engine = _Eng()  # type: ignore[assignment]
    proxy.last_eval_cp, proxy.last_policy, proxy.last_visits, proxy.last_bestmove = (
        None,
        {},
        {},
        None,
    )
    board = chess.Board("r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3")
    replies = proxy.predict_reply(board, top_n=2)
    assert [m.uci() for m, _ in replies] == ["f1c4", "f1b5"]
    assert replies[0][1] > replies[1][1] and sum(w for _, w in replies) == pytest.approx(1.0)


@pytest.mark.slow
def test_real_lc0_victim_mode_matches_engine_bestmove() -> None:
    import shutil as _sh

    net = Path("engines/lc0nets/t1-256x10-distilled-swa-2432500.pb.gz")
    if _sh.which("lc0") is None or not net.exists():
        pytest.skip("lc0 or T1 net not available")
    import chess.engine

    proxy = Lc0PolicyProxy("lc0", str(net.resolve()), nodes=100)
    victim = chess.engine.SimpleEngine.popen_uci("lc0", timeout=180)
    victim.configure({"WeightsFile": str(net.resolve()), "Threads": 1})
    try:
        board = chess.Board("r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3")
        pred = proxy.predict_reply(board, top_n=2)[0][0]
        actual = victim.play(board, chess.engine.Limit(nodes=100)).move
        assert board.is_legal(pred)
        assert pred == actual, (
            f"proxy {pred} vs victim {actual}"
        )  # same engine, same budget, fresh hash
    finally:
        proxy.close()
        victim.quit()
