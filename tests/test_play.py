"""SteeringPlayer: engine ownership, fallbacks, telemetry; one slow end-to-end run."""

from __future__ import annotations

import json
import time
from pathlib import Path

import chess
import pytest

from lostfish.play import FallbackProfile, SteeringPlayer
from tests.steer_fakes import (
    FakeBudget,
    FakeEngine,
    FakeProfile,
    line,
    make_cfg,
    ranked_script,
    static_script,
)

QUIET_MIDDLEGAME = "r1bq1rk1/pp2bppp/2n1pn2/2pp4/2PP4/2N1PN2/PP2BPPP/R1BQ1RK1 w - - 0 8"
TELEMETRY_KEYS = {
    "candidates",
    "chosen",
    "reason",
    "tolerance_cp",
    "effective_depth",
    "timings_ms",
    "profile",
    "lambda",
    "best",
    "deadline_hit",
}


def flat_script(board, pov, k):
    """Every legal move scores 0: all of them are certified (within any tolerance)."""
    moves = sorted(board.legal_moves, key=lambda m: m.uci())[:k]
    return [line(m.uci(), 0, i + 1, ebd={d: 0 for d in range(1, 12)}) for i, m in enumerate(moves)]


class Factory:
    def __init__(self, scripts=None, fails=None):
        self.scripts = scripts or {}
        self.fails = fails or {}
        self.created: dict[str, FakeEngine] = {}

    def __call__(self, path, *, hash_mb, threads, syzygy_path, name):
        eng = FakeEngine(
            self.scripts.get(name, static_script(name)),
            name=name,
            fail=self.fails.get(name),
            path=path,
            hash_mb=hash_mb,
            threads=threads,
            syzygy_path=syzygy_path,
        )
        self.created[name] = eng
        return eng


def make_player(factory=None, profile=None, **kwargs):
    factory = factory or Factory({"certifier": flat_script, "proxy": ranked_script("px")})
    loader = kwargs.pop("profile_loader", lambda name, cfg: profile or FakeProfile())
    player = SteeringPlayer(make_cfg(), engine_factory=factory, profile_loader=loader, **kwargs)
    return player, factory


def test_three_persistent_engines_with_expected_settings():
    player, f = make_player()
    assert set(f.created) == {"certifier", "proxy", "evaluator"}
    assert f.created["proxy"].kwargs["hash_mb"] == 16
    assert (
        f.created["certifier"].kwargs["hash_mb"] == f.created["evaluator"].kwargs["hash_mb"] == 64
    )
    assert all(e.kwargs["threads"] == 1 for e in f.created.values())
    assert f.created["proxy"].kwargs["syzygy_path"] is None
    for _ in range(3):
        player.choose(chess.Board(), FakeBudget())
    assert len(f.created) == 3
    player.new_game()
    assert all(e.new_games == 1 for e in f.created.values())
    player.close()
    player.close()  # idempotent
    assert all(e.closed for e in f.created.values())


def test_choose_returns_certified_move_and_full_telemetry():
    player, f = make_player(profile=FakeProfile(effective_depth=6))
    board = chess.Board(QUIET_MIDDLEGAME)
    move, rec = player.choose(board, FakeBudget(k=3, proxy_depth_cap=8))
    assert move in board.legal_moves and rec["reason"] == "steer"
    assert TELEMETRY_KEYS <= rec.keys()
    assert rec["chosen"] == move.uci() and move.uci() in [c["move"] for c in rec["candidates"]]
    assert rec["effective_depth"] == 6
    assert {c["depth"] for c in f.created["proxy"].calls} == {6}
    assert {"certify", "steer", "proxy", "eval", "features", "total"} <= rec["timings_ms"].keys()
    for row in rec["candidates"]:
        assert {"move", "cp", "rank", "expected_eval", "weakness", "score", "replies"} <= row.keys()
        assert all({"move", "weight", "eval"} <= r.keys() for r in row["replies"])
    json.dumps(rec, allow_nan=False)  # telemetry must be strict JSON


def test_proxy_depth_capped_by_budget_and_recomputed_per_move():
    player, f = make_player(profile=FakeProfile(effective_depth=12))
    _, rec = player.choose(chess.Board(), FakeBudget(proxy_depth_cap=8))
    assert rec["effective_depth"] == 8
    _, rec = player.choose(chess.Board(), FakeBudget(proxy_depth_cap=14))
    assert rec["effective_depth"] == 12
    assert {c["depth"] for c in f.created["proxy"].calls} == {8, 12}


def test_single_candidate_fast_path():
    def only(b, p, k):
        return [line("e2e4", 50, 1), line("a2a3", -200, 2)][:k]

    player, f = make_player(Factory({"certifier": only}))
    move, rec = player.choose(chess.Board(), FakeBudget())
    assert move.uci() == "e2e4" and rec["reason"] == "single_candidate"
    assert f.created["proxy"].calls == [] and f.created["evaluator"].calls == []


def test_no_time_left_plays_best_without_steering():
    player, f = make_player()
    move, rec = player.choose(chess.Board(), FakeBudget(soft_ms=0))
    assert rec["reason"] == "fallback_best" and rec["deadline_hit"]
    assert move.uci() == rec["best"] and f.created["proxy"].calls == []


def test_uci_stop_mid_search_plays_best_and_stops_engines():
    holder = {}

    def certifier(board, pov, k):
        holder["player"].stop()  # UCI `stop` arrives while the certifier is searching
        return flat_script(board, pov, k)

    player, f = make_player(Factory({"certifier": certifier, "proxy": ranked_script()}))
    holder["player"] = player
    move, rec = player.choose(chess.Board(), FakeBudget())
    assert rec["reason"] == "fallback_best" and rec["deadline_hit"]
    assert move.uci() == rec["best"] and f.created["proxy"].calls == []
    assert all(e.stops == 1 for e in f.created.values())
    f.created["certifier"].script = flat_script
    _, rec = player.choose(chess.Board(), FakeBudget())  # the stop does not leak into the next move
    assert rec["reason"] == "steer"


def test_steering_error_plays_certified_best():
    player, _ = make_player(Factory({"certifier": flat_script}, {"proxy": RuntimeError("boom")}))
    move, rec = player.choose(chess.Board(), FakeBudget())
    assert rec["reason"] == "error" and "boom" in rec["error"]
    assert move.uci() == rec["best"]


def test_certifier_failure_uses_fresh_single_pv_search():
    player, f = make_player(Factory({}, {"certifier": RuntimeError("certifier died")}))
    board = chess.Board()
    move, rec = player.choose(board, FakeBudget(certify_nodes=4321))
    assert rec["reason"] == "error" and "certifier died" in rec["error"]
    assert move in board.legal_moves and rec["candidates"] == []
    call = f.created["evaluator"].calls[-1]
    assert call["multipv"] == 1 and call["nodes"] == 4321
    json.dumps(rec, allow_nan=False)


def test_everything_failing_still_returns_a_legal_move():
    fails = {n: RuntimeError(n) for n in ("certifier", "proxy", "evaluator")}
    player, _ = make_player(Factory({}, fails))
    board = chess.Board(QUIET_MIDDLEGAME)
    move, rec = player.choose(board, FakeBudget())
    assert move in board.legal_moves and rec["reason"] == "error"


def test_illegal_certified_move_is_never_played():
    def bogus(b, p, k):
        return [line("e2e5", 0, 1)]  # illegal from the start position

    player, _ = make_player(Factory({"certifier": bogus}))
    board = chess.Board()
    move, rec = player.choose(board, FakeBudget())
    assert move in board.legal_moves and rec["reason"] == "error"


def test_overrides_do_not_mutate_the_callers_config():
    cfg = make_cfg()
    player = SteeringPlayer(
        cfg,
        steering_lambda=0.5,
        tolerance_cp=10,
        engine_factory=Factory(),
        profile_loader=lambda n, c: FakeProfile(),
    )
    assert player.cfg.steer.lambda_weakness == 0.5 and player.cfg.certify.tolerance_cp == 10
    assert cfg.steer.lambda_weakness == 0.15 and cfg.certify.tolerance_cp == 30


def test_overrides_with_real_config():
    config = pytest.importorskip("lostfish.config", reason="lostfish.config not available")
    cfg = config.load_config()
    player = SteeringPlayer(cfg, steering_lambda=0.3, tolerance_cp=12, engine_factory=Factory())
    assert player.cfg.steer.lambda_weakness == 0.3 and player.cfg.certify.tolerance_cp == 12
    assert cfg.certify.tolerance_cp != 12 or cfg.steer.lambda_weakness != 0.3


def test_profile_loader_failure_never_crashes():
    def broken(name, cfg):
        raise OSError("disk on fire")

    player, _ = make_player(profile_loader=broken)
    player.set_opponent("somebot", 2100)
    assert isinstance(player.profile, FallbackProfile) and player.profile.name == "somebot"
    _, rec = player.choose(chess.Board(), FakeBudget(proxy_depth_cap=8))
    assert rec["effective_depth"] == 8 and rec["profile"] == "somebot"


def test_unknown_opponent_with_real_profiles_module():
    pytest.importorskip("lostfish.profiles", reason="lostfish.profiles not available")
    player = SteeringPlayer(make_cfg(), engine_factory=Factory({"certifier": flat_script}))
    player.set_opponent("no_such_bot_xyz", None)
    assert player.profile is not None and player.profile.effective_depth >= 1
    _, rec = player.choose(chess.Board(), FakeBudget())
    assert rec["reason"] in ("steer", "fallback_best")


# ------------------------------------------------------------------ slow: real Stockfish


@pytest.mark.slow
def test_end_to_end_bullet_budget_with_real_engines():
    pytest.importorskip("lostfish.engines", reason="lostfish.engines (agent A) not available")
    config = pytest.importorskip("lostfish.config", reason="lostfish.config not available")
    cfg = config.load_config()
    if not Path(cfg.engines.stockfish).is_file():
        pytest.skip(f"Stockfish binary missing at {cfg.engines.stockfish}; run setup_engines.sh")
    try:
        from lostfish.timeman import Budget
    except ImportError:
        Budget = FakeBudget
    budget = Budget(
        tc_class="bullet",
        certify_nodes=200_000,
        eval_nodes=50_000,
        k=3,
        proxy_depth_cap=8,
        soft_ms=1000,
        hard_ms=1500,
        clock_fraction=1.0,
    )
    player = SteeringPlayer(cfg)
    try:
        player.set_opponent(None, None)
        player.new_game()
        board = chess.Board(QUIET_MIDDLEGAME)
        t0 = time.perf_counter()
        move, rec = player.choose(board, budget)
        elapsed = time.perf_counter() - t0
        print("\nsteering timings_ms:", json.dumps(rec["timings_ms"]), "reason:", rec["reason"])
        print("candidates:", json.dumps(rec["candidates"]))
        assert move in board.legal_moves
        assert rec["reason"] in ("steer", "fallback_best", "single_candidate"), rec.get("error")
        assert move.uci() in [c["move"] for c in rec["candidates"]]
        assert TELEMETRY_KEYS <= rec.keys()
        assert elapsed < 1.5, f"choose() took {elapsed:.2f}s"
        json.dumps(rec, allow_nan=False)
    finally:
        player.close()
