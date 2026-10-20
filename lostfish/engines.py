"""Persistent, pooled Stockfish processes (python-chess `SimpleEngine`).

This is the only module that sees raw engine scores. Everything it returns is in centipawns
from the `pov` colour's point of view (default: the side to move).

Mate scores (python-chess semantics, `score.pov(pov).score(mate_score=MATE_CP)`): if `pov`
mates in m moves (UCI `score mate m`, m counted in full moves, not plies) the cp value is
`MATE_CP - m`; if `pov` is mated in m moves it is `-(MATE_CP - m)`. `PVLine.mate` keeps the
signed move distance (+m / -m). Any |cp| >= MATE_THRESHOLD is a mate score.

Searches are node- or depth-limited only (never time-limited), with Threads=1 and a fixed Hash,
so results are reproducible. `Engine.stop()` (safe from another thread) ends the current search
early and `analyse()` returns the best-so-far lines.
"""

from __future__ import annotations

import atexit
import contextlib
import logging
import os
import threading
import weakref
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Self

import chess
import chess.engine

MATE_CP = 32000
MATE_THRESHOLD = MATE_CP - 1000  # |cp| at or above this is a mate score
_INFO = chess.engine.INFO_BASIC | chess.engine.INFO_SCORE | chess.engine.INFO_PV

log = logging.getLogger(__name__)


@dataclass
class PVLine:
    move: chess.Move  # first move of this PV
    cp: int  # centipawns from `pov`'s POV
    mate: int | None  # signed mate distance in moves from `pov`, if any
    depth: int
    seldepth: int | None
    nodes: int
    pv: list[chess.Move]
    rank: int  # 1-based MultiPV rank (1 = best)
    eval_by_depth: dict[int, int] = field(default_factory=dict)  # rank-1 only, trajectory=True
    best_by_depth: dict[int, chess.Move] = field(default_factory=dict)  # same conditions


def is_mate_cp(cp: int) -> bool:
    return abs(cp) >= MATE_THRESHOLD


def uci_score(cp: int) -> str:
    """Format a pov cp value for a UCI `info score` field: `cp X` or `mate ±N` (moves)."""
    if is_mate_cp(cp):
        m = MATE_CP - abs(cp)
        return f"mate {m if cp > 0 else -m}"
    return f"cp {cp}"


def pov_cp(score: chess.engine.PovScore, pov: chess.Color) -> tuple[int, int | None]:
    """(cp, signed mate-in-moves) from `pov`, using the MATE_CP convention above."""
    s = score.pov(pov)
    cp = s.score(mate_score=MATE_CP)
    assert cp is not None
    return int(cp), s.mate()


def has_tablebases(path: str | None) -> bool:
    """True if any directory in the os.pathsep-separated `path` holds Syzygy WDL files."""
    if not path:
        return False
    for p in str(path).split(os.pathsep):
        d = Path(p)
        try:
            if d.is_dir() and any(d.glob("*.rtbw")):
                return True
        except OSError:
            continue
    return False


# Engines still alive at interpreter shutdown are closed before non-daemon threads are joined
# (python-chess runs each engine's event loop on a non-daemon thread).
_LIVE: weakref.WeakSet[Engine] = weakref.WeakSet()


def _close_all() -> None:
    for eng in list(_LIVE):
        with contextlib.suppress(Exception):  # best effort at shutdown
            eng.close()


_register = getattr(threading, "_register_atexit", None)
try:
    if _register is not None:
        _register(_close_all)
    else:  # pragma: no cover
        atexit.register(_close_all)
except RuntimeError:  # pragma: no cover - interpreter already shutting down
    atexit.register(_close_all)


class Engine:
    """One persistent UCI engine process. Not re-entrant: one search at a time (locked)."""

    def __init__(
        self,
        path: str,
        *,
        hash_mb: int = 64,
        threads: int = 1,
        syzygy_path: str | None = None,
        name: str = "sf",
    ) -> None:
        self.path = str(path)
        self.name = name
        self.hash_mb = int(hash_mb)
        self.threads = int(threads)
        self._lock = threading.Lock()  # held for the duration of a search
        self._cur_lock = threading.Lock()  # guards self._current
        self._current: chess.engine.SimpleAnalysisResult | None = None
        self._closed = True  # until the process is up
        self._game: object = object()  # python-chess sends ucinewgame when this changes
        self._engine = chess.engine.SimpleEngine.popen_uci([self.path], timeout=30.0)
        self._closed = False
        _LIVE.add(self)
        options: dict[str, Any] = {"Threads": self.threads, "Hash": self.hash_mb}
        self.syzygy_path = syzygy_path if has_tablebases(syzygy_path) else None
        if syzygy_path and not self.syzygy_path:
            log.info("%s: no Syzygy files under %s; tablebases disabled", name, syzygy_path)
        if self.syzygy_path and "SyzygyPath" in self._engine.options:
            options["SyzygyPath"] = self.syzygy_path
        try:
            self._engine.configure(options)
        except Exception:
            self.close()
            raise

    @property
    def pid(self) -> int | None:
        try:
            return int(self._engine.transport.get_pid())
        except Exception:  # noqa: BLE001
            return None

    def new_game(self) -> None:
        """Start a new game: `ucinewgame` (hash cleared) + `isready`.

        python-chess sends `ucinewgame` lazily, right before the next search, whenever the game
        token changes; we change the token and ping (`isready`) here.
        """
        with self._lock:
            self._game = object()
            self._engine.ping()

    def stop(self) -> None:
        """End the current search early (thread-safe). No-op if not searching."""
        with self._cur_lock:
            cur = self._current
        if cur is not None:
            with contextlib.suppress(Exception):  # the search may have just finished
                cur.stop()

    def analyse(
        self,
        board: chess.Board,
        *,
        nodes: int | None = None,
        depth: int | None = None,
        multipv: int = 1,
        pov: chess.Color | None = None,
        trajectory: bool = False,
    ) -> list[PVLine]:
        """Search `board` (node- or depth-limited) and return MultiPV lines sorted by rank.

        Exactly one of `nodes`/`depth`. Returns [] if the position has no legal moves.
        With `trajectory=True` the rank-1 line carries `eval_by_depth`/`best_by_depth` built
        from the iterative-deepening info stream (the last rank-1 report at each depth; for the
        final, possibly unfinished depth that report may be an aspiration bound).
        Rank 1 is always the engine's `bestmove`.
        """
        if (nodes is None) == (depth is None):
            raise ValueError("pass exactly one of nodes= or depth=")
        if (nodes is not None and nodes <= 0) or (depth is not None and depth <= 0):
            raise ValueError("nodes/depth must be positive")
        n_legal = board.legal_moves.count()
        if n_legal == 0:
            return []
        pov = board.turn if pov is None else pov
        limit = (
            chess.engine.Limit(nodes=nodes)
            if nodes is not None
            else chess.engine.Limit(depth=depth)
        )
        k = max(1, min(int(multipv), n_legal))

        latest: dict[int, dict[str, Any]] = {}
        eval_by_depth: dict[int, int] = {}
        best_by_depth: dict[int, chess.Move] = {}
        with self._lock:
            if self._closed:
                raise chess.engine.EngineTerminatedError(f"{self.name}: engine closed")
            analysis = self._engine.analysis(board, limit, multipv=k, game=self._game, info=_INFO)
            with self._cur_lock:
                self._current = analysis
            try:
                for info in analysis:
                    if "pv" not in info or "score" not in info or not info["pv"]:
                        continue
                    rank = int(info.get("multipv", 1))
                    # Newest report wins, bound or not: the report Stockfish prints when the
                    # node limit stops it mid-iteration (often a lowerbound after a fail-high
                    # on a new best move) is the one its `bestmove` comes from.
                    latest[rank] = info
                    if trajectory and rank == 1 and "depth" in info:
                        cp, _ = pov_cp(info["score"], pov)
                        eval_by_depth[int(info["depth"])] = cp
                        best_by_depth[int(info["depth"])] = info["pv"][0]
                best = analysis.wait()
            finally:
                with self._cur_lock:
                    self._current = None
                analysis.stop()  # no-op if finished; makes sure the engine is idle

        lines: list[PVLine] = []
        for rank in sorted(latest):
            info = latest[rank]
            cp, mate = pov_cp(info["score"], pov)
            pv = list(info["pv"])
            lines.append(
                PVLine(
                    move=pv[0],
                    cp=cp,
                    mate=mate,
                    depth=int(info.get("depth", 0)),
                    seldepth=info.get("seldepth"),
                    nodes=int(info.get("nodes", 0)),
                    pv=pv,
                    rank=len(lines) + 1,
                )
            )
        if not lines:
            # Stopped before depth 1 finished: fall back to the engine's bestmove, score unknown.
            move = best.move if best.move is not None else next(iter(board.legal_moves))
            lines.append(PVLine(move, 0, None, 0, None, 0, [move], 1))
        elif best.move is not None and best.move != lines[0].move:
            # Rank 1 is always Stockfish's own bestmove (the move plain Stockfish would play).
            log.debug("%s: bestmove %s != rank-1 PV %s", self.name, best.move, lines[0].move)
            i = next((i for i, ln in enumerate(lines) if ln.move == best.move), None)
            if i is not None:
                lines.insert(0, lines.pop(i))
            else:
                top = lines[0]
                pv = [best.move] + ([best.ponder] if best.ponder else [])
                lines.insert(0, PVLine(best.move, top.cp, None, top.depth, None, top.nodes, pv, 1))
                lines = lines[:k]
            for r, ln in enumerate(lines, 1):
                ln.rank = r
        if trajectory:
            lines[0].eval_by_depth = dict(sorted(eval_by_depth.items()))
            lines[0].best_by_depth = dict(sorted(best_by_depth.items()))
        return lines

    def close(self) -> None:
        """Quit the engine process cleanly (kill it if it does not respond). Idempotent."""
        if self._closed:
            return
        self._closed = True
        _LIVE.discard(self)
        self.stop()
        got = self._lock.acquire(timeout=5.0)
        try:
            if got:
                with contextlib.suppress(Exception):  # the engine may already be dead
                    self._engine.quit()
            self._engine.close()
        finally:
            if got:
                self._lock.release()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def __del__(self) -> None:
        with contextlib.suppress(Exception):
            if not self.__dict__.get("_closed", True):
                self.close()


class EnginePool:
    """A fixed set of persistent engines, created once (never one process per move)."""

    def __init__(self, path: str, n: int, **engine_kwargs: Any) -> None:
        if n < 1:
            raise ValueError("pool needs at least one engine")
        base = str(engine_kwargs.pop("name", "sf"))
        self.engines: list[Engine] = []
        try:
            for i in range(n):
                self.engines.append(Engine(path, name=f"{base}{i}", **engine_kwargs))
        except Exception:
            self.close()
            raise

    def __len__(self) -> int:
        return len(self.engines)

    def __getitem__(self, i: int) -> Engine:
        return self.engines[i]

    def new_game(self) -> None:
        for e in self.engines:
            e.new_game()

    def stop(self) -> None:
        for e in self.engines:
            e.stop()

    def close(self) -> None:
        for e in self.engines:
            e.close()
