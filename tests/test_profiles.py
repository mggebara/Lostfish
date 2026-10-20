"""lostfish.profiles: round trip, fallback chain, UCI_Opponent parsing."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from lostfish.profiles import (
    DEFAULT_EFFECTIVE_DEPTH,
    Profile,
    WeakCluster,
    load_profile,
    parse_uci_opponent,
    save_profile,
)


def cfg_for(tmp_path: Path, fallback: str = "_generic") -> SimpleNamespace:
    return SimpleNamespace(profiles=SimpleNamespace(dir=str(tmp_path), fallback=fallback))


def sample(name: str = "SomeBot") -> Profile:
    return Profile(
        name=name,
        version=1,
        built_at="2026-10-19",
        n_games=300,
        n_positions=9000,
        rating=2100,
        proxy="stockfish_depth",
        effective_depth=7,
        depth_agreement={1: 0.3, 7: 0.55, 12: 0.5},
        base_blunder_rate=0.08,
        weak_clusters=[
            WeakCluster("high passed_pawns_them", [0.1, 2.0], [1.0, 0.5], 1.8, 0.144, 120)
        ],
        openings=[{"eco": "C20", "name": "KP", "moves": "e4 e5", "count": 4, "score": 0.5}],
        notes={"k": 8},
    )


def test_round_trip(tmp_path: Path) -> None:
    cfg = cfg_for(tmp_path)
    path = save_profile(sample(), cfg)
    assert path == tmp_path / "somebot.json"
    loaded = load_profile("somebot", cfg)
    assert loaded == sample("somebot")
    assert isinstance(next(iter(loaded.depth_agreement)), int)
    assert isinstance(loaded.weak_clusters[0], WeakCluster)


def test_case_insensitive(tmp_path: Path) -> None:
    cfg = cfg_for(tmp_path)
    save_profile(sample(), cfg)
    assert load_profile("SOMEBOT", cfg).name == "somebot"
    (tmp_path / "MixedCase.json").write_text(json.dumps({"name": "MixedCase"}))
    assert load_profile("mixedcase", cfg).name == "mixedcase"


def test_fallback_chain(tmp_path: Path) -> None:
    cfg = cfg_for(tmp_path)
    # nothing on disk -> built-in default
    p = load_profile("unknown", cfg)
    assert p.effective_depth == DEFAULT_EFFECTIVE_DEPTH and p.weak_clusters == []
    assert p.name == "_generic"
    # generic present -> generic
    save_profile(sample("_generic"), cfg)
    assert load_profile("unknown", cfg).name == "_generic"
    assert load_profile(None, cfg).name == "_generic"
    assert load_profile("", cfg).name == "_generic"
    # corrupt profile -> generic, never raises
    (tmp_path / "broken.json").write_text("{not json")
    assert load_profile("broken", cfg).name == "_generic"
    # path tricks are ignored
    assert load_profile("../etc/passwd", cfg).name == "_generic"


def test_cfg_variants(tmp_path: Path) -> None:
    save_profile(sample("x"), {"profiles": {"dir": str(tmp_path)}})
    assert load_profile("x", {"profiles": {"dir": str(tmp_path)}}).name == "x"
    assert load_profile("x", SimpleNamespace()).name in ("x", "_generic")  # no .profiles: default
    assert isinstance(load_profile("definitely-not-a-bot", None), Profile)
    custom = cfg_for(tmp_path, fallback="x")
    assert load_profile("nobody", custom).name == "x"


def test_missing_keys_get_defaults(tmp_path: Path) -> None:
    (tmp_path / "sparse.json").write_text(json.dumps({"name": "sparse", "effective_depth": 5}))
    p = load_profile("sparse", cfg_for(tmp_path))
    assert p.effective_depth == 5 and p.weak_clusters == [] and p.rating is None


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("BOT 2300 computer maia1", ("maia1", 2300, "computer")),
        ("none none human someone", ("someone", None, "human")),
        ("GM 2700 human Magnus", ("Magnus", 2700, "human")),
        ("BOT none computer Some-Bot_2", ("Some-Bot_2", None, "computer")),
        ("maia1", ("maia1", None, None)),
        ("", (None, None, None)),
        ("   ", (None, None, None)),
        ("none", (None, None, None)),
    ],
)
def test_parse_uci_opponent(value: str, expected: tuple) -> None:
    assert parse_uci_opponent(value) == expected
