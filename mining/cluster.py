"""Position-type clusters with per-cluster blunder uplift (the bot's weak spots).

    python -m mining.cluster --bots all --k 8 --blunder-cp 100 --min-cluster 30

Features (`lostfish.features`) for every annotated position: pov = the bot (the side to move),
eval_deep = cp_best, eval_shallow = the eval at the smallest completed depth >= 4. Features are
standardised as raw / std (no centring: Euclidean distances equal z-score distances and the
contract only carries `scale`), clustered with numpy k-means (k-means++, several restarts), and
each cluster's blunder rate is compared with the bot's base rate: uplift = rate / base.
A blunder is `max(0, clip(cp_best) - clip(cp_played)) >= blunder_cp` with evals clipped to
±clip_cp, so converting mate-in-3 into +900 is not a 31000 cp "blunder".
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from typing import Any

import chess
import numpy as np
import pandas as pd

from lostfish.features import FEATURE_NAMES, N_FEATURES, extract
from mining.common import (
    annot_path,
    clusters_path,
    depth_dict_from_json,
    mining_config,
    select_bots,
    write_json,
)

SHALLOW_MIN_DEPTH = 4


def log(msg: str) -> None:
    print(f"[cluster {datetime.now():%H:%M:%S}] {msg}", flush=True)


def shallow_eval(eval_by_depth: Any, min_depth: int = SHALLOW_MIN_DEPTH) -> int | None:
    evals = depth_dict_from_json(eval_by_depth)
    depths = [d for d in evals if d >= min_depth]
    return int(evals[min(depths)]) if depths else None


def frame_features(df: pd.DataFrame) -> np.ndarray:
    """[n, N_FEATURES] float32 feature matrix for an annotation frame."""
    out = np.zeros((len(df), N_FEATURES), dtype=np.float32)
    cols = zip(df["fen"], df["bot_color"], df["cp_best"], df["eval_by_depth"], strict=True)
    for i, (fen, color, cp_best, ebd) in enumerate(cols):
        board = chess.Board(fen)
        pov = chess.WHITE if color == "white" else chess.BLACK
        out[i] = extract(board, pov, eval_deep=int(cp_best), eval_shallow=shallow_eval(ebd))
    return out


def blunder_mask(df: pd.DataFrame, blunder_cp: int, clip_cp: int) -> np.ndarray:
    best = df["cp_best"].clip(-clip_cp, clip_cp).to_numpy(dtype=float)
    played = df["cp_played"].clip(-clip_cp, clip_cp).to_numpy(dtype=float)
    return np.maximum(0.0, best - played) >= blunder_cp


# ---------------------------------------------------------------------------------------------
# k-means (numpy only)


def _sq_dists(x: np.ndarray, c: np.ndarray, x2: np.ndarray) -> np.ndarray:
    return np.maximum(x2[:, None] - 2.0 * x @ c.T + (c * c).sum(1)[None, :], 0.0)


def _kmeanspp(x: np.ndarray, k: int, rng: np.random.Generator, x2: np.ndarray) -> np.ndarray:
    centers = [x[rng.integers(len(x))]]
    d2 = _sq_dists(x, np.array(centers), x2)[:, 0]
    for _ in range(1, k):
        total = d2.sum()
        idx = rng.choice(len(x), p=d2 / total) if total > 0 else rng.integers(len(x))
        centers.append(x[idx])
        d2 = np.minimum(d2, _sq_dists(x, x[idx : idx + 1], x2)[:, 0])
    return np.array(centers)


def kmeans(
    x: np.ndarray, k: int, *, n_init: int = 8, max_iter: int = 100, seed: int = 0
) -> tuple[np.ndarray, np.ndarray, float]:
    """Lloyd's k-means with k-means++ init; returns (centroids, labels, inertia) of the best run."""
    x = np.asarray(x, dtype=np.float64)
    k = max(1, min(k, len(x)))
    rng = np.random.default_rng(seed)
    x2 = (x * x).sum(1)
    best: tuple[np.ndarray, np.ndarray, float] | None = None
    for _ in range(n_init):
        c = _kmeanspp(x, k, rng, x2)
        labels = np.full(len(x), -1)
        for _ in range(max_iter):
            d = _sq_dists(x, c, x2)
            new = d.argmin(1)
            if np.array_equal(new, labels):
                break
            labels = new
            for j in range(k):
                members = labels == j
                if members.any():
                    c[j] = x[members].mean(0)
                else:  # empty cluster: move it to the worst-fit point
                    far = d[np.arange(len(x)), labels].argmax()
                    c[j] = x[far]
        inertia = float(_sq_dists(x, c, x2)[np.arange(len(x)), labels].sum())
        if best is None or inertia < best[2]:
            best = (c.copy(), labels.copy(), inertia)
    assert best is not None
    return best


def label_for(offset: np.ndarray, names: list[str], top: int = 3, min_abs: float = 0.4) -> str:
    """Human label from the most extreme standardised offsets from the overall mean."""
    order = np.argsort(-np.abs(offset))[:top]
    parts = [
        f"{'high' if offset[j] > 0 else 'low'} {names[j]}"
        for j in order
        if abs(offset[j]) >= min_abs
    ]
    return ", ".join(parts) if parts else "typical"


def cluster_features(
    x: np.ndarray,
    blunders: np.ndarray,
    *,
    k: int = 8,
    min_cluster: int = 30,
    n_init: int = 8,
    seed: int = 0,
    names: list[str] | None = None,
) -> dict[str, Any]:
    """Cluster a feature matrix and score each cluster's blunder rate against the base rate."""
    names = names or FEATURE_NAMES
    x = np.asarray(x, dtype=np.float64)
    blunders = np.asarray(blunders, dtype=bool)
    mean = x.mean(0)
    scale = x.std(0)
    scale[scale < 1e-6] = 1.0
    z = x / scale
    centroids, labels, inertia = kmeans(z, k, n_init=n_init, seed=seed)
    base = float(blunders.mean()) if len(blunders) else 0.0
    clusters = []
    for j in range(len(centroids)):
        m = labels == j
        n = int(m.sum())
        if n == 0:
            continue
        rate = float(blunders[m].mean())
        se = np.sqrt(max(base * (1 - base), 1e-12) / n)
        clusters.append(
            {
                "id": j,
                "label": label_for(centroids[j] - mean / scale, names),
                "n": n,
                "n_blunders": int(blunders[m].sum()),
                "blunder_rate": rate,
                "uplift": rate / base if base > 0 else 1.0,
                "z": float((rate - base) / se),
                "kept": n >= min_cluster,
                "centroid": centroids[j].round(5).tolist(),
                "centroid_raw": (centroids[j] * scale).round(4).tolist(),
            }
        )
    clusters.sort(key=lambda c: (-c["kept"], -c["uplift"]))
    return {
        "feature_names": list(names),
        "n_positions": len(x),
        "k": len(centroids),
        "min_cluster": min_cluster,
        "base_blunder_rate": base,
        "n_blunders": int(blunders.sum()),
        "inertia": inertia,
        "mean": mean.round(5).tolist(),
        "scale": scale.round(5).tolist(),
        "labels": labels,
        "clusters": clusters,
    }


def cluster_frame(
    df: pd.DataFrame,
    *,
    k: int = 8,
    blunder_cp: int = 100,
    clip_cp: int = 1000,
    min_cluster: int = 30,
    n_init: int = 8,
    seed: int = 0,
    features: np.ndarray | None = None,
) -> dict[str, Any]:
    x = frame_features(df) if features is None else features
    res = cluster_features(
        x,
        blunder_mask(df, blunder_cp, clip_cp),
        k=k,
        min_cluster=min_cluster,
        n_init=n_init,
        seed=seed,
    )
    res.update({"blunder_cp": blunder_cp, "clip_cp": clip_cp, "seed": seed})
    return res


def main(argv: list[str] | None = None) -> int:
    cfg = mining_config()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--bots", default="all")
    ap.add_argument("--k", type=int, default=int(cfg["k"]))
    ap.add_argument("--blunder-cp", type=int, default=int(cfg["blunder_cp"]))
    ap.add_argument("--clip-cp", type=int, default=int(cfg["clip_cp"]))
    ap.add_argument("--min-cluster", type=int, default=int(cfg["min_cluster"]))
    ap.add_argument("--n-init", type=int, default=8)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args(argv)
    for bot in select_bots(args.bots, "annot"):
        path = annot_path(bot)
        if not path.exists():
            log(f"{bot}: no annotations, skipping")
            continue
        df = pd.read_parquet(path)
        if df.empty:
            continue
        res = cluster_frame(
            df,
            k=args.k,
            blunder_cp=args.blunder_cp,
            clip_cp=args.clip_cp,
            min_cluster=args.min_cluster,
            n_init=args.n_init,
            seed=args.seed,
        )
        res.pop("labels")
        res = {"bot": bot, "built_at": datetime.now().isoformat(timespec="seconds"), **res}
        write_json(clusters_path(bot), res)
        top = next((c for c in res["clusters"] if c["kept"]), None)
        log(
            f"{bot}: {res['n_positions']} pos, base blunder rate {res['base_blunder_rate']:.3f}"
            + (f"; top cluster x{top['uplift']:.2f} (n={top['n']}): {top['label']}" if top else "")
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
