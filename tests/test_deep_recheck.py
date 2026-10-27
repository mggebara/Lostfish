"""scripts/deep_recheck.py: pricing arithmetic and the held-at-depth summary (no engine)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import chess
import pandas as pd
import pytest

_spec = importlib.util.spec_from_file_location(
    "deep_recheck", Path(__file__).resolve().parents[1] / "scripts" / "deep_recheck.py"
)
dr = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(dr)


def test_price_uses_the_mover_pov_for_both_searches(monkeypatch) -> None:
    seen = []

    def fake_search(engine, board, limit, pov):
        seen.append((board.fen(), pov, limit.nodes))
        return (30, None) if board.turn == chess.WHITE else (-120, None)

    monkeypatch.setattr(dr, "_search", fake_search)
    cp_root, cp_after, loss = dr.price(object(), chess.STARTING_FEN, "e2e4", 5000)
    assert (cp_root, cp_after, loss) == (30, -120, 150)
    assert [p for _, p, _ in seen] == [chess.WHITE, chess.WHITE]
    assert {n for *_, n in seen} == {5000}


def test_summarise_counts_held_blunders() -> None:
    df = pd.DataFrame(
        {
            "group": ["a", "a", "a", "b"],
            "loss_ref": [150, 200, 20, 300],
            "loss_deep": [120, 40, 0, 10],
        }
    )
    s = dr.summarise(df).set_index("group")
    assert s.loc["a", "ref_blunders"] == 2 and s.loc["a", "held_at_depth_pct"] == 50
    assert s.loc["b", "held_at_depth_pct"] == 0 and s.loc["a", "deep_blunder_pct"] == pytest.approx(
        100 / 3
    )
