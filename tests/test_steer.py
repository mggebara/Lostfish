"""Exploit search arithmetic, weakness matching, and pick()'s safety invariants."""

from __future__ import annotations

import math
import random
import threading
import time

import chess
import numpy as np
import pytest

from lostfish.certify import MATE_CP, Candidate, Certified, certify
from lostfish.steer import exploit_eval, pick, pick_detailed, weakness_match
from tests.steer_fakes import (
    FakeBudget,
    FakeCluster,
    FakeEngine,
    FakeProfile,
    FakePVLine,
    ScriptedOpponent,
    line,
    make_cfg,
    static_script,
)

OPEN = chess.Board()
for _uci in ("e2e4", "e7e5"):
    OPEN.push_uci(_uci)


def fen_after(board: chess.Board, *ucis: str) -> str:
    b = board.copy()
    for u in ucis:
        b.push_uci(u)
    return b.fen()


def table_evaluator(table: dict[str, int], default: int = 0) -> FakeEngine:
    """Evaluator returning table[fen] (LostFish POV) for each position searched."""

    def script(board: chess.Board, pov: chess.Color, k: int) -> list[FakePVLine]:
        return [FakePVLine(next(iter(board.legal_moves)), table.get(board.fen(), default), 1)]

    return FakeEngine(script, name="evaluator")


def raising_extract(*args, **kwargs):
    raise AssertionError("extract must not be called")


@pytest.fixture
def cfg():
    return make_cfg()


@pytest.fixture
def setup():
    """1.e4 e5, White to move. Candidates Nf3 (30), d4 (20), Bc4 (15); tolerance 30."""
    certified = certify([line("g1f3", 30, 1), line("d2d4", 20, 2), line("f1c4", 15, 3)], 30)
    opponent = ScriptedOpponent(
        {
            fen_after(OPEN, "g1f3"): [("b8c6", 0.75), ("d7d6", 0.25)],
            fen_after(OPEN, "d2d4"): [("e5d4", 1.0)],
            fen_after(OPEN, "f1c4"): [("g8f6", 1.0)],
        }
    )
    evals = {
        fen_after(OPEN, "g1f3", "b8c6"): 40,
        fen_after(OPEN, "g1f3", "d7d6"): 0,
        fen_after(OPEN, "d2d4", "e5d4"): 100,
        fen_after(OPEN, "f1c4", "g8f6"): 10,
    }
    return certified, opponent, table_evaluator(evals)


# ------------------------------------------------------------------ exploit search


def test_expected_eval_is_weighted_sum_and_board_restored(setup, cfg):
    _, opponent, evaluator = setup
    after = OPEN.copy()
    after.push_uci("g1f3")
    before = (after.fen(), list(after.move_stack))
    ex = exploit_eval(after, chess.WHITE, opponent, evaluator, eval_nodes=777, top_n=2)
    assert ex.expected_eval == 30  # 0.75 * 40 + 0.25 * 0
    assert [(m.uci(), w, e) for m, w, e in ex.replies] == [("b8c6", 0.75, 40), ("d7d6", 0.25, 0)]
    assert all(c["nodes"] == 777 and c["pov"] == chess.WHITE for c in evaluator.calls)
    assert (after.fen(), list(after.move_stack)) == before


def test_low_weight_replies_pruned_and_renormalised(cfg):
    after = OPEN.copy()
    after.push_uci("g1f3")
    opponent = ScriptedOpponent({after.fen(): [("b8c6", 0.99), ("d7d6", 0.01)]})
    evaluator = table_evaluator({fen_after(after, "b8c6"): 50})
    ex = exploit_eval(after, chess.WHITE, opponent, evaluator, eval_nodes=1, min_weight=0.02)
    assert [(m.uci(), w) for m, w, _ in ex.replies] == [("b8c6", 1.0)]
    assert ex.expected_eval == 50 and len(evaluator.calls) == 1


def test_terminal_positions():
    mate_board = chess.Board("6k1/5ppp/8/8/8/8/8/R5K1 w - - 0 1")
    mate_board.push_uci("a1a8")
    opp = ScriptedOpponent(fail=AssertionError("no reply exists"))
    ev = FakeEngine(fail=AssertionError("no eval needed"))
    assert exploit_eval(mate_board, chess.WHITE, opp, ev, eval_nodes=1).expected_eval == MATE_CP
    stale = chess.Board("7k/8/6K1/8/8/8/8/5Q2 w - - 0 1")
    stale.push_uci("f1f7")
    assert exploit_eval(stale, chess.WHITE, opp, ev, eval_nodes=1).expected_eval == 0
    fools = chess.Board()
    for u in ("f2f3", "e7e5", "g2g4"):
        fools.push_uci(u)
    opp = ScriptedOpponent({fools.fen(): [("d8h4", 1.0)]})
    ex = exploit_eval(fools, chess.WHITE, opp, ev, eval_nodes=1)
    assert ex.expected_eval == -MATE_CP and ex.replies[0][2] == -MATE_CP


# ------------------------------------------------------------------ pick


def test_pick_prefers_highest_expected_eval(setup, cfg):
    certified, opponent, evaluator = setup
    move, scored = pick(OPEN, certified, FakeProfile(), opponent, evaluator, FakeBudget(), cfg)
    assert move.uci() == "d2d4"
    assert [s.expected_eval for s in scored] == [30, 100, 10]
    assert all(s.evaluated and s.weakness == 0.0 for s in scored)


def test_ties_broken_by_certified_rank(cfg):
    certified = certify([line("g1f3", 30, 1), line("d2d4", 30, 2), line("f1c4", 30, 3)], 30)
    evaluator = FakeEngine(lambda b, p, k: [FakePVLine(next(iter(b.legal_moves)), 25, 1)])
    for order in ([0, 1, 2], [2, 1, 0]):
        shuffled = Certified(certified.best, [certified.candidates[i] for i in order], 30, {})
        res = pick_detailed(
            OPEN, shuffled, FakeProfile(), ScriptedOpponent(), evaluator, FakeBudget(), cfg
        )
        assert res.move.uci() == "g1f3" and res.reason == "steer"


def _weak_profile(uplift: float) -> FakeProfile:
    return FakeProfile(weak_clusters=[FakeCluster("w", [1.0, 1.0], [1.0, 1.0], uplift)])


def _extract_for(target_fen: str):
    """Feature fake: [1, 1] (inside the cluster) only for target_fen, far away otherwise."""

    def extract(board, pov, *, eval_deep=None, eval_shallow=None):
        return np.array([1.0, 1.0] if board.fen() == target_fen else [50.0, 50.0])

    return extract


def test_weakness_bonus_can_flip_choice_within_tolerance(cfg):
    certified = certify([line("g1f3", 30, 1), line("d2d4", 28, 2)], 30)
    evaluator = table_evaluator({fen_after(OPEN, "g1f3", "b8c6"): 40}, default=30)
    opponent = ScriptedOpponent(default=lambda b: [(chess.Move.from_uci("b8c6"), 1.0)])
    target = fen_after(OPEN, "d2d4")
    args = (OPEN, certified, _weak_profile(2.0), opponent, evaluator, FakeBudget())
    cfg.steer.lambda_weakness = 0.0
    assert pick(*args, cfg, extract=_extract_for(target))[0].uci() == "g1f3"
    cfg.steer.lambda_weakness = 0.15  # 0.15 * 100 * (2.0 - 1) = +15 cp beats a 10 cp deficit
    move, scored = pick(*args, cfg, extract=_extract_for(target))
    assert move.uci() == "d2d4"
    assert scored[1].weakness == 1.0 and scored[1].score == pytest.approx(30 + 15)


def test_fallback_to_best_when_steer_looks_worse_than_tolerance(cfg):
    certified = certify([line("g1f3", 30, 1), line("d2d4", 28, 2)], 30)
    evaluator = table_evaluator({fen_after(OPEN, "g1f3", "b8c6"): 100}, default=40)
    opponent = ScriptedOpponent(default=lambda b: [(chess.Move.from_uci("b8c6"), 1.0)])
    cfg.steer.lambda_weakness = 1.0  # +100 cp bonus outweighs the 60 cp expected-eval deficit
    res = pick_detailed(
        OPEN,
        certified,
        _weak_profile(2.0),
        opponent,
        evaluator,
        FakeBudget(),
        cfg,
        extract=_extract_for(fen_after(OPEN, "d2d4")),
    )
    assert res.scored[1].score > res.scored[0].score
    assert res.move.uci() == "g1f3" and res.reason == "fallback_best"


@pytest.mark.parametrize("failure", ["opponent", "evaluator", "extract", "illegal", "empty"])
def test_any_exception_returns_best(setup, cfg, failure):
    certified, opponent, evaluator = setup
    profile = FakeProfile()
    extract = None
    if failure == "opponent":
        opponent.fail = RuntimeError("proxy died")
    elif failure == "evaluator":
        evaluator.fail = RuntimeError("evaluator died")
    elif failure == "extract":
        profile = _weak_profile(2.0)

        def extract(*a, **k):
            raise ValueError("bad features")
    elif failure == "illegal":
        opponent.table[fen_after(OPEN, "g1f3")] = [("e1e8", 1.0)]
    else:
        opponent.table[fen_after(OPEN, "d2d4")] = []
    res = pick_detailed(
        OPEN, certified, profile, opponent, evaluator, FakeBudget(), cfg, extract=extract
    )
    assert res.move == certified.best.move and res.reason == "error" and res.error
    assert (
        pick(OPEN, certified, profile, opponent, evaluator, FakeBudget(), cfg, extract=extract)[0]
        == certified.best.move
    )


def test_deadline_passed_evaluates_only_best(setup, cfg):
    certified, opponent, evaluator = setup
    res = pick_detailed(
        OPEN,
        certified,
        FakeProfile(),
        opponent,
        evaluator,
        FakeBudget(),
        cfg,
        deadline=time.monotonic() - 1.0,
    )
    assert res.move == certified.best.move and res.deadline_hit
    assert [s.evaluated for s in res.scored] == [True, False, False]
    assert [s.score for s in res.scored][1:] == [-math.inf, -math.inf]
    assert opponent.calls == [fen_after(OPEN, "g1f3")] and len(evaluator.calls) == 2


def test_stop_event_skips_remaining_candidates(setup, cfg):
    certified, opponent, evaluator = setup
    stop = threading.Event()
    stop.set()
    res = pick_detailed(
        OPEN, certified, FakeProfile(), opponent, evaluator, FakeBudget(), cfg, stop=stop
    )
    assert res.move == certified.best.move and res.deadline_hit
    assert [s.evaluated for s in res.scored] == [True, False, False]


def test_deadline_skips_candidates_predicted_to_overrun(setup, cfg, monkeypatch):
    certified, opponent, _ = setup
    clock = [1000.0]
    monkeypatch.setattr(time, "monotonic", lambda: clock[0])

    def slow(board, pov, k):
        clock[0] += 10.0  # every evaluation "takes" 10 s
        return [FakePVLine(next(iter(board.legal_moves)), 0, 1)]

    def run(deadline: float):
        return pick_detailed(
            OPEN,
            certified,
            FakeProfile(),
            opponent,
            FakeEngine(slow),
            FakeBudget(),
            cfg,
            deadline=deadline,
        )

    # best costs 20 s (2 replies); d4 would start at +20 and is predicted to end at +40
    assert [s.evaluated for s in run(clock[0] + 35).scored] == [True, False, False]
    clock[0] = 1000.0
    # with +45: d4 runs (+20 → +30); Bc4 predicted +30 + 10 = +40 <= 45 runs too
    assert [s.evaluated for s in run(clock[0] + 45).scored] == [True, True, True]


def test_single_candidate_needs_no_search(cfg):
    certified = certify([line("g1f3", 30, 1), line("d2d4", -50, 2)], 30)
    ev = FakeEngine(fail=AssertionError("no search"))
    opp = ScriptedOpponent(fail=AssertionError("no search"))
    res = pick_detailed(OPEN, certified, FakeProfile(), opp, ev, FakeBudget(), cfg)
    assert res.move.uci() == "g1f3" and res.reason == "single_candidate"


def test_pick_never_mutates_board(setup, cfg):
    certified, opponent, evaluator = setup
    before = (OPEN.fen(), list(OPEN.move_stack))
    pick(OPEN, certified, FakeProfile(), opponent, evaluator, FakeBudget(), cfg)
    assert (OPEN.fen(), list(OPEN.move_stack)) == before


# ------------------------------------------------------------------ weakness_match


def vec(*xs):
    return lambda board, pov, **kw: np.array(xs, dtype=np.float32)


def test_weakness_empty_profile_is_zero_without_features():
    assert weakness_match(OPEN, FakeProfile(), chess.WHITE, extract=raising_extract) == 0.0


def test_weakness_inside_outside_and_nearest():
    near = FakeCluster("near", [1.0, 1.0], [1.0, 2.0], 1.8)
    far = FakeCluster("far", [10.0, 10.0], [1.0, 1.0], 5.0)
    other = FakeCluster("other", [1.5, 1.5], [1.0, 2.0], 3.0)
    assert weakness_match(OPEN, FakeProfile(weak_clusters=[near]), True, extract=vec(1, 2)) == (
        pytest.approx(0.8)
    )
    assert weakness_match(OPEN, FakeProfile(weak_clusters=[far]), True, extract=vec(1, 2)) == 0.0
    both = FakeProfile(weak_clusters=[other, far, near])
    assert weakness_match(OPEN, both, True, extract=vec(1, 2)) == pytest.approx(0.8)


def test_weakness_clamped_and_robust():
    def prof(uplift, centroid=(0.0, 0.0), scale=(1.0, 1.0)):
        return FakeProfile(weak_clusters=[FakeCluster("c", list(centroid), list(scale), uplift)])

    assert weakness_match(OPEN, prof(50.0), True, extract=vec(0, 0)) == 2.0
    assert weakness_match(OPEN, prof(50.0), True, extract=vec(0, 0), max_weakness=0.5) == 0.5
    assert weakness_match(OPEN, prof(0.0), True, extract=vec(0, 0)) == -1.0
    assert weakness_match(OPEN, prof(math.nan), True, extract=vec(0, 0)) == 0.0
    assert weakness_match(OPEN, prof(3.0, (0, 0, 0), (1, 1, 1)), True, extract=vec(0, 0)) == 0.0
    assert weakness_match(OPEN, prof(3.0, scale=(0.0, math.inf)), True, extract=vec(0, 0)) == 2.0


def test_weakness_uses_opponent_pov_for_features():
    seen = {}

    def spy(board, pov, *, eval_deep=None, eval_shallow=None):
        seen.update(pov=pov, deep=eval_deep, shallow=eval_shallow)
        return np.zeros(2)

    profile = FakeProfile(weak_clusters=[FakeCluster("c", [0, 0], [1, 1], 2.0)])
    weakness_match(OPEN, profile, chess.WHITE, eval_deep=30, eval_shallow=-10, extract=spy)
    assert seen == {"pov": chess.BLACK, "deep": -30, "shallow": 10}


def test_weakness_bounded_under_random_inputs():
    rng = random.Random(11)
    for _ in range(500):
        n = rng.randint(1, 6)
        clusters = [
            FakeCluster(
                "r",
                [rng.uniform(-3, 3) for _ in range(rng.choice([n, n, n + 1]))],
                [rng.choice([0.0, 1e-12, rng.uniform(0.1, 5), math.inf]) for _ in range(n)],
                rng.choice([rng.uniform(-5, 50), math.nan, math.inf]),
            )
            for _ in range(rng.randint(0, 4))
        ]
        x = [rng.choice([rng.uniform(-5, 5), math.nan]) for _ in range(n)]
        w = weakness_match(OPEN, FakeProfile(weak_clusters=clusters), True, extract=vec(*x))
        assert -1.0 <= w <= 2.0 and math.isfinite(w)


def test_weakness_with_real_features_module():
    features = pytest.importorskip("lostfish.features", reason="lostfish.features not available")
    after = OPEN.copy()
    after.push_uci("g1f3")
    x = features.extract(after, chess.BLACK, eval_deep=-30, eval_shallow=-10).astype(float)
    scale = [1.0] * len(x)
    profile = FakeProfile(weak_clusters=[FakeCluster("exact", list(x), scale, 1.6)])
    w = weakness_match(after, profile, chess.WHITE, eval_deep=30, eval_shallow=10)
    assert w == pytest.approx(0.6)


# ------------------------------------------------------------------ randomised invariant


def _random_board(rng: random.Random) -> chess.Board:
    board = chess.Board()
    for _ in range(rng.randint(0, 60)):
        legal = list(board.legal_moves)
        if not legal:
            break
        board.push(rng.choice(legal))
    return board


def _random_certified(rng: random.Random, board: chess.Board) -> Certified:
    legal = list(board.legal_moves)
    chosen = rng.sample(legal, rng.randint(1, min(6, len(legal))))
    cp = rng.choice([rng.randint(-400, 400), MATE_CP - 3, -(MATE_CP - 4)])
    lines = []
    for rank, move in enumerate(chosen, start=1):
        lines.append(FakePVLine(move, cp, rank, pv=[move]))
        cp -= rng.randint(0, 40)
    return certify(lines, rng.randint(0, 60))


def _chaos_opponent(rng: random.Random) -> ScriptedOpponent:
    def default(board: chess.Board):
        roll = rng.random()
        if roll < 0.05:
            raise RuntimeError("chaos")
        legal = list(board.legal_moves)
        if roll < 0.08:
            return [(chess.Move.from_uci("a1a1"), 1.0)]  # garbage move
        if roll < 0.10:
            return [(legal[0], math.nan)]
        picks = rng.sample(legal, min(len(legal), rng.randint(1, 3)))
        weights = [rng.random() + 1e-6 for _ in picks]
        return [(m, w / sum(weights)) for m, w in zip(picks, weights, strict=True)]

    return ScriptedOpponent(default=default)


def test_pick_never_leaves_candidate_set_randomised(cfg):
    rng = random.Random(2026)
    outcomes = {"steer": 0, "fallback_best": 0, "single_candidate": 0, "error": 0}
    for _ in range(500):
        board = _random_board(rng)
        if board.is_game_over():
            continue
        certified = _random_certified(rng, board)
        allowed = {c.move for c in certified.candidates}
        evaluator = FakeEngine(static_script(str(rng.random())))
        if rng.random() < 0.05:
            evaluator.fail = RuntimeError("evaluator chaos")
        n = rng.randint(1, 5)
        clusters = [
            FakeCluster("c", [rng.uniform(-2, 2) for _ in range(n)], [1.0] * n, rng.uniform(0, 9))
            for _ in range(rng.randint(0, 3))
        ]

        def extract(b, pov, *, eval_deep=None, eval_shallow=None, n=n):
            if rng.random() < 0.03:
                raise ValueError("features chaos")
            return np.array([rng.uniform(-2, 2) for _ in range(n)])

        cfg.steer.lambda_weakness = rng.choice([0.0, 0.15, 1.0, 5.0])
        deadline = rng.choice([None, time.monotonic() - 1, time.monotonic() + 60])
        res = pick_detailed(
            board,
            certified,
            FakeProfile(weak_clusters=clusters),
            _chaos_opponent(rng),
            evaluator,
            FakeBudget(),
            cfg,
            deadline=deadline,
            extract=extract,
        )
        outcomes[res.reason] += 1
        assert res.move in allowed
        if res.reason in ("error", "fallback_best", "single_candidate"):
            assert res.move == certified.best.move
        if res.reason == "steer" and res.move != certified.best.move:
            chosen = next(s for s in res.scored if s.candidate.move == res.move)
            assert chosen.evaluated
            assert chosen.expected_eval >= res.scored[0].expected_eval - certified.tolerance_cp
    assert all(v > 0 for v in outcomes.values()), outcomes  # every path was exercised


def test_candidate_dataclass_fields_match_contract():
    c = Candidate(chess.Move.from_uci("e2e4"), 10, 1, [])
    assert (c.move.uci(), c.cp, c.rank, c.pv) == ("e2e4", 10, 1, [])
