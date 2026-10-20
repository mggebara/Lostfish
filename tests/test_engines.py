"""lostfish.engines against a real Stockfish (skipped when engines/stockfish is missing)."""

from __future__ import annotations

import os
import threading
import time
from pathlib import Path

import chess
import pytest

from lostfish.engines import (
    MATE_CP,
    Engine,
    EnginePool,
    has_tablebases,
    is_mate_cp,
    uci_score,
)

ROOT = Path(__file__).resolve().parent.parent
STOCKFISH = str(ROOT / "engines" / "stockfish")
pytestmark = pytest.mark.skipif(
    not Path(STOCKFISH).exists(), reason="engines/stockfish missing (run scripts/setup_engines.sh)"
)
ITALIAN = "r1bqk1nr/pppp1ppp/2n5/2b1p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4"
BLACK_UP_A_ROOK = "r5k1/5ppp/8/8/8/8/5PPP/6K1 b - - 0 1"
MATE_IN_ONE = "6k1/5ppp/8/8/8/8/5PPP/3R2K1 w - - 0 1"  # Rd8#
CHECKMATED = "7k/6Q1/6K1/8/8/8/8/8 b - - 0 1"


@pytest.fixture(scope="module")
def sf():
    eng = Engine(STOCKFISH, hash_mb=16, name="test")
    yield eng
    eng.close()


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


def test_multipv_sorted_by_rank(sf: Engine) -> None:
    sf.new_game()
    lines = sf.analyse(chess.Board(ITALIAN), nodes=100_000, multipv=4)
    assert [ln.rank for ln in lines] == [1, 2, 3, 4]
    assert len({ln.move for ln in lines}) == 4
    board = chess.Board(ITALIAN)
    for ln in lines:
        assert ln.move in board.legal_moves
        assert ln.pv[0] == ln.move
        assert ln.depth > 0 and ln.nodes > 0
        assert ln.eval_by_depth == {} and ln.best_by_depth == {}  # trajectory off
    same_depth = [ln.cp for ln in lines if ln.depth == lines[0].depth]
    assert same_depth == sorted(same_depth, reverse=True)


def test_multipv_capped_by_legal_moves(sf: Engine) -> None:
    board = chess.Board("7k/8/8/8/8/8/8/K7 w - - 0 1")  # 3 legal moves
    lines = sf.analyse(board, depth=6, multipv=10)
    assert len(lines) == 3


def test_pov_conversion(sf: Engine) -> None:
    board = chess.Board(BLACK_UP_A_ROOK)
    sf.new_game()
    mine = sf.analyse(board, nodes=50_000)[0]  # pov defaults to the side to move (black)
    sf.new_game()
    white = sf.analyse(board, nodes=50_000, pov=chess.WHITE)[0]
    assert mine.cp > 300
    assert white.cp == -mine.cp
    assert white.move == mine.move


def test_mate_scores(sf: Engine) -> None:
    board = chess.Board(MATE_IN_ONE)
    win = sf.analyse(board, nodes=20_000)[0]
    assert win.move == chess.Move.from_uci("d1d8")
    assert win.mate == 1 and win.cp == MATE_CP - 1 and is_mate_cp(win.cp)
    lose = sf.analyse(board, nodes=20_000, pov=chess.BLACK)[0]
    assert lose.mate == -1 and lose.cp == -(MATE_CP - 1)
    assert uci_score(win.cp) == "mate 1" and uci_score(lose.cp) == "mate -1"
    assert uci_score(35) == "cp 35"


def test_no_legal_moves_returns_empty(sf: Engine) -> None:
    assert sf.analyse(chess.Board(CHECKMATED), nodes=1000) == []


def test_exactly_one_limit(sf: Engine) -> None:
    with pytest.raises(ValueError):
        sf.analyse(chess.Board(), nodes=1000, depth=5)
    with pytest.raises(ValueError):
        sf.analyse(chess.Board())


def test_depth_limit(sf: Engine) -> None:
    lines = sf.analyse(chess.Board(ITALIAN), depth=9)
    assert lines[0].depth >= 9


def test_trajectory(sf: Engine) -> None:
    sf.new_game()
    lines = sf.analyse(chess.Board(ITALIAN), nodes=200_000, multipv=3, trajectory=True)
    top = lines[0]
    depths = list(top.eval_by_depth)
    assert len(depths) >= 8
    assert depths == sorted(depths) and len(set(depths)) == len(depths)
    assert list(top.best_by_depth) == depths
    assert depths[-1] == top.depth
    assert top.eval_by_depth[depths[-1]] == top.cp
    assert top.best_by_depth[depths[-1]] == top.move  # the final report is the bestmove's
    assert all(abs(v) < 1000 for v in top.eval_by_depth.values())
    assert all(ln.eval_by_depth == {} for ln in lines[1:])  # rank-1 only


def test_determinism_after_new_game(sf: Engine) -> None:
    board = chess.Board(ITALIAN)
    results = []
    for _ in range(2):
        sf.new_game()
        ln = sf.analyse(board, nodes=80_000, multipv=2)
        results.append([(x.move, x.cp, x.depth) for x in ln])
    assert results[0] == results[1]


def test_stop_returns_best_so_far(sf: Engine) -> None:
    sf.new_game()
    timer = threading.Timer(0.3, sf.stop)
    t0 = time.monotonic()
    timer.start()
    lines = sf.analyse(chess.Board(), nodes=500_000_000)
    assert time.monotonic() - t0 < 2.0
    assert lines and lines[0].move in chess.Board().legal_moves
    sf.stop()  # no search running: harmless
    assert sf.analyse(chess.Board(), nodes=1000)  # engine still usable


def test_close_is_clean_and_idempotent() -> None:
    eng = Engine(STOCKFISH, hash_mb=16, syzygy_path=str(ROOT / "no" / "such" / "dir"))
    assert eng.syzygy_path is None  # a missing tablebase dir is tolerated
    pid = eng.pid
    assert pid is not None and _alive(pid)
    assert eng.analyse(chess.Board(), nodes=1000)
    eng.close()
    eng.close()
    deadline = time.monotonic() + 5
    while _alive(pid) and time.monotonic() < deadline:
        time.sleep(0.05)
    assert not _alive(pid)
    with pytest.raises(chess.engine.EngineTerminatedError):
        eng.analyse(chess.Board(), nodes=1000)


def test_pool_is_persistent() -> None:
    pool = EnginePool(STOCKFISH, 2, hash_mb=16, name="pool")
    try:
        assert len(pool) == 2
        pids = [e.pid for e in pool.engines]
        assert len(set(pids)) == 2
        assert [e.name for e in pool.engines] == ["pool0", "pool1"]
        pool.new_game()
        for e in pool.engines:
            e.analyse(chess.Board(), nodes=2000)
        assert [e.pid for e in pool.engines] == pids  # no respawn per search
    finally:
        pool.close()


def test_syzygy_detection(tmp_path: Path) -> None:
    assert not has_tablebases(None)
    assert not has_tablebases(str(tmp_path))
    (tmp_path / "KQvK.rtbw.part").write_bytes(b"")  # partial download does not count
    assert not has_tablebases(str(tmp_path))
    tb = ROOT / "tb" / "syzygy"
    if any(tb.glob("*.rtbw")):
        assert has_tablebases(f"{tmp_path}{os.pathsep}{tb}")
        eng = Engine(STOCKFISH, hash_mb=16, syzygy_path=str(tb))
        try:
            assert eng.syzygy_path == str(tb)
            line = eng.analyse(chess.Board("8/8/8/8/8/2k5/8/KQ6 w - - 0 1"), nodes=5000)[0]
            assert line.cp > 1000
        finally:
            eng.close()
