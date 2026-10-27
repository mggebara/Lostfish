"""Do raw-net labels predict the victim's real search blunders? (DECISIONS 2026-10-26 docket, step 1)

    .venv/bin/python scripts/cheap_labels_report.py data/victim_errors/lc0-t1-n200_gpu_a.parquet \
        data/cheap_labels/lc0-t1-n200_gpu_a.parquet

Joins the on-policy rows (search labels from mining/victim_errors.py) with the raw-net rows
(mining/cheap_labels.py) on fen and reports, per blunder definition, the AUC (Hanley-McNeil 95 % CI) and
precision in the top 3 % (Wilson 95 % CI) of each cheap predictor, next to the predictor-free baselines the
training script already uses. Higher score = more likely to blunder.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BLUNDER_CP = 100
BLUNDER_WP = 0.10
TOP_FRAC = 0.03


def win_prob(cp: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.power(10.0, -np.clip(cp, -3000, 3000) / 400.0))


def auc_ci(score: np.ndarray, y: np.ndarray) -> tuple[float, float, float]:
    """Rank AUC with the Hanley-McNeil standard error."""
    n1, n0 = int(y.sum()), int((1 - y).sum())
    if n1 == 0 or n0 == 0:
        return math.nan, math.nan, math.nan
    ranks = pd.Series(score).rank(method="average").to_numpy()
    a = (ranks[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)
    q1, q2 = a / (2 - a), 2 * a * a / (1 + a)
    se = math.sqrt((a * (1 - a) + (n1 - 1) * (q1 - a * a) + (n0 - 1) * (q2 - a * a)) / (n1 * n0))
    return a, a - 1.96 * se, a + 1.96 * se


def wilson(k: int, n: int) -> tuple[float, float, float]:
    if n == 0:
        return math.nan, math.nan, math.nan
    p, z = k / n, 1.96
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return p, c - h, c + h


def precision_at(score: np.ndarray, y: np.ndarray, frac: float) -> tuple[float, float, float, int]:
    k = max(1, math.ceil(frac * len(score)))
    top = np.argsort(-score, kind="stable")[:k]
    p, lo, hi = wilson(int(y[top].sum()), k)
    return p, lo, hi, k


def fmt(p: float, lo: float, hi: float, pct: bool = False) -> str:
    if math.isnan(p):
        return "n/a"
    s = 100 if pct else 1
    return f"{p * s:.1f} [{lo * s:.1f}, {hi * s:.1f}]" if pct else f"{p:.3f} [{lo:.3f}, {hi:.3f}]"


def main(argv: list[str]) -> int:
    on, cheap = pd.read_parquet(argv[0]), pd.read_parquet(argv[1])
    meta_path = Path(argv[1]).with_suffix(".json")
    df = on.merge(cheap, on="fen", how="inner")
    df = df[df["raw_top"].notna()].copy()
    print(f"rows joined: {len(df)} of {len(on)} on-policy rows ({len(cheap)} unique FENs labelled)")
    if meta_path.exists():
        m = json.loads(meta_path.read_text())
        print(
            f"throughput: {m.get('pos_per_s')} positions/s with {m.get('workers')} workers "
            f"({m.get('wall_s')} s wall, median {m.get('median_ms'):.1f} ms per position per process)"
        )
    agree = (df["raw_top"] == df["move"]).to_numpy()
    p, lo, hi = wilson(int(agree.sum()), len(df))
    print(f"raw top move == move played at 200 nodes: {fmt(p, lo, hi, pct=True)} %")
    isbest = (df["raw_top"] == df["best"]).to_numpy()
    p, lo, hi = wilson(int(isbest.sum()), len(df))
    print(f"raw top move == Stockfish best: {fmt(p, lo, hi, pct=True)} %")
    cens = df["raw_top_censored"].to_numpy().astype(bool)
    print(f"raw_top_loss known for {100 * (1 - cens.mean()):.1f} % of rows (censored otherwise)")

    dwp = win_prob(df["cp_best"].to_numpy()) - win_prob(df["cp_after"].to_numpy())
    labels = {
        f"dWP>={BLUNDER_WP}": (dwp >= BLUNDER_WP).astype(int),
        f"loss>={BLUNDER_CP}cp": (df["loss"].to_numpy() >= BLUNDER_CP).astype(int),
    }
    preds = {
        "policy miss (1 - p_best)": 1.0 - df["p_best"].to_numpy(),
        "raw top-move cp loss (uncensored rows)": df["raw_top_loss"].to_numpy(),
        "|raw Q - cp_best|": np.abs(df["raw_q_cp"].to_numpy() - df["cp_best"].to_numpy()),
        "raw top != played move": (~agree).astype(float),
        "baseline: depth-10 SF loss": df["baseline_loss"].to_numpy().astype(float),
        "baseline: |cp_best|": np.abs(df["cp_best"].to_numpy()).astype(float),
    }
    for lname, y in labels.items():
        base = y.mean()
        print(f"\n### label {lname}: rate {100 * base:.2f} % of {len(y)}\n")
        print("| predictor | n | AUC [95 %] | precision@3 % [95 %] | lift |")
        print("|---|---|---|---|---|")
        for pname, s in preds.items():
            ok = ~np.isnan(s)
            a, alo, ahi = auc_ci(s[ok], y[ok])
            pr, plo, phi, _k = precision_at(s[ok], y[ok], TOP_FRAC)
            lift = pr / y[ok].mean() if y[ok].mean() > 0 else math.nan
            print(
                f"| {pname} | {ok.sum()} | {fmt(a, alo, ahi)} | {fmt(pr, plo, phi, pct=True)} | {lift:.1f}x |"
            )
        # how the blunder rate splits by whether the net's top move was the move actually searched
        for name, mask in (("raw top == played", agree), ("raw top != played", ~agree)):
            p, lo, hi = wilson(int(y[mask].sum()), int(mask.sum()))
            print(f"\n{name}: blunder rate {fmt(p, lo, hi, pct=True)} % (n={mask.sum()})", end="")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
