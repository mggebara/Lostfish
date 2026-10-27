"""mining.cheap_labels without an engine: label arithmetic and the in-process run with a fake proxy."""

from __future__ import annotations

import math
from pathlib import Path

import chess
import pandas as pd
import pytest

from mining import cheap_labels as cl

START = chess.STARTING_FEN
AFTER_E4 = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"
MATE = (
    "rnb1kbnr/pppp1ppp/8/4p3/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3"  # fool's mate, no legal moves
)


def test_reference_table_merges_sources_and_skips_missing() -> None:
    row = {"best": "d2d4", "cp_best": 30, "move": "e2e4", "cp_after": 10}
    assert cl.reference_table(row) == {"d2d4": 30, "e2e4": 10}
    # the played move equal to best keeps best's eval; NaN/None references are ignored
    assert cl.reference_table({"best": "d2d4", "cp_best": 30, "move": "d2d4", "cp_after": 29}) == {
        "d2d4": 30
    }
    assert cl.reference_table({"best": None, "cp_best": float("nan")}) == {}
    multi = {"best": "d2d4", "cp_best": 30, "ref_moves": ["d2d4", "g1f3"], "ref_cps": [31, 5]}
    assert cl.reference_table(multi) == {"d2d4": 30, "g1f3": 5}


def test_cheap_label_exact_censored_and_empty() -> None:
    policy = {"e2e4": 0.5, "d2d4": 0.3, "g1f3": 0.2}
    lab = cl.cheap_label(policy, 17, {"d2d4": 30, "e2e4": 10}, "d2d4")
    assert lab["raw_top"] == "e2e4" and lab["raw_top_p"] == 0.5
    assert lab["p_best"] == 0.3 and lab["raw_q_cp"] == 17
    assert lab["raw_top_loss"] == 20.0 and lab["raw_top_censored"] is False
    # the top move has no reference eval -> loss unknown, censored
    lab = cl.cheap_label(policy, 17, {"d2d4": 30}, "d2d4")
    assert math.isnan(lab["raw_top_loss"]) and lab["raw_top_censored"] is True
    # no reference at all -> p_best unknown too
    lab = cl.cheap_label(policy, None, {}, None)
    assert math.isnan(lab["p_best"]) and math.isnan(lab["raw_top_loss"])
    # the net returned nothing
    lab = cl.cheap_label({}, -5, {"d2d4": 30}, "d2d4")
    assert lab["raw_top"] is None and lab["raw_top_censored"] is True and lab["raw_q_cp"] == -5


class FakeProxy:
    """Uniform policy with a2a3 (else the first legal move) favoured; counts calls to check resume."""

    calls = 0

    def __init__(self) -> None:
        self.last_eval_cp: int | None = None

    def root_policy(self, board: chess.Board) -> dict[str, float]:
        FakeProxy.calls += 1
        legal = [m.uci() for m in board.legal_moves]
        policy = {m: 0.5 / len(legal) for m in legal}
        policy["a2a3" if "a2a3" in policy else legal[0]] += 0.5
        self.last_eval_cp = 42
        return policy


def test_run_in_process_dedupes_fens_and_resumes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cl, "_make_proxy", lambda lc0, weights, nodes=1: FakeProxy())
    FakeProxy.calls = 0
    df = pd.DataFrame(
        {
            "fen": [START, START, AFTER_E4, MATE],
            "best": ["e2e4", "d2d4", "e7e5", None],
            "cp_best": [20, 25, -15, None],
            "move": ["a2a3", "a2a3", "e7e5", None],
            "cp_after": [-10, -10, -15, None],
        }
    )
    out = tmp_path / "labels.parquet"
    frame = cl.run(df, lc0="lc0", weights="w.pb.gz", out=out, workers=0, chunk=2)
    assert FakeProxy.calls == 2  # START evaluated once, the mated position not at all
    assert sorted(frame["fen"]) == sorted([START, AFTER_E4, MATE])
    row = frame.set_index("fen").loc[START]
    assert row["raw_top"] == "a2a3" and row["p_best"] == pytest.approx(
        0.5 / 20
    )  # first row's refs win
    assert row["raw_top_loss"] == 30.0 and not row["raw_top_censored"] and row["raw_q_cp"] == 42
    mated = frame.set_index("fen").loc[MATE]
    assert mated["n_legal"] == 0 and mated["raw_top_censored"]
    assert out.with_suffix(".json").exists()

    more = pd.concat(
        [df, pd.DataFrame({"fen": ["8/8/8/8/8/8/8/K6k w - - 0 1"]})], ignore_index=True
    )
    frame2 = cl.run(more, lc0="lc0", weights="w.pb.gz", out=out, workers=0, chunk=2, resume=True)
    assert FakeProxy.calls == 3 and len(frame2) == 4
