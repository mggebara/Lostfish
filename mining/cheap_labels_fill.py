"""Fill censored raw-top losses with Stockfish so the raw-top cp-loss label is exact (docket step 1b).

    python -m mining.cheap_labels_fill --labels data/cheap_labels/lc0-t1-n200_gpu_a.parquet \
        --ref data/victim_errors/lc0-t1-n200_gpu_a.parquet --workers 3

mining/cheap_labels.py only knows the loss of the net's top move when that move is among the reference
moves (Stockfish's best or the move the victim played). For every other labelled FEN this searches the
position after `raw_top` with the reference's own Stockfish budget (`nodes` column, default 100000) from
the mover's point of view and sets raw_top_loss = cp_best - cp(after raw_top), raw_top_censored = False,
raw_top_loss_src = "sf" ("ref" for losses the references already gave). The labels parquet is rewritten in
place every --flush-every chunks, so an interrupted run resumes by rerunning the same command.
"""

from __future__ import annotations

import argparse
import multiprocessing as mp
import sys
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import chess
import chess.engine
import pandas as pd

from mining.common import mining_config, open_engine
from mining.victim_errors import _clip, _search

Task = tuple[str, str, int, int]  # fen, raw_top, cp_best, nodes


def _log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def pending(labels: pd.DataFrame, ref: pd.DataFrame, default_nodes: int = 100_000) -> list[Task]:
    """(fen, raw_top, cp_best, nodes) for every censored labelled FEN with a reference eval."""
    cols = ["fen", "cp_best"] + (["nodes"] if "nodes" in ref else [])
    first = ref.drop_duplicates("fen", keep="first")[cols]
    df = labels.merge(first, on="fen", how="inner")
    df = df[df["raw_top_censored"].astype(bool) & df["raw_top"].notna() & df["cp_best"].notna()]
    nodes = df["nodes"] if "nodes" in df else pd.Series(default_nodes, index=df.index)
    return list(
        zip(df["fen"], df["raw_top"], df["cp_best"].astype(int), nodes.astype(int), strict=True)
    )


def apply_fill(labels: pd.DataFrame, losses: Mapping[str, int]) -> pd.DataFrame:
    """Write the Stockfish losses into the label frame and mark their source."""
    out = labels.copy()
    if "raw_top_loss_src" not in out:
        out["raw_top_loss_src"] = None
        out.loc[~out["raw_top_censored"].astype(bool), "raw_top_loss_src"] = "ref"
    if losses:
        idx = out.index[out["fen"].isin(losses)]
        out.loc[idx, "raw_top_loss"] = [float(losses[f]) for f in out.loc[idx, "fen"]]
        out.loc[idx, "raw_top_censored"] = False
        out.loc[idx, "raw_top_loss_src"] = "sf"
    return out


def raw_top_loss(engine: Any, fen: str, raw_top: str, cp_best: int, nodes: int) -> int:
    board = chess.Board(fen)
    child = board.copy(stack=False)
    child.push(chess.Move.from_uci(raw_top))
    cp_after, _ = _search(engine, child, chess.engine.Limit(nodes=nodes), board.turn)
    return _clip(cp_best - cp_after)


_ENGINE: Any = None


def _init_worker(stockfish: str, hash_mb: int) -> None:
    global _ENGINE
    _ENGINE = open_engine(stockfish, hash_mb=hash_mb)


def _work(tasks: list[Task]) -> list[tuple[str, int]]:
    assert _ENGINE is not None
    out = []
    for fen, top, cp_best, nodes in tasks:
        try:
            out.append((fen, raw_top_loss(_ENGINE, fen, top, cp_best, nodes)))
        except (chess.engine.EngineError, ValueError) as exc:
            _log(f"skipped {fen}: {exc!r}")
    return out


def main(argv: list[str] | None = None) -> int:
    cfg = mining_config()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--labels", required=True)
    ap.add_argument("--ref", required=True, help="parquet with fen, cp_best (and nodes)")
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--chunk", type=int, default=50)
    ap.add_argument(
        "--flush-every", type=int, default=20, help="rewrite the parquet every N chunks"
    )
    ap.add_argument("--max", type=int, default=0)
    ap.add_argument("--stockfish", default=str(cfg["stockfish"]))
    ap.add_argument("--hash-mb", type=int, default=int(cfg["hash_mb"]))
    args = ap.parse_args(argv)

    path = Path(args.labels)
    labels = pd.read_parquet(path)
    tasks = pending(labels, pd.read_parquet(args.ref))
    if args.max:
        tasks = tasks[: args.max]
    chunks = [tasks[i : i + args.chunk] for i in range(0, len(tasks), args.chunk)]
    _log(f"{len(tasks)} censored rows to fill in {len(chunks)} chunks, workers={args.workers}")
    losses: dict[str, int] = {}
    t0 = time.time()

    def flush() -> None:
        tmp = path.with_suffix(".tmp.parquet")
        apply_fill(labels, losses).to_parquet(tmp, index=False)
        tmp.replace(path)

    ctx = mp.get_context("spawn")
    with ctx.Pool(
        args.workers, initializer=_init_worker, initargs=(args.stockfish, args.hash_mb)
    ) as pool:
        for i, res in enumerate(pool.imap_unordered(_work, chunks), 1):
            losses.update(res)
            if i % 10 == 0 or i == len(chunks):
                el = time.time() - t0
                _log(f"{len(losses)}/{len(tasks)} filled, {len(losses) / el:.1f}/s, {el:.0f} s")
            if args.flush_every and i % args.flush_every == 0:
                flush()
    flush()
    _log(f"done: {len(losses)} filled in {time.time() - t0:.0f} s -> {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
