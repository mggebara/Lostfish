"""Annotate bot games with node-limited Stockfish trajectories.

    python -m mining.annotate --bots all --nodes 20000 --workers 4 --min-ply 20

For every position with the bot to move at ply >= min_ply: one MultiPV=1 `go nodes N` search
(best move, eval, eval/best-move per completed depth), then one search at the same node count on
the position after the bot's actual move (`cp_played`, bot POV). When the bot played the engine's
best move the second search is skipped and cp_played = cp_best (loss 0). Each worker keeps one
persistent Stockfish; `ucinewgame` is sent per game so results do not depend on scheduling.
Rows are appended to data/annot/<bot>.parquet; already-annotated game ids are skipped.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import multiprocessing as mp
import multiprocessing.util
import sys
import time
from datetime import datetime
from typing import Any

import chess
import chess.engine
import chess.pgn
import pandas as pd

from mining.common import (
    DATA_DIR,
    analyse_trajectory,
    annot_path,
    bot_key,
    game_id_from_headers,
    games_path,
    iter_games,
    mining_config,
    open_engine,
    pgn_headers,
    read_json,
    resolve,
    select_bots,
    write_bytes_atomic,
)

COLUMNS = [
    "bot", "game_id", "ply", "fen", "bot_color", "played", "best", "cp_best", "cp_played",
    "loss", "depth_reached", "eval_by_depth", "best_by_depth", "opponent", "opponent_title",
    "opponent_rating", "bot_rating", "result_for_bot", "tc", "perf", "clock_ms", "agree_final",
    "nodes",
]  # fmt: skip


def log(msg: str) -> None:
    print(f"[annotate {datetime.now():%H:%M:%S}] {msg}", flush=True)


def _int(v: str | None) -> int | None:
    try:
        return int(v) if v not in (None, "", "?", "-") else None
    except ValueError:
        return None


def _result_for(result: str, color: chess.Color) -> float | None:
    table = {"1-0": 1.0, "0-1": 0.0, "1/2-1/2": 0.5}
    if result not in table:
        return None
    r = table[result]
    return r if color == chess.WHITE else 1.0 - r


def annotate_game(
    engine: chess.engine.SimpleEngine, game_text: str, bot: str, nodes: int, min_ply: int
) -> tuple[list[dict[str, Any]], int]:
    """Rows for one PGN game (empty for non-standard games or games without the bot).

    Returns (rows, number_of_engine_searches).
    """
    h = pgn_headers(game_text)
    bot = bot_key(bot)
    if h.get("Variant", "Standard") not in ("Standard", "") or h.get("SetUp") == "1":
        return [], 0
    if bot_key(h.get("White", "")) == bot:
        color = chess.WHITE
    elif bot_key(h.get("Black", "")) == bot:
        color = chess.BLACK
    else:
        return [], 0
    try:
        game = chess.pgn.read_game(io.StringIO(game_text))
    except Exception:  # noqa: BLE001 - malformed PGN
        return [], 0
    if game is None or game.errors:
        return [], 0
    gid = game_id_from_headers(h) or ""
    opp_side = "Black" if color == chess.WHITE else "White"
    me_side = "White" if color == chess.WHITE else "Black"
    tc = h.get("TimeControl", "-")
    base_ms = _int(tc.split("+")[0]) if "+" in tc else None
    clock = {chess.WHITE: base_ms * 1000 if base_ms else None}
    clock[chess.BLACK] = clock[chess.WHITE]
    event = h.get("Event", "").lower()
    perf = next((p for p in ("bullet", "blitz", "rapid", "classical") if p in event), "")
    common = {
        "bot": bot,
        "game_id": gid,
        "bot_color": "white" if color == chess.WHITE else "black",
        "opponent": h.get(opp_side, ""),
        "opponent_title": h.get(f"{opp_side}Title") or None,
        "opponent_rating": _int(h.get(f"{opp_side}Elo")),
        "bot_rating": _int(h.get(f"{me_side}Elo")),
        "result_for_bot": _result_for(h.get("Result", "*"), color),
        "tc": tc,
        "perf": perf,
        "nodes": int(nodes),
    }
    rows: list[dict[str, Any]] = []
    searches = 0
    board = game.board()
    for node in game.mainline():
        move = node.move
        mover, ply = board.turn, board.ply()
        if mover == color and ply >= min_ply:
            fen = board.fen()
            res = analyse_trajectory(engine, board, nodes, pov=color, game=gid)
            searches += 1
            played = move.uci()
            board.push(move)
            if res["best"] == played:
                cp_played = res["cp"]
            else:
                cp_played = analyse_trajectory(engine, board, nodes, pov=color, game=gid)["cp"]
                searches += 1
            rows.append(
                {
                    **common,
                    "ply": ply,
                    "fen": fen,
                    "played": played,
                    "best": res["best"],
                    "cp_best": res["cp"],
                    "cp_played": cp_played,
                    "loss": max(0, res["cp"] - cp_played),
                    "depth_reached": res["depth"],
                    "eval_by_depth": json.dumps(res["eval_by_depth"]),
                    "best_by_depth": json.dumps(res["best_by_depth"]),
                    "clock_ms": clock[color],
                    "agree_final": played == res["best"],
                }
            )
        else:
            board.push(move)
        clk = node.clock()
        if clk is not None:
            clock[mover] = round(clk * 1000)
    return rows, searches


# ---------------------------------------------------------------------------------------------
# worker pool

_ENGINE: chess.engine.SimpleEngine | None = None
_ENGINE_ARGS: tuple[str, int] = ("", 16)


def _start_engine() -> None:
    global _ENGINE
    _ENGINE = open_engine(_ENGINE_ARGS[0], hash_mb=_ENGINE_ARGS[1])
    multiprocessing.util.Finalize(_ENGINE, _ENGINE.quit, exitpriority=10)


def _init_worker(sf_path: str, hash_mb: int) -> None:
    global _ENGINE_ARGS
    _ENGINE_ARGS = (sf_path, hash_mb)
    _start_engine()


def _work(task: tuple[str, int, int, list[str]]) -> tuple[str, list[dict], int, int]:
    bot, nodes, min_ply, games = task
    rows: list[dict] = []
    searches = 0
    for text in games:
        for attempt in range(2):
            try:
                assert _ENGINE is not None
                r, s = annotate_game(_ENGINE, text, bot, nodes, min_ply)
                rows.extend(r)
                searches += s
                break
            except (chess.engine.EngineError, chess.engine.EngineTerminatedError, OSError):
                with contextlib.suppress(Exception):
                    if _ENGINE is not None:
                        _ENGINE.close()
                _start_engine()
                if attempt:
                    print(f"annotate: giving up on a {bot} game after engine failure", flush=True)
            except Exception as e:  # noqa: BLE001 - one odd game must not kill the run
                print(f"annotate: skipping a {bot} game: {type(e).__name__}: {e}", flush=True)
                break
    return bot, rows, searches, len(games)


def _write(bot: str, frames: list[pd.DataFrame]) -> int:
    df = pd.concat([f for f in frames if len(f)], ignore_index=True) if frames else pd.DataFrame()
    if df.empty:
        return 0
    df = df.drop_duplicates(subset=["game_id", "ply"], keep="first")
    for col in ("clock_ms", "opponent_rating", "bot_rating"):
        df[col] = df[col].astype("Int64")
    buf = io.BytesIO()
    df.to_parquet(buf, index=False)
    write_bytes_atomic(annot_path(bot), buf.getvalue())
    return len(df)


def bot_order(bots: list[str]) -> list[str]:
    """Activity order from the last fetch selection, then the rest alphabetically."""
    sel = [bot_key(b) for b in (read_json(DATA_DIR / "last_selection.json", []) or [])]
    rank = {b: i for i, b in enumerate(sel)}
    return sorted(bots, key=lambda b: (rank.get(b, len(rank)), b))


def main(argv: list[str] | None = None) -> int:
    cfg = mining_config()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--bots", default="all")
    ap.add_argument("--nodes", type=int, default=int(cfg["nodes"]))
    ap.add_argument("--workers", type=int, default=int(cfg["workers"]))
    ap.add_argument("--min-ply", type=int, default=int(cfg["min_ply"]))
    ap.add_argument("--max-games", type=int, default=0, help="cap games per bot (0 = all)")
    ap.add_argument("--chunk", type=int, default=4, help="games per worker task")
    ap.add_argument("--flush-every", type=int, default=60, help="write parquet every N games")
    ap.add_argument("--stockfish", default=str(cfg["stockfish"]))
    ap.add_argument("--hash-mb", type=int, default=int(cfg["hash_mb"]))
    args = ap.parse_args(argv)

    bots = bot_order([b for b in select_bots(args.bots, "games") if games_path(b).exists()])
    log(f"{len(bots)} bots, nodes={args.nodes}, workers={args.workers}, min_ply={args.min_ply}")
    ctx = mp.get_context("spawn")
    sf = str(resolve(args.stockfish))
    t_all, pos_all, search_all = time.monotonic(), 0, 0
    with ctx.Pool(args.workers, initializer=_init_worker, initargs=(sf, args.hash_mb)) as pool:
        for i, bot in enumerate(bots, 1):
            path = annot_path(bot)
            frames = [pd.read_parquet(path)] if path.exists() else []
            done = set(frames[0]["game_id"].unique()) if frames else set()
            todo = [g for g in iter_games(games_path(bot)) if _gid(g) not in done]
            if args.max_games:
                todo = todo[: max(0, args.max_games - len(done))]
            if not todo:
                log(f"[{i}/{len(bots)}] {bot}: nothing to do ({len(done)} games annotated)")
                continue
            tasks = [
                (bot, args.nodes, args.min_ply, todo[j : j + args.chunk])
                for j in range(0, len(todo), args.chunk)
            ]
            t0, n_games, n_pos, n_search, since_flush = time.monotonic(), 0, 0, 0, 0
            new_rows: list[dict] = []
            for _, rows, searches, ng in pool.imap_unordered(_work, tasks):
                new_rows.extend(rows)
                n_games, n_pos, n_search = n_games + ng, n_pos + len(rows), n_search + searches
                since_flush += ng
                if since_flush >= args.flush_every:
                    frames.append(pd.DataFrame(new_rows, columns=COLUMNS))
                    new_rows, since_flush = [], 0
                    total = _write(bot, frames)
                    dt = time.monotonic() - t0
                    log(
                        f"  {bot}: {n_games}/{len(todo)} games, {total} rows, "
                        f"{n_pos / dt:.1f} pos/s, {n_search / dt:.1f} searches/s"
                    )
            frames.append(pd.DataFrame(new_rows, columns=COLUMNS))
            total = _write(bot, frames)
            dt = time.monotonic() - t0
            pos_all, search_all = pos_all + n_pos, search_all + n_search
            log(
                f"[{i}/{len(bots)}] {bot}: done, {n_games} new games, {n_pos} new positions "
                f"({total} total) in {dt:.0f} s: {n_pos / max(dt, 1e-9):.1f} pos/s, "
                f"{n_search / max(dt, 1e-9):.1f} searches/s"
            )
    dt = time.monotonic() - t_all
    log(
        f"all done: {pos_all} positions, {search_all} searches in {dt:.0f} s "
        f"({pos_all / max(dt, 1e-9):.1f} pos/s)"
    )
    return 0


def _gid(game_text: str) -> str:
    return game_id_from_headers(pgn_headers(game_text)) or ""


if __name__ == "__main__":
    sys.exit(main())
