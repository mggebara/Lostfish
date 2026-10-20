"""Typed view of `configs/lostfish.yaml`.

`load_config()` returns a `Config` dataclass tree mirroring the yaml. Known keys become typed
fields; unknown keys are preserved in each section's `.extra` (and are also readable as
attributes, e.g. `cfg.certify.some_new_key`). Unknown top-level sections land in `Config.extra`
as `Section` objects (a dict with attribute access). Relative paths (engine binaries, syzygy,
profiles dir) are resolved against the repo root: the parent of the `configs/` directory that
holds the yaml, or this checkout's root when the yaml lives elsewhere.

The config path is, in order: the `path` argument, `$LOSTFISH_CONFIG`, `configs/lostfish.yaml`.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field, fields, replace
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = REPO_ROOT / "configs" / "lostfish.yaml"
TC_CLASSES = ("bullet", "blitz", "rapid")


class Section(dict):
    """A dict whose keys are also attributes (nested dicts are wrapped too)."""

    def __init__(self, data: dict[str, Any] | None = None) -> None:
        super().__init__({k: _wrap(v) for k, v in (data or {}).items()})

    def __getattr__(self, name: str) -> Any:
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name) from None


def _wrap(value: Any) -> Any:
    return Section(value) if isinstance(value, dict) and not isinstance(value, Section) else value


class _ExtraAttrs:
    """Mixin: fall back to `self.extra[name]` for attributes that are not typed fields."""

    def __getattr__(self, name: str) -> Any:
        if name.startswith("__"):
            raise AttributeError(name)
        extra = self.__dict__.get("extra") or {}
        if name in extra:
            return extra[name]
        raise AttributeError(f"{type(self).__name__} has no attribute {name!r}")


@dataclass
class EnginesConfig(_ExtraAttrs):
    stockfish: str = "engines/stockfish"
    stockfish_version: str = ""
    fastchess: str = "engines/fastchess"
    fastchess_version: str = ""
    syzygy_path: str | None = None  # None (or a missing dir) disables tablebases
    hash_mb: int = 64
    threads: int = 1
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class CertifyConfig(_ExtraAttrs):
    multipv: int = 5
    tolerance_cp: int = 30
    tolerance_min_cp: int = 0
    tighten_when_behind_cp: int = 150
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class SteerConfig(_ExtraAttrs):
    lambda_weakness: float = 0.15
    proxy_depth_cap: int = 12
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class BudgetConfig(_ExtraAttrs):
    certify_nodes: int = 600_000
    eval_nodes: int = 150_000
    k: int = 5
    proxy_depth_cap: int = 12
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class TimemanConfig(_ExtraAttrs):
    moves_to_go_assumed: int = 30
    increment_fraction: float = 0.8
    min_move_ms: int = 50
    reserve_ms: int = 300
    nps_estimate: int = 1_000_000
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class ProfilesConfig(_ExtraAttrs):
    dir: str = "profiles"
    fallback: str = "_generic"
    extra: dict[str, Any] = field(default_factory=dict)


DEFAULT_BUDGETS: dict[str, BudgetConfig] = {
    "bullet": BudgetConfig(200_000, 50_000, 3, 8),
    "blitz": BudgetConfig(600_000, 150_000, 5, 12),
    "rapid": BudgetConfig(1_500_000, 400_000, 6, 14),
}


@dataclass
class Config(_ExtraAttrs):
    engines: EnginesConfig = field(default_factory=EnginesConfig)
    certify: CertifyConfig = field(default_factory=CertifyConfig)
    steer: SteerConfig = field(default_factory=SteerConfig)
    budgets: dict[str, BudgetConfig] = field(
        default_factory=lambda: {k: replace(v) for k, v in DEFAULT_BUDGETS.items()}
    )
    timeman: TimemanConfig = field(default_factory=TimemanConfig)
    profiles: ProfilesConfig = field(default_factory=ProfilesConfig)
    mining: Section | None = None
    extra: dict[str, Any] = field(default_factory=dict)
    root: Path = REPO_ROOT
    path: Path | None = None

    def resolve_path(self, p: str | Path) -> Path:
        """Resolve `p` against the repo root unless it is absolute."""
        q = Path(p).expanduser()
        return q if q.is_absolute() else (self.root / q)


def _section(cls: type, raw: Any, name: str, base: Any = None) -> Any:
    """Build dataclass `cls` from a yaml mapping, keeping unknown keys in `.extra`.

    Missing keys take their value from `base` (an instance of `cls`) or the class defaults.
    """
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise TypeError(f"config section {name!r} must be a mapping, got {type(raw).__name__}")
    known = {f.name for f in fields(cls)} - {"extra"}
    kwargs: dict[str, Any] = {n: getattr(base, n) for n in known} if base is not None else {}
    extra: dict[str, Any] = {}
    for key, value in raw.items():
        if key in known:
            kwargs[key] = value
        else:
            extra[str(key)] = _wrap(value)
    obj = cls(**kwargs)
    obj.extra = extra
    return obj


def _coerce_ints(obj: Any, names: tuple[str, ...]) -> None:
    for n in names:
        v = getattr(obj, n)
        if v is not None and not isinstance(v, bool):
            setattr(obj, n, int(v))


def _repo_root_for(config_path: Path) -> Path:
    parent = config_path.resolve().parent
    return parent.parent if parent.name == "configs" else REPO_ROOT


def load_config(path: str | Path | None = None) -> Config:
    """Load and validate the LostFish config. Raises on a missing/invalid file."""
    if path is None:
        env = os.environ.get("LOSTFISH_CONFIG")
        path = Path(env) if env else DEFAULT_CONFIG_PATH
    cfg_path = Path(path).expanduser()
    with open(cfg_path) as fh:
        raw = yaml.safe_load(fh) or {}
    if not isinstance(raw, dict):
        raise TypeError(f"{cfg_path}: top level must be a mapping")

    root = _repo_root_for(cfg_path)
    engines = _section(EnginesConfig, raw.get("engines"), "engines")
    certify = _section(CertifyConfig, raw.get("certify"), "certify")
    steer = _section(SteerConfig, raw.get("steer"), "steer")
    timeman = _section(TimemanConfig, raw.get("timeman"), "timeman")
    profiles = _section(ProfilesConfig, raw.get("profiles"), "profiles")

    budgets: dict[str, BudgetConfig] = {}
    raw_budgets = raw.get("budgets") or {}
    if not isinstance(raw_budgets, dict):
        raise TypeError("config section 'budgets' must be a mapping")
    for tc in TC_CLASSES:
        budgets[tc] = _section(
            BudgetConfig, raw_budgets.get(tc), f"budgets.{tc}", base=DEFAULT_BUDGETS[tc]
        )
    for tc, value in raw_budgets.items():
        if tc not in budgets:
            budgets[str(tc)] = _section(BudgetConfig, value, f"budgets.{tc}")

    _coerce_ints(engines, ("hash_mb", "threads"))
    _coerce_ints(certify, ("multipv", "tolerance_cp", "tolerance_min_cp", "tighten_when_behind_cp"))
    _coerce_ints(timeman, ("moves_to_go_assumed", "min_move_ms", "reserve_ms", "nps_estimate"))
    timeman.increment_fraction = float(timeman.increment_fraction)
    steer.lambda_weakness = float(steer.lambda_weakness)
    for b in budgets.values():
        _coerce_ints(b, ("certify_nodes", "eval_nodes", "k", "proxy_depth_cap"))

    cfg = Config(
        engines=engines,
        certify=certify,
        steer=steer,
        budgets=budgets,
        timeman=timeman,
        profiles=profiles,
        mining=Section(raw["mining"]) if isinstance(raw.get("mining"), dict) else None,
        extra={
            str(k): _wrap(v)
            for k, v in raw.items()
            if k not in {"engines", "certify", "steer", "budgets", "timeman", "profiles", "mining"}
        },
        root=root,
        path=cfg_path.resolve(),
    )
    # Resolve paths against the repo root.
    engines.stockfish = str(cfg.resolve_path(engines.stockfish))
    if engines.fastchess:
        engines.fastchess = str(cfg.resolve_path(engines.fastchess))
    if engines.syzygy_path in ("", "<empty>"):
        engines.syzygy_path = None
    if engines.syzygy_path:
        engines.syzygy_path = os.pathsep.join(
            str(cfg.resolve_path(p)) for p in str(engines.syzygy_path).split(os.pathsep) if p
        )
    profiles.dir = str(cfg.resolve_path(profiles.dir))
    return cfg
