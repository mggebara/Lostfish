"""mining.cluster on synthetic data (no engine, no network)."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from lostfish.features import N_FEATURES
from mining.cluster import (
    blunder_mask,
    cluster_features,
    cluster_frame,
    kmeans,
    shallow_eval,
)


def blobs(seed: int = 0) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    centers = np.array([[0.0, 0.0, 0.0], [10.0, 0.0, 0.0], [0.0, 10.0, 5.0]])
    sizes = [400, 300, 100]
    x = np.vstack([c + rng.normal(0, 0.5, (n, 3)) for c, n in zip(centers, sizes, strict=True)])
    truth = np.repeat(np.arange(3), sizes)
    rates = np.array([0.05, 0.05, 0.5])
    blunders = rng.random(len(x)) < rates[truth]
    return x, truth, blunders


def test_kmeans_recovers_blobs() -> None:
    x, truth, _ = blobs()
    centroids, labels, inertia = kmeans(x, 3, n_init=4, seed=1)
    assert centroids.shape == (3, 3)
    # each true blob maps to exactly one cluster
    for t in range(3):
        assert len(set(labels[truth == t])) == 1
    assert len(set(labels)) == 3
    again = kmeans(x, 3, n_init=4, seed=1)
    np.testing.assert_array_equal(again[1], labels)
    assert inertia == pytest.approx(again[2])


def test_uplift_identifies_weak_cluster() -> None:
    x, _truth, blunders = blobs()
    res = cluster_features(x, blunders, k=3, min_cluster=150, names=["a", "b", "c"], n_init=4)
    base = blunders.mean()
    assert res["base_blunder_rate"] == pytest.approx(base)
    weak = next(c for c in res["clusters"] if c["n"] == 100)
    assert weak["uplift"] == pytest.approx(weak["blunder_rate"] / base)
    assert weak["uplift"] > 2
    assert not weak["kept"]  # below min_cluster
    kept = [c for c in res["clusters"] if c["kept"]]
    assert [c["n"] for c in kept] and all(c["n"] >= 150 for c in kept)
    assert res["clusters"][: len(kept)] == kept  # kept clusters first, by uplift
    # centroids are in raw / scale units
    scale = np.array(res["scale"])
    for c in res["clusters"]:
        np.testing.assert_allclose(np.array(c["centroid"]) * scale, c["centroid_raw"], atol=1e-3)
    assert "b" in weak["label"] or "c" in weak["label"]


def test_blunder_mask_clips_mates() -> None:
    df = pd.DataFrame({"cp_best": [31990, 31990, 50, 0], "cp_played": [950, 800, -60, 0]})
    assert blunder_mask(df, 100, 1000).tolist() == [False, True, True, False]


def test_shallow_eval_uses_smallest_depth_at_least_4() -> None:
    assert shallow_eval(json.dumps({"1": 5, "4": 40, "6": 60})) == 40
    assert shallow_eval(json.dumps({"1": 5, "3": 30})) is None
    assert shallow_eval(None) is None


def test_cluster_frame_end_to_end() -> None:
    fens = [
        "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        "r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4",
        "8/5pk1/6p1/8/3R4/6P1/5PK1/1r6 w - - 0 40",
        "8/8/4k3/8/2p5/8/1P3K2/8 b - - 0 50",
    ] * 10
    df = pd.DataFrame(
        {
            "fen": fens,
            "bot_color": ["white", "white", "white", "black"] * 10,
            "cp_best": [20, 30, 0, -10] * 10,
            "cp_played": [20, -200, 0, -10] * 10,
            "eval_by_depth": [json.dumps({"4": 10, "8": 20})] * 40,
        }
    )
    res = cluster_frame(df, k=3, min_cluster=5, n_init=2)
    assert res["n_positions"] == 40
    assert len(res["scale"]) == N_FEATURES
    assert res["base_blunder_rate"] == pytest.approx(0.25)
    assert max(c["uplift"] for c in res["clusters"]) == pytest.approx(4.0)
