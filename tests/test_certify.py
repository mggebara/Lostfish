"""certify(): inclusion/exclusion and mates; tolerance_policy(): monotonicity and clamps."""

from __future__ import annotations

import itertools
import random

import chess
import pytest

from lostfish.certify import MATE_CP, certify, certify_position, knob, tolerance_policy, volatility
from tests.steer_fakes import FakeBudget, FakeEngine, line, make_cfg, ranked_script

QUIET = {d: 20 for d in range(1, 20)}


@pytest.fixture
def cfg():
    return make_cfg()


def nonincreasing(xs):
    return all(a >= b for a, b in itertools.pairwise(xs))


def moves(certified):
    return [c.move.uci() for c in certified.candidates]


# ------------------------------------------------------------------ certify


def test_candidates_within_tolerance_in_rank_order():
    lines = [line("e2e4", 40, 1), line("d2d4", 25, 2), line("g1f3", 10, 3), line("c2c4", 9, 4)]
    c = certify(lines, 30)
    assert moves(c) == ["e2e4", "d2d4", "g1f3"]  # 40-30 = 10 is the boundary, inclusive
    assert c.best.move.uci() == "e2e4" and c.tolerance_cp == 30
    assert [x.rank for x in c.candidates] == [1, 2, 3]


def test_unsorted_input_is_ranked_and_best_always_included():
    lines = [line("g1f3", -500, 3), line("e2e4", 40, 1), line("d2d4", -100, 2)]
    c = certify(lines, 30)
    assert moves(c) == ["e2e4"]
    assert certify(lines, 0).candidates == [c.best]


def test_zero_or_negative_tolerance_keeps_exact_ties_only():
    lines = [line("e2e4", 15, 1), line("d2d4", 15, 2), line("g1f3", 14, 3)]
    assert moves(certify(lines, 0)) == ["e2e4", "d2d4"]
    c = certify(lines, -20)
    assert c.tolerance_cp == 0 and moves(c) == ["e2e4", "d2d4"]


def test_eval_by_depth_comes_from_rank_one():
    lines = [line("d2d4", 5, 2, ebd={9: 1}), line("e2e4", 10, 1, ebd={10: 3, 11: 10})]
    assert certify(lines, 30).eval_by_depth == {10: 3, 11: 10}


def test_winning_mate_keeps_only_mates_no_slower():
    lines = [
        line("h5f7", MATE_CP - 2, 1, mate=2),
        line("h5h7", MATE_CP - 2, 2, mate=2),
        line("d1d8", MATE_CP - 4, 3, mate=4),  # slower mate: excluded
        line("e2e4", 900, 4),  # crushing but not mate: excluded
    ]
    assert moves(certify(lines, 30)) == ["h5f7", "h5h7"]


def test_mate_detected_from_cp_when_mate_field_missing():
    lines = [line("h5f7", MATE_CP - 1, 1), line("e2e4", MATE_CP - 30, 2)]
    assert moves(certify(lines, 50)) == ["h5f7"]


def test_getting_mated_passes_through_only_best():
    lines = [
        line("e1e2", -(MATE_CP - 6), 1, mate=-6),
        line("e1d2", -(MATE_CP - 6), 2, mate=-6),
        line("e1f1", -(MATE_CP - 3), 3, mate=-3),
    ]
    assert moves(certify(lines, 30)) == ["e1e2"]


def test_lines_where_we_get_mated_never_certified_in_normal_position():
    lines = [line("e2e4", -20, 1), line("f2f3", -(MATE_CP - 2), 2, mate=-2)]
    assert moves(certify(lines, 10_000)) == ["e2e4"]


def test_empty_lines_raise():
    with pytest.raises(ValueError):
        certify([], 30)


def test_duplicate_moves_dropped():
    lines = [line("e2e4", 10, 1), line("e2e4", 9, 2), line("d2d4", 8, 3)]
    assert moves(certify(lines, 30)) == ["e2e4", "d2d4"]


def test_mate_cp_matches_engines_module():
    engines = pytest.importorskip("lostfish.engines", reason="lostfish.engines not available")
    assert engines.MATE_CP == MATE_CP


# ------------------------------------------------------------------ tolerance_policy


def test_base_tolerance_in_quiet_even_position(cfg):
    assert tolerance_policy(0, QUIET, 1.0, cfg) == 30
    assert tolerance_policy(120, {}, 1.0, cfg) == 30


def test_more_behind_is_tighter_and_floors_at_min(cfg):
    tols = [tolerance_policy(cp, QUIET, 1.0, cfg) for cp in range(0, -400, -10)]
    assert nonincreasing(tols)
    assert tolerance_policy(-75, QUIET, 1.0, cfg) == 15  # linear: halfway to -150 → half
    assert tolerance_policy(-150, QUIET, 1.0, cfg) == 0
    assert tolerance_policy(-1000, QUIET, 1.0, cfg) == 0


def test_tolerance_min_is_respected(cfg):
    cfg.certify.tolerance_min_cp = 8
    assert tolerance_policy(-500, {1: 0, 2: 900, 3: -900, 4: 0}, 0.0, cfg) == 8


def test_low_clock_is_tighter(cfg):
    assert tolerance_policy(0, QUIET, 0.15, cfg) == 30
    tols = [tolerance_policy(0, QUIET, cf / 100, cfg) for cf in range(15, -1, -1)]
    assert nonincreasing(tols)
    assert tolerance_policy(0, QUIET, 0.0, cfg) == 15


def test_ahead_is_wider_up_to_fifty_percent(cfg):
    assert tolerance_policy(150, QUIET, 1.0, cfg) == 30
    assert tolerance_policy(225, QUIET, 1.0, cfg) > 30
    assert tolerance_policy(300, QUIET, 1.0, cfg) == 45
    assert tolerance_policy(5000, QUIET, 1.0, cfg) == 45


def test_volatility_tightens_and_only_deepest_depths_count(cfg):
    sharp = {13: 0, 14: 100, 15: 20, 16: 50}  # max-min = 100 → half
    assert volatility(sharp) == 100
    assert tolerance_policy(0, sharp, 1.0, cfg) == 15
    noisy_early = {1: -400, 2: 300, 3: 0, 13: 10, 14: 12, 15: 11, 16: 10}
    assert volatility(noisy_early) == 2  # depths 1-3 are ignored
    assert volatility({5: 31_990, 6: 0}) == 1000  # mate scores clamped
    vols = [tolerance_policy(0, {1: 0, 2: v}, 1.0, cfg) for v in range(0, 600, 25)]
    assert nonincreasing(vols)


def test_clamped_to_min_and_twice_base_under_random_inputs(cfg):
    rng = random.Random(7)
    for _ in range(2000):
        cfg.certify.tolerance_cp = rng.randint(0, 80)
        cfg.certify.tolerance_min_cp = rng.randint(0, 20)
        cfg.certify.expand_when_ahead = rng.choice([0.5, 1.5, 3.0])  # can exceed 2x: must clamp
        ebd = {d: rng.randint(-2000, 2000) for d in range(1, rng.randint(1, 20))}
        tol = tolerance_policy(rng.randint(-3000, 3000), ebd, rng.random(), cfg)
        t0, t_min = (
            cfg.certify.tolerance_cp,
            min(cfg.certify.tolerance_min_cp, cfg.certify.tolerance_cp),
        )
        assert t_min <= tol <= 2 * t0


def test_policy_reads_knobs_from_real_config_extra():
    config = pytest.importorskip("lostfish.config", reason="lostfish.config not available")
    real = config.load_config()
    assert knob(real, "certify", "tolerance_cp", None) == real.certify.tolerance_cp
    real.certify.extra["volatility_half_cp"] = 50
    assert knob(real, "certify", "volatility_half_cp", 100) == 50
    assert tolerance_policy(0, {1: 0, 2: 50}, 1.0, real) == 15
    assert knob(real, "steer", "no_such_knob", 123) == 123


# ------------------------------------------------------------------ certify_position


def test_certify_position_glue(cfg):
    engine = FakeEngine(ranked_script("cp"))
    board = chess.Board()
    budget = FakeBudget(certify_nodes=123_456, k=4, clock_fraction=0.9)
    c = certify_position(engine, board, chess.WHITE, budget, cfg)
    call = engine.calls[-1]
    assert call["nodes"] == 123_456 and call["multipv"] == 4 and call["trajectory"]
    assert call["pov"] == chess.WHITE and call["depth"] is None
    assert c.best.rank == 1 and all(m in board.legal_moves for m in [x.move for x in c.candidates])
    assert c.tolerance_cp == tolerance_policy(c.best.cp, c.eval_by_depth, 0.9, cfg)


def test_certify_position_uses_depth_when_budget_has_one(cfg):
    engine = FakeEngine(ranked_script())
    certify_position(engine, chess.Board(), chess.WHITE, FakeBudget(depth=9), cfg)
    assert engine.calls[-1]["depth"] == 9 and engine.calls[-1]["nodes"] is None


def test_certify_position_no_lines_raises(cfg):
    engine = FakeEngine(lambda b, p, k: [])
    with pytest.raises(ValueError):
        certify_position(engine, chess.Board(), chess.WHITE, FakeBudget(), cfg)
