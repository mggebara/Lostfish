"""Effective-depth fingerprint: which Stockfish depth best predicts the bot's moves?

    python -m mining.fingerprint --bots all

For every annotated position we know Stockfish's best move after each completed iteration
(`best_by_depth`). Two agreement curves are reported per depth d = 1..max_depth:

* raw: agreement over positions where depth d was completed (the PLAN definition). Biased at high
  depths, because only simple positions complete deep iterations within the node budget;
* imputed: depth d's move where it exists, else the search's final move (the best estimate of
  deeper play). Every depth is scored on the same positions, so depths are comparable.

`effective_depth` is chosen on the training games (80/20 split by a hash of game_id) as the argmax
of the imputed curve over the *resolvable* depths (completed in >= min_coverage of positions),
ties toward the lower depth; held-out agreement at that depth is compared with every resolvable
fixed depth (Phase 1 gate). Deeper "depths" would only be the node-limited search's final move,
which is reported separately (`test_agreement_final`); `depth_capped` flags bots whose curve still
rises at the deepest resolvable depth (their true depth exceeds what the node budget measures).
The summary (`data/fingerprints/_summary.json`) compares per-bot depths with the best single
global depth across bots. The profile depth is then refit on all games with the same rule.
"""

from __future__ import annotations

import argparse
import sys
import zlib
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd

from mining.common import (
    DATA_DIR,
    annot_path,
    depth_dict_from_json,
    fingerprint_path,
    mining_config,
    read_json,
    select_bots,
    write_json,
)

CP_BUCKETS = [(0, 50), (50, 150), (150, 300), (300, 600), (600, 10**9)]


def log(msg: str) -> None:
    print(f"[fingerprint {datetime.now():%H:%M:%S}] {msg}", flush=True)


def is_test_game(game_id: str, test_fraction: float = 0.2) -> bool:
    """Deterministic split by game id (stable across runs and machines)."""
    return (zlib.crc32(str(game_id).encode()) % 10_000) < test_fraction * 10_000


def phase_of(fen: str) -> str:
    placement = fen.split(" ", 1)[0]
    men = sum(ch.isalpha() for ch in placement)
    pieces = sum(ch in "nbrqNBRQ" for ch in placement)
    if men >= 28:
        return "opening"
    return "endgame" if pieces <= 6 else "middlegame"


def cp_bucket(cp: float) -> str:
    a = abs(cp)
    for lo, hi in CP_BUCKETS:
        if lo <= a < hi:
            return f"{lo}-{hi}" if hi < 10**9 else f"{lo}+"
    return f"{CP_BUCKETS[-1][0]}+"


def move_matrix(df: pd.DataFrame, max_depth: int) -> tuple[np.ndarray, np.ndarray]:
    """(raw, imputed) object arrays [n, max_depth]; column d-1 is the best move at depth d."""
    n = len(df)
    raw = np.full((n, max_depth), None, dtype=object)
    imp = np.full((n, max_depth), None, dtype=object)
    for i, (bbd, best) in enumerate(zip(df["best_by_depth"], df["best"], strict=True)):
        moves = depth_dict_from_json(bbd)
        for d in range(1, max_depth + 1):
            m = moves.get(d)
            raw[i, d - 1] = m
            imp[i, d - 1] = m if m is not None else best
    return raw, imp


def curves(raw: np.ndarray, imp: np.ndarray, played: np.ndarray) -> dict[str, list]:
    have = raw.astype(bool)  # None -> False, a UCI string -> True
    hit_raw = (raw == played[:, None]) & have
    hit_imp = imp == played[:, None]
    n = max(len(played), 1)
    cov = have.sum(axis=0)
    return {
        "coverage": (cov / n).round(4).tolist(),
        "n": cov.astype(int).tolist(),
        "raw": [float(h / c) if c else None for h, c in zip(hit_raw.sum(0), cov, strict=True)],
        "imputed": (hit_imp.sum(axis=0) / n).tolist(),
    }


def resolvable_depth(coverage: list[float], min_coverage: float) -> int:
    """Deepest depth completed in >= min_coverage of positions (at least 1)."""
    return max([d for d, c in enumerate(coverage, start=1) if c >= min_coverage] or [1])


def pick_depth(imputed: list[float], coverage: list[float], min_coverage: float) -> int:
    """Argmax of the imputed curve over resolvable depths; ties -> lower depth."""
    top = resolvable_depth(coverage, min_coverage)
    best_d, best_v = 1, -1.0
    for d, v in enumerate(imputed[:top], start=1):
        if v > best_v + 1e-12:
            best_d, best_v = d, v
    return best_d


def _agree_by(groups: pd.Series, played: np.ndarray, pred: np.ndarray, final: np.ndarray) -> dict:
    out: dict[str, Any] = {}
    for g in sorted(groups.unique()):
        m = (groups == g).to_numpy()
        out[g] = {
            "n": int(m.sum()),
            "agree_effective": float((pred[m] == played[m]).mean()),
            "agree_final": float(final[m].mean()),
        }
    return out


def fingerprint_frame(
    df: pd.DataFrame,
    *,
    max_depth: int = 20,
    test_fraction: float = 0.2,
    min_coverage: float = 0.5,
) -> dict[str, Any]:
    """Fingerprint one bot's (or a pooled) annotation frame. Pure function of the frame."""
    df = df.reset_index(drop=True)
    played = df["played"].to_numpy(dtype=object)
    final = (df["played"] == df["best"]).to_numpy()
    raw, imp = move_matrix(df, max_depth)
    test = np.array([is_test_game(g, test_fraction) for g in df["game_id"]], dtype=bool)
    if test.all() or not test.any():  # tiny data: fall back to an alternating split by game
        ids = {g: i for i, g in enumerate(pd.unique(df["game_id"]))}
        test = np.array([ids[g] % 5 == 4 for g in df["game_id"]], dtype=bool)
    train = ~test
    c_all = curves(raw, imp, played)
    c_tr = curves(raw[train], imp[train], played[train])
    c_te = curves(raw[test], imp[test], played[test])
    top = resolvable_depth(c_tr["coverage"], min_coverage)
    eff_train = pick_depth(c_tr["imputed"], c_tr["coverage"], min_coverage)
    test_at_eff = c_te["imputed"][eff_train - 1] if test.any() else float("nan")
    # fixed-depth competitors: the same resolvable range (deeper "depths" would just be the
    # final move of the node-limited search, reported separately as test_agreement_final)
    best_fixed = int(np.argmax(c_te["imputed"][:top])) + 1 if test.any() else eff_train
    best_fixed_v = c_te["imputed"][best_fixed - 1] if test.any() else float("nan")
    n_test = int(test.sum())
    se = float(np.sqrt(max(test_at_eff * (1 - test_at_eff), 1e-9) / max(n_test, 1)))
    eff_all = pick_depth(c_all["imputed"], c_all["coverage"], min_coverage)
    top_all = resolvable_depth(c_all["coverage"], min_coverage)
    pred_all = imp[:, eff_all - 1]
    final_all = float(final.mean()) if len(df) else 0.0
    return {
        "n_games": int(df["game_id"].nunique()),
        "n_positions": len(df),
        "n_train": int(train.sum()),
        "n_test": n_test,
        "n_test_games": int(df.loc[test, "game_id"].nunique()),
        "max_depth": max_depth,
        "min_coverage": min_coverage,
        "final_agreement": final_all,
        "effective_depth": eff_all,
        "effective_depth_train": eff_train,
        "resolvable_depth": top_all,
        # agreement still rising at the deepest resolvable depth: the bot's real effective depth
        # is probably deeper than this node budget can measure (a lower bound, not a fit)
        "depth_capped": bool(
            eff_all == top_all and c_all["imputed"][eff_all - 1] - min(c_all["imputed"]) > 0.02
        ),
        "test_agreement_effective": test_at_eff,
        "test_agreement_se": se,
        "test_best_fixed_depth": best_fixed,
        "test_best_fixed_agreement": best_fixed_v,
        "test_gap_to_best_fixed": test_at_eff - best_fixed_v,
        "gate_pass": bool(test_at_eff >= best_fixed_v - 1e-12),
        "test_agreement_final": float(final[test].mean()) if test.any() else float("nan"),
        "curves": {"all": c_all, "train": c_tr, "test": c_te},
        "by_phase": _agree_by(df["fen"].map(phase_of), played, pred_all, final),
        "by_cp_bucket": _agree_by(df["cp_best"].map(cp_bucket), played, pred_all, final),
    }


def summarise(fps: dict[str, dict]) -> dict[str, Any]:
    """Across bots: per-bot fingerprinted depth vs the best single global fixed depth."""
    fps = {b: f for b, f in fps.items() if f.get("n_test", 0) > 0}
    if not fps:
        return {"n_bots": 0}
    max_depth = min(
        resolvable_depth(f["curves"]["train"]["coverage"], f.get("min_coverage", 0.5))
        for f in fps.values()
    )
    per_depth = np.array([f["curves"]["test"]["imputed"][:max_depth] for f in fps.values()])
    fp = np.array([f["test_agreement_effective"] for f in fps.values()])
    weights = np.array([f["n_test"] for f in fps.values()], dtype=float)
    mean_by_depth = per_depth.mean(axis=0)
    best_global = int(np.argmax(mean_by_depth)) + 1
    wins = int((fp >= per_depth[:, best_global - 1] - 1e-12).sum())
    return {
        "n_bots": len(fps),
        "common_resolvable_depth": max_depth,
        "fingerprinted_mean_test_agreement": float(fp.mean()),
        "fingerprinted_pooled_test_agreement": float((fp * weights).sum() / weights.sum()),
        "fixed_depth_mean_test_agreement": {
            str(d): float(v) for d, v in enumerate(mean_by_depth, start=1)
        },
        "best_global_fixed_depth": best_global,
        "best_global_fixed_mean_test_agreement": float(mean_by_depth[best_global - 1]),
        "gate_pass_vs_global_fixed": bool(fp.mean() >= mean_by_depth[best_global - 1] - 1e-12),
        "bots_at_least_global_fixed": wins,
        "bots_at_least_per_bot_oracle_fixed": int(sum(f["gate_pass"] for f in fps.values())),
        "bots_depth_capped": sorted(b for b, f in fps.items() if f.get("depth_capped")),
        "final_search_mean_test_agreement": float(
            np.mean([f["test_agreement_final"] for f in fps.values()])
        ),
    }


def main(argv: list[str] | None = None) -> int:
    cfg = mining_config()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--bots", default="all")
    ap.add_argument("--max-depth", type=int, default=20)
    ap.add_argument("--test-fraction", type=float, default=float(cfg["test_fraction"]))
    ap.add_argument("--min-coverage", type=float, default=float(cfg["min_coverage"]))
    ap.add_argument(
        "--max-abs-cp",
        type=int,
        default=0,
        help="only positions with |cp_best| below this (0 = all); lopsided positions flatten "
        "the depth curve",
    )
    args = ap.parse_args(argv)
    for bot in select_bots(args.bots, "annot"):
        path = annot_path(bot)
        if not path.exists():
            log(f"{bot}: no annotations, skipping")
            continue
        df = pd.read_parquet(path)
        if args.max_abs_cp:
            df = df[df["cp_best"].abs() < args.max_abs_cp]
        if df.empty:
            continue
        fp = {"bot": bot, "built_at": datetime.now().isoformat(timespec="seconds")}
        fp["max_abs_cp"] = args.max_abs_cp or None
        fp |= fingerprint_frame(
            df,
            max_depth=args.max_depth,
            test_fraction=args.test_fraction,
            min_coverage=args.min_coverage,
        )
        write_json(fingerprint_path(bot), fp)
        log(
            f"{bot}: {fp['n_positions']} pos / {fp['n_games']} games, eff depth "
            f"{fp['effective_depth']} (train {fp['effective_depth_train']}), test "
            f"{fp['test_agreement_effective']:.3f}±{fp['test_agreement_se']:.3f} vs best fixed "
            f"d{fp['test_best_fixed_depth']} {fp['test_best_fixed_agreement']:.3f}, final "
            f"{fp['final_agreement']:.3f}" + (" [depth capped]" if fp["depth_capped"] else "")
        )
    fps = {}
    for p in sorted((DATA_DIR / "fingerprints").glob("*.json")):
        if not p.name.startswith("_"):
            fps[p.stem] = read_json(p, {}) or {}
    summary = summarise(fps)
    write_json(DATA_DIR / "fingerprints" / "_summary.json", summary)
    if summary.get("n_bots"):
        log(
            f"summary over {summary['n_bots']} bots: fingerprinted "
            f"{summary['fingerprinted_mean_test_agreement']:.3f} vs best global fixed depth "
            f"d{summary['best_global_fixed_depth']} "
            f"{summary['best_global_fixed_mean_test_agreement']:.3f}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
