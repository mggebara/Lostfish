"""lostfish.features: shape, symmetry, and speed."""

from __future__ import annotations

import random
import time

import chess
import numpy as np
import pytest

from lostfish.features import FEATURE_NAMES, N_FEATURES, extract

IDX = {n: i for i, n in enumerate(FEATURE_NAMES)}
DIFFS = ["material_diff", "mobility_diff", "depth_gap"]
SIGNED = DIFFS + [n for n in FEATURE_NAMES if n.startswith("imb_")] + ["in_check"]
PAIRS = [
    (n, n[: -len("_us")] + "_them") for n in FEATURE_NAMES if n.endswith("_us")
]  # (x_us, x_them)


def random_positions(n: int, seed: int = 7) -> list[chess.Board]:
    rng = random.Random(seed)
    out: list[chess.Board] = []
    while len(out) < n:
        b = chess.Board()
        for _ in range(rng.randint(4, 90)):
            moves = list(b.legal_moves)
            if not moves:
                break
            b.push(rng.choice(moves))
        if not b.is_game_over():
            out.append(b.copy(stack=False))
    return out


@pytest.fixture(scope="module")
def positions() -> list[chess.Board]:
    return random_positions(200)


def test_shape_and_dtype() -> None:
    v = extract(chess.Board(), chess.WHITE)
    assert v.shape == (N_FEATURES,)
    assert v.dtype == np.float32
    assert len(set(FEATURE_NAMES)) == N_FEATURES
    assert all(pair[1] in IDX for pair in PAIRS)


def test_start_position_diffs_are_zero() -> None:
    for pov in chess.COLORS:
        v = extract(chess.Board(), pov)
        for name in SIGNED:
            assert v[IDX[name]] == 0, name
        for us, them in PAIRS:
            assert v[IDX[us]] == v[IDX[them]], us
        assert v[IDX["phase"]] == pytest.approx(1.0)
        assert v[IDX["castling_rights_us"]] == 2


def test_mirror_is_exact(positions: list[chess.Board]) -> None:
    for b in positions:
        for pov in chess.COLORS:
            np.testing.assert_array_equal(extract(b, pov), extract(b.mirror(), not pov), b.fen())


def test_pov_flip_mirrors_signed_features(positions: list[chess.Board]) -> None:
    for b in positions:
        w, k = extract(b, chess.WHITE), extract(b, chess.BLACK)
        for name in SIGNED:
            assert w[IDX[name]] == -k[IDX[name]], (name, b.fen())
        for us, them in PAIRS:
            assert w[IDX[us]] == k[IDX[them]], (us, b.fen())


def test_known_values() -> None:
    # W: Ke1 Qd1 Pa2 Pb2 Pe4; B: Ke8 Ra8 Pa7 Pe5 -> e4/e5 is a locked ram; a7 stops a2 and b2
    v = extract(chess.Board("r3k3/p7/8/4p3/4P3/8/PP6/3QK3 w - - 0 1"), chess.WHITE)
    assert v[IDX["material_diff"]] == (9 + 3) - (5 + 2)
    assert v[IDX["pawn_rams"]] == 1
    assert v[IDX["locked_pawn_pairs"]] == 1
    assert v[IDX["passed_pawns_us"]] == 0
    assert v[IDX["half_open_files_us"]] == 0
    assert v[IDX["half_open_files_them"]] == 1  # b-file: white pawn only
    passers = extract(chess.Board("4k3/8/8/8/8/8/P6p/4K3 w - - 0 1"), chess.WHITE)
    assert passers[IDX["passed_pawns_us"]] == 1
    assert passers[IDX["passed_pawns_them"]] == 1
    blockade = extract(chess.Board("4k3/8/8/8/8/n7/P7/4K3 w - - 0 1"), chess.WHITE)
    assert blockade[IDX["blockaded_passers_us"]] == 1
    assert blockade[IDX["imb_minor_vs_pawns"]] == 0  # minor vs one pawn is not the class
    loose = extract(chess.Board("4k3/8/8/3n4/8/8/8/3R1K2 w - - 0 1"), chess.WHITE)
    assert loose[IDX["hanging_them"]] == 1  # Rd1 hits the undefended Nd5
    assert loose[IDX["hanging_us"]] == 0
    guarded = extract(chess.Board("4k3/8/4p3/3n4/8/8/8/3R1K2 w - - 0 1"), chess.WHITE)
    assert guarded[IDX["hanging_them"]] == 0  # e6 pawn defends d5
    gap = extract(chess.Board(), chess.WHITE, eval_deep=120, eval_shallow=20)
    assert gap[IDX["depth_gap"]] == 100
    exchange = extract(chess.Board("4k3/8/8/8/8/8/8/R3K1n1 w - - 0 1"), chess.WHITE)
    assert exchange[IDX["imb_exchange_up"]] == 1


def test_checks_and_in_check() -> None:
    v = extract(chess.Board("4k3/8/8/8/8/8/8/R3K3 w - - 0 1"), chess.WHITE)
    assert v[IDX["checks_available_us"]] == 1  # Ra8+
    assert v[IDX["checks_available_them"]] == 0
    checked = chess.Board("4k3/8/8/8/8/8/8/4R1K1 b - - 0 1")
    assert extract(checked, chess.BLACK)[IDX["in_check"]] == 1
    assert extract(checked, chess.WHITE)[IDX["in_check"]] == -1


def test_does_not_mutate_board(positions: list[chess.Board]) -> None:
    for b in positions[:20]:
        fen = b.fen()
        extract(b, chess.WHITE)
        assert b.fen() == fen


def test_speed_under_1ms(positions: list[chess.Board]) -> None:
    for b in positions[:10]:
        extract(b, b.turn)  # warm up
    t0 = time.perf_counter()
    for b in positions:
        extract(b, b.turn, eval_deep=30, eval_shallow=10)
    avg_ms = (time.perf_counter() - t0) / len(positions) * 1000
    assert avg_ms < 1.0, f"{avg_ms:.3f} ms per position"
