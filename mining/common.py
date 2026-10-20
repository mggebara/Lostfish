"""Shared helpers for the offline mining pipeline.

Mining deliberately does not depend on `lostfish.engines` or `lostfish.config`: it drives Stockfish
through a thin `chess.engine.SimpleEngine` wrapper (Threads=1, small fixed Hash, node-limited
searches) and reads its settings from the `mining:` section of `configs/lostfish.yaml`.

Data layout (all under `data/`, gitignored):
    bots.json                       known BOT accounts (merged across runs)
    games/<bot>.pgn.zst             rated bullet/blitz games, one zstd frame per fetch
    games/<bot>.meta.json           fetch bookkeeping (ids, newest/oldest createdAt, counts)
    annot/<bot>.parquet             one row per bot-to-move position
    fingerprints/<bot>.json         depth-agreement fingerprint
    clusters/<bot>.json             feature clusters with blunder uplift
"""

from __future__ import annotations

import io
import json
import os
import re
import tempfile
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

import chess
import chess.engine
import yaml
import zstandard

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"
CONFIG_PATH = REPO_ROOT / "configs" / "lostfish.yaml"

MATE_CP = 32000
USER_AGENT = "LostFish-mining (research; github.com/mggebara/Lostfish)"

MINING_DEFAULTS: dict[str, Any] = {
    "stockfish": "engines/stockfish",
    "hash_mb": 16,
    "nodes": 20000,
    "workers": 4,
    "min_ply": 20,
    "max_games": 300,
    "min_games": 50,
    "perf": "bullet,blitz",
    "since_days": 365,
    "k": 8,
    "blunder_cp": 100,
    "clip_cp": 1000,
    "min_cluster": 30,
    "test_fraction": 0.2,
    "min_coverage": 0.5,
    "opening_plies": 8,
}


# ---------------------------------------------------------------------------------------------
# configuration and paths


def mining_config(path: Path | None = None) -> dict[str, Any]:
    """Defaults overlaid with the `mining:` section of configs/lostfish.yaml (if present)."""
    cfg = dict(MINING_DEFAULTS)
    try:
        with open(path or CONFIG_PATH) as fh:
            raw = yaml.safe_load(fh) or {}
        section = raw.get("mining") or {}
        if isinstance(section, dict):
            cfg.update(section)
    except (OSError, yaml.YAMLError):
        pass
    return cfg


def resolve(path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else REPO_ROOT / p


def bot_key(name: str) -> str:
    """Canonical (lowercase) bot id; Lichess ids are lowercase usernames."""
    return name.strip().lower()


def bots_json_path() -> Path:
    return DATA_DIR / "bots.json"


def games_path(bot: str) -> Path:
    return DATA_DIR / "games" / f"{bot_key(bot)}.pgn.zst"


def games_meta_path(bot: str) -> Path:
    return DATA_DIR / "games" / f"{bot_key(bot)}.meta.json"


def annot_path(bot: str) -> Path:
    return DATA_DIR / "annot" / f"{bot_key(bot)}.parquet"


def fingerprint_path(bot: str) -> Path:
    return DATA_DIR / "fingerprints" / f"{bot_key(bot)}.json"


def clusters_path(bot: str) -> Path:
    return DATA_DIR / "clusters" / f"{bot_key(bot)}.json"


def bots_with(kind: str) -> list[str]:
    """Bot ids that have a given artefact: 'games', 'annot', 'fingerprints' or 'clusters'."""
    suffix = {
        "games": ".pgn.zst",
        "annot": ".parquet",
        "fingerprints": ".json",
        "clusters": ".json",
    }[kind]
    d = DATA_DIR / kind
    if not d.is_dir():
        return []
    out = [p.name[: -len(suffix)] for p in d.iterdir() if p.name.endswith(suffix)]
    return sorted(b for b in out if not b.startswith("_"))


def select_bots(spec: str, kind: str) -> list[str]:
    """Parse a `--bots` argument: 'all' means every bot with the given artefact."""
    if spec.strip().lower() == "all":
        return bots_with(kind)
    return [bot_key(b) for b in spec.split(",") if b.strip()]


# ---------------------------------------------------------------------------------------------
# JSON / file helpers


def read_json(path: Path, default: Any = None) -> Any:
    try:
        with open(path) as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        return default


def write_json(path: Path, obj: Any) -> None:
    """Atomic JSON write (tmp file + rename)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    with os.fdopen(fd, "w") as fh:
        json.dump(obj, fh, indent=2, sort_keys=False)
        fh.write("\n")
    os.chmod(tmp, 0o644)
    os.replace(tmp, path)


def write_bytes_atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    with os.fdopen(fd, "wb") as fh:
        fh.write(data)
    os.chmod(tmp, 0o644)
    os.replace(tmp, path)


# ---------------------------------------------------------------------------------------------
# zstd PGN storage

_GAME_SPLIT = re.compile(r"(?m)^(?=\[Event )")
_HEADER = re.compile(r'^\[(\w+) "(.*)"\]\s*$', re.MULTILINE)


def split_pgn(text: str) -> list[str]:
    """Split a multi-game PGN string into one string per game."""
    return [g.strip() + "\n" for g in _GAME_SPLIT.split(text) if g.strip()]


def pgn_headers(game_text: str) -> dict[str, str]:
    """Cheap header parse (no move parsing)."""
    head = game_text.split("\n\n", 1)[0]
    return {m.group(1): m.group(2) for m in _HEADER.finditer(head)}


def game_id_from_headers(headers: dict[str, str]) -> str | None:
    site = headers.get("Site") or headers.get("GameId") or ""
    if not site:
        return None
    return site.rstrip("/").rsplit("/", 1)[-1][:8] or None


def append_pgn_zst(path: Path, games: Iterable[str]) -> int:
    """Append games as a new zstd frame (concatenated frames form a valid stream)."""
    games = list(games)
    if not games:
        return 0
    frame = zstandard.ZstdCompressor(level=10).compress("\n".join(games).encode() + b"\n")
    old = path.read_bytes() if path.exists() else b""
    write_bytes_atomic(path, old + frame)
    return len(games)


def read_pgn_zst(path: Path) -> str:
    if not path.exists():
        return ""
    with open(path, "rb") as fh:
        reader = zstandard.ZstdDecompressor().stream_reader(fh, read_across_frames=True)
        return io.TextIOWrapper(reader, encoding="utf-8", errors="replace").read()


def iter_games(path: Path) -> Iterator[str]:
    yield from split_pgn(read_pgn_zst(path))


# ---------------------------------------------------------------------------------------------
# Stockfish


def score_to_cp(score: chess.engine.PovScore, pov: chess.Color) -> int:
    """Centipawns from `pov`; mate maps to ±(MATE_CP - plies) as in docs/INTERFACES.md.

    Plies are counted from the searched position, whose side to move is `score.turn`.
    """
    rel = score.relative
    mate = rel.mate()
    if mate is None:
        v = int(rel.score() or 0)
    elif mate > 0:  # side to move mates in `mate` moves = 2*mate - 1 plies
        v = MATE_CP - (2 * mate - 1)
    else:  # side to move is mated in -mate moves = 2*(-mate) plies (Mate(0): mated now)
        v = -(MATE_CP - 2 * (-mate))
    return v if score.turn == pov else -v


def open_engine(path: str | Path | None = None, *, hash_mb: int = 16) -> chess.engine.SimpleEngine:
    """One persistent Stockfish (Threads=1, fixed Hash). Callers keep it for many positions."""
    cfg = mining_config()
    sf = resolve(path or cfg["stockfish"])
    engine = chess.engine.SimpleEngine.popen_uci(str(sf))
    engine.configure({"Threads": 1, "Hash": int(hash_mb)})
    return engine


def analyse_trajectory(
    engine: chess.engine.SimpleEngine,
    board: chess.Board,
    nodes: int,
    *,
    pov: chess.Color | None = None,
    game: object | None = None,
) -> dict[str, Any]:
    """One node-limited MultiPV=1 search with the iterative-deepening trajectory.

    Returns {"cp", "best", "eval_by_depth", "best_by_depth", "depth"} with cp values from `pov`
    (default: side to move). `eval_by_depth`/`best_by_depth` contain only completed (exact-score)
    iterations; the final, possibly aspiration-bounded line still sets `cp` and `best` because it
    is what Stockfish would report/play at this node count. `best` is a UCI string or None.
    """
    pov = board.turn if pov is None else pov
    if board.is_game_over(claim_draw=False):
        if board.is_checkmate():
            cp = -MATE_CP if board.turn == pov else MATE_CP
        else:
            cp = 0
        return {"cp": cp, "best": None, "eval_by_depth": {}, "best_by_depth": {}, "depth": 0}
    eval_by_depth: dict[int, int] = {}
    best_by_depth: dict[int, str] = {}
    last_cp: int | None = None
    last_move: str | None = None
    with engine.analysis(board, chess.engine.Limit(nodes=int(nodes)), game=game) as analysis:
        for info in analysis:
            depth = info.get("depth")
            score = info.get("score")
            pv = info.get("pv")
            if depth is None or score is None or not pv or info.get("multipv", 1) != 1:
                continue
            cp = score_to_cp(score, pov)
            last_cp, last_move = cp, pv[0].uci()
            if info.get("lowerbound") or info.get("upperbound"):
                continue
            eval_by_depth[int(depth)] = cp
            best_by_depth[int(depth)] = pv[0].uci()
        result = analysis.wait()
    best = result.move.uci() if result.move is not None else last_move
    if last_cp is None:
        last_cp = 0
    return {
        "cp": last_cp,
        "best": best,
        "eval_by_depth": eval_by_depth,
        "best_by_depth": best_by_depth,
        "depth": max(eval_by_depth) if eval_by_depth else 0,
    }


def depth_dict_from_json(value: Any) -> dict[int, Any]:
    """Decode the eval_by_depth / best_by_depth columns (JSON strings with str keys)."""
    if value is None:
        return {}
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return {}
    if isinstance(value, dict):
        return {int(k): v for k, v in value.items()}
    return {}


def clip_cp(cp: float, limit: float) -> float:
    return max(-limit, min(limit, cp))
