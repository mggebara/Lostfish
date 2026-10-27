"""training.cheap_dataset: cheap labels -> trainer schema (no engine)."""

from __future__ import annotations

import math

import chess
import pandas as pd

from training.cheap_dataset import build

F1, F2, F3, F4 = (
    chess.STARTING_FEN,
    "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1",
    "8/8/8/8/8/8/8/K6k w - - 0 1",
    "8/8/8/8/8/8/8/k6K b - - 0 1",
)


def test_build_maps_losses_and_handles_censoring() -> None:
    positions = pd.DataFrame(
        {
            "fen": [F1, F2, F3, F4],
            "best": ["e2e4", "e7e5", "a1b2", "a1b2"],
            "cp_best": [20, -10, 0, 300],
            "ref_cps": [[20, 10], [-10, -40], [0, -5], [300, 150]],
            "pieces": [32, 32, 2, 2],
        }
    )
    labels = pd.DataFrame(
        {
            "fen": [F1, F2, F3, F4],
            "raw_top": ["d2d4", "e7e5", "a1a2", "a1a2"],
            "raw_top_loss": [10.0, 0.0, math.nan, math.nan],
            "raw_top_censored": [False, False, True, True],
        }
    )
    out = build(positions, labels)
    # F3 is censored with an undecidable bound (5 cp) and is dropped; F4's bound (150) proves a blunder
    assert list(out["fen"]) == [F1, F2, F4]
    row = out.set_index("fen")
    assert (
        row.loc[F1, "cp_after"] == 10
        and row.loc[F1, "loss"] == 10
        and row.loc[F1, "move"] == "d2d4"
    )
    assert row.loc[F2, "loss"] == 0 and row.loc[F2, "victim_color"] == "black"
    assert row.loc[F4, "loss"] == 150 and row.loc[F4, "cp_after"] == 150
    assert out["game_id"].is_unique and set(out["baseline_loss"]) == {0}
    assert len(build(positions, labels, keep_sure=False)) == 2
