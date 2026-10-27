"""Re-price moves with a deeper Stockfish than the 100k reference (DECISIONS 2026-10-27, pass-2 caveat).

    python scripts/deep_recheck.py --inp data/cheap_labels/deep_sample.parquet \
        --out data/cheap_labels/deep_recheck.parquet --nodes 1000000 --workers 4

Input rows: fen, move, group, loss_ref (the move's loss against the 100k reference). For each row the root is
searched at --nodes (mover's POV) and so is the position after `move`; loss_deep = clip(cp_root - cp_after).
The summary says, per group, what share of the reference losses >= 100 cp still hold at depth: where the
victim is as strong as the 100k reference, a "loss" may be the reference's mistake rather than the victim's.
"""

from __future__ import annotations

import argparse
import multiprocessing as mp
import sys
import time
from pathlib import Path
from typing import Any

import chess
import chess.engine
import pandas as pd

from mining.common import mining_config, open_engine
from mining.victim_errors import _clip, _search

BLUNDER_CP = 100
Row = tuple[str, str]  # fen, move


def price(engine: Any, fen: str, move: str, nodes: int) -> tuple[int, int, int]:
    board = chess.Board(fen)
    limit = chess.engine.Limit(nodes=nodes)
    cp_root, _ = _search(engine, board, limit, board.turn)
    child = board.copy(stack=False)
    child.push(chess.Move.from_uci(move))
    cp_after, _ = _search(engine, child, limit, board.turn)
    return int(cp_root), int(cp_after), _clip(cp_root - cp_after)


def summarise(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for g, part in df.groupby("group"):
        ref_bl = part["loss_ref"] >= BLUNDER_CP
        held = (
            (part.loc[ref_bl, "loss_deep"] >= BLUNDER_CP).mean() if ref_bl.any() else float("nan")
        )
        rows.append(
            {
                "group": g,
                "n": len(part),
                "ref_blunders": int(ref_bl.sum()),
                "held_at_depth_pct": 100 * float(held),
                "median_loss_ref": float(part["loss_ref"].median()),
                "median_loss_deep": float(part["loss_deep"].median()),
                "deep_blunder_pct": 100 * float((part["loss_deep"] >= BLUNDER_CP).mean()),
            }
        )
    return pd.DataFrame(rows)


_ENGINE: Any = None
_NODES = 0


def _init_worker(stockfish: str, hash_mb: int, nodes: int) -> None:
    global _ENGINE, _NODES
    _ENGINE = open_engine(stockfish, hash_mb=hash_mb)
    _NODES = nodes


def _work(rows: list[Row]) -> list[tuple[str, str, int, int, int]]:
    out = []
    for fen, move in rows:
        try:
            out.append((fen, move, *price(_ENGINE, fen, move, _NODES)))
        except (chess.engine.EngineError, ValueError) as exc:
            print(f"skipped {fen} {move}: {exc!r}", file=sys.stderr, flush=True)
    return out


def main(argv: list[str] | None = None) -> int:
    cfg = mining_config()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--inp", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--nodes", type=int, default=1_000_000)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--chunk", type=int, default=10)
    ap.add_argument("--stockfish", default=str(cfg["stockfish"]))
    ap.add_argument("--hash-mb", type=int, default=64)
    args = ap.parse_args(argv)
    df = pd.read_parquet(args.inp)
    rows = list(zip(df["fen"], df["move"], strict=True))
    chunks = [rows[i : i + args.chunk] for i in range(0, len(rows), args.chunk)]
    t0 = time.time()
    got: list[tuple[str, str, int, int, int]] = []
    ctx = mp.get_context("spawn")
    with ctx.Pool(
        args.workers, initializer=_init_worker, initargs=(args.stockfish, args.hash_mb, args.nodes)
    ) as pool:
        for i, res in enumerate(pool.imap_unordered(_work, chunks), 1):
            got.extend(res)
            if i % 20 == 0 or i == len(chunks):
                el = time.time() - t0
                print(
                    f"{len(got)}/{len(rows)} priced, {len(got) / el:.2f}/s, {el:.0f} s", flush=True
                )
    deep = pd.DataFrame(got, columns=["fen", "move", "cp_root_deep", "cp_after_deep", "loss_deep"])
    out = df.merge(deep, on=["fen", "move"], how="inner")
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(args.out, index=False)
    print(summarise(out).to_string(index=False, float_format=lambda x: f"{x:.1f}"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
