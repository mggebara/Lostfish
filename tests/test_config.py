"""configs/lostfish.yaml -> Config (pure, no engines)."""

from __future__ import annotations

import copy
from pathlib import Path

import pytest

from lostfish.config import REPO_ROOT, Config, Section, load_config


def test_default_config_loads() -> None:
    cfg = load_config()
    assert isinstance(cfg, Config)
    assert cfg.root == REPO_ROOT
    assert set(cfg.budgets) >= {"bullet", "blitz", "rapid"}
    assert cfg.budgets["blitz"].certify_nodes > cfg.budgets["bullet"].certify_nodes
    assert cfg.engines.threads == 1
    assert cfg.timeman.nps_estimate > 0
    assert cfg.certify.multipv >= 1
    assert cfg.profiles.fallback == "_generic"


def test_paths_resolve_against_repo_root() -> None:
    cfg = load_config()
    assert Path(cfg.engines.stockfish).is_absolute()
    assert Path(cfg.engines.stockfish) == REPO_ROOT / "engines" / "stockfish"
    assert Path(cfg.profiles.dir) == REPO_ROOT / "profiles"
    assert cfg.engines.syzygy_path is None or Path(cfg.engines.syzygy_path).is_absolute()


def _write(dirpath: Path, text: str) -> Path:
    dirpath.mkdir(parents=True, exist_ok=True)
    p = dirpath / "lostfish.yaml"
    p.write_text(text)
    return p


YAML = """
engines:
  stockfish: bin/sf
  syzygy_path: "<empty>"
  hash_mb: 32
  future_engine_key: 7
certify:
  tolerance_cp: 25
  new_knob: 3
budgets:
  bullet: { certify_nodes: 1000 }
  marathon: { certify_nodes: 9, eval_nodes: 1, k: 1, proxy_depth_cap: 1 }
timeman:
  nps_estimate: 500000
mining:
  nodes: 20000
  sub: { a: 1 }
agent_c_section:
  lambda: 0.5
"""


def test_env_override_and_repo_root_from_configs_dir(tmp_path, monkeypatch) -> None:
    path = _write(tmp_path / "configs", YAML)
    monkeypatch.setenv("LOSTFISH_CONFIG", str(path))
    cfg = load_config()
    assert cfg.path == path.resolve()
    assert cfg.root == tmp_path.resolve()
    assert cfg.engines.stockfish == str(tmp_path.resolve() / "bin" / "sf")
    assert cfg.engines.syzygy_path is None
    assert cfg.engines.hash_mb == 32
    assert cfg.timeman.nps_estimate == 500000
    assert cfg.timeman.min_move_ms == 50  # default for a missing key


def test_config_outside_configs_dir_uses_checkout_root(tmp_path) -> None:
    cfg = load_config(_write(tmp_path / "elsewhere", YAML))
    assert cfg.root == REPO_ROOT
    assert cfg.engines.stockfish == str(REPO_ROOT / "bin" / "sf")


def test_unknown_keys_are_kept(tmp_path) -> None:
    cfg = load_config(_write(tmp_path / "configs", YAML))
    assert cfg.engines.extra == {"future_engine_key": 7}
    assert cfg.engines.future_engine_key == 7  # attribute access falls back to .extra
    assert cfg.certify.new_knob == 3
    assert cfg.certify.tolerance_cp == 25
    assert cfg.extra["agent_c_section"]["lambda"] == 0.5
    assert isinstance(cfg.agent_c_section, Section)
    assert cfg.mining is not None and cfg.mining.nodes == 20000 and cfg.mining.sub.a == 1
    with pytest.raises(AttributeError):
        _ = cfg.certify.not_there


def test_partial_budgets_keep_class_defaults(tmp_path) -> None:
    cfg = load_config(_write(tmp_path / "configs", YAML))
    assert cfg.budgets["bullet"].certify_nodes == 1000
    assert cfg.budgets["bullet"].k == 3  # bullet default, not the generic dataclass default
    assert cfg.budgets["rapid"].certify_nodes == 1_500_000  # missing class -> default
    assert cfg.budgets["marathon"].k == 1  # extra classes allowed


def test_missing_sections_use_defaults(tmp_path) -> None:
    cfg = load_config(_write(tmp_path / "configs", "{}\n"))
    assert cfg.certify.tolerance_cp == 30
    assert cfg.budgets["blitz"].certify_nodes == 600_000
    assert cfg.mining is None


def test_bad_config_raises(tmp_path) -> None:
    with pytest.raises(TypeError):
        load_config(_write(tmp_path / "a" / "configs", "- just\n- a list\n"))
    with pytest.raises(TypeError):
        load_config(_write(tmp_path / "b" / "configs", "certify: 3\n"))
    with pytest.raises(OSError):
        load_config(tmp_path / "missing.yaml")


def test_config_deepcopies() -> None:
    cfg = load_config()
    dup = copy.deepcopy(cfg)
    dup.engines.hash_mb = 1
    assert cfg.engines.hash_mb != 1
    assert dup.budgets["blitz"] is not cfg.budgets["blitz"]
