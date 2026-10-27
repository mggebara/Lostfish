"""Blind-spot pass 2: do the raw net's errors survive the victim's own search? (DECISIONS 2026-10-27)

    python scripts/raw_error_survival.py build --ref data/victim_errors/lc0-t1-n200_gpu_a.parquet \
        --labels data/cheap_labels/bt4_onpolicy_t1games.parquet --out data/cheap_labels/bt4_pass2_shortlist.parquet
    python -m mining.cheap_labels --inp data/cheap_labels/bt4_pass2_shortlist.parquet \
        --out data/cheap_labels/bt4_pass2_n1000.parquet --weights <BT4> --nodes 1000 --workers 3
    python -m mining.cheap_labels_fill --labels data/cheap_labels/bt4_pass2_n1000.parquet \
        --ref data/cheap_labels/bt4_pass2_shortlist.parquet
    python scripts/raw_error_survival.py report --shortlist data/cheap_labels/bt4_pass2_shortlist.parquet \
        --labels data/cheap_labels/bt4_pass2_n1000.parquet

`build` keeps every reference row of the flagged FENs (pass-1 raw-top loss >= 100 cp) plus `--control` random
FENs whose raw top is a known non-blunder, tagged in a `group` column. `report` gives, per group, how often
the searched move still loses >= 100 cp (Wilson 95 % interval), how often the search keeps the raw net's move,
and how many rows are still censored. The control group's rate is the victim's base blunder rate at that
node count; the flagged group's rate is the survival rate of the raw net's errors.
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BLUNDER_CP = 100


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float, float]:
    if n == 0:
        return math.nan, math.nan, math.nan
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return p, c - h, c + h


def build(ref: pd.DataFrame, labels: pd.DataFrame, *, control: int, seed: int = 1) -> pd.DataFrame:
    lab = labels.drop_duplicates("fen").set_index("fen")
    loss = lab["raw_top_loss"].astype(float)
    flagged = set(loss.index[loss >= BLUNDER_CP])
    clean = loss.index[loss < BLUNDER_CP].to_series()  # NaN (censored) is neither
    ctrl = set(clean.sample(n=min(control, len(clean)), random_state=seed))
    out = ref[ref["fen"].isin(flagged | ctrl)].copy()
    out["group"] = np.where(out["fen"].isin(flagged), "flagged", "control")
    out["raw_top_pass1"] = out["fen"].map(lab["raw_top"])
    return out.reset_index(drop=True)


def report(shortlist: pd.DataFrame, labels: pd.DataFrame) -> pd.DataFrame:
    s = shortlist.drop_duplicates("fen")[["fen", "group", "raw_top_pass1"]]
    lab = labels.drop_duplicates("fen")[["fen", "raw_top", "raw_top_loss"]]
    d = s.merge(lab, on="fen", how="left")
    rows = []
    for g, part in d.groupby("group"):
        loss = part["raw_top_loss"].astype(float)
        known = loss.notna()
        k, n = int((loss[known] >= BLUNDER_CP).sum()), int(known.sum())
        p, lo, hi = wilson(k, n)
        rows.append(
            {
                "group": g,
                "positions": len(part),
                "known": n,
                "censored": len(part) - n,
                "search_blunders": k,
                "search_blunder_pct": 100 * p,
                "ci_lo": 100 * lo,
                "ci_hi": 100 * hi,
                "keeps_raw_move_pct": 100
                * float((part["raw_top"] == part["raw_top_pass1"]).mean()),
            }
        )
    return pd.DataFrame(rows)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--ref", required=True)
    b.add_argument("--labels", required=True)
    b.add_argument("--out", required=True)
    b.add_argument("--control", type=int, default=3000)
    b.add_argument("--seed", type=int, default=1)
    r = sub.add_parser("report")
    r.add_argument("--shortlist", required=True)
    r.add_argument("--labels", required=True)
    args = ap.parse_args(argv)
    if args.cmd == "build":
        out = build(
            pd.read_parquet(args.ref),
            pd.read_parquet(args.labels),
            control=args.control,
            seed=args.seed,
        )
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        out.to_parquet(args.out, index=False)
        print(out.drop_duplicates("fen")["group"].value_counts().to_dict(), "->", args.out)
    else:
        rep = report(pd.read_parquet(args.shortlist), pd.read_parquet(args.labels))
        print(rep.to_string(index=False, float_format=lambda x: f"{x:.2f}"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
