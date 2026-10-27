"""Stream positions with Stockfish multi-PV evals out of the Lichess evaluation database (docket step 2).

    python -m mining.lichess_eval --n 2000000 --out data/lichess_eval/positions.parquet

`lichess_db_eval.jsonl.zst` (~22 GB compressed, >100 M positions) is streamed and decompressed on the fly
and reading stops after `--n` qualifying positions, so only the prefix is downloaded. One record per FEN:
`{"fen": ..., "evals": [{"pvs": [{"cp"|"mate", "line"}, ...], "knodes", "depth"}, ...]}` with evals from
White's point of view. The deepest eval is kept when it has at least `--min-depth` and `--min-pvs` lines.

Output columns (centipawns from the side to move, mates clipped to +-3000 like mining/victim_errors.py):
fen (normalised), stm, best, cp_best, ref_moves, ref_cps (the PVs' first moves and evals, best first),
n_pvs, depth, knodes, pieces. `ref_moves`/`ref_cps` feed mining/cheap_labels.py directly.
"""

from __future__ import annotations

import argparse
import io
import json
import sys
import time
from pathlib import Path
from typing import Any

import chess
import pandas as pd

URL = "https://database.lichess.org/lichess_db_eval.jsonl.zst"
CP_CLIP = 3000


def _log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def pv_cp_stm(pv: dict[str, Any], white_to_move: bool) -> int | None:
    """A PV's score as centipawns for the side to move; None when the record carries neither cp nor mate."""
    if "cp" in pv:
        cp = int(pv["cp"])
    elif "mate" in pv:
        cp = CP_CLIP if int(pv["mate"]) > 0 else -CP_CLIP
    else:
        return None
    cp = max(-CP_CLIP, min(CP_CLIP, cp))
    return cp if white_to_move else -cp


def parse_record(rec: dict[str, Any], *, min_depth: int, min_pvs: int) -> dict[str, Any] | None:
    """One output row from one database record, or None when no eval qualifies or the FEN is unusable."""
    evals = [e for e in rec.get("evals", []) if int(e.get("depth", 0)) >= min_depth]
    evals = [e for e in evals if len(e.get("pvs", [])) >= min_pvs]
    if not evals:
        return None
    ev = max(evals, key=lambda e: (int(e.get("depth", 0)), int(e.get("knodes", 0))))
    try:
        board = chess.Board(rec["fen"])
    except ValueError:
        return None
    if not board.is_valid() or board.is_game_over():
        return None
    moves: list[str] = []
    cps: list[int] = []
    for pv in ev["pvs"]:
        line = str(pv.get("line", "")).split()
        cp = pv_cp_stm(pv, board.turn == chess.WHITE)
        if not line or cp is None:
            continue
        try:
            mv = chess.Move.from_uci(line[0])
        except ValueError:
            continue
        if not board.is_legal(mv) or mv.uci() in moves:
            continue
        moves.append(mv.uci())
        cps.append(cp)
    if len(moves) < min_pvs:
        return None
    order = sorted(range(len(moves)), key=lambda i: -cps[i])  # best for the side to move first
    moves, cps = [moves[i] for i in order], [cps[i] for i in order]
    return {
        "fen": board.fen(),
        "stm": "w" if board.turn == chess.WHITE else "b",
        "best": moves[0],
        "cp_best": cps[0],
        "ref_moves": moves,
        "ref_cps": cps,
        "n_pvs": len(moves),
        "depth": int(ev.get("depth", 0)),
        "knodes": int(ev.get("knodes", 0)),
        "pieces": chess.popcount(board.occupied),
    }


def open_stream(url: str) -> io.TextIOBase:
    """Line iterator over the remote zst file (or a local path), decompressed on the fly."""
    import zstandard

    dctx = zstandard.ZstdDecompressor()
    if url.startswith(("http://", "https://")):
        import requests

        resp = requests.get(url, stream=True, timeout=120)
        resp.raise_for_status()
        raw: Any = resp.raw
    else:
        raw = open(url, "rb")  # noqa: SIM115 - closed through the TextIOWrapper
    return io.TextIOWrapper(dctx.stream_reader(raw), encoding="utf-8")


def collect(
    lines: Any,
    *,
    n: int,
    min_depth: int,
    min_pvs: int,
    out: Path | None = None,
    flush_every: int = 250_000,
    log_every: int = 100_000,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    seen = 0
    t0 = time.time()
    for line in lines:
        seen += 1
        line = line.strip()
        if not line:
            continue
        try:
            row = parse_record(json.loads(line), min_depth=min_depth, min_pvs=min_pvs)
        except (ValueError, KeyError, TypeError):
            row = None
        if row is None:
            continue
        rows.append(row)
        if len(rows) % log_every == 0:
            _log(f"{len(rows)} kept of {seen} records, {time.time() - t0:.0f} s")
        if out is not None and flush_every and len(rows) % flush_every == 0:
            pd.DataFrame(rows).to_parquet(out, index=False)
        if len(rows) >= n:
            break
    df = pd.DataFrame(rows)
    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(out, index=False)
    _log(f"done: {len(df)} positions kept of {seen} records in {time.time() - t0:.0f} s")
    return df


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--n", type=int, default=2_000_000)
    ap.add_argument("--out", required=True)
    ap.add_argument("--url", default=URL, help="remote .zst URL or a local .zst path")
    ap.add_argument("--min-depth", type=int, default=20)
    ap.add_argument("--min-pvs", type=int, default=2)
    args = ap.parse_args(argv)
    stream = open_stream(args.url)
    try:
        collect(
            stream, n=args.n, min_depth=args.min_depth, min_pvs=args.min_pvs, out=Path(args.out)
        )
    finally:
        stream.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
