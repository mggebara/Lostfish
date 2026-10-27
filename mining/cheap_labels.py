"""Cheap victim labels from the raw Lc0 net: one batch per position, no search (DECISIONS 2026-10-26 docket).

    python -m mining.cheap_labels --inp data/victim_errors/lc0-t1-n200_gpu_a.parquet \
        --out data/cheap_labels/lc0-t1-n200_gpu_a.parquet --profile profiles/lc0-t1-n200.json --workers 6

Input: a parquet with a `fen` column plus optional references, all centipawns from the side to move:
`best`/`cp_best` (reference best move and its eval), `move`/`cp_after` (a second move and its eval) and/or
`ref_moves`/`ref_cps` (lists, for multi-PV sources such as the Lichess evaluation database). Every unique
FEN is evaluated once with `Lc0PolicyProxy(nodes=--nodes)` (default 1: root policy and root Q straight from
the net; N > 1: the victim's own search, so raw_top is its bestmove-by-visits and q its search value); the
references of the first row with that FEN are used.

Output: one row per unique FEN with raw_top (the net's top-policy move), raw_top_p, p_best (policy mass
on `best`), raw_q_cp (root Q as centipawns, side to move), raw_top_loss (cp_best minus the reference eval
of raw_top; NaN when unknown), raw_top_censored (True when raw_top has no reference eval, so its loss is
only known to be at least the worst listed reference's), n_legal and ms (net time in its worker). A JSON
sidecar next to the output records throughput. `--resume` skips FENs already in the output.
"""

from __future__ import annotations

import argparse
import json
import math
import multiprocessing as mp
import sys
import time
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

import chess
import pandas as pd

from lostfish.opponent import Lc0PolicyProxy

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROFILE = ROOT / "profiles" / "lc0-t1-n200.json"
LABEL_COLS = ["raw_top", "raw_top_p", "p_best", "raw_q_cp", "raw_top_loss", "raw_top_censored"]


def _log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def _missing(x: Any) -> bool:
    return x is None or (isinstance(x, float) and math.isnan(x))


def reference_table(row: Mapping[str, Any]) -> dict[str, int]:
    """{uci: cp from the side to move} for every move the input row knows an eval for."""
    refs: dict[str, int] = {}
    best, cp_best = row.get("best"), row.get("cp_best")
    if not _missing(best) and not _missing(cp_best):
        refs[str(best)] = int(cp_best)
    move, cp_after = row.get("move"), row.get("cp_after")
    if not _missing(move) and not _missing(cp_after):
        refs.setdefault(str(move), int(cp_after))
    moves, cps = row.get("ref_moves"), row.get("ref_cps")
    if moves is not None and cps is not None and not _missing(moves) and not _missing(cps):
        for m, c in zip(list(moves), list(cps), strict=True):
            if not _missing(m) and not _missing(c):
                refs.setdefault(str(m), int(c))
    return refs


def cheap_label(
    policy: Mapping[str, float],
    q_cp: int | None,
    refs: Mapping[str, int],
    best: str | None,
) -> dict[str, Any]:
    """Raw-net label for one position (see the module docstring for the columns)."""
    nan = float("nan")
    if not policy:
        return dict.fromkeys(LABEL_COLS, nan) | {
            "raw_top": None,
            "raw_q_cp": q_cp,
            "raw_top_censored": True,
        }
    top = max(policy, key=policy.__getitem__)
    cp_best = refs.get(best) if best and not _missing(best) else None
    loss = float(cp_best - refs[top]) if cp_best is not None and top in refs else nan
    return {
        "raw_top": top,
        "raw_top_p": float(policy[top]),
        "p_best": float(policy.get(str(best), 0.0)) if cp_best is not None else nan,
        "raw_q_cp": q_cp,
        "raw_top_loss": loss,
        "raw_top_censored": bool(math.isnan(loss)),
    }


def evaluate_fens(proxy: Any, fens: Iterable[str]) -> list[dict[str, Any]]:
    """Raw policy and root Q for each FEN from a `Lc0PolicyProxy`-like object (duck-typed for tests)."""
    out: list[dict[str, Any]] = []
    for fen in fens:
        board = chess.Board(fen)
        n_legal = board.legal_moves.count()
        if n_legal == 0:
            out.append({"fen": fen, "policy": {}, "q_cp": None, "n_legal": 0, "ms": 0.0})
            continue
        t0 = time.perf_counter()
        policy = dict(proxy.root_policy(board))
        ms = (time.perf_counter() - t0) * 1000.0
        out.append(
            {"fen": fen, "policy": policy, "q_cp": proxy.last_eval_cp, "n_legal": n_legal, "ms": ms}
        )
    return out


def _make_proxy(lc0: str, weights: str, nodes: int = 1) -> Any:
    return Lc0PolicyProxy(lc0, weights, threads=1, nodes=nodes, name="cheap-labels")


_PROXY: Any = None


def _init_worker(lc0: str, weights: str, nodes: int = 1) -> None:
    global _PROXY
    _PROXY = _make_proxy(lc0, weights, nodes)


def _work(fens: list[str]) -> list[dict[str, Any]]:
    assert _PROXY is not None
    return evaluate_fens(_PROXY, fens)


def _rows(
    evals: Iterable[dict[str, Any]], refs_by_fen: Mapping[str, tuple[dict[str, int], Any]]
) -> list[dict]:
    rows = []
    for ev in evals:
        refs, best = refs_by_fen[ev["fen"]]
        best = None if _missing(best) else str(best)
        rows.append(
            {"fen": ev["fen"], **cheap_label(ev["policy"], ev["q_cp"], refs, best)}
            | {"n_legal": ev["n_legal"], "ms": ev["ms"]}
        )
    return rows


def run(
    df: pd.DataFrame,
    *,
    lc0: str,
    weights: str,
    out: Path,
    workers: int = 6,
    nodes: int = 1,
    chunk: int = 64,
    flush_every: int = 50,
    resume: bool = False,
    log_every: int = 20,
) -> pd.DataFrame:
    """Label every unique FEN of `df`; write `out` (parquet) and `<out>.json` (throughput); return the frame."""
    first = df.drop_duplicates("fen", keep="first")
    refs_by_fen = {r["fen"]: (reference_table(r), r.get("best")) for r in first.to_dict("records")}
    existing = pd.read_parquet(out) if resume and out.exists() else None
    done = set(existing["fen"]) if existing is not None else set()
    todo = [f for f in first["fen"] if f not in done]
    chunks = [todo[i : i + chunk] for i in range(0, len(todo), chunk)]
    _log(f"{len(df)} rows, {len(first)} unique FENs, {len(todo)} to evaluate, workers={workers}")
    rows: list[dict] = []
    t0 = time.time()

    def flush() -> pd.DataFrame:
        frames = [f for f in (existing, pd.DataFrame(rows)) if f is not None and len(f)]
        frame = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=["fen"])
        out.parent.mkdir(parents=True, exist_ok=True)
        frame.to_parquet(out, index=False)
        return frame

    def progress(i: int) -> None:
        n = len(rows)
        if n and (i % log_every == 0 or i == len(chunks)):
            el = time.time() - t0
            _log(f"{n}/{len(todo)} positions, {n / el:.0f} pos/s, {el:.0f} s")

    if workers <= 0:
        proxy = _make_proxy(lc0, weights, nodes)
        for i, ch in enumerate(chunks, 1):
            rows.extend(_rows(evaluate_fens(proxy, ch), refs_by_fen))
            progress(i)
            if flush_every and i % flush_every == 0:
                flush()
    else:
        ctx = mp.get_context("spawn")
        with ctx.Pool(workers, initializer=_init_worker, initargs=(lc0, weights, nodes)) as pool:
            for i, res in enumerate(pool.imap_unordered(_work, chunks), 1):
                rows.extend(_rows(res, refs_by_fen))
                progress(i)
                if flush_every and i % flush_every == 0:
                    flush()
    wall = time.time() - t0
    frame = flush()
    meta = {
        "positions": len(todo),
        "unique_fens": len(first),
        "rows_in": len(df),
        "workers": workers,
        "wall_s": round(wall, 1),
        "pos_per_s": round(len(todo) / wall, 1) if wall > 0 else None,
        "median_ms": float(pd.Series([r["ms"] for r in rows]).median()) if rows else None,
        "nodes": nodes,
        "lc0": lc0,
        "weights": weights,
    }
    out.with_suffix(".json").write_text(json.dumps(meta, indent=1))
    _log(json.dumps(meta))
    return frame


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--inp", required=True, help="parquet with a fen column (+ reference columns)")
    ap.add_argument("--out", required=True)
    ap.add_argument(
        "--profile", default=str(DEFAULT_PROFILE), help="profile whose notes.lc0_weights to use"
    )
    ap.add_argument("--weights", default=None, help="overrides the profile's weights")
    ap.add_argument("--lc0", default="engines/lc0")
    ap.add_argument(
        "--nodes",
        type=int,
        default=1,
        help="proxy search nodes: 1 = raw net (blind-spot pass 1), N = the victim's own search (pass 2)",
    )
    ap.add_argument("--workers", type=int, default=6, help="0 = in-process (debugging)")
    ap.add_argument("--chunk", type=int, default=64)
    ap.add_argument("--flush-every", type=int, default=50, help="write the parquet every N chunks")
    ap.add_argument("--max", type=int, default=0, help="cap input rows (0 = all), for smoke tests")
    ap.add_argument("--resume", action="store_true", help="skip FENs already in --out")
    args = ap.parse_args(argv)

    weights = args.weights
    if not weights:
        notes = json.loads(Path(args.profile).read_text()).get("notes") or {}
        weights = notes.get("lc0_weights")
    if not weights:
        _log("no weights: pass --weights or a profile with notes.lc0_weights")
        return 2
    df = pd.read_parquet(args.inp)
    if args.max:
        df = df.head(args.max)
    run(
        df,
        lc0=str((ROOT / args.lc0).resolve()) if not Path(args.lc0).is_absolute() else args.lc0,
        weights=str((ROOT / weights).resolve()) if not Path(weights).is_absolute() else weights,
        out=Path(args.out),
        workers=args.workers,
        nodes=args.nodes,
        chunk=args.chunk,
        flush_every=args.flush_every,
        resume=args.resume,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
