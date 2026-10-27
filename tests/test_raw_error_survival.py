"""scripts/raw_error_survival.py: shortlist grouping and survival report (no engine)."""

from __future__ import annotations

import importlib.util
import math
from pathlib import Path

import chess
import pandas as pd

_spec = importlib.util.spec_from_file_location(
    "raw_error_survival", Path(__file__).resolve().parents[1] / "scripts" / "raw_error_survival.py"
)
res = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(res)

F1 = chess.STARTING_FEN
F2 = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"
F3 = "8/8/8/8/8/8/8/K6k w - - 0 1"
F4 = "8/8/8/8/8/8/8/k6K b - - 0 1"


def test_build_groups_and_report_survival() -> None:
    ref = pd.DataFrame(
        {
            "fen": [F1, F1, F2, F3, F4],
            "best": ["e2e4", "e2e4", "e7e5", "a1b2", "a1b2"],
            "cp_best": [20, 20, -10, 0, 0],
            "move": ["d2d4", "g1f3", "e7e5", "a1a2", "a1a2"],
            "cp_after": [-130, 10, -10, 0, 0],
        }
    )
    labels = pd.DataFrame(
        {
            "fen": [F1, F2, F3, F4],
            "raw_top": ["d2d4", "e7e5", "a1a2", "a1a2"],
            "raw_top_loss": [150.0, 0.0, math.nan, 30.0],
        }
    )
    s = res.build(ref, labels, control=5, seed=0)
    assert set(s.loc[s["group"] == "flagged", "fen"]) == {F1} and (s["fen"] == F1).sum() == 2
    assert set(s.loc[s["group"] == "control", "fen"]) == {F2, F4}  # F3 is censored: never a control
    pass2 = pd.DataFrame(
        {
            "fen": [F1, F2, F4],
            "raw_top": ["d2d4", "e7e5", "b1b2"],
            "raw_top_loss": [120.0, 0.0, math.nan],
        }
    )
    r = res.report(s, pass2).set_index("group")
    assert r.loc["flagged", "known"] == 1 and r.loc["flagged", "search_blunder_pct"] == 100
    assert r.loc["flagged", "keeps_raw_move_pct"] == 100
    assert r.loc["control", "positions"] == 2 and r.loc["control", "known"] == 1
    assert r.loc["control", "search_blunders"] == 0 and r.loc["control", "keeps_raw_move_pct"] == 50
    assert r.loc["control", "ci_hi"] > 0 and r.loc["control", "censored"] == 1
