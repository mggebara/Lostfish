"""Time management: clock -> node budgets (pure, no engines)."""

from __future__ import annotations

import chess
import pytest

from lostfish.config import load_config
from lostfish.timeman import Budget, GoParams, classify_tc, ms_to_nodes, parse_go, plan

CFG = load_config()
TM = CFG.timeman


@pytest.mark.parametrize(
    ("base_s", "inc_s", "expected"),
    [
        (15, 0, "bullet"),  # ultrabullet folds into bullet
        (60, 0, "bullet"),
        (120, 1, "bullet"),  # 120 + 40 = 160 s
        (60, 2, "bullet"),  # 60 + 80 = 140 s
        (180, 0, "blitz"),  # 3+0: exactly 180 s is blitz
        (120, 2, "blitz"),  # 2+2 -> 200 s
        (300, 0, "blitz"),
        (300, 3, "blitz"),  # 420 s
        (480, 0, "rapid"),
        (600, 0, "rapid"),
        (900, 10, "rapid"),
    ],
)
def test_classify_tc(base_s: int, inc_s: int, expected: str) -> None:
    assert classify_tc(base_s * 1000, inc_s * 1000) == expected


def test_parse_go_variants() -> None:
    g = parse_go("wtime 1000 btime 2000 winc 10 binc 20 movestogo 5")
    assert (g.wtime, g.btime, g.winc, g.binc, g.movestogo) == (1000, 2000, 10, 20, 5)
    assert parse_go("nodes 20000").nodes == 20000
    assert parse_go("depth 12").depth == 12
    assert parse_go("movetime 500").movetime == 500
    assert parse_go("infinite").infinite
    p = parse_go("ponder wtime 5 btime 5 searchmoves e2e4 d2d4 nodes 7")
    assert p.ponder and p.searchmoves == ["e2e4", "d2d4"] and p.nodes == 7
    assert parse_go("") == GoParams()
    assert parse_go("nodes banana wtime x") == GoParams()
    assert parse_go(["wtime", "-50"]).wtime == -50


def test_go_nodes_is_exact() -> None:
    for n in (1, 777, 50_000, 600_000, 5_000_000):
        b = plan(GoParams(nodes=n), chess.WHITE, CFG)
        assert b.certify_nodes == n
    # nodes wins over a clock too (fastchess can send both)
    b = plan(GoParams(nodes=600_000, wtime=1000, btime=1000), chess.WHITE, CFG)
    assert b.certify_nodes == 600_000
    assert b.tc_class == "bullet"


def test_go_nodes_class_and_generous_wall_time() -> None:
    assert plan(GoParams(nodes=50_000), chess.WHITE, CFG).tc_class == "bullet"
    blitz = plan(GoParams(nodes=600_000), chess.WHITE, CFG)
    assert blitz.tc_class == "blitz"
    assert blitz.k == CFG.budgets["blitz"].k
    assert blitz.eval_nodes == CFG.budgets["blitz"].eval_nodes
    assert plan(GoParams(nodes=3_000_000), chess.WHITE, CFG).tc_class == "rapid"
    # without a clock the wall-time budget must not bind a node-limited move
    nominal_ms = 1000 * (blitz.certify_nodes + blitz.k * blitz.eval_nodes) / TM.nps_estimate
    assert blitz.soft_ms >= 2 * nominal_ms
    assert blitz.hard_ms >= blitz.soft_ms


def test_clock_formula_v0() -> None:
    b = plan(GoParams(wtime=120_000, btime=1, winc=2000, binc=0), chess.WHITE, CFG)
    expected = 120_000 / TM.moves_to_go_assumed + 2000 * TM.increment_fraction
    assert b.soft_ms == int(expected)
    assert b.hard_ms == 2 * b.soft_ms
    assert b.tc_class == "blitz"  # 120 + 40*2 = 200 s
    assert b.certify_nodes == min(CFG.budgets["blitz"].certify_nodes, ms_to_nodes(b.soft_ms, CFG))


def test_black_uses_its_own_clock() -> None:
    go = GoParams(wtime=600_000, btime=30_000, winc=0, binc=0)
    w = plan(go, chess.WHITE, CFG)
    b = plan(go, chess.BLACK, CFG)
    assert b.soft_ms < w.soft_ms
    assert b.soft_ms == int(30_000 / TM.moves_to_go_assumed)


def test_clock_caps_and_floors() -> None:
    # hard never exceeds remaining - reserve
    for remaining in (2_000, 5_000, 20_000, 180_000):
        b = plan(GoParams(wtime=remaining, btime=remaining, winc=5000), chess.WHITE, CFG)
        assert b.hard_ms <= max(TM.min_move_ms, remaining - TM.reserve_ms)
        assert b.soft_ms <= b.hard_ms
    # nearly flagging: bullet floor of min_move_ms worth of nodes
    b = plan(GoParams(wtime=200, btime=200), chess.WHITE, CFG)
    assert b.soft_ms == TM.min_move_ms
    assert b.certify_nodes == ms_to_nodes(TM.min_move_ms, CFG)
    # certify_nodes never above the yaml value for the class
    b = plan(GoParams(wtime=3_600_000, btime=3_600_000), chess.WHITE, CFG)
    assert b.tc_class == "rapid"
    assert b.certify_nodes == CFG.budgets["rapid"].certify_nodes


def test_short_clock_scales_eval_nodes() -> None:
    b = plan(GoParams(wtime=1000, btime=1000), chess.WHITE, CFG)
    y = CFG.budgets["bullet"]
    assert b.certify_nodes < y.certify_nodes
    assert b.eval_nodes <= y.eval_nodes
    assert b.eval_nodes == max(1000, round(y.eval_nodes * b.certify_nodes / y.certify_nodes))


def test_overhead_and_movestogo() -> None:
    go = GoParams(wtime=10_000, btime=10_000)
    assert plan(go, chess.WHITE, CFG, overhead_ms=1000).soft_ms < plan(go, chess.WHITE, CFG).soft_ms
    one = plan(GoParams(wtime=10_000, btime=10_000, movestogo=1), chess.WHITE, CFG)
    assert one.soft_ms == 10_000 // 2  # never plan more than half the clock on one move
    assert one.hard_ms <= 10_000 - TM.reserve_ms


def test_clock_fraction() -> None:
    go = GoParams(wtime=45_000, btime=60_000)
    assert plan(go, chess.WHITE, CFG).clock_fraction == 1.0  # unknown initial
    assert plan(go, chess.WHITE, CFG, initial_ms=180_000).clock_fraction == pytest.approx(0.25)
    assert plan(go, chess.WHITE, CFG, initial_ms=180_000).tc_class == "blitz"  # from initial
    assert plan(go, chess.WHITE, CFG, initial_ms=10_000).clock_fraction == 1.0  # capped


def test_movetime() -> None:
    b = plan(GoParams(movetime=1000), chess.WHITE, CFG)
    assert b.soft_ms == b.hard_ms == 1000 - TM.reserve_ms
    assert b.certify_nodes == min(CFG.budgets[b.tc_class].certify_nodes, ms_to_nodes(700, CFG))
    tiny = plan(GoParams(movetime=100), chess.WHITE, CFG)
    assert 1 <= tiny.soft_ms <= 100
    assert classify_tc(0, 15_000) == "rapid"  # movetime 15 s ~ 40 moves x 15 s


def test_depth_infinite_and_bare_go() -> None:
    d = plan(GoParams(depth=10), chess.WHITE, CFG)
    assert d.depth == 10 and d.certify_nodes > 0
    assert plan(GoParams(depth=20), chess.WHITE, CFG).certify_nodes > d.certify_nodes
    inf = plan(GoParams(infinite=True), chess.WHITE, CFG)
    assert inf.tc_class == "rapid" and inf.certify_nodes == CFG.budgets["rapid"].certify_nodes
    bare = plan(GoParams(), chess.WHITE, CFG)
    assert bare.tc_class == "blitz" and bare.certify_nodes == CFG.budgets["blitz"].certify_nodes
    assert bare.depth is None and bare.clock_fraction == 1.0


def test_budget_fields_match_contract() -> None:
    b = plan(GoParams(wtime=60_000, btime=60_000), chess.WHITE, CFG)
    assert isinstance(b, Budget)
    assert b.tc_class in ("bullet", "blitz", "rapid")
    for name in ("certify_nodes", "eval_nodes", "k", "proxy_depth_cap", "soft_ms", "hard_ms"):
        assert isinstance(getattr(b, name), int) and getattr(b, name) > 0
    assert 0.0 <= b.clock_fraction <= 1.0
