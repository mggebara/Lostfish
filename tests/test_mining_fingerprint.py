"""mining.fingerprint on synthetic annotation frames (no engine, no network)."""

from __future__ import annotations

import json
import random

import pandas as pd
import pytest

from mining.fingerprint import (
    cp_bucket,
    fingerprint_frame,
    is_test_game,
    phase_of,
    pick_depth,
    summarise,
)

START = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
ENDGAME = "8/5pk1/6p1/8/3R4/6P1/5PK1/1r6 w - - 0 40"


def synthetic(
    true_depth: int, n_games: int = 60, per_game: int = 25, seed: int = 0
) -> pd.DataFrame:
    """Bot plays Stockfish's depth-`true_depth` move 80% of the time.

    Depth d's best move changes every 3 depths (as real trajectories do), searches complete
    depth 1..12 everywhere and 13..16 only on 20% of positions, where the bot always agrees
    (the easy-position bias of raw deep-depth agreement).
    """
    rng = random.Random(seed)
    rows = []
    for g in range(n_games):
        for p in range(per_game):
            deep = rng.random() < 0.2
            max_d = 16 if deep else 12
            bbd = {d: f"m{(d - 1) // 3}" for d in range(1, max_d + 1)}
            final = bbd[max_d]
            if deep:
                played = final
                bbd = {d: final for d in bbd}
            elif rng.random() < 0.8:
                played = bbd[true_depth]
            else:
                played = "x" + str(rng.randint(0, 9))
            rows.append(
                {
                    "bot": "synth",
                    "game_id": f"g{g:04d}",
                    "ply": 20 + 2 * p,
                    "fen": ENDGAME if p % 5 == 0 else START,
                    "played": played,
                    "best": final,
                    "cp_best": rng.choice([0, 80, 200, 700]),
                    "best_by_depth": json.dumps(bbd),
                }
            )
    return pd.DataFrame(rows)


def test_split_is_deterministic_and_balanced() -> None:
    ids = [f"game{i}" for i in range(5000)]
    flags = [is_test_game(g) for g in ids]
    assert flags == [is_test_game(g) for g in ids]
    assert 0.17 < sum(flags) / len(flags) < 0.23


def test_recovers_true_depth() -> None:
    fp = fingerprint_frame(synthetic(true_depth=5), min_coverage=0.5)
    # depths 4..6 share the depth-5 move; ties break toward the lower depth
    assert fp["effective_depth"] == 4
    assert fp["effective_depth_train"] == 4
    assert fp["gate_pass"]
    assert fp["test_agreement_effective"] == pytest.approx(
        fp["test_best_fixed_agreement"], abs=1e-12
    )
    # raw deep agreement is inflated by easy positions, but low coverage keeps it unselected
    raw = fp["curves"]["all"]["raw"]
    assert raw[13] == pytest.approx(1.0)
    assert fp["curves"]["all"]["coverage"][13] < 0.5
    assert set(fp["by_phase"]) <= {"opening", "middlegame", "endgame"}
    assert sum(v["n"] for v in fp["by_cp_bucket"].values()) == fp["n_positions"]
    assert fp["n_train"] + fp["n_test"] == fp["n_positions"]


def test_test_games_disjoint_from_train() -> None:
    df = synthetic(true_depth=8, n_games=30)
    fp = fingerprint_frame(df)
    test_games = {g for g in df["game_id"].unique() if is_test_game(g)}
    assert fp["n_test_games"] == len(test_games)
    assert fp["n_test"] == int(df["game_id"].isin(test_games).sum())


def test_pick_depth_ties_and_coverage() -> None:
    assert pick_depth([0.3, 0.5, 0.5, 0.4], [1, 1, 1, 1], 0.5) == 2
    assert pick_depth([0.3, 0.4, 0.9], [1, 1, 0.1], 0.5) == 2


def test_summary_compares_with_global_fixed_depth() -> None:
    fps = {
        "a": fingerprint_frame(synthetic(true_depth=2, seed=1)),
        "b": fingerprint_frame(synthetic(true_depth=11, seed=2)),
    }
    s = summarise(fps)
    assert s["n_bots"] == 2
    assert s["gate_pass_vs_global_fixed"]
    assert s["fingerprinted_mean_test_agreement"] > s["best_global_fixed_mean_test_agreement"]


def test_phase_and_bucket_helpers() -> None:
    assert phase_of(START) == "opening"
    assert phase_of(ENDGAME) == "endgame"
    assert cp_bucket(-75) == "50-150"
    assert cp_bucket(31990) == "600+"
