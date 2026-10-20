"""Certification: turn one Stockfish MultiPV search into the set of moves LostFish may play.

The certified set bounds the damage steering can do: `steer.pick` reorders these candidates and
never adds one (CLAUDE.md non-negotiable 2). All centipawns are from LostFish's point of view;
`engines.py` converts at the boundary via `pov=`.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import chess

if TYPE_CHECKING:
    from lostfish.config import Config
    from lostfish.engines import Engine, PVLine
    from lostfish.timeman import Budget

MATE_CP = 32000  # mirrors lostfish.engines.MATE_CP (docs/INTERFACES.md)
MATE_THRESHOLD = MATE_CP - 1000  # |cp| at or above this is a mate score
_VOL_CLAMP_CP = 1000  # depth evals are clamped to ±this before measuring volatility
_MISSING = object()


@dataclass
class Candidate:
    move: chess.Move
    cp: int
    rank: int
    pv: list[chess.Move] = field(default_factory=list)


@dataclass
class Certified:
    best: Candidate
    candidates: list[Candidate]  # rank order, best first
    tolerance_cp: int
    eval_by_depth: dict[int, int] = field(default_factory=dict)


# --------------------------------------------------------------------------------------------
# Config access. Config is agent A's dataclass tree; knobs added by the steering work may live in
# a section's `.extra` (unknown keys are kept there), so read them defensively with a default.
# --------------------------------------------------------------------------------------------


def _get(obj: Any, key: str) -> Any:
    if obj is None or obj is _MISSING:
        return _MISSING
    if isinstance(obj, Mapping):
        return obj.get(key, _MISSING)
    value = getattr(obj, key, _MISSING)
    if value is _MISSING:
        extra = getattr(obj, "extra", None)
        if isinstance(extra, Mapping):
            value = extra.get(key, _MISSING)
    return value


def knob(cfg: Any, section: str, key: str, default: Any) -> Any:
    """Return ``cfg.<section>.<key>``; tolerates dataclasses, dicts, `.extra` maps and gaps."""
    value = _get(_get(cfg, section), key)
    if value is _MISSING:
        extra = getattr(cfg, "extra", None)
        if isinstance(extra, Mapping) and isinstance(extra.get(section), Mapping):
            value = extra[section].get(key, _MISSING)
    return default if value is _MISSING or value is None else value


# --------------------------------------------------------------------------------------------
# Mate helpers
# --------------------------------------------------------------------------------------------


def mate_sign(line: Any) -> int:
    """+1 if the line mates for us, -1 if we get mated, 0 otherwise."""
    mate = getattr(line, "mate", None)
    if mate is not None and mate != 0:
        return 1 if mate > 0 else -1
    if line.cp >= MATE_THRESHOLD:
        return 1
    if line.cp <= -MATE_THRESHOLD:
        return -1
    return 0


# --------------------------------------------------------------------------------------------
# Tolerance policy
# --------------------------------------------------------------------------------------------


def volatility(eval_by_depth: Mapping[int, int], n_depths: int = 4) -> int:
    """max - min of the eval over the deepest `n_depths` depths (each clamped to ±1000 cp)."""
    if not eval_by_depth or n_depths < 2:
        return 0
    deepest = sorted(eval_by_depth)[-n_depths:]
    vals = [max(-_VOL_CLAMP_CP, min(_VOL_CLAMP_CP, int(eval_by_depth[d]))) for d in deepest]
    return max(vals) - min(vals) if len(vals) >= 2 else 0


def tolerance_policy(
    best_cp: int, eval_by_depth: dict[int, int], clock_fraction: float, cfg: Config
) -> int:
    """Tolerance (cp) for this move. With T0 = certify.tolerance_cp, Tmin = tolerance_min_cp:

        T = Tmin + (T0 - Tmin) * f_behind * f_vol * f_clock * f_ahead,
        clamped to [Tmin, 2*T0] and rounded half-up.

    - f_behind = 1 - min(1, -best_cp / B) when best_cp < 0, else 1; B = tighten_when_behind_cp
      (150). Linear from T0 at 0 cp down to Tmin at -150 cp and below.
    - f_vol = 1 / (1 + V / volatility_half_cp), V = max - min of the rank-1 eval over the deepest
      `volatility_depths` (4) depths. With volatility_half_cp = 100, V = 100 cp halves T.
    - f_clock = 0.5 + 0.5 * clock_fraction / low_clock_fraction when clock_fraction is below
      low_clock_fraction (0.15), else 1. So T halves as the clock runs out.
    - f_ahead = 1 + expand_when_ahead * min(1, (best_cp - A) / A) when best_cp > A,
      A = expand_when_ahead_cp (150). Up to +50 % (expand_when_ahead 0.5) at best_cp >= 2A.

    T is non-decreasing in best_cp and clock_fraction and non-increasing in V.
    """
    t0 = float(knob(cfg, "certify", "tolerance_cp", 30))
    t_min = float(knob(cfg, "certify", "tolerance_min_cp", 0))
    behind = float(knob(cfg, "certify", "tighten_when_behind_cp", 150))
    n_depths = int(knob(cfg, "certify", "volatility_depths", 4))
    vol_half = float(knob(cfg, "certify", "volatility_half_cp", 100))
    low_clock = float(knob(cfg, "certify", "low_clock_fraction", 0.15))
    ahead_cp = float(knob(cfg, "certify", "expand_when_ahead_cp", 150))
    ahead_gain = float(knob(cfg, "certify", "expand_when_ahead", 0.5))
    t_min = min(t_min, t0)

    f_behind = 1.0
    if best_cp < 0:
        f_behind = 0.0 if behind <= 0 else max(0.0, 1.0 - (-best_cp) / behind)

    vol = volatility(eval_by_depth, n_depths)
    f_vol = 1.0 / (1.0 + vol / vol_half) if vol_half > 0 else 1.0

    f_clock = 1.0
    cf = clock_fraction if math.isfinite(clock_fraction) else 1.0
    if low_clock > 0 and cf < low_clock:
        f_clock = 0.5 + 0.5 * max(0.0, cf) / low_clock

    f_ahead = 1.0
    if ahead_cp > 0 and best_cp > ahead_cp:
        f_ahead = 1.0 + ahead_gain * min(1.0, (best_cp - ahead_cp) / ahead_cp)

    tol = t_min + (t0 - t_min) * f_behind * f_vol * f_clock * f_ahead
    tol = min(max(tol, t_min), 2.0 * t0)
    return math.floor(tol + 0.5)


# --------------------------------------------------------------------------------------------
# Certification
# --------------------------------------------------------------------------------------------


def certify(lines: list[PVLine], tolerance_cp: int) -> Certified:
    """Pure. Best = rank-1 line; candidates = lines with cp >= best.cp - tolerance_cp, rank order.

    Mate handling: if best mates for us, only lines that also mate no slower (cp >= best.cp) are
    candidates; if best is getting mated, only best passes. Duplicate moves are dropped.
    """
    if not lines:
        raise ValueError("certify() needs at least one PV line (position has no legal moves?)")
    ordered = sorted(lines, key=lambda ln: ln.rank)
    best_line = ordered[0]
    tol = max(0, int(tolerance_cp))
    sign = mate_sign(best_line)
    if sign > 0:
        keep = [ln for ln in ordered if mate_sign(ln) > 0 and ln.cp >= best_line.cp]
    elif sign < 0:
        keep = [best_line]
    else:
        keep = [ln for ln in ordered if ln.cp >= best_line.cp - tol]
    seen: set[chess.Move] = set()
    candidates: list[Candidate] = []
    for ln in [best_line, *keep]:
        if ln.move in seen:
            continue
        seen.add(ln.move)
        candidates.append(Candidate(move=ln.move, cp=int(ln.cp), rank=int(ln.rank), pv=list(ln.pv)))
    eval_by_depth = dict(getattr(best_line, "eval_by_depth", None) or {})
    return Certified(
        best=candidates[0], candidates=candidates, tolerance_cp=tol, eval_by_depth=eval_by_depth
    )


def certify_position(
    engine: Engine, board: chess.Board, pov: chess.Color, budget: Budget, cfg: Config
) -> Certified:
    """One MultiPV search → tolerance_policy → certify.

    Node-limited (budget.certify_nodes) unless the budget carries a depth (`go depth D`).
    """
    depth = getattr(budget, "depth", None)
    limit = {"depth": int(depth)} if depth else {"nodes": int(budget.certify_nodes)}
    lines = engine.analyse(board, multipv=max(1, int(budget.k)), pov=pov, trajectory=True, **limit)
    if not lines:
        raise ValueError(f"certifier returned no lines for {board.fen()}")
    best = min(lines, key=lambda ln: ln.rank)
    tol = tolerance_policy(
        int(best.cp),
        dict(getattr(best, "eval_by_depth", None) or {}),
        float(getattr(budget, "clock_fraction", 1.0)),
        cfg,
    )
    return certify(lines, tol)
