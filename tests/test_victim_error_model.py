import chess
import numpy as np
import pytest

torch = pytest.importorskip("torch")
from training.victim_error_model import PLANES, VictimErrorNet, auc, encode


def test_encode_shape_and_flip_symmetry():
    b = chess.Board("r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3")
    x = encode(b)
    assert x.shape == (PLANES, 8, 8) and x[:12].sum() == 32
    m = b.mirror()  # colours swapped, board flipped: identical from the side to move's view
    assert np.array_equal(encode(m), x)


def test_auc_and_forward():
    assert auc(np.array([0.1, 0.4, 0.35, 0.8]), np.array([0, 0, 1, 1])) == 0.75
    net = VictimErrorNet(8, 1, 16).eval()
    out = net(torch.zeros(2, PLANES, 8, 8))
    assert out.shape == (2, 2)
