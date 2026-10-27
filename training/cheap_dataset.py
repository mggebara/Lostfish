"""Turn raw-net (cheap) labels into the victim-error trainer's schema for pretraining (DECISIONS 2026-10-26).

    python -m training.cheap_dataset --positions data/lichess_eval/positions.parquet \
        --labels data/cheap_labels/lichess_eval.parquet --out data/victim_errors/cheap_lichess_t1.parquet

The trainer (`training/victim_error_model.py`) wants fen, best, cp_best, cp_after, loss, pieces, game_id, ply
and baseline_loss. Here the "victim move" is the net's top-policy move: cp_after = cp_best - raw_top_loss and
loss = max(0, raw_top_loss), both from the side to move. Rows whose raw-top loss is still unknown (censored
and not filled by mining/cheap_labels_fill.py) are dropped unless the censoring bound already proves a
blunder (`--keep-sure`, then loss = that bound). Each position is its own game_id, so the trainer's game split
is a position split. baseline_loss is 0 (no depth-10 Stockfish pass on this pool) and ply is 0.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BLUNDER_CP = 100


def build(positions: pd.DataFrame, labels: pd.DataFrame, *, keep_sure: bool = True) -> pd.DataFrame:
    pos = positions.drop_duplicates("fen", keep="first")
    df = pos.merge(labels, on="fen", how="inner")
    df = df[df["raw_top"].notna() & df["cp_best"].notna()].copy()
    loss = df["raw_top_loss"].to_numpy(dtype=float)
    known = ~np.isnan(loss)
    if keep_sure and "ref_cps" in df:
        worst = np.array([min(c) if len(c) else np.nan for c in df["ref_cps"]], dtype=float)
        bound = df["cp_best"].to_numpy(dtype=float) - worst
        sure = ~known & (bound >= BLUNDER_CP)
        loss = np.where(sure, bound, loss)
        known = known | sure
    df = df[known].copy()
    loss = loss[known]
    if "pieces" not in df:
        df["pieces"] = df["fen"].map(lambda f: sum(ch.isalpha() for ch in f.split()[0]))
    out = pd.DataFrame(
        {
            "source": "cheap",
            "game_id": [f"cheap:{i}" for i in range(len(df))],
            "round": "0",
            "ply": 0,
            "fen": df["fen"].to_numpy(),
            "victim_color": np.where(df["fen"].str.split().str[1] == "w", "white", "black"),
            "opponent": "lichess_eval",
            "result_for_victim": np.nan,
            "move": df["raw_top"].to_numpy(),
            "best": df["best"].to_numpy(),
            "cp_best": df["cp_best"].to_numpy(dtype=int),
            "cp_after": (df["cp_best"].to_numpy(dtype=float) - loss).round().astype(int),
            "loss": np.clip(loss, 0, 3000).round().astype(int),
            "baseline_move": None,
            "baseline_loss": 0,
            "pieces": df["pieces"].to_numpy(dtype=int),
            "nodes": 0,
            "baseline_depth": 0,
        }
    )
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--positions", required=True)
    ap.add_argument("--labels", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument(
        "--no-keep-sure",
        action="store_true",
        help="drop censored rows even when the bound proves a blunder",
    )
    args = ap.parse_args(argv)
    out = build(
        pd.read_parquet(args.positions),
        pd.read_parquet(args.labels),
        keep_sure=not args.no_keep_sure,
    )
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(args.out, index=False)
    rate = (out["loss"] >= BLUNDER_CP).mean()
    print(f"{len(out)} rows -> {args.out}; loss>={BLUNDER_CP}cp rate {100 * rate:.2f} %")
    return 0


if __name__ == "__main__":
    sys.exit(main())
