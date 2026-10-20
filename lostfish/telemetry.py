"""Per-move telemetry: one JSON line per move appended to `logs/moves.jsonl`.

`$LOSTFISH_LOG` overrides the default path (`off` disables logging). Relative paths resolve
against the repo root. `log_move` never raises: telemetry must not cost us a game.
"""

from __future__ import annotations

import dataclasses
import json
import logging
import os
import time
from pathlib import Path
from typing import Any

from lostfish.config import REPO_ROOT

DEFAULT_LOG = "logs/moves.jsonl"
_DISABLED = {"off", "none", "0", "false"}

log = logging.getLogger(__name__)


def _default(obj: Any) -> Any:
    """JSON fallback: moves -> uci, dataclasses -> dict, paths/sets/others -> str/list."""
    uci = getattr(obj, "uci", None)
    if callable(uci):
        return uci()
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return dataclasses.asdict(obj)
    if isinstance(obj, set | frozenset | tuple):
        return list(obj)
    if hasattr(obj, "item") and callable(obj.item):  # numpy scalars
        return obj.item()
    if hasattr(obj, "tolist") and callable(obj.tolist):  # numpy arrays
        return obj.tolist()
    return str(obj)


def move_record(
    body: dict,
    *,
    fen: str,
    ply: int,
    opponent: dict[str, Any],
    budget: Any,
    go: Any,
    chosen: str,
    elapsed_ms: float,
    player: str = "",
) -> dict[str, Any]:
    """The per-move record: the Player's telemetry `body` plus what the UCI layer knows."""
    rec = dict(body)
    go_d = dataclasses.asdict(go) if dataclasses.is_dataclass(go) else dict(go or {})
    rec.update(
        ts=round(time.time(), 3),
        fen=fen,
        ply=ply,
        opponent=opponent,
        tc_class=getattr(budget, "tc_class", None),
        budget=dataclasses.asdict(budget) if dataclasses.is_dataclass(budget) else budget,
        go={k: v for k, v in go_d.items() if v not in (None, False, [])},
        player=rec.get("player", player),
        candidates=rec.get("candidates", []),
        chosen=chosen,
        reason=rec.get("reason"),
        elapsed_ms=elapsed_ms,
        over_hard=elapsed_ms > getattr(budget, "hard_ms", float("inf")),
        pid=os.getpid(),
    )
    return rec


def log_path(path: str | Path = DEFAULT_LOG) -> Path | None:
    """Where `log_move(…, path)` writes; None when logging is disabled."""
    env = os.environ.get("LOSTFISH_LOG")
    if env is not None and str(path) == DEFAULT_LOG:
        if env.strip().lower() in _DISABLED:
            return None
        path = env
    p = Path(path).expanduser()
    return p if p.is_absolute() else REPO_ROOT / p


def log_move(record: dict, path: str | Path = DEFAULT_LOG) -> None:
    """Append `record` (plus `ts` if missing) as one JSON line. Never raises."""
    try:
        target = log_path(path)
        if target is None:
            return
        rec = dict(record)
        rec.setdefault("ts", round(time.time(), 3))
        line = json.dumps(rec, default=_default, separators=(",", ":")) + "\n"
        target.parent.mkdir(parents=True, exist_ok=True)
        # One write() on an O_APPEND fd keeps lines intact with concurrent writers.
        fd = os.open(target, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
        try:
            os.write(fd, line.encode())
        finally:
            os.close(fd)
    except Exception:
        log.debug("telemetry write failed", exc_info=True)
