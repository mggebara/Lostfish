"""SteeringPlayer: the Player that uci.py drives when Steering=true.

Per move: certify (MultiPV on the certifier) → single candidate? play it → exploit search with
the opponent proxy + evaluator (`steer.pick_detailed`) → telemetry dict. Three persistent engine
processes are created once in __init__ and reused for every move; close() quits them.
"""

from __future__ import annotations

import copy
import dataclasses
import logging
import math
import os
import random
import threading
import time
from collections.abc import Callable, MutableMapping
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import chess

from lostfish.certify import Certified, certify_position, knob
from lostfish.opponent import DEFAULT_TEMPERATURE_CP, Lc0PolicyProxy, StockfishDepthProxy
from lostfish.steer import ExtractFn, Scored, pick_detailed

if TYPE_CHECKING:
    from lostfish.config import Config
    from lostfish.engines import Engine
    from lostfish.profiles import Profile
    from lostfish.timeman import Budget

log = logging.getLogger(__name__)

EngineFactory = Callable[..., "Engine"]
ProfileLoader = Callable[[str | None, Any], Any]


@dataclass
class FallbackProfile:
    """Used only if lostfish.profiles is unavailable or load_profile raises (it should not)."""

    name: str = "_generic"
    effective_depth: int = 99  # capped by budget.proxy_depth_cap
    weak_clusters: list[Any] = field(default_factory=list)


def _override(cfg: Any, section: str, key: str, value: Any) -> Any:
    """Deep-copy cfg and set cfg.<section>.<key> = value (dataclass, frozen dataclass or dict)."""
    new = copy.deepcopy(cfg)
    sec = new[section] if isinstance(new, MutableMapping) else getattr(new, section)
    if isinstance(sec, MutableMapping):
        sec[key] = value
        return new
    try:
        setattr(sec, key, value)
    except (AttributeError, dataclasses.FrozenInstanceError):
        setattr(new, section, dataclasses.replace(sec, **{key: value}))
    return new


def _ms(since: float) -> float:
    return round((time.perf_counter() - since) * 1000.0, 2)


class SteeringPlayer:
    """certify → proxy → exploit search → steer.pick, with safe fallbacks at every stage."""

    _steer_ms_ema: float | None = (
        None  # running mean cost of a full steering pass (clock_skip rule)
    )

    def __init__(
        self,
        cfg: Config | None = None,
        *,
        steering_lambda: float | None = None,
        tolerance_cp: int | None = None,
        engine_factory: EngineFactory | None = None,
        profile_loader: ProfileLoader | None = None,
        extract: ExtractFn | None = None,
    ) -> None:
        if cfg is None:
            from lostfish.config import load_config

            cfg = load_config()
        if steering_lambda is not None:
            cfg = _override(cfg, "steer", "lambda_weakness", float(steering_lambda))
        if tolerance_cp is not None:
            cfg = _override(cfg, "certify", "tolerance_cp", int(tolerance_cp))
        self.cfg = cfg
        self.predictor = None
        self._predictor_mode = str(knob(cfg, "steer", "predictor_mode", "gate"))
        self._rng = random.Random(
            os.getpid() ^ int(time.time() * 1000)
        )  # for predictor_mode: random
        predictor_path = knob(cfg, "steer", "predictor_path", None)
        if predictor_path:
            from lostfish.predictor import VictimErrorPredictor

            self.predictor = VictimErrorPredictor(str(predictor_path))
        self._extract = extract
        self._profile_loader = profile_loader
        if engine_factory is None:
            from lostfish.engines import Engine

            engine_factory = Engine
        path = str(knob(cfg, "engines", "stockfish", "engines/stockfish"))
        hash_mb = int(knob(cfg, "engines", "hash_mb", 64))
        threads = int(knob(cfg, "engines", "threads", 1))
        syzygy = knob(cfg, "engines", "syzygy_path", None)
        proxy_hash = int(knob(cfg, "steer", "proxy_hash_mb", 16))
        self._engines: list[Any] = []
        try:
            self.certifier = self._spawn(
                engine_factory, path, hash_mb, threads, syzygy, "certifier"
            )
            self.proxy_engine = self._spawn(engine_factory, path, proxy_hash, 1, None, "proxy")
            self.evaluator = self._spawn(
                engine_factory, path, hash_mb, threads, syzygy, "evaluator"
            )
        except Exception:
            self.close()
            raise
        self.opponent_name: str | None = None
        self.opponent_rating: int | None = None
        self.profile: Profile | FallbackProfile | None = None
        self._stop = threading.Event()
        self._lc0_proxy: Lc0PolicyProxy | None = None

    def _spawn(
        self,
        factory: EngineFactory,
        path: str,
        hash_mb: int,
        threads: int,
        syzygy: str | None,
        name: str,
    ) -> Engine:
        eng = factory(path, hash_mb=hash_mb, threads=threads, syzygy_path=syzygy, name=name)
        self._engines.append(eng)
        return eng

    # ---------------------------------------------------------------- Player protocol

    def new_game(self) -> None:
        for eng in self._engines:
            eng.new_game()

    def set_opponent(self, name: str | None, rating: int | None) -> None:
        self.opponent_name = name
        self.opponent_rating = rating
        self.profile = self._load_profile(name)

    def stop(self) -> None:
        """UCI `stop` (called from another thread): end the running search, skip the rest."""
        self._stop.set()
        for eng in list(self._engines):
            stop = getattr(eng, "stop", None)
            if callable(stop):
                try:
                    stop()
                except Exception:
                    log.exception("stopping %s failed", getattr(eng, "name", eng))

    def close(self) -> None:
        if self._lc0_proxy is not None:
            self._lc0_proxy.close()
            self._lc0_proxy = None
        engines, self._engines = self._engines, []
        for eng in engines:
            try:
                eng.close()
            except Exception:
                log.exception("closing %s failed", getattr(eng, "name", eng))

    def choose(self, board: chess.Board, budget: Budget) -> tuple[chess.Move, dict[str, Any]]:
        t_start = time.perf_counter()
        self._stop.clear()
        deadline = time.monotonic() + max(0, int(budget.soft_ms)) / 1000.0
        pov = board.turn
        timings: dict[str, float] = {}
        record: dict[str, Any] = {"reason": "error", "deadline_hit": False}
        certified: Certified | None = None
        scored: list[Scored] = []
        try:
            t = time.perf_counter()
            certified = certify_position(self.certifier, board, pov, budget, self.cfg)
            timings["certify"] = _ms(t)
            if self.profile is None:
                self.profile = self._load_profile(self.opponent_name)
            depth = self._proxy_depth(budget)
            record["tolerance_cp"] = certified.tolerance_cp
            record["effective_depth"] = depth
            record["best"] = certified.best.move.uci()
            if len(certified.candidates) == 1:
                move, record["reason"] = certified.best.move, "single_candidate"
            elif time.monotonic() >= deadline or self._stop.is_set():  # no time to steer
                move = certified.best.move
                record.update(reason="fallback_best", deadline_hit=True)
            elif self._clock_skip(deadline, record):  # low clock: steering could not finish
                move, record["reason"] = certified.best.move, "clock_skip"
            else:
                risky = self._predict_risk(board, certified, record, timings)
                if risky is False:  # predictor gate: nothing worth the exact tree here
                    move, record["reason"] = certified.best.move, "gate_skip"
                elif risky is True and self._predictor_mode == "steer":
                    move, record["reason"] = self._steer_by_risk(certified, record)
                else:
                    move, scored = self._steer(
                        board, certified, budget, depth, deadline, record, timings
                    )
        except Exception as exc:  # noqa: BLE001 - always answer with a legal move
            record["reason"] = "error"
            record["error"] = f"{type(exc).__name__}: {exc}"
            move = self._emergency_move(board, budget, certified)
        if not board.is_legal(move):
            record["reason"] = "error"
            record["error"] = f"chosen move {move} is illegal; " + record.get("error", "")
            move = self._emergency_move(board, budget, None)
        record["chosen"] = move.uci()
        depth_reached = max(certified.eval_by_depth, default=None) if certified else None
        record["candidates"] = _candidate_rows(
            certified,
            scored,
            depth=int(depth_reached) if depth_reached else None,
            nodes=int(budget.certify_nodes),
        )
        record["profile"] = getattr(self.profile, "name", None)
        record["lambda"] = float(knob(self.cfg, "steer", "lambda_weakness", 0.15))
        record["line_depth"] = int(knob(self.cfg, "steer", "line_depth", 1))
        record["config"] = os.path.basename(os.environ.get("LOSTFISH_CONFIG", "lostfish.yaml"))
        timings["total"] = _ms(t_start)
        record["timings_ms"] = timings
        return move, record

    # ---------------------------------------------------------------- helpers

    def _clock_skip(self, deadline: float, record: dict[str, Any]) -> bool:
        """True when the time left before the soft deadline cannot fit a useful steering pass.

        Steering needs at least two candidates evaluated before it can deviate, so with less than
        `steer.clock_skip_ms` left, or less than `steer.clock_skip_factor` x the running mean of
        recent steering passes, it would only burn clock. Node-limited moves get a >= 30 s soft
        budget (timeman), so fixed-node gauntlets never skip.
        """
        left_ms = (deadline - time.monotonic()) * 1000.0
        need = float(knob(self.cfg, "steer", "clock_skip_ms", 250))
        if self._steer_ms_ema is not None:
            factor = float(knob(self.cfg, "steer", "clock_skip_factor", 0.5))
            need = max(need, factor * self._steer_ms_ema)
        record["clock"] = {"left_ms": round(left_ms), "need_ms": round(need)}
        return left_ms < need

    def _predict_risk(
        self,
        board: chess.Board,
        certified: Certified,
        record: dict[str, Any],
        timings: dict[str, float],
    ) -> bool | None:
        """Score each certified candidate's child position with the victim-error predictor.

        Returns None without a predictor; otherwise True when the position is worth steering
        (gate mode: max risk >= threshold; steer mode: always) and False when it is not.
        """
        if self.predictor is None:
            return None
        t = time.perf_counter()
        children = []
        for cand in certified.candidates:
            child = board.copy(stack=False)
            child.push(cand.move)
            children.append(child)
        risks = self.predictor.risk(children)
        timings["predictor"] = _ms(t)
        record["risk"] = {
            c.move.uci(): round(r, 3) for c, r in zip(certified.candidates, risks, strict=True)
        }
        if self._predictor_mode == "steer":
            return True
        if (
            self._predictor_mode == "random"
        ):  # control: open the gate at random at the predictor gate's rate
            rate = float(knob(self.cfg, "steer", "predictor_gate_rate", 0.25))
            return self._rng.random() < rate
        threshold = float(knob(self.cfg, "steer", "predictor_gate_threshold", 0.5))
        return max(risks) >= threshold

    def _steer_by_risk(
        self, certified: Certified, record: dict[str, Any]
    ) -> tuple[chess.Move, str]:
        """Predictor-only steering: expected eval = cp + gain * P(victim blunders after this move)."""
        gain = float(knob(self.cfg, "steer", "predictor_gain_cp", 300.0))
        min_gain = float(knob(self.cfg, "steer", "min_gain_cp", 0.0))
        risk = record.get("risk") or {}
        scores = {c.move: c.cp + gain * risk.get(c.move.uci(), 0.0) for c in certified.candidates}
        best = certified.best.move
        pick = max(scores, key=lambda m: scores[m])
        record["predictor_scores"] = {m.uci(): round(v, 1) for m, v in scores.items()}
        if pick != best and scores[pick] - scores[best] >= min_gain:
            return pick, "steer_pred"
        return best, "steer_pred_hold"

    def _steer(
        self,
        board: chess.Board,
        certified: Certified,
        budget: Budget,
        depth: int,
        deadline: float,
        record: dict[str, Any],
        timings: dict[str, float],
    ) -> tuple[chess.Move, list[Scored]]:
        temperature = float(knob(self.cfg, "steer", "reply_temperature_cp", DEFAULT_TEMPERATURE_CP))
        proxy = self._make_proxy(depth, temperature, record)
        t = time.perf_counter()
        result = pick_detailed(
            board,
            certified,
            self.profile,
            proxy,
            self.evaluator,
            budget,
            self.cfg,
            deadline=deadline,
            extract=self._extract,
            stop=self._stop,
        )
        timings["steer"] = _ms(t)
        timings.update({k: round(v, 2) for k, v in result.timings_ms.items()})
        record.update(reason=result.reason, deadline_hit=result.deadline_hit)
        if not result.deadline_hit and not self._stop.is_set():  # a complete pass: learn its cost
            ema = self._steer_ms_ema
            self._steer_ms_ema = (
                timings["steer"] if ema is None else 0.8 * ema + 0.2 * timings["steer"]
            )
        if result.error:
            record["error"] = result.error
        return result.move, result.scored

    def _make_proxy(
        self, depth: int, temperature: float, record: dict[str, Any]
    ) -> StockfishDepthProxy | Lc0PolicyProxy:
        """Opponent model for the current profile.

        `profile.proxy == "lc0_policy"` (Maia-like bots) uses a persistent Lc0 process with the
        network named in `profile.notes["lc0_weights"]` (path relative to the repo root); anything
        else, or any failure to start Lc0, falls back to Stockfish at the fingerprinted depth.
        """
        kind = str(getattr(self.profile, "proxy", "stockfish_depth") or "stockfish_depth")
        notes = getattr(self.profile, "notes", None) or {}
        weights = str(notes.get("lc0_weights") or "") if isinstance(notes, dict) else ""
        if kind == "lc0_policy" and weights:
            try:
                lc0_nodes = max(1, int(notes.get("lc0_nodes") or 1))
                stale = self._lc0_proxy is not None and (
                    self._lc0_proxy.weights != weights or self._lc0_proxy.nodes != lc0_nodes
                )
                if self._lc0_proxy is None or stale:
                    if self._lc0_proxy is not None:
                        self._lc0_proxy.close()
                        self._lc0_proxy = None
                    lc0_path = str(knob(self.cfg, "steer", "lc0_path", "lc0"))
                    self._lc0_proxy = Lc0PolicyProxy(lc0_path, weights, threads=1, nodes=lc0_nodes)
                record["proxy"] = f"lc0_policy:{weights.rsplit('/', 1)[-1]}@{lc0_nodes}"
                return self._lc0_proxy
            except Exception:
                log.exception("lc0 policy proxy unavailable (%s); using the depth proxy", weights)
        record["proxy"] = f"stockfish_depth:{depth}"
        return StockfishDepthProxy(self.proxy_engine, depth, temperature_cp=temperature)

    def _load_profile(self, name: str | None) -> Profile | FallbackProfile:
        try:
            loader = self._profile_loader
            if loader is None:
                from lostfish.profiles import load_profile as loader
            return loader(name, self.cfg)
        except Exception:
            log.exception("load_profile(%r) failed; using a built-in fallback profile", name)
            return FallbackProfile(name=name or "_generic")

    def _proxy_depth(self, budget: Budget) -> int:
        cap = int(budget.proxy_depth_cap)
        eff = getattr(self.profile, "effective_depth", None)
        depth = cap if not eff else min(int(eff), cap)
        return max(1, depth)

    def _emergency_move(
        self, board: chess.Board, budget: Budget, certified: Certified | None
    ) -> chess.Move:
        """Best certified move; else a fresh MultiPV=1 search on the evaluator; else first legal."""
        if certified is not None and board.is_legal(certified.best.move):
            return certified.best.move
        try:
            lines = self.evaluator.analyse(
                board, nodes=max(1, int(budget.certify_nodes)), multipv=1, pov=board.turn
            )
            if lines and board.is_legal(lines[0].move):
                return lines[0].move
        except Exception:
            log.exception("emergency search failed; playing the first legal move")
        return next(iter(board.legal_moves))


def _candidate_rows(
    certified: Certified | None,
    scored: list[Scored],
    *,
    depth: int | None = None,
    nodes: int | None = None,
) -> list[dict[str, Any]]:
    """JSON-safe telemetry rows, one per certified candidate (rank order).

    `pv`, `depth` and `nodes` let uci.py print a standard `info` line (fastchess/lichess-bot
    record them in the PGN); they describe the certify search the candidates came from.
    """
    if certified is None:
        return []
    by_move = {s.candidate.move: s for s in scored}
    rows: list[dict[str, Any]] = []
    for cand in certified.candidates:
        row: dict[str, Any] = {
            "move": cand.move.uci(),
            "cp": cand.cp,
            "rank": cand.rank,
            "pv": [m.uci() for m in (cand.pv or [cand.move])],
        }
        if depth:
            row["depth"] = int(depth)
        if nodes:
            row["nodes"] = int(nodes)
        s = by_move.get(cand.move)
        if s is not None:
            row["evaluated"] = s.evaluated
            row["expected_eval"] = s.expected_eval if s.evaluated else None
            row["weakness"] = round(s.weakness, 4)
            row["score"] = round(s.score, 2) if math.isfinite(s.score) else None
            row["replies"] = [
                {"move": r.uci(), "weight": round(w, 4), "eval": e} for r, w, e in s.replies
            ]
            for j, (line, evs) in enumerate(zip(s.lines, s.line_evals, strict=False)):
                if j < len(row["replies"]):
                    row["replies"][j]["line"] = line
                    row["replies"][j]["line_evals"] = evs
        rows.append(row)
    return rows
