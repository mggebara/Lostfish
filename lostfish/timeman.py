"""Clock -> node budgets (v0).

LostFish never runs time-limited searches; the clock is converted to node budgets here.

Policy (all times in ms, `remaining` is our clock minus `overhead_ms`):
    soft = remaining / moves_to_go + inc * increment_fraction
    soft = clamp(soft, min_move_ms, remaining - reserve_ms)   (min_move_ms wins if they cross)
    hard = clamp(2 * soft, soft, remaining - reserve_ms)
    certify_nodes = max(min_move_ms worth of nodes, min(budgets[tc].certify_nodes, soft worth))
with `nps_estimate` (yaml `timeman.nps_estimate`) converting ms to nodes. `eval_nodes` is scaled
down by the same ratio when the clock cuts certify_nodes below the yaml value.

Other `go` forms: `nodes N` -> certify_nodes = N exactly (equal-node gauntlets rely on this);
`depth D` -> Budget.depth = D and certify_nodes estimated for that depth; `movetime T` ->
soft = hard = T - reserve_ms; `infinite`/bare `go` -> the class budget with no clock limit.
Without a clock (nodes/depth/infinite/bare go) soft_ms/hard_ms are deliberately generous
(max(NO_CLOCK_SLACK x the nominal time of certify + k evals, NO_CLOCK_FLOOR_MS)) so they never bind a
node-limited move; in the first line-search gauntlet a 200 ms soft budget cut 26% of 2-ply moves short.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import chess

from lostfish.config import BudgetConfig, Config

BULLET_MAX_S = 180  # lichess: estimated duration = base + 40 * increment
BLITZ_MAX_S = 480
_MAX_NODES = 2_000_000_000
NO_CLOCK_SLACK = 3
NO_CLOCK_FLOOR_MS = 30_000  # clockless moves never see a binding deadline (line search needs this)


@dataclass
class GoParams:
    """A parsed `go` command; None where absent."""

    wtime: int | None = None
    btime: int | None = None
    winc: int | None = None
    binc: int | None = None
    movestogo: int | None = None
    movetime: int | None = None
    nodes: int | None = None
    depth: int | None = None
    infinite: bool = False
    ponder: bool = False
    mate: int | None = None
    searchmoves: list[str] = field(default_factory=list)


@dataclass
class Budget:
    tc_class: str  # "bullet" | "blitz" | "rapid"
    certify_nodes: int
    eval_nodes: int
    k: int
    proxy_depth_cap: int
    soft_ms: int  # target wall time for the whole move
    hard_ms: int  # never exceed
    clock_fraction: float  # remaining/initial estimate, 0..1 (1.0 when unknown)
    depth: int | None = None  # set for `go depth D`: search to this depth instead of nodes


_INT_KEYS = ("wtime", "btime", "winc", "binc", "movestogo", "movetime", "nodes", "depth", "mate")
_KEYWORDS = set(_INT_KEYS) | {"infinite", "ponder", "searchmoves"}


def parse_go(args: str | list[str]) -> GoParams:
    """Parse the arguments of a UCI `go` command (the part after `go`). Never raises."""
    tokens = args.split() if isinstance(args, str) else list(args)
    go = GoParams()
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok in _INT_KEYS and i + 1 < len(tokens):
            try:
                setattr(go, tok, int(float(tokens[i + 1])))
            except ValueError:
                pass
            i += 2
            continue
        if tok == "infinite":
            go.infinite = True
        elif tok == "ponder":
            go.ponder = True
        elif tok == "searchmoves":
            i += 1
            while i < len(tokens) and tokens[i] not in _KEYWORDS:
                go.searchmoves.append(tokens[i])
                i += 1
            continue
        i += 1
    return go


def classify_tc(base_ms: int, inc_ms: int) -> str:
    """Lichess speed classes on base + 40*inc: bullet < 180 s <= blitz < 480 s <= rapid."""
    est_s = (max(0, base_ms) + 40 * max(0, inc_ms)) / 1000.0
    if est_s < BULLET_MAX_S:
        return "bullet"
    if est_s < BLITZ_MAX_S:
        return "blitz"
    return "rapid"


def _budget_cfg(cfg: Config, tc: str) -> BudgetConfig:
    if tc in cfg.budgets:
        return cfg.budgets[tc]
    return cfg.budgets.get("blitz") or next(iter(cfg.budgets.values()))


def _class_for_nodes(cfg: Config, nodes: int) -> str:
    """The class with the largest yaml certify_nodes <= nodes (bullet if none)."""
    best, best_n = "bullet", -1
    for tc in ("bullet", "blitz", "rapid"):
        b = cfg.budgets.get(tc)
        if b is not None and best_n < b.certify_nodes <= nodes:
            best, best_n = tc, b.certify_nodes
    return best


def depth_to_nodes(depth: int) -> int:
    """Rough Stockfish 19 nodes needed for `depth` (measured: d12 ~30k, d16 ~150k, d20 ~800k)."""
    return int(min(_MAX_NODES, max(1000, 250 * 1.5 ** max(1, depth))))


def ms_to_nodes(ms: float, cfg: Config) -> int:
    return int(min(_MAX_NODES, max(1, ms * cfg.timeman.nps_estimate / 1000.0)))


def nodes_to_ms(nodes: int, cfg: Config) -> int:
    return max(1, int(nodes * 1000 / max(1, cfg.timeman.nps_estimate)))


def _make(
    cfg: Config,
    tc: str,
    certify_nodes: int,
    soft: int | None,
    hard: int | None,
    frac: float,
    depth: int | None = None,
) -> Budget:
    """Fill k/eval_nodes/proxy_depth_cap from budgets[tc]; soft=None means "no clock"."""
    b = _budget_cfg(cfg, tc)
    ratio = min(1.0, certify_nodes / max(1, b.certify_nodes))
    eval_nodes = max(1000, round(b.eval_nodes * ratio)) if b.eval_nodes > 0 else 0
    if soft is None:
        nominal = nodes_to_ms(certify_nodes + b.k * eval_nodes, cfg)
        soft = max(NO_CLOCK_SLACK * nominal + cfg.timeman.min_move_ms, NO_CLOCK_FLOOR_MS)
        hard = 2 * soft
    return Budget(
        tc_class=tc,
        certify_nodes=int(certify_nodes),
        eval_nodes=min(eval_nodes, b.eval_nodes) if b.eval_nodes > 0 else 0,
        k=b.k,
        proxy_depth_cap=b.proxy_depth_cap,
        soft_ms=int(soft),
        hard_ms=int(max(soft, hard or soft)),
        clock_fraction=float(min(1.0, max(0.0, frac))),
        depth=depth,
    )


def plan(
    go: GoParams,
    color: chess.Color,
    cfg: Config,
    *,
    ply: int = 0,
    initial_ms: int | None = None,
    overhead_ms: int = 0,
) -> Budget:
    """Turn a `go` command into a Budget for the side `color`.

    `initial_ms` (our clock at the start of the game, if known) only feeds `clock_fraction` and
    the speed class; `overhead_ms` (UCI MoveOverhead) is subtracted from our clock and movetime.
    """
    tm = cfg.timeman
    floor_nodes = ms_to_nodes(tm.min_move_ms, cfg)
    remaining = go.wtime if color == chess.WHITE else go.btime
    inc = (go.winc if color == chess.WHITE else go.binc) or 0

    clock: tuple[str, int, int, float] | None = None  # (tc_class, soft, hard, clock_fraction)
    if remaining is not None:
        base = max(remaining, initial_ms or 0)
        tc = classify_tc(base, inc)
        avail = max(0, remaining - overhead_ms)
        mtg = tm.moves_to_go_assumed
        if go.movestogo is not None and go.movestogo > 0:
            mtg = max(2, min(go.movestogo, tm.moves_to_go_assumed))
        raw = avail / mtg + inc * tm.increment_fraction
        cap = avail - tm.reserve_ms
        soft = max(tm.min_move_ms, min(raw, cap))
        hard = max(soft, min(2 * soft, cap))
        frac = remaining / initial_ms if initial_ms else 1.0
        clock = (tc, int(soft), int(hard), frac)

    if go.nodes is not None and go.nodes > 0:  # exact node budget
        n = int(go.nodes)
        if clock is not None:
            tc, soft, hard, frac = clock
            return _make(cfg, tc, n, soft, hard, frac)
        return _make(cfg, _class_for_nodes(cfg, n), n, None, None, 1.0)

    if go.depth is not None and go.depth > 0:
        n = depth_to_nodes(go.depth)
        if clock is not None:
            tc, soft, hard, frac = clock
            n = min(n, max(floor_nodes, ms_to_nodes(soft, cfg)))
            return _make(cfg, tc, n, soft, hard, frac, depth=go.depth)
        return _make(cfg, _class_for_nodes(cfg, n), n, None, None, 1.0, depth=go.depth)

    if go.movetime is not None and go.movetime > 0:
        mt = go.movetime - overhead_ms
        ms = mt - tm.reserve_ms
        if ms < tm.min_move_ms:
            ms = max(1, min(tm.min_move_ms, mt))
        tc = classify_tc(0, go.movetime)  # 40 moves at this rate
        b = _budget_cfg(cfg, tc)
        n = min(b.certify_nodes, ms_to_nodes(ms, cfg))
        return _make(cfg, tc, n, ms, ms, 1.0)

    if clock is not None and not go.infinite:
        tc, soft, hard, frac = clock
        b = _budget_cfg(cfg, tc)
        n = max(floor_nodes, min(b.certify_nodes, ms_to_nodes(soft, cfg)))
        return _make(cfg, tc, n, soft, hard, frac)

    # `go infinite`, `go ponder` without a clock, or a bare `go`: class budget, no clock limit.
    tc = clock[0] if clock is not None else ("rapid" if go.infinite else "blitz")
    b = _budget_cfg(cfg, tc)
    return _make(cfg, tc, b.certify_nodes, None, None, clock[3] if clock else 1.0)
