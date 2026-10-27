"""mining.lichess_eval record parsing on real-format records (no network)."""

from __future__ import annotations

import json

from mining.lichess_eval import collect, parse_record, pv_cp_stm

REC1 = {
    "fen": "7r/1p3k2/p1bPR3/5p2/2B2P1p/8/PP4P1/3K4 b - -",
    "evals": [
        {
            "pvs": [
                {"cp": 69, "line": "f7g7 e6e2 h8d8"},
                {"cp": 163, "line": "h8d8 d1e1 a6a5"},
                {"cp": 229, "line": "h8a8 d1e1 a6a5"},
                {"mate": 5, "line": "h8f8 d1e1"},
                {"cp": 237, "line": "zzzz"},
            ],
            "knodes": 4189972,
            "depth": 46,
        }
    ],
}
REC2 = {
    "fen": "8/4r3/2R2pk1/6pp/3P4/6P1/5K1P/8 b - -",
    "evals": [
        {
            "pvs": [{"cp": 0, "line": "e7a7 f2e3"}, {"cp": 0, "line": "e7b7 f2e3"}],
            "knodes": 5,
            "depth": 58,
        },
        {
            "pvs": [
                {"cp": 10, "line": "e7e4"},
                {"cp": 0, "line": "g6f5"},
                {"cp": -3, "line": "e7a7"},
            ],
            "depth": 30,
        },
    ],
}


def test_pv_cp_is_side_to_move_and_mates_clip() -> None:
    assert pv_cp_stm({"cp": 69}, white_to_move=False) == -69
    assert pv_cp_stm({"cp": 69}, white_to_move=True) == 69
    assert pv_cp_stm({"mate": -3}, white_to_move=False) == 3000
    assert pv_cp_stm({"cp": 9999}, white_to_move=True) == 3000
    assert pv_cp_stm({"line": "e2e4"}, white_to_move=True) is None


def test_parse_record_black_to_move_sorts_best_first_and_drops_bad_lines() -> None:
    row = parse_record(REC1, min_depth=20, min_pvs=2)
    assert row is not None
    assert (
        row["fen"].startswith("7r/1p3k2/p1bPR3/5p2/2B2P1p/8/PP4P1/3K4 b - -") and row["stm"] == "b"
    )
    assert row["best"] == "f7g7" and row["cp_best"] == -69
    # the bogus "zzzz" line is dropped; mate-for-white is -3000 for black and sorts last
    assert row["ref_moves"] == ["f7g7", "h8d8", "h8a8", "h8f8"]
    assert row["ref_cps"] == [-69, -163, -229, -3000]
    assert row["n_pvs"] == 4 and row["depth"] == 46 and row["pieces"] == 15


def test_parse_record_picks_deepest_qualifying_eval() -> None:
    row = parse_record(REC2, min_depth=20, min_pvs=2)
    assert row is not None and row["depth"] == 58 and row["ref_moves"] == ["e7a7", "e7b7"]
    # a stricter PV requirement falls through to the shallower eval with three lines
    row = parse_record(REC2, min_depth=20, min_pvs=3)
    # white-POV 10/0/-3 become -10/0/+3 for black, so e7a7 is black's best
    assert row is not None and row["depth"] == 30 and row["best"] == "e7a7" and row["cp_best"] == 3
    assert row["ref_moves"] == ["e7a7", "g6f5", "e7e4"]
    assert parse_record(REC2, min_depth=60, min_pvs=2) is None


def test_collect_stops_at_n_and_skips_junk(tmp_path) -> None:
    lines = [json.dumps(REC1), "not json", "", json.dumps(REC2), json.dumps(REC1)]
    out = tmp_path / "p.parquet"
    df = collect(iter(lines), n=2, min_depth=20, min_pvs=2, out=out, flush_every=0)
    assert len(df) == 2 and list(df["best"]) == ["f7g7", "e7a7"] and out.exists()
