"""Steering: exploit search over certified candidates plus a profile weakness bonus.

For each certified candidate c (best first, then rank order):
    after   = board + c
    replies = opponent.predict_reply(after)           # [(r_i, w_i)], Σ w_i = 1
    eval_i  = evaluator(after + r_i, nodes=eval_nodes) # LostFish POV
    expected_eval(c) = Σ w_i · eval_i
    score(c) = expected_eval(c) + λ · 100 · weakness_match(after)
The argmax (ties → better certified rank) is played, subject to the safety invariants in
`pick_detailed`. See docs/STEERING.md.
"""

from __future__ import annotations

import math
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import chess
import numpy as np

from lostfish.certify import MATE_CP, Candidate, Certified, knob

if TYPE_CHECKING:
    from lostfish.config import Config
    from lostfish.engines import Engine
    from lostfish.opponent import OpponentModel
    from lostfish.profiles import Profile
    from lostfish.timeman import Budget

ExtractFn = Callable[..., Any]  # features.extract(board, pov, *, eval_deep, eval_shallow)


@dataclass
class Scored:
    candidate: Candidate
    expected_eval: int  # Σ w_i · eval_after_reply_i (pov); candidate.cp when not evaluated
    weakness: float  # profile uplift match of the position after our move
    score: float  # expected_eval + lambda * 100 * weakness; -inf when not evaluated
    replies: list[tuple[chess.Move, float, int]] = field(default_factory=list)
    evaluated: bool = True  # False when skipped (deadline) or not searched (single candidate)
    lines: list[list[str]] = field(default_factory=list)  # per reply: uci moves after the candidate
    line_evals: list[list[int]] = field(default_factory=list)  # per reply: pov evals at our nodes


@dataclass
class Exploit:
    expected_eval: int
    replies: list[tuple[chess.Move, float, int]]
    shallow_cp: int | None  # proxy's eval of `after`, LostFish POV (None if not searched)
    lines: list[list[str]] = field(default_factory=list)
    line_evals: list[list[int]] = field(default_factory=list)


@dataclass
class PickResult:
    move: chess.Move
    scored: list[Scored]
    reason: str  # "steer" | "fallback_best" | "single_candidate" | "error"
    error: str | None = None
    deadline_hit: bool = False
    timings_ms: dict[str, float] = field(default_factory=dict)


def terminal_eval(board: chess.Board, pov: chess.Color) -> int | None:
    """±MATE_CP / 0 if the side to move has no legal moves, else None."""
    if board.is_checkmate():
        return -MATE_CP if board.turn == pov else MATE_CP
    if board.is_stalemate():
        return 0
    return None


def _prune(
    dist: list[tuple[chess.Move, float]], min_weight: float
) -> list[tuple[chess.Move, float]]:
    """Drop replies below min_weight (always keep the heaviest) and renormalise to sum 1."""
    dist = [(m, float(w)) for m, w in dist if math.isfinite(w) and w > 0]
    if not dist:
        return []
    top = max(w for _, w in dist)
    kept = [(m, w) for m, w in dist if w >= min_weight or w == top]
    total = sum(w for _, w in kept)
    return [(m, w / total) for m, w in kept]


def _add_ms(timings: dict[str, float] | None, key: str, since: float) -> None:
    if timings is not None:
        timings[key] = timings.get(key, 0.0) + (time.perf_counter() - since) * 1000.0


def line_value(
    board: chess.Board,
    pov: chess.Color,
    opponent: OpponentModel,
    evaluator: Engine,
    *,
    replies_left: int,
    line_nodes: int,
    eval_nodes: int,
    decisive_cp: int = 600,
    timings: dict[str, float] | None = None,
) -> tuple[int, list[str], list[int]]:
    """Victim-play rollout from a position with *us* to move (PLAN §1 idea 2, several plies deep).

    Each step plays our best move (evaluator, `line_nodes`) and then the opponent model's top-1
    predicted reply, `replies_left` times; the leaf is evaluated with `eval_nodes`. The line stops
    early at a terminal position or once our search already sees a decisive eval (|cp| >=
    decisive_cp): there is nothing left to steer. Returns (leaf eval from pov, uci moves played,
    evals at each of our nodes, the last one being the leaf). `board` is copied, not mutated.
    """
    b = board.copy()
    moves: list[str] = []
    evals: list[int] = []
    for _ in range(max(0, int(replies_left))):
        term = terminal_eval(b, pov)
        if term is not None:
            return term, moves, evals
        t = time.perf_counter()
        lines = evaluator.analyse(b, nodes=int(line_nodes), pov=pov)
        _add_ms(timings, "line", t)
        if not lines:
            raise RuntimeError(f"evaluator returned no lines for {b.fen()}")
        ours, cp = lines[0].move, int(lines[0].cp)
        evals.append(cp)
        if abs(cp) >= decisive_cp or not b.is_legal(ours):
            return cp, moves, evals
        b.push(ours)
        moves.append(ours.uci())
        term = terminal_eval(b, pov)
        if term is not None:
            return term, moves, evals
        t = time.perf_counter()
        dist = _prune(opponent.predict_reply(b, top_n=1), 0.0)
        _add_ms(timings, "proxy", t)
        if not dist or not b.is_legal(dist[0][0]):
            raise RuntimeError(f"opponent model gave no legal reply in {b.fen()}")
        b.push(dist[0][0])
        moves.append(dist[0][0].uci())
    term = terminal_eval(b, pov)
    if term is not None:
        return term, moves, evals
    t = time.perf_counter()
    lines = evaluator.analyse(b, nodes=int(eval_nodes), pov=pov)
    _add_ms(timings, "eval", t)
    if not lines:
        raise RuntimeError(f"evaluator returned no lines for {b.fen()}")
    cp = int(lines[0].cp)
    evals.append(cp)
    return cp, moves, evals


def exploit_eval(
    after: chess.Board,
    pov: chess.Color,
    opponent: OpponentModel,
    evaluator: Engine,
    *,
    eval_nodes: int,
    top_n: int = 2,
    min_weight: float = 0.0,
    line_depth: int = 1,
    line_nodes: int | None = None,
    decisive_cp: int = 600,
    timings: dict[str, float] | None = None,
) -> Exploit:
    """Expected eval (pov) of `after` (opponent to move) against the opponent model.

    `line_depth` = number of opponent replies in each line. 1 (default) evaluates right after the
    predicted reply; d > 1 continues the line with our best move and the opponent's predicted
    top-1 reply (victim-play rollout, see `line_value`) before the leaf eval, so multi-move traps
    the opponent walks into become visible. `after` is pushed/popped in place and restored.
    """
    terminal = terminal_eval(after, pov)
    if terminal is not None:
        return Exploit(terminal, [], None)
    t = time.perf_counter()
    dist = opponent.predict_reply(after, top_n=top_n)
    _add_ms(timings, "proxy", t)
    raw_shallow = getattr(opponent, "last_eval_cp", None)
    shallow = -int(raw_shallow) if raw_shallow is not None else None
    dist = _prune(dist, min_weight)
    if not dist:
        raise RuntimeError(f"opponent model gave no reply in {after.fen()}")
    replies: list[tuple[chess.Move, float, int]] = []
    all_lines: list[list[str]] = []
    all_evals: list[list[int]] = []
    depth = max(1, int(line_depth))
    lnodes = int(line_nodes) if line_nodes else max(1, int(eval_nodes) // 2)
    for reply, weight in dist:
        if not after.is_legal(reply):
            raise ValueError(f"opponent model proposed illegal reply {reply} in {after.fen()}")
        after.push(reply)
        line, evals = [reply.uci()], []
        try:
            ev = terminal_eval(after, pov)
            if ev is None and depth == 1:
                t = time.perf_counter()
                lines = evaluator.analyse(after, nodes=int(eval_nodes), pov=pov)
                _add_ms(timings, "eval", t)
                if not lines:
                    raise RuntimeError(f"evaluator returned no lines for {after.fen()}")
                ev = int(lines[0].cp)
                evals = [ev]
            elif ev is None:
                ev, more, evals = line_value(
                    after,
                    pov,
                    opponent,
                    evaluator,
                    replies_left=depth - 1,
                    line_nodes=lnodes,
                    eval_nodes=int(eval_nodes),
                    decisive_cp=decisive_cp,
                    timings=timings,
                )
                line += more
        finally:
            after.pop()
        replies.append((reply, weight, ev))
        all_lines.append(line)
        all_evals.append(evals)
    expected = round(sum(w * e for _, w, e in replies))
    return Exploit(expected, replies, shallow, all_lines, all_evals)


def weakness_match(
    board_after: chess.Board,
    profile: Profile,
    pov: chess.Color,
    *,
    eval_deep: int | None = None,
    eval_shallow: int | None = None,
    extract: ExtractFn | None = None,
    radius_factor: float = 1.5,
    max_weakness: float = 2.0,
) -> float:
    """`uplift - 1` of the nearest weak cluster if within radius, else 0. Range [-1, max_weakness].

    `pov` is LostFish's colour and `eval_deep` / `eval_shallow` are LostFish-POV cp, like every
    eval in this module. Profiles are mined with features from the bot's side (the side to move
    in `board_after`, see lostfish.features), so they are converted at this boundary:
    `extract(board_after, not pov, eval_deep=-eval_deep, eval_shallow=-eval_shallow)`.
    Standardisation is z = x / scale per cluster (the centroid is stored in those units); the
    match radius is radius_factor · sqrt(n_features) in z units. Clusters whose dimension does
    not match the feature vector are ignored.
    """
    clusters = list(getattr(profile, "weak_clusters", None) or [])
    if not clusters:
        return 0.0
    if extract is None:
        from lostfish.features import extract as features_extract  # lazy import

        extract = features_extract
    x = np.nan_to_num(
        np.asarray(
            extract(
                board_after, not pov, eval_deep=_neg(eval_deep), eval_shallow=_neg(eval_shallow)
            ),
            dtype=np.float64,
        ).ravel()
    )
    best_d, best_uplift = math.inf, None
    for cluster in clusters:
        centroid = np.asarray(cluster.centroid, dtype=np.float64).ravel()
        scale = np.abs(np.asarray(cluster.scale, dtype=np.float64).ravel())
        if centroid.shape != x.shape or scale.shape != x.shape:
            continue
        scale = np.where(np.isfinite(scale) & (scale > 1e-9), scale, 1.0)
        d = float(np.linalg.norm(x / scale - centroid))
        if math.isfinite(d) and d < best_d:
            best_d, best_uplift = d, float(cluster.uplift)
    if best_uplift is None or best_d > radius_factor * math.sqrt(x.size):
        return 0.0
    w = best_uplift - 1.0
    return float(min(max(w, -1.0), max_weakness)) if math.isfinite(w) else 0.0


def _neg(cp: int | None) -> int | None:
    return None if cp is None else -int(cp)


def _ordered(certified: Certified) -> list[Candidate]:
    """Best first, then the other candidates in certified rank order, no duplicate moves."""
    out = [certified.best]
    seen = {certified.best.move}
    for cand in sorted(certified.candidates, key=lambda c: c.rank):
        if cand.move not in seen:
            seen.add(cand.move)
            out.append(cand)
    return out


def pick_detailed(
    board: chess.Board,
    certified: Certified,
    profile: Profile,
    opponent: OpponentModel,
    evaluator: Engine,
    budget: Budget,
    cfg: Config,
    *,
    deadline: float | None = None,
    extract: ExtractFn | None = None,
    stop: threading.Event | None = None,
) -> PickResult:
    """Score every certified candidate and choose one. Safety invariants (tested):

    1. The returned move is always in certified.candidates.
    2. Any exception → certified.best.move (reason "error").
    3. If the argmax's expected_eval < best.expected_eval - tolerance_cp → best ("fallback_best").
    4. Deadline (time.monotonic() seconds): best is always evaluated first; a further candidate is
       started only if now + (duration of the previous candidate) <= deadline, else it is
       skipped with score -inf. A set `stop` event (UCI `stop`) skips them the same way.
    """
    best = certified.best
    timings: dict[str, float] = {"proxy": 0.0, "eval": 0.0, "features": 0.0}
    scored: list[Scored] = []
    deadline_hit = False
    try:
        cands = _ordered(certified)
        if len(cands) == 1:
            only = Scored(best, best.cp, 0.0, float(best.cp), [], evaluated=False)
            return PickResult(best.move, [only], "single_candidate", timings_ms=timings)
        pov = board.turn
        lam = float(knob(cfg, "steer", "lambda_weakness", 0.15))
        top_n = int(knob(cfg, "steer", "replies", 2))
        min_weight = float(knob(cfg, "steer", "min_reply_weight", 0.02))
        radius = float(knob(cfg, "steer", "weakness_radius", 1.5))
        max_weak = float(knob(cfg, "steer", "max_weakness", 2.0))
        line_depth = int(knob(cfg, "steer", "line_depth", 1))
        line_nodes = knob(cfg, "steer", "line_nodes", None)
        decisive = int(knob(cfg, "steer", "decisive_cp", 600))
        min_gain = float(knob(cfg, "steer", "min_gain_cp", 0.0))
        last_cost = 0.0
        for i, cand in enumerate(cands):
            started = time.monotonic()
            out_of_time = deadline is not None and started + last_cost > deadline
            if i > 0 and (out_of_time or (stop is not None and stop.is_set())):
                deadline_hit = True
                scored.append(Scored(cand, cand.cp, 0.0, -math.inf, [], evaluated=False))
                continue
            if not board.is_legal(cand.move):
                raise ValueError(f"certified move {cand.move} is illegal in {board.fen()}")
            after = board.copy()
            after.push(cand.move)
            ex = exploit_eval(
                after,
                pov,
                opponent,
                evaluator,
                eval_nodes=int(budget.eval_nodes),
                top_n=top_n,
                min_weight=min_weight,
                line_depth=line_depth,
                line_nodes=int(line_nodes) if line_nodes else None,
                decisive_cp=decisive,
                timings=timings,
            )
            t = time.perf_counter()
            weak = weakness_match(
                after,
                profile,
                pov,
                eval_deep=cand.cp,
                eval_shallow=ex.shallow_cp,
                extract=extract,
                radius_factor=radius,
                max_weakness=max_weak,
            )
            _add_ms(timings, "features", t)
            score = ex.expected_eval + lam * 100.0 * weak
            scored.append(
                Scored(
                    cand, ex.expected_eval, weak, score, ex.replies, True, ex.lines, ex.line_evals
                )
            )
            last_cost = time.monotonic() - started
        move, reason = _choose(scored, certified, min_gain_cp=min_gain)
        return PickResult(move, scored, reason, deadline_hit=deadline_hit, timings_ms=timings)
    except Exception as exc:  # noqa: BLE001 - invariant 2: a steering bug must not lose the game
        return PickResult(
            best.move,
            scored,
            "error",
            error=f"{type(exc).__name__}: {exc}",
            deadline_hit=deadline_hit,
            timings_ms=timings,
        )


def _choose(
    scored: list[Scored], certified: Certified, *, min_gain_cp: float = 0.0
) -> tuple[chess.Move, str]:
    allowed = {c.move for c in certified.candidates} | {certified.best.move}
    best_s = scored[0]  # _ordered puts best first and it is always evaluated
    pool = [s for s in scored if s.evaluated and s.candidate.move in allowed]
    top = max(pool, key=lambda s: (s.score, -s.candidate.rank))
    if top is not best_s and top.expected_eval < best_s.expected_eval - certified.tolerance_cp:
        return certified.best.move, "fallback_best"
    if top is not best_s and top.score < best_s.score + min_gain_cp:  # not worth deviating
        return certified.best.move, "fallback_best"
    return top.candidate.move, "steer"


def pick(
    board: chess.Board,
    certified: Certified,
    profile: Profile,
    opponent: OpponentModel,
    evaluator: Engine,
    budget: Budget,
    cfg: Config,
    *,
    deadline: float | None = None,
    extract: ExtractFn | None = None,
    stop: threading.Event | None = None,
) -> tuple[chess.Move, list[Scored]]:
    """Contract entry point (docs/INTERFACES.md). Never returns a move outside the certified set."""
    result = pick_detailed(
        board,
        certified,
        profile,
        opponent,
        evaluator,
        budget,
        cfg,
        deadline=deadline,
        extract=extract,
        stop=stop,
    )
    return result.move, result.scored
