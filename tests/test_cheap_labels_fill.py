"""mining.cheap_labels_fill bookkeeping without Stockfish."""

from __future__ import annotations

import math

import chess
import pandas as pd

from mining.cheap_labels_fill import apply_fill, pending, raw_top_loss

F1, F2, F3 = chess.STARTING_FEN, "8/8/8/8/8/8/8/K6k w - - 0 1", "8/8/8/8/8/8/8/k6K b - - 0 1"


def _labels() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "fen": [F1, F2, F3],
            "raw_top": ["g1f3", "a1b2", None],
            "raw_top_loss": [math.nan, 0.0, math.nan],
            "raw_top_censored": [True, False, True],
        }
    )


def test_pending_selects_censored_rows_with_a_reference() -> None:
    ref = pd.DataFrame(
        {"fen": [F1, F1, F2, F3], "cp_best": [20, 21, 0, 0], "nodes": [100, 100, 100, 100]}
    )
    assert pending(_labels(), ref) == [
        (F1, "g1f3", 20, 100)
    ]  # first reference row wins; F3 has no move
    assert pending(_labels(), ref.drop(columns="nodes"), default_nodes=7) == [(F1, "g1f3", 20, 7)]


def test_apply_fill_marks_sources_and_uncensors() -> None:
    out = apply_fill(_labels(), {F1: 35})
    row = out.set_index("fen").loc[F1]
    assert (
        row["raw_top_loss"] == 35.0
        and not row["raw_top_censored"]
        and row["raw_top_loss_src"] == "sf"
    )
    assert out.set_index("fen").loc[F2, "raw_top_loss_src"] == "ref"
    assert out.set_index("fen").loc[F3, "raw_top_loss_src"] is None
    assert apply_fill(_labels(), {}).set_index("fen").loc[F1, "raw_top_censored"]


class _Engine:
    """Returns +50 for whoever is to move in the searched (child) position."""

    def analyse(self, board: chess.Board, limit: chess.engine.Limit) -> dict:
        return {"score": chess.engine.PovScore(chess.engine.Cp(50), board.turn), "pv": []}


def test_raw_top_loss_is_from_the_parent_mover() -> None:
    # white to move, cp_best 20; after g1f3 black is to move and the engine says +50 for black -> -50 for white
    assert raw_top_loss(_Engine(), F1, "g1f3", 20, 100) == 70
