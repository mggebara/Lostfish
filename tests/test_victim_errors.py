import chess

from mining.victim_errors import game_id, iter_victim_moves, victim_color

PGN = """[Event "Fastchess Tournament"]
[Site "?"]
[Round "7"]
[White "LostFish-v2-tol0"]
[Black "lc0-t1-n200"]
[Result "1-0"]

1. e4 {book} e5 {book} 2. Nf3 {+0.3/10} Nc6 {-0.2/1} 3. Bb5 {+0.4/10} a6 {-0.3/1} 1-0
"""


def test_iter_victim_moves_skips_book_and_picks_victim_colour():
    moves = iter_victim_moves(PGN, "lc0-t1-n200")
    assert [(ply, m.uci()) for ply, _, m in moves] == [(3, "b8c6"), (5, "a7a6")]
    assert moves[0][1].split()[1] == "b"  # black to move in the stored FEN
    assert iter_victim_moves(PGN, "nobody") == []


def test_game_id_and_colour():
    headers = {"Round": "7", "White": "LostFish-v2-tol0", "Black": "lc0-t1-n200"}
    assert victim_color(headers, "lc0-t1-n200") == chess.BLACK
    assert game_id("lc0_long_n200_control", headers, chess.BLACK) == "lc0_long_n200_control:7:b"
