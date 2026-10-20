"""LostFish UCI front end: `python -m lostfish.uci` (or the `lostfish` console script).

The main thread reads stdin; each `go` runs on a worker thread so `isready`/`stop` stay
responsive. Exactly one `bestmove` is printed per `go`. Searches are delegated to a Player
(docs/INTERFACES.md): PassthroughPlayer when the `Steering` option is false, otherwise
`lostfish.play.SteeringPlayer` (imported lazily; falls back to passthrough if unavailable).
"""

from __future__ import annotations

import contextlib
import copy
import importlib
import logging
import os
import signal
import sys
import threading
import time
from dataclasses import dataclass
from typing import Any, Protocol, TextIO

import chess

from lostfish.config import Config, load_config
from lostfish.engines import uci_score
from lostfish.passthrough import PassthroughPlayer
from lostfish.telemetry import log_move, move_record
from lostfish.timeman import Budget, GoParams, parse_go, plan

ENGINE_NAME = "LostFish"
VERSION = "0.0.1"
AUTHOR = "LostFish"
_EMPTY = ("", "<empty>")


class Player(Protocol):
    def new_game(self) -> None: ...
    def set_opponent(self, name: str | None, rating: int | None) -> None: ...
    def choose(self, board: chess.Board, budget: Budget) -> tuple[chess.Move, dict]: ...
    def close(self) -> None: ...


@dataclass
class Option:
    name: str
    kind: str  # "spin" | "check" | "string"
    default: Any
    lo: int = 0
    hi: int = 0

    def declare(self) -> str:
        if self.kind == "spin":
            return f"option name {self.name} type spin default {self.default} min {self.lo} max {self.hi}"
        if self.kind == "check":
            return f"option name {self.name} type check default {str(self.default).lower()}"
        return f"option name {self.name} type string default {self.default or '<empty>'}"

    def parse(self, raw: str) -> Any:
        if self.kind == "spin":
            return max(self.lo, min(self.hi, int(float(raw))))
        if self.kind == "check":
            return raw.strip().lower() == "true"
        return "" if raw.strip() in _EMPTY else raw.strip()


def parse_uci_opponent_local(value: str) -> tuple[str | None, int | None, str | None]:
    """lichess-bot format: "<title|none> <rating|none> <computer|human> <name...>"."""
    tok = value.split()
    if len(tok) < 4:
        return ((" ".join(tok) or None) if len(tok) == 1 else None), None, None
    rating = int(tok[1]) if tok[1].isdigit() else None
    kind = tok[2].lower() if tok[2].lower() in ("computer", "human") else None
    return " ".join(tok[3:]) or None, rating, kind


def parse_opponent(value: str) -> tuple[str | None, int | None, str | None]:
    try:
        from lostfish.profiles import parse_uci_opponent

        return parse_uci_opponent(value)
    except Exception:  # noqa: BLE001 - profiles may not exist yet or may reject the value
        return parse_uci_opponent_local(value)


def emergency_move(board: chess.Board) -> chess.Move | None:
    """Last resort when every engine failed: mate in one if available, else any legal move."""
    moves = list(board.legal_moves)
    for m in moves:
        board.push(m)
        mate = board.is_checkmate()
        board.pop()
        if mate:
            return m
    return moves[0] if moves else None


def info_line(board: chess.Board, move: chess.Move, tel: dict, ms: float) -> str:
    """A standard `info ... score ... pv` line for the chosen move, if its score is known."""
    cand = next(
        (
            c
            for c in tel.get("candidates") or []
            if isinstance(c, dict) and c.get("move") == move.uci() and c.get("cp") is not None
        ),
        None,
    )
    if cand is None:
        return ""
    pv: list[str] = []
    b = board.copy(stack=False)
    for u in cand.get("pv") or [move.uci()]:
        try:
            mv = chess.Move.from_uci(str(u))
        except ValueError:
            break
        if mv not in b.legal_moves or (not pv and mv != move):
            break
        pv.append(mv.uci())
        b.push(mv)
    parts = ["info"]
    for key in ("depth", "seldepth"):
        if cand.get(key):
            parts += [key, str(int(cand[key]))]
    parts += ["score", uci_score(int(cand["cp"]))]
    if cand.get("nodes"):
        parts += ["nodes", str(int(cand["nodes"]))]
    parts += ["time", str(int(ms)), "pv", " ".join(pv or [move.uci()])]
    return " ".join(parts)


class UciEngine:
    def __init__(self, cfg: Config, out: TextIO | None = None) -> None:
        self.cfg = cfg
        self.out = out or sys.stdout
        self.warnings: list[str] = []
        self._out_lock = threading.Lock()
        self._player_lock = threading.RLock()
        self._release = threading.Event()  # stop / ponderhit / quit release a held bestmove
        self._worker: threading.Thread | None = None
        self.debug = False
        self.board = chess.Board()
        self.player: Player | None = None
        self.player_kind = ""
        self._player_key: tuple | None = None
        self.opponent: tuple[str | None, int | None, str | None] = (None, None, None)
        self._initial_ms: int | None = None
        self.decl = [
            Option("Hash", "spin", cfg.engines.hash_mb, 1, 65536),
            Option("Threads", "spin", 1, 1, 1024),
            Option("SyzygyPath", "string", cfg.engines.syzygy_path or ""),
            Option("UCI_Opponent", "string", ""),
            Option("Steering", "check", False),
            Option("MoveOverhead", "spin", 100, 0, 5000),
            Option("Profile", "string", ""),
        ]
        self.options: dict[str, Any] = {o.name: o.default for o in self.decl}
        self._by_key = {o.name.lower().replace(" ", ""): o for o in self.decl}

    # -- output --------------------------------------------------------------------------
    def send(self, line: str) -> None:
        with self._out_lock, contextlib.suppress(OSError, ValueError):  # GUI went away
            self.out.write(line + "\n")
            self.out.flush()

    def info(self, msg: str) -> None:
        self.send("info string " + " ".join(str(msg).split()))

    # -- main loop -----------------------------------------------------------------------
    def run(self, inp: TextIO) -> int:
        while True:
            line = inp.readline()
            if not line or not self.handle(line):
                break
        self.shutdown()
        return 0

    def handle(self, line: str) -> bool:
        """Process one command line. Returns False on `quit`."""
        tokens = line.strip().split()
        handlers = self._handlers
        # UCI: skip unknown leading tokens and parse the rest ("joho debug on" -> "debug on").
        while tokens and tokens[0] not in handlers:
            tokens = tokens[1:]
        if not tokens:
            return True
        cmd, args = tokens[0], tokens[1:]
        try:
            handlers[cmd](args)
        except Exception as exc:  # noqa: BLE001 - never die on a bad command
            self.info(f"error in {cmd}: {type(exc).__name__}: {exc}")
        return cmd != "quit"

    @property
    def _handlers(self) -> dict[str, Any]:
        return {
            "uci": self.cmd_uci,
            "debug": self.cmd_debug,
            "isready": self.cmd_isready,
            "setoption": self.cmd_setoption,
            "register": lambda _a: None,
            "ucinewgame": self.cmd_ucinewgame,
            "position": self.cmd_position,
            "go": self.cmd_go,
            "stop": self.cmd_stop,
            "ponderhit": self.cmd_ponderhit,
            "quit": lambda _a: None,
        }

    def cmd_uci(self, _args: list[str]) -> None:
        self.send(f"id name {ENGINE_NAME} {VERSION}")
        self.send(f"id author {AUTHOR}")
        for o in self.decl:
            self.send(o.declare())
        for w in self.warnings:
            self.info(w)
        self.send("uciok")

    def cmd_debug(self, args: list[str]) -> None:
        self.debug = bool(args) and args[0] == "on"

    def cmd_isready(self, _args: list[str]) -> None:
        if not self.searching:
            self.ensure_player()
        self.send("readyok")

    def cmd_setoption(self, args: list[str]) -> None:
        if "name" not in args:
            return
        i = args.index("name") + 1
        j = args.index("value", i) if "value" in args[i:] else len(args)
        name, raw = " ".join(args[i:j]), " ".join(args[j + 1 :])
        opt = self._by_key.get(name.lower().replace(" ", ""))
        if opt is None:
            if self.debug:
                self.info(f"unknown option {name!r} ignored")
            return
        try:
            self.options[opt.name] = opt.parse(raw)
        except ValueError:
            self.info(f"bad value {raw!r} for option {opt.name}")
            return
        if opt.name == "Threads" and self.options["Threads"] != 1:
            self.info("LostFish runs each Stockfish with Threads=1; Threads accepted, not used")
        if opt.name == "UCI_Opponent":
            self.opponent = parse_opponent(raw) if raw.strip() not in _EMPTY else (None, None, None)
            self.apply_opponent()
        elif opt.name == "Profile":
            self.apply_opponent()

    def cmd_ucinewgame(self, _args: list[str]) -> None:
        self.finish_search()
        self.board = chess.Board()
        self._initial_ms = None
        player = self.ensure_player()
        if player is not None:
            try:
                player.new_game()
            except Exception as exc:  # noqa: BLE001
                self.info(f"new_game failed: {exc}; restarting player")
                self.close_player()

    def cmd_position(self, args: list[str]) -> None:
        if not args:
            return
        k = args.index("moves") if "moves" in args else len(args)
        if args[0] == "startpos":
            board = chess.Board()
        elif args[0] == "fen":
            board = chess.Board(" ".join(args[1:k]))
        else:
            self.info(f"bad position command: {' '.join(args)}")
            return
        for u in args[k + 1 :]:
            try:
                board.push(board.parse_uci(u))
            except ValueError:
                self.info(f"illegal move {u} in position command; ignoring the rest")
                break
        self.board = board

    def cmd_go(self, args: list[str]) -> None:
        t0 = time.perf_counter()
        self.finish_search()
        go = parse_go(args)
        self._release.clear()
        board = self.board.copy()
        if any(board.generate_legal_moves()):
            self.ensure_player()
        self._worker = threading.Thread(
            target=self._search, args=(board, go, t0), name="lostfish-search", daemon=True
        )
        self._worker.start()

    def cmd_stop(self, _args: list[str]) -> None:
        if self.searching:
            self._release.set()
            self._stop_player()

    def cmd_ponderhit(self, _args: list[str]) -> None:
        # The ponder search was planned on our clock already; just release its bestmove.
        self._release.set()

    # -- search ----------------------------------------------------------------------------
    @property
    def searching(self) -> bool:
        return self._worker is not None and self._worker.is_alive()

    def _stop_player(self) -> None:
        stop = getattr(self.player, "stop", None)
        if callable(stop):
            with contextlib.suppress(Exception):
                stop()

    def finish_search(self, timeout: float = 30.0) -> None:
        """Stop and join a running search (its bestmove is still printed)."""
        if self._worker is None:
            return
        if self._worker.is_alive():
            self._release.set()
            self._stop_player()
            self._worker.join(timeout)
        self._worker = None

    def _search(self, board: chess.Board, go: GoParams, t0: float) -> None:
        move: chess.Move | None = None
        tel: dict = {}
        budget: Budget | None = None
        try:
            if any(board.generate_legal_moves()):
                us = board.turn
                remaining = go.wtime if us == chess.WHITE else go.btime
                if remaining is not None:
                    self._initial_ms = max(self._initial_ms or 0, remaining)
                budget = plan(
                    go,
                    us,
                    self.cfg,
                    ply=board.ply(),
                    initial_ms=self._initial_ms,
                    overhead_ms=int(self.options["MoveOverhead"]),
                )
                if self.debug:
                    self.info(f"budget {budget}")
                move, tel = self._choose(board, budget)
        except Exception as exc:  # noqa: BLE001 - must still answer bestmove
            self.info(f"search failed: {type(exc).__name__}: {exc}")
            move = emergency_move(board)
            tel = {"reason": f"emergency: {type(exc).__name__}"}
        finally:
            elapsed = round((time.perf_counter() - t0) * 1000.0, 1)
            if go.infinite or go.ponder:
                self._release.wait()  # UCI: no bestmove before stop/ponderhit
            if move is not None and (info := info_line(board, move, tel, elapsed)):
                self.send(info)
            self.send(f"bestmove {move.uci() if move is not None else '0000'}")
        if move is not None and budget is not None:
            self._log(board, go, budget, move, tel, elapsed)

    def _choose(self, board: chess.Board, budget: Budget) -> tuple[chess.Move, dict]:
        with self._player_lock:
            player = self.player
        try:
            if player is None:
                raise RuntimeError("no player available")
            move, tel = player.choose(board, budget)
            if move not in board.legal_moves:
                raise ValueError(f"player returned illegal move {move}")
            return move, dict(tel or {})
        except Exception as exc:  # noqa: BLE001 - retry once on a fresh passthrough
            self.info(f"{self.player_kind or 'player'} failed: {type(exc).__name__}: {exc}")
            with self._player_lock:
                self.close_player()
                self.player = PassthroughPlayer(self._player_cfg())
                self.player_kind = "passthrough"
                self._player_key = None  # rebuild per options before the next search
                self.apply_opponent()
                move, tel = self.player.choose(board, budget)
            tel = dict(tel or {})
            tel["reason"] = f"fallback after {type(exc).__name__}"
            return move, tel

    def _log(
        self,
        board: chess.Board,
        go: GoParams,
        budget: Budget,
        move: chess.Move,
        tel: dict,
        ms: float,
    ) -> None:
        name, rating, kind = self.opponent
        opp = {"name": name, "rating": rating, "kind": kind, "profile": self._profile()}
        rec = move_record(
            tel,
            fen=board.fen(),
            ply=board.ply(),
            opponent=opp,
            budget=budget,
            go=go,
            chosen=move.uci(),
            elapsed_ms=ms,
            player=self.player_kind,
        )
        log_move(rec)

    # -- player lifecycle --------------------------------------------------------------------
    def _profile(self) -> str | None:
        return str(self.options["Profile"]) or None

    def _player_cfg(self) -> Config:
        cfg = copy.deepcopy(self.cfg)
        cfg.engines.hash_mb = int(self.options["Hash"])
        cfg.engines.threads = 1
        sp = str(self.options["SyzygyPath"])
        cfg.engines.syzygy_path = (
            None
            if sp in _EMPTY
            else os.pathsep.join(str(cfg.resolve_path(p)) for p in sp.split(os.pathsep) if p)
        )
        return cfg

    def _make_player(self, steering: bool, cfg: Config) -> Player:
        if steering:
            try:
                mod = importlib.import_module("lostfish.play")
                player = mod.SteeringPlayer(cfg)
                self.player_kind = "steering"
                return player
            except Exception as exc:  # noqa: BLE001 - agent C's module may be absent or broken
                self.info(f"steering unavailable ({type(exc).__name__}: {exc}); using passthrough")
        self.player_kind = "passthrough"
        return PassthroughPlayer(cfg)

    def ensure_player(self) -> Player | None:
        """Build (or rebuild after an option change) the player. Never raises."""
        key = (bool(self.options["Steering"]), self.options["Hash"], self.options["SyzygyPath"])
        with self._player_lock:
            if self.player is not None and self._player_key == key:
                return self.player
            self.close_player()
            try:
                self.player = self._make_player(key[0], self._player_cfg())
                self._player_key = key
                self.apply_opponent()
            except Exception as exc:  # noqa: BLE001 - e.g. missing Stockfish binary
                self.info(f"cannot start player: {type(exc).__name__}: {exc}")
                self.player, self._player_key = None, None
            return self.player

    def apply_opponent(self) -> None:
        name, rating, _kind = self.opponent
        if self.player is None:
            return
        try:
            self.player.set_opponent(self._profile() or name, rating)
        except Exception as exc:  # noqa: BLE001
            self.info(f"set_opponent failed: {exc}")

    def close_player(self) -> None:
        with self._player_lock:
            if self.player is not None:
                with contextlib.suppress(Exception):
                    self.player.close()
            self.player, self._player_key = None, None

    def shutdown(self) -> None:
        self.finish_search(timeout=10.0)
        self.close_player()


def _fallback_config() -> Config:
    cfg = Config()
    cfg.engines.stockfish = str(cfg.resolve_path(cfg.engines.stockfish))
    cfg.profiles.dir = str(cfg.resolve_path(cfg.profiles.dir))
    return cfg


def main(argv: list[str] | None = None) -> int:
    del argv  # no command-line arguments; everything arrives over UCI
    logging.getLogger("chess.engine").setLevel(logging.ERROR)  # e.g. SF's own `info string`
    warnings: list[str] = []
    try:
        cfg = load_config()
    except Exception as exc:  # noqa: BLE001 - stay a valid UCI engine on a bad config
        cfg = _fallback_config()
        warnings.append(f"config error ({type(exc).__name__}: {exc}); using defaults")
    engine = UciEngine(cfg)
    engine.warnings = warnings
    with contextlib.suppress(ValueError):  # not in the main thread
        signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    try:
        return engine.run(sys.stdin)
    except KeyboardInterrupt:
        return 0
    finally:
        engine.shutdown()


if __name__ == "__main__":
    sys.exit(main())
