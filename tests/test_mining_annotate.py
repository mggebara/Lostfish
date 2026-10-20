"""mining.annotate against the real Stockfish (slow) plus engine-free PGN helpers."""

from __future__ import annotations

import json
from pathlib import Path

import chess
import pytest

from mining.common import (
    MATE_CP,
    append_pgn_zst,
    game_id_from_headers,
    pgn_headers,
    read_pgn_zst,
    split_pgn,
)

SF = Path(__file__).resolve().parents[1] / "engines" / "stockfish"

# Blackburne Shilling trap: White (the "bot" in one test) walks into 7...Nf3#.
PGN = """[Event "rated blitz game"]
[Site "https://lichess.org/abcdefgh"]
[White "WhiteBot"]
[Black "BlackBot"]
[Result "0-1"]
[WhiteElo "1500"]
[BlackElo "1600"]
[WhiteTitle "BOT"]
[BlackTitle "BOT"]
[Variant "Standard"]
[TimeControl "180+0"]

1. e4 { [%clk 0:03:00] } 1... e5 { [%clk 0:03:00] } 2. Nf3 { [%clk 0:02:59] } 2... Nc6 { [%clk 0:02:58] } 3. Bc4 { [%clk 0:02:58] } 3... Nd4 { [%clk 0:02:57] } 4. Nxe5 { [%clk 0:02:57] } 4... Qg5 { [%clk 0:02:55] } 5. Nxf7 { [%clk 0:02:55] } 5... Qxg2 { [%clk 0:02:54] } 6. Rf1 { [%clk 0:02:54] } 6... Qxe4+ { [%clk 0:02:53] } 7. Be2 { [%clk 0:02:52] } 7... Nf3# { [%clk 0:02:52] } 0-1
"""


def test_pgn_zst_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "x.pgn.zst"
    append_pgn_zst(path, [PGN])
    append_pgn_zst(path, [PGN.replace("abcdefgh", "zzzzzzzz")])
    games = split_pgn(read_pgn_zst(path))
    assert [game_id_from_headers(pgn_headers(g)) for g in games] == ["abcdefgh", "zzzzzzzz"]


def test_non_standard_games_are_skipped() -> None:
    from mining.annotate import annotate_game

    variant = PGN.replace('[Variant "Standard"]', '[Variant "Chess960"]')
    assert annotate_game(None, variant, "whitebot", 1000, 4) == ([], 0)  # type: ignore[arg-type]
    assert annotate_game(None, PGN, "nobody", 1000, 4) == ([], 0)  # type: ignore[arg-type]


@pytest.mark.slow
@pytest.mark.skipif(not SF.exists(), reason="engines/stockfish missing (scripts/setup_engines.sh)")
def test_annotate_short_game_with_stockfish() -> None:
    from mining.annotate import annotate_game
    from mining.common import open_engine

    engine = open_engine(SF, hash_mb=16)
    try:
        white_rows, white_searches = annotate_game(engine, PGN, "WhiteBot", 5000, 4)
        black_rows, _ = annotate_game(engine, PGN, "blackbot", 5000, 4)
    finally:
        engine.quit()
    assert [r["ply"] for r in white_rows] == [4, 6, 8, 10, 12]
    assert [r["ply"] for r in black_rows] == [5, 7, 9, 11, 13]
    assert len(white_rows) <= white_searches <= 2 * len(white_rows)
    for r in white_rows + black_rows:
        board = chess.Board(r["fen"])
        assert chess.Move.from_uci(r["best"]) in board.legal_moves
        assert chess.Move.from_uci(r["played"]) in board.legal_moves
        assert r["loss"] == max(0, r["cp_best"] - r["cp_played"])
        assert r["agree_final"] == (r["played"] == r["best"])
        evals = {int(k): v for k, v in json.loads(r["eval_by_depth"]).items()}
        assert r["depth_reached"] == max(evals) >= 5
        assert sorted(evals) == list(range(1, max(evals) + 1))
        assert set(json.loads(r["best_by_depth"])) == set(json.loads(r["eval_by_depth"]))
        assert r["tc"] == "180+0" and r["perf"] == "blitz" and r["opponent_title"] == "BOT"
    # 7. Be2?? allows mate in one: bot-POV cp_played is (almost) -MATE_CP, a huge loss
    last_white = white_rows[-1]
    assert last_white["played"] == "c4e2"
    assert last_white["cp_played"] == -(MATE_CP - 1)
    assert last_white["loss"] > 1000
    assert last_white["clock_ms"] == 174_000  # bot's clock before the move
    # Black finds the mate: bot-POV +MATE_CP - 1, agreement with the final best move
    mate = black_rows[-1]
    assert mate["played"] == "d4f3" and mate["best"] == "d4f3"
    assert mate["cp_best"] == MATE_CP - 1 and mate["loss"] == 0
    assert white_rows[0]["result_for_bot"] == 0.0 and black_rows[0]["result_for_bot"] == 1.0
    assert white_rows[0]["opponent"] == "BlackBot" and white_rows[0]["bot_rating"] == 1500
