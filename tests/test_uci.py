"""UCI conformance. LostFish must answer `uci` with `uciok`, `isready` with `readyok`, and every
`go` with exactly one legal `bestmove`. The subprocess tests drive `python -m lostfish.uci` with
scripted sessions (they need engines/stockfish); the in-process tests use fake players."""

from __future__ import annotations

import io
import json
import os
import queue
import subprocess
import sys
import threading
import time
import types
from pathlib import Path
from typing import ClassVar

import chess
import chess.pgn
import pytest

from lostfish import uci
from lostfish.config import load_config

ROOT = Path(__file__).resolve().parent.parent
STOCKFISH = ROOT / "engines" / "stockfish"
needs_sf = pytest.mark.skipif(
    not STOCKFISH.exists(), reason="engines/stockfish missing (run scripts/setup_engines.sh)"
)
MATE_IN_ONE = "6k1/5ppp/8/8/8/8/5PPP/3R2K1 w - - 0 1"  # Rd8#
CHECKMATED = "7k/6Q1/6K1/8/8/8/8/8 b - - 0 1"
STALEMATE = "7k/5Q2/6K1/8/8/8/8/8 b - - 0 1"


class UciProc:
    """A LostFish subprocess with a line queue for its stdout."""

    def __init__(self, log_path: Path) -> None:
        env = dict(os.environ, LOSTFISH_LOG=str(log_path), PYTHONUNBUFFERED="1")
        self.p = subprocess.Popen(
            [sys.executable, "-m", "lostfish.uci"],
            cwd=ROOT,
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
        )
        self.lines: queue.Queue[str] = queue.Queue()
        threading.Thread(target=self._pump, daemon=True).start()

    def _pump(self) -> None:
        assert self.p.stdout is not None
        for line in self.p.stdout:
            self.lines.put(line.rstrip("\n"))

    def send(self, *cmds: str) -> None:
        assert self.p.stdin is not None
        for c in cmds:
            self.p.stdin.write(c + "\n")
        self.p.stdin.flush()

    def expect(self, prefix: str, timeout: float = 10.0) -> tuple[str, list[str]]:
        """Read lines until one starts with `prefix`; returns (that line, lines before it)."""
        seen: list[str] = []
        deadline = time.monotonic() + timeout
        while True:
            left = deadline - time.monotonic()
            if left <= 0:
                raise AssertionError(f"no {prefix!r} within {timeout}s; got {seen}")
            try:
                line = self.lines.get(timeout=left)
            except queue.Empty:
                continue
            if line.startswith(prefix):
                return line, seen
            seen.append(line)

    def bestmove(self, timeout: float = 10.0) -> str:
        return self.expect("bestmove", timeout)[0].split()[1]

    def children(self) -> list[int]:
        out = subprocess.run(
            ["pgrep", "-P", str(self.p.pid)], check=False, capture_output=True, text=True
        )
        return [int(x) for x in out.stdout.split()]

    def close(self) -> int:
        if self.p.poll() is None:
            try:
                self.send("quit")
            except (BrokenPipeError, OSError):
                pass
        try:
            return self.p.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.p.kill()
            return self.p.wait()


@pytest.fixture
def lf(tmp_path: Path):
    proc = UciProc(tmp_path / "moves.jsonl")
    proc.send("uci")
    proc.expect("uciok")
    proc.send("isready")
    proc.expect("readyok", timeout=30)
    yield proc
    proc.close()


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    out = subprocess.run(
        ["ps", "-o", "stat=", "-p", str(pid)], check=False, capture_output=True, text=True
    )
    return bool(out.stdout.strip()) and not out.stdout.strip().startswith("Z")


# --- subprocess sessions ------------------------------------------------------------------


@needs_sf
def test_handshake_and_options(tmp_path: Path) -> None:
    proc = UciProc(tmp_path / "moves.jsonl")
    try:
        proc.send("uci")
        _, lines = proc.expect("uciok")
        assert "id name LostFish 0.0.1" in lines
        assert "id author LostFish" in lines
        opts = " ".join(lines)
        for name in ("Hash", "Threads", "SyzygyPath", "UCI_Opponent", "MoveOverhead", "Profile"):
            assert f"option name {name} type" in opts
        assert "option name Steering type check default false" in lines
        proc.send("isready")
        proc.expect("readyok", timeout=30)
        proc.send("isready")
        proc.expect("readyok", timeout=2)
    finally:
        assert proc.close() == 0


@needs_sf
def test_go_nodes_returns_legal_move(lf: UciProc) -> None:
    lf.send("ucinewgame", "position startpos moves e2e4 e7e5", "go nodes 20000")
    board = chess.Board()
    board.push_uci("e2e4")
    board.push_uci("e7e5")
    line, before = lf.expect("bestmove")
    assert chess.Move.from_uci(line.split()[1]) in board.legal_moves
    assert any(" score " in ln and " pv " in ln for ln in before)  # info line for GUIs/adjudication


@needs_sf
def test_go_clock_is_fast(lf: UciProc) -> None:
    lf.send("ucinewgame", "position startpos")
    t0 = time.monotonic()
    lf.send("go wtime 1000 btime 1000 winc 0 binc 0")
    mv = lf.bestmove(timeout=5)
    assert time.monotonic() - t0 < 2.0
    assert chess.Move.from_uci(mv) in chess.Board().legal_moves


@needs_sf
def test_mate_and_no_legal_moves(lf: UciProc) -> None:
    lf.send(f"position fen {MATE_IN_ONE}", "go nodes 20000")
    assert lf.bestmove() == "d1d8"
    lf.send(f"position fen {CHECKMATED}", "go nodes 20000")
    assert lf.bestmove() == "0000"
    lf.send(f"position fen {STALEMATE}", "go wtime 1000 btime 1000")
    assert lf.bestmove() == "0000"
    lf.send("isready")
    lf.expect("readyok")


@needs_sf
def test_garbage_is_ignored(lf: UciProc) -> None:
    lf.send(
        "",
        "hello world",
        "position",
        "position fen not-a-fen",
        "position startpos moves e2e4 zzzz",
        "setoption name NoSuchOption value 3",
        "setoption name Hash value notanumber",
        "setoption",
        "go nodes banana",
        "register later",
        "debug on",
        "joho debug off",
        "ponderhit",
        "stop",
    )
    lf.bestmove()  # the `go nodes banana` above is a plain go
    lf.send("isready")
    lf.expect("readyok")
    lf.send("position startpos moves e2e4", "go nodes 5000")
    board = chess.Board()
    board.push_uci("e2e4")
    assert chess.Move.from_uci(lf.bestmove()) in board.legal_moves


@needs_sf
def test_isready_during_search_and_stop(lf: UciProc) -> None:
    lf.send("ucinewgame", "position startpos", "go infinite")
    time.sleep(0.2)
    t0 = time.monotonic()
    lf.send("isready")
    _, before = lf.expect("readyok", timeout=2)
    assert time.monotonic() - t0 < 0.5
    assert not any(ln.startswith("bestmove") for ln in before)  # infinite: wait for stop
    time.sleep(0.3)
    t0 = time.monotonic()
    lf.send("stop")
    assert chess.Move.from_uci(lf.bestmove(timeout=3)) in chess.Board().legal_moves
    assert time.monotonic() - t0 < 1.0
    lf.send("isready")
    _, between = lf.expect("readyok")
    assert not any(ln.startswith("bestmove") for ln in between)  # exactly one bestmove


@needs_sf
def test_one_bestmove_per_go(lf: UciProc) -> None:
    lf.send("ucinewgame", "position startpos")
    for _ in range(5):
        lf.send("go nodes 2000")
    for _ in range(5):
        lf.bestmove()
    lf.send("isready")
    _, extra = lf.expect("readyok")
    assert not any(ln.startswith("bestmove") for ln in extra)


@needs_sf
def test_determinism_same_nodes_same_move(lf: UciProc) -> None:
    fen = "r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3"
    moves = []
    for _ in range(2):
        lf.send("ucinewgame", f"position fen {fen} moves f1b5 a7a6", "go nodes 60000")
        moves.append(lf.bestmove())
    assert moves[0] == moves[1]


@needs_sf
def test_telemetry_line_written(tmp_path: Path) -> None:
    log = tmp_path / "moves.jsonl"
    proc = UciProc(log)
    try:
        proc.send("uci", "setoption name UCI_Opponent value BOT 2450 computer Some-Bot", "isready")
        proc.expect("readyok", timeout=30)
        proc.send("ucinewgame", "position startpos moves d2d4", "go wtime 60000 btime 60000")
        mv = proc.bestmove()
    finally:
        assert proc.close() == 0
    rec = json.loads(log.read_text().splitlines()[-1])
    for key in (
        "ts",
        "fen",
        "opponent",
        "tc_class",
        "budget",
        "candidates",
        "chosen",
        "elapsed_ms",
    ):
        assert key in rec
    assert rec["chosen"] == mv
    assert rec["tc_class"] == "bullet"
    assert rec["opponent"]["name"] == "Some-Bot"
    assert rec["opponent"]["rating"] == 2450
    assert rec["candidates"][0]["move"] == mv


@needs_sf
def test_quit_exits_cleanly_without_orphans(tmp_path: Path) -> None:
    proc = UciProc(tmp_path / "moves.jsonl")
    proc.send("uci", "isready")
    proc.expect("readyok", timeout=30)
    proc.send("position startpos", "go nodes 1000")
    proc.bestmove()
    kids = proc.children()
    assert kids, "expected a Stockfish child process"
    proc.send("quit")
    assert proc.p.wait(timeout=10) == 0
    deadline = time.monotonic() + 5
    while any(_alive(k) for k in kids) and time.monotonic() < deadline:
        time.sleep(0.05)
    assert not any(_alive(k) for k in kids)


@needs_sf
def test_eof_and_quit_mid_search(tmp_path: Path) -> None:
    proc = UciProc(tmp_path / "moves.jsonl")
    proc.send("uci", "isready")
    proc.expect("readyok", timeout=30)
    proc.send("position startpos", "go infinite")
    time.sleep(0.2)
    assert proc.p.stdin is not None
    proc.p.stdin.close()  # EOF behaves like quit, even mid-search
    assert proc.p.wait(timeout=10) == 0


# --- in-process tests with fake players (no Stockfish needed) -----------------------------


class Capture(io.StringIO):
    def __init__(self) -> None:
        super().__init__()
        self.cond = threading.Condition()

    def write(self, s: str) -> int:
        with self.cond:
            n = super().write(s)
            self.cond.notify_all()
            return n

    def wait_for(self, prefix: str, count: int = 1, timeout: float = 5.0) -> list[str]:
        with self.cond:
            ok = self.cond.wait_for(
                lambda: sum(ln.startswith(prefix) for ln in self.getvalue().splitlines()) >= count,
                timeout,
            )
        assert ok, f"no {prefix!r} in {self.getvalue()!r}"
        return self.getvalue().splitlines()


class FakePlayer:
    instances: ClassVar[list[FakePlayer]] = []
    kind = "passthrough"

    def __init__(self, cfg: object) -> None:
        self.cfg = cfg
        self.opponent: tuple[str | None, int | None] | None = None
        self.games = 0
        self.closed = False
        FakePlayer.instances.append(self)

    def new_game(self) -> None:
        self.games += 1

    def set_opponent(self, name: str | None, rating: int | None) -> None:
        self.opponent = (name, rating)

    def choose(self, board: chess.Board, budget: object) -> tuple[chess.Move, dict]:
        move = min(board.legal_moves, key=lambda m: m.uci())
        return move, {"candidates": [{"move": move.uci(), "cp": 12, "rank": 1}], "who": self.kind}

    def close(self) -> None:
        self.closed = True


class FakeSteering(FakePlayer):
    kind = "steering"


class BrokenSteering(FakePlayer):
    kind = "broken"

    def choose(self, board: chess.Board, budget: object) -> tuple[chess.Move, dict]:
        raise RuntimeError("boom")


@pytest.fixture
def engine(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setenv("LOSTFISH_LOG", str(tmp_path / "moves.jsonl"))
    monkeypatch.setattr(uci, "PassthroughPlayer", FakePlayer)
    FakePlayer.instances.clear()
    out = Capture()
    eng = uci.UciEngine(load_config(), out=out)
    yield eng, out
    eng.shutdown()


def _fake_play_module(cls: type) -> types.ModuleType:
    mod = types.ModuleType("lostfish.play")
    mod.SteeringPlayer = cls  # type: ignore[attr-defined]
    return mod


def test_passthrough_by_default(engine) -> None:
    eng, out = engine
    for cmd in ("uci", "isready", "position startpos", "go nodes 100"):
        eng.handle(cmd)
    lines = out.wait_for("bestmove")
    assert eng.player_kind == "passthrough"
    assert lines[-1] == "bestmove a2a3"
    assert any(ln.startswith("info") and "score cp 12" in ln for ln in lines)


def test_steering_true_uses_steering_player(engine, monkeypatch: pytest.MonkeyPatch) -> None:
    eng, out = engine
    monkeypatch.setitem(sys.modules, "lostfish.play", _fake_play_module(FakeSteering))
    for cmd in ("setoption name Steering value true", "isready", "go nodes 100"):
        eng.handle(cmd)
    out.wait_for("bestmove")
    assert eng.player_kind == "steering"
    assert isinstance(eng.player, FakeSteering)


def test_steering_import_failure_falls_back(engine, monkeypatch: pytest.MonkeyPatch) -> None:
    eng, out = engine
    monkeypatch.setitem(sys.modules, "lostfish.play", None)  # import raises ImportError
    for cmd in ("setoption name Steering value true", "isready", "go nodes 100"):
        eng.handle(cmd)
    lines = out.wait_for("bestmove")
    assert eng.player_kind == "passthrough"
    assert any(ln.startswith("info string steering unavailable") for ln in lines)


def test_failing_player_falls_back_to_passthrough(engine, monkeypatch) -> None:
    eng, out = engine
    monkeypatch.setitem(sys.modules, "lostfish.play", _fake_play_module(BrokenSteering))
    for cmd in ("setoption name Steering value true", "isready", "go wtime 5000 btime 5000"):
        eng.handle(cmd)
    lines = out.wait_for("bestmove")
    assert lines[-1] == "bestmove a2a3"
    assert any(ln.startswith("info string steering failed: RuntimeError") for ln in lines)
    assert eng.player_kind == "passthrough"


def test_option_changes_rebuild_player(engine) -> None:
    eng, _out = engine
    eng.handle("isready")
    first = eng.player
    eng.handle("setoption name Hash value 128")
    eng.handle("isready")
    assert eng.player is not first and isinstance(first, FakePlayer) and first.closed
    assert eng.player.cfg.engines.hash_mb == 128  # type: ignore[union-attr]
    eng.handle("setoption name SyzygyPath value <empty>")
    eng.handle("isready")
    assert eng.player.cfg.engines.syzygy_path is None  # type: ignore[union-attr]


def test_uci_opponent_and_profile_override(engine) -> None:
    eng, _out = engine
    eng.handle("isready")
    eng.handle("ucinewgame")
    eng.handle("setoption name UCI_Opponent value GM 2650 computer Strong-Bot")
    player = eng.player
    assert isinstance(player, FakePlayer)
    assert player.games == 1
    assert player.opponent == ("Strong-Bot", 2650)
    eng.handle("setoption name Profile value _generic")
    assert player.opponent == ("_generic", 2650)
    eng.handle("setoption name UCI_Opponent value none none human Some Person")
    assert player.opponent == ("_generic", None)


def test_ponder_holds_bestmove_until_ponderhit(engine) -> None:
    eng, out = engine
    eng.handle("position startpos")
    eng.handle("go ponder wtime 1000 btime 1000")
    time.sleep(0.2)
    assert "bestmove" not in out.getvalue()
    eng.handle("ponderhit")
    out.wait_for("bestmove")


def test_local_opponent_parser() -> None:
    assert uci.parse_uci_opponent_local("BOT 2300 computer maia1") == ("maia1", 2300, "computer")
    assert uci.parse_uci_opponent_local("none none human John Doe") == ("John Doe", None, "human")
    assert uci.parse_uci_opponent_local("solo") == ("solo", None, None)
    assert uci.parse_uci_opponent_local("") == (None, None, None)


def test_emergency_move_prefers_mate() -> None:
    assert uci.emergency_move(chess.Board(MATE_IN_ONE)) == chess.Move.from_uci("d1d8")
    assert uci.emergency_move(chess.Board(CHECKMATED)) is None


# --- end to end through fastchess (slow) --------------------------------------------------

FASTCHESS = ROOT / "engines" / "fastchess"


@pytest.mark.slow
@needs_sf
@pytest.mark.skipif(not FASTCHESS.exists(), reason="engines/fastchess missing")
def test_fastchess_pair_mirrors_stockfish(tmp_path: Path) -> None:
    """Passthrough at equal nodes is move-for-move Stockfish: a colour-reversed pair mirrors."""
    (tmp_path / "config.toml").write_text(
        "rounds = 1\ngames = 2\nconcurrency = 1\n[each]\nnodes = 20000\n"
        '[[engine]]\nname = "LostFish"\ncmd = "scripts/lostfish"\n'
        '[engine.options]\nSteering = false\nSyzygyPath = "<empty>"\n'
        '[[engine]]\nname = "Stockfish"\ncmd = "engines/stockfish"\n'
        "[engine.options]\nThreads = 1\nHash = 64\n"
    )
    env = dict(os.environ, LOSTFISH_LOG=str(tmp_path / "moves.jsonl"))
    res = subprocess.run(
        [str(ROOT / "scripts" / "run_gauntlet.sh"), str(tmp_path)],
        check=False,
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert res.returncode == 0, res.stdout[-2000:] + res.stderr[-2000:]
    result = (tmp_path / "RESULT.md").read_text()
    assert "Games in games.pgn: 2" in result
    assert "time losses 0, illegal moves 0, disconnects/crashes 0" in result
    with open(tmp_path / "games.pgn") as fh:
        games = [chess.pgn.read_game(fh), chess.pgn.read_game(fh)]
    a, b = ([m.uci() for m in g.mainline_moves()] for g in games if g is not None)
    assert a == b
