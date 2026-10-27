"""Off-policy (Lichess) raw-net labels next to the on-policy ones (DECISIONS 2026-10-26 docket, step 2).

    .venv/bin/python scripts/cheap_labels_offpolicy_report.py \
        data/lichess_eval/positions.parquet data/cheap_labels/lichess_eval.parquet \
        data/victim_errors/lc0-t1-n200_gpu_a.parquet data/cheap_labels/lc0-t1-n200_gpu_a.parquet

For each pool: how often the raw top move is Stockfish's best, the raw-top cp-loss "blunder" rate as an
interval (uncensored losses are exact; a censored row counts as a blunder when even the worst listed PV is
>= 100 cp below best, and as unknown otherwise), and the position mix (side to move, piece-count phase,
|cp_best|) so the two distributions can be compared before any pretraining.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BLUNDER_CP = 100
PHASES = [
    ("opening (>=28 pieces)", 28, 33),
    ("middlegame (16-27)", 16, 27),
    ("endgame (<=15)", 0, 15),
]


def wilson(k: int, n: int) -> tuple[float, float, float]:
    if n == 0:
        return math.nan, math.nan, math.nan
    p, z = k / n, 1.96
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return p, c - h, c + h


def pct(k: int, n: int) -> str:
    p, lo, hi = wilson(k, n)
    return "n/a" if math.isnan(p) else f"{100 * p:.2f} [{100 * lo:.2f}, {100 * hi:.2f}]"


def worst_ref_cp(df: pd.DataFrame) -> np.ndarray:
    """The lowest reference eval the input knew for each row (multi-PV list, else the played move)."""
    if "ref_cps" in df:
        return np.array([min(c) if len(c) else np.nan for c in df["ref_cps"]], dtype=float)
    return df["cp_after"].to_numpy(dtype=float)


def summarise(name: str, pos: pd.DataFrame, lab: pd.DataFrame, meta: Path) -> dict[str, float]:
    df = pos.drop_duplicates("fen").merge(lab, on="fen", how="inner")
    df = df[df["raw_top"].notna()].copy()
    n = len(df)
    print(f"\n## {name}: {n} positions")
    if meta.exists():
        m = json.loads(meta.read_text())
        print(
            f"throughput {m.get('pos_per_s')} pos/s, {m.get('workers')} workers, {m.get('wall_s')} s"
        )
    is_best = (df["raw_top"] == df["best"]).to_numpy()
    print(f"raw top == Stockfish best: {pct(int(is_best.sum()), n)} %")
    loss = df["raw_top_loss"].to_numpy(dtype=float)
    cens = np.isnan(loss)
    bound = df["cp_best"].to_numpy(dtype=float) - worst_ref_cp(
        df
    )  # loss is at least this when censored
    sure = (~cens & (loss >= BLUNDER_CP)) | (cens & (bound >= BLUNDER_CP))
    unknown = cens & ~(bound >= BLUNDER_CP)
    lo, hi = int(sure.sum()), int(sure.sum() + unknown.sum())
    print(
        f"raw-top blunder rate (loss >= {BLUNDER_CP} cp): between {100 * lo / n:.2f} % and "
        f"{100 * hi / n:.2f} % ({100 * cens.mean():.1f} % of rows censored, "
        f"{100 * unknown.mean():.1f} % undecidable)"
    )
    print(f"side to move white: {100 * (df['fen'].str.split().str[1] == 'w').mean():.1f} %")
    pieces = df["pieces"].to_numpy()
    for label, a, b in PHASES:
        mask = (pieces >= a) & (pieces <= b)
        print(
            f"  {label}: {100 * mask.mean():.1f} % of rows, raw top == best "
            f"{pct(int(is_best[mask].sum()), int(mask.sum()))} %, "
            f"sure-blunder {100 * sure[mask].mean():.2f} %"
        )
    abs_cp = np.abs(df["cp_best"].to_numpy(dtype=float))
    print(
        f"|cp_best| median {np.median(abs_cp):.0f}, mean {abs_cp.mean():.0f}; "
        f"share within 100 cp of equal {100 * (abs_cp <= 100).mean():.1f} %"
    )
    return {"n": n, "is_best": is_best.mean(), "blunder_lo": lo / n, "blunder_hi": hi / n}


def main(argv: list[str]) -> int:
    off_pos, off_lab, on_pos, on_lab = (pd.read_parquet(p) for p in argv[:4])
    summarise(
        "off-policy: Lichess evaluation DB", off_pos, off_lab, Path(argv[1]).with_suffix(".json")
    )
    on_pos = on_pos.assign(cp_after=on_pos["cp_after"])
    summarise(
        "on-policy: control vs lc0@200 games", on_pos, on_lab, Path(argv[3]).with_suffix(".json")
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
