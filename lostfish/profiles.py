"""Opponent profiles: `profiles/<bot>.json`, written by `mining/build_profile.py`.

`load_profile` never raises. Lookup is case-insensitive; an unknown or unreadable profile falls
back to `<dir>/_generic.json`, and if that is missing too, to a built-in default (effective
depth 8, no clusters). `cfg` is duck-typed (`cfg.profiles.dir`, `cfg.profiles.fallback`; a dict
with the same keys or `None` also work) so this module does not depend on `lostfish.config`.

Cluster convention (see `lostfish.features`): features are computed with pov = the bot = the side
to move; `WeakCluster.centroid` is in units of `raw / scale` (no mean subtraction, which leaves
Euclidean distances identical to z-scores); assign a position to its nearest centroid.
"""

from __future__ import annotations

import dataclasses
import json
import os
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
DEFAULT_DIR = "profiles"
DEFAULT_FALLBACK = "_generic"
DEFAULT_EFFECTIVE_DEPTH = 8
_REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass
class WeakCluster:
    label: str
    centroid: list[float]  # features.FEATURE_NAMES order, standardised units (raw / scale)
    scale: list[float]  # per-feature std used for standardisation
    uplift: float  # cluster blunder rate / base blunder rate
    blunder_rate: float
    n: int


@dataclass
class Profile:
    name: str
    version: int = SCHEMA_VERSION
    built_at: str = ""
    n_games: int = 0
    n_positions: int = 0
    rating: int | None = None
    proxy: str = "stockfish_depth"
    effective_depth: int = DEFAULT_EFFECTIVE_DEPTH
    depth_agreement: dict[int, float] = field(default_factory=dict)
    base_blunder_rate: float = 0.0
    weak_clusters: list[WeakCluster] = field(default_factory=list)
    openings: list[dict] = field(default_factory=list)
    notes: dict = field(default_factory=dict)


def default_profile(name: str = DEFAULT_FALLBACK) -> Profile:
    return Profile(
        name=name,
        built_at=date.today().isoformat(),
        notes={"source": "built-in default (no profile file found)"},
    )


# ---------------------------------------------------------------------------------------------
# cfg access (duck-typed)


def _cfg_get(cfg: Any, key: str, default: Any) -> Any:
    section = None
    if cfg is not None:
        section = cfg.get("profiles") if isinstance(cfg, dict) else getattr(cfg, "profiles", None)
    if section is None:
        return default
    value = section.get(key) if isinstance(section, dict) else getattr(section, key, None)
    return default if value in (None, "") else value


def profiles_dir(cfg: Any = None) -> Path:
    d = Path(str(_cfg_get(cfg, "dir", DEFAULT_DIR)))
    return d if d.is_absolute() else _REPO_ROOT / d


def _fallback_name(cfg: Any = None) -> str:
    return str(_cfg_get(cfg, "fallback", DEFAULT_FALLBACK))


# ---------------------------------------------------------------------------------------------
# (de)serialisation


def profile_to_dict(profile: Profile) -> dict:
    d = dataclasses.asdict(profile)
    d["depth_agreement"] = {str(k): float(v) for k, v in sorted(profile.depth_agreement.items())}
    return d


def profile_from_dict(d: dict) -> Profile:
    clusters = []
    for c in d.get("weak_clusters") or []:
        clusters.append(
            WeakCluster(
                label=str(c.get("label", "")),
                centroid=[float(x) for x in c.get("centroid", [])],
                scale=[float(x) for x in c.get("scale", [])],
                uplift=float(c.get("uplift", 1.0)),
                blunder_rate=float(c.get("blunder_rate", 0.0)),
                n=int(c.get("n", 0)),
            )
        )
    rating = d.get("rating")
    return Profile(
        name=str(d.get("name", "")).lower(),
        version=int(d.get("version", SCHEMA_VERSION)),
        built_at=str(d.get("built_at", "")),
        n_games=int(d.get("n_games", 0)),
        n_positions=int(d.get("n_positions", 0)),
        rating=int(rating) if rating is not None else None,
        proxy=str(d.get("proxy", "stockfish_depth")),
        effective_depth=int(d.get("effective_depth", DEFAULT_EFFECTIVE_DEPTH)),
        depth_agreement={int(k): float(v) for k, v in (d.get("depth_agreement") or {}).items()},
        base_blunder_rate=float(d.get("base_blunder_rate", 0.0)),
        weak_clusters=clusters,
        openings=list(d.get("openings") or []),
        notes=dict(d.get("notes") or {}),
    )


def _find_file(directory: Path, name: str) -> Path | None:
    exact = directory / f"{name}.json"
    if exact.is_file():
        return exact
    if not directory.is_dir():
        return None
    target = f"{name}.json".lower()
    for p in directory.iterdir():
        if p.name.lower() == target and p.is_file():
            return p
    return None


def _read(path: Path) -> Profile:
    with open(path) as fh:
        return profile_from_dict(json.load(fh))


def load_profile(name: str | None, cfg: Any = None) -> Profile:
    """Profile for `name` (case-insensitive) -> fallback profile -> built-in default."""
    try:
        directory = profiles_dir(cfg)
        fallback = _fallback_name(cfg)
    except Exception:  # noqa: BLE001 - must never raise
        directory, fallback = _REPO_ROOT / DEFAULT_DIR, DEFAULT_FALLBACK
    for candidate in (name, fallback):
        if not candidate or not str(candidate).strip():
            continue
        key = str(candidate).strip().lower()
        if "/" in key or "\\" in key or key.startswith(".."):
            continue
        try:
            path = _find_file(directory, key)
            if path is not None:
                return _read(path)
        except Exception as e:  # noqa: BLE001 - corrupt file: fall through to the next option
            print(f"lostfish.profiles: could not read profile {key!r}: {e}", file=sys.stderr)
    return default_profile(fallback)


def save_profile(profile: Profile, cfg: Any = None) -> Path:
    directory = profiles_dir(cfg)
    directory.mkdir(parents=True, exist_ok=True)
    profile.name = profile.name.lower()
    path = directory / f"{profile.name}.json"
    fd, tmp = tempfile.mkstemp(dir=directory, prefix=f".{path.name}.", suffix=".tmp")
    with os.fdopen(fd, "w") as fh:
        json.dump(profile_to_dict(profile), fh, indent=1)
        fh.write("\n")
    os.chmod(tmp, 0o644)
    os.replace(tmp, path)
    return path


def parse_uci_opponent(value: str) -> tuple[str | None, int | None, str | None]:
    """Parse lichess-bot's UCI_Opponent: "<title|none> <rating|none> <computer|human> <name...>".

    "BOT 2300 computer maia1" -> ("maia1", 2300, "computer"); a bare "name" -> ("name", None, None).
    """
    tokens = (value or "").split()
    if not tokens:
        return None, None, None
    if len(tokens) >= 4 and tokens[2].lower() in ("computer", "human"):
        name = " ".join(tokens[3:])
        rating: int | None
        try:
            rating = int(tokens[1])
        except ValueError:
            rating = None
        name_out = None if name.lower() == "none" else name
        return name_out, rating, tokens[2].lower()
    if len(tokens) == 1:
        return (None if tokens[0].lower() == "none" else tokens[0]), None, None
    return tokens[-1], None, None
