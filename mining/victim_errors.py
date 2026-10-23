"""Label a victim engine's moves with Stockfish loss (training data for the victim-error predictor).

    python -m mining.victim_errors --pgn 'experiments/lc0_*n200*/games.pgn' --victim lc0-t1-n200 \
        --nodes 100000 --baseline-depth 10 --workers 3

For every move the victim played (book moves skipped), from the victim's point of view:
  cp_best   Stockfish `go nodes N` on the position (and its best move),
  cp_after  the same search after the victim's move (skipped when the victim played the best move),
  loss      cp_best - cp_after, clipped to +-3000 (mates saturate),
  baseline  a depth-limited Stockfish move on the same position and ITS loss: how hard the position is
            for a conventional searcher, so a model can separate victim-specific error from sharpness.
Rows append to data/victim_errors/<victim>.parquet, deduplicated by (game_id, ply). Game ids are
"<pgn parent dir>:<Round>:<w|b>" because fastchess writes Site "?".
"""

from __future__ import annotations

import argparse
import glob
import io
import multiprocessing as mp
import sys
import time
from pathlib import Path
from typing import Any

import chess
import chess.engine
import chess.pgn
import pandas as pd

from mining.common import (
    DATA_DIR,
    MATE_CP,
    mining_config,
    open_engine,
    pgn_headers,
    resolve,
    score_to_cp,
    split_pgn,
    write_bytes_atomic,
)

LOSS_CLIP = 3000
RESULT_SCORE = {"1-0": 1.0, "0-1": 0.0, "1/2-1/2": 0.5}


def _log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", file=sys.stderr, flush=True)


def victim_color(headers: dict[str, str], victim: str) -> chess.Color | None:
    if headers.get("White") == victim:
        return chess.WHITE
    if headers.get("Black") == victim:
        return chess.BLACK
    return None


def game_id(source: str, headers: dict[str, str], color: chess.Color) -> str:
    return f"{source}:{headers.get('Round', '?')}:{'w' if color == chess.WHITE else 'b'}"


def iter_victim_moves(game_text: str, victim: str) -> list[tuple[int, str, chess.Move]]:
    """(ply, fen, move) for every non-book move the victim made; [] if the victim is not in the game."""
    game = chess.pgn.read_game(io.StringIO(game_text))
    if game is None:
        return []
    color = victim_color(dict(game.headers), victim)
    if color is None:
        return []
    out: list[tuple[int, str, chess.Move]] = []
    board = game.board()
    for ply, node in enumerate(game.mainline()):
        if board.turn == color and "book" not in (node.comment or ""):
            out.append((ply, board.fen(), node.move))
        board.push(node.move)
    return out


def _terminal_cp(board: chess.Board, pov: chess.Color) -> int:
    if board.is_checkmate():  # side to move is mated
        return -(MATE_CP - 1) if board.turn == pov else MATE_CP - 1
    return 0


def _search(
    engine: chess.engine.SimpleEngine,
    board: chess.Board,
    limit: chess.engine.Limit,
    pov: chess.Color,
) -> tuple[int, chess.Move | None]:
    if board.is_game_over():
        return _terminal_cp(board, pov), None
    info = engine.analyse(board, limit)
    pv = info.get("pv") or []
    return score_to_cp(info["score"], pov), (pv[0] if pv else None)


def _clip(x: int) -> int:
    return max(-LOSS_CLIP, min(LOSS_CLIP, int(x)))


def label_game(
    engine: chess.engine.SimpleEngine,
    game_text: str,
    *,
    source: str,
    victim: str,
    nodes: int,
    baseline_depth: int,
) -> list[dict[str, Any]]:
    headers = pgn_headers(game_text)
    color = victim_color(headers, victim)
    if color is None:
        return []
    gid = game_id(source, headers, color)
    opponent = headers.get("Black" if color == chess.WHITE else "White", "?")
    result = RESULT_SCORE.get(headers.get("Result", ""))
    if result is not None and color == chess.BLACK:
        result = 1.0 - result
    deep = chess.engine.Limit(nodes=nodes)
    shallow = chess.engine.Limit(depth=baseline_depth)
    rows: list[dict[str, Any]] = []
    for ply, fen, move in iter_victim_moves(game_text, victim):
        board = chess.Board(fen)
        cp_best, best = _search(engine, board, deep, color)
        if best == move:
            cp_after = cp_best
        else:
            child = board.copy(stack=False)
            child.push(move)
            cp_after, _ = _search(engine, child, deep, color)
        loss = _clip(cp_best - cp_after)
        _, bmove = _search(engine, board, shallow, color)
        if bmove is None or bmove == best:
            bloss = 0
        elif bmove == move:
            bloss = loss
        else:
            child = board.copy(stack=False)
            child.push(bmove)
            bcp, _ = _search(engine, child, deep, color)
            bloss = _clip(cp_best - bcp)
        rows.append(
            {
                "source": source,
                "game_id": gid,
                "round": headers.get("Round", "?"),
                "ply": ply,
                "fen": fen,
                "victim_color": "white" if color == chess.WHITE else "black",
                "opponent": opponent,
                "result_for_victim": result,
                "move": move.uci(),
                "best": best.uci() if best else None,
                "cp_best": _clip(cp_best),
                "cp_after": _clip(cp_after),
                "loss": loss,
                "baseline_move": bmove.uci() if bmove else None,
                "baseline_loss": bloss,
                "pieces": chess.popcount(board.occupied),
                "nodes": nodes,
                "baseline_depth": baseline_depth,
            }
        )
    return rows


# --- multiprocessing -------------------------------------------------------------------------

_ENGINE: chess.engine.SimpleEngine | None = None


def _init_worker(stockfish: str, hash_mb: int) -> None:
    global _ENGINE
    _ENGINE = open_engine(stockfish, hash_mb=hash_mb)


def _work(task: tuple[str, str, int, int, list[str]]) -> tuple[list[dict[str, Any]], int]:
    source, victim, nodes, baseline_depth, games = task
    assert _ENGINE is not None
    rows: list[dict[str, Any]] = []
    for g in games:
        try:
            rows.extend(
                label_game(
                    _ENGINE,
                    g,
                    source=source,
                    victim=victim,
                    nodes=nodes,
                    baseline_depth=baseline_depth,
                )
            )
        except (
            chess.engine.EngineError,
            ValueError,
            KeyError,
        ) as exc:  # one bad game must not kill the run
            _log(f"game skipped ({source}): {exc!r}")
    return rows, len(games)


def _write(path: Path, frames: list[pd.DataFrame]) -> int:
    df = pd.concat([f for f in frames if len(f)], ignore_index=True)
    df = df.drop_duplicates(subset=["game_id", "ply"], keep="first")
    buf = io.BytesIO()
    df.to_parquet(buf, index=False)
    write_bytes_atomic(path, buf.getvalue())
    return len(df)


def main(argv: list[str] | None = None) -> int:
    cfg = mining_config()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument(
        "--pgn", action="append", required=True, help="glob(s) of PGN files (repeatable)"
    )
    ap.add_argument("--victim", default="lc0-t1-n200", help="engine name in the PGN headers")
    ap.add_argument("--nodes", type=int, default=100_000)
    ap.add_argument("--baseline-depth", type=int, default=10)
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--chunk", type=int, default=2, help="games per worker task")
    ap.add_argument("--max-games", type=int, default=0, help="cap games (0 = all), for smoke tests")
    ap.add_argument("--flush-every", type=int, default=40, help="write parquet every N games")
    ap.add_argument("--stockfish", default=str(cfg["stockfish"]))
    ap.add_argument("--hash-mb", type=int, default=int(cfg["hash_mb"]))
    ap.add_argument("--out", default=None, help="default data/victim_errors/<victim>.parquet")
    args = ap.parse_args(argv)

    out = Path(args.out) if args.out else DATA_DIR / "victim_errors" / f"{args.victim}.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    frames = [pd.read_parquet(out)] if out.exists() else []
    done = set(frames[0]["game_id"].unique()) if frames else set()

    tasks: list[tuple[str, str, int, int, list[str]]] = []
    n_todo = 0
    for pattern in args.pgn:
        for file in sorted(glob.glob(pattern)):
            source = Path(file).parent.name
            todo = []
            for g in split_pgn(Path(file).read_text()):
                h = pgn_headers(g)
                color = victim_color(h, args.victim)
                if color is None or game_id(source, h, color) in done:
                    continue
                todo.append(g)
            if args.max_games:
                todo = todo[: max(0, args.max_games - n_todo)]
            n_todo += len(todo)
            tasks += [
                (source, args.victim, args.nodes, args.baseline_depth, todo[j : j + args.chunk])
                for j in range(0, len(todo), args.chunk)
            ]
    _log(
        f"{n_todo} games to label ({len(done)} already done), nodes={args.nodes}, "
        f"baseline depth={args.baseline_depth}, workers={args.workers} -> {out}"
    )
    if not tasks:
        return 0
    ctx = mp.get_context("spawn")
    sf = str(resolve(args.stockfish))
    t0, n_games, n_rows, since_flush = time.monotonic(), 0, 0, 0
    new_rows: list[dict[str, Any]] = []
    with ctx.Pool(args.workers, initializer=_init_worker, initargs=(sf, args.hash_mb)) as pool:
        for rows, ng in pool.imap_unordered(_work, tasks):
            new_rows.extend(rows)
            n_games += ng
            n_rows += len(rows)
            since_flush += ng
            if since_flush >= args.flush_every:
                frames.append(pd.DataFrame(new_rows))
                new_rows, since_flush = [], 0
                total = _write(out, frames)
                frames = [pd.read_parquet(out)]
                dt = time.monotonic() - t0
                _log(
                    f"{n_games}/{n_todo} games, {n_rows} positions ({n_rows / dt:.1f}/s), "
                    f"{total} rows on disk"
                )
    if new_rows:
        frames.append(pd.DataFrame(new_rows))
    total = _write(out, frames) if frames else 0
    _log(
        f"done: {n_games} games, {n_rows} positions in {time.monotonic() - t0:.0f}s; {total} rows -> {out}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
