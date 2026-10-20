"""Assemble opponent profiles from fingerprints, clusters, openings and game stats.

    python -m mining.build_profile --bots all        # profiles/<bot>.json
    python -m mining.build_profile --generic         # profiles/_generic.json (pooled field)

Per-bot profiles need data/fingerprints/<bot>.json and data/clusters/<bot>.json (run
mining.fingerprint and mining.cluster first). `--generic` pools every bot's annotations and
fingerprints/clusters them directly. Every cluster with n >= min_cluster goes into
`weak_clusters`, sorted by uplift (uplift < 1 marks the bot's strong zones), so nearest-centroid
assignment covers the whole feature space.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter, defaultdict
from datetime import date, datetime
from typing import Any

import numpy as np
import pandas as pd

from lostfish.profiles import Profile, WeakCluster, save_profile
from mining.cluster import cluster_frame
from mining.common import (
    annot_path,
    bot_key,
    bots_json_path,
    bots_with,
    clusters_path,
    fingerprint_path,
    games_path,
    iter_games,
    mining_config,
    pgn_headers,
    read_json,
    select_bots,
    write_json,
)
from mining.fingerprint import fingerprint_frame

_COMMENT = re.compile(r"\{[^}]*\}|\([^)]*\)|\$\d+")
_MOVE_NO = re.compile(r"^\d+\.(\.\.)?$|^\d+\.\.\.$")
_RESULTS = {"1-0", "0-1", "1/2-1/2", "*"}
FEATURE_POV_NOTE = (
    "features: lostfish.features.extract(board, pov=bot=side to move, eval_deep, eval_shallow) "
    "with bot-POV evals; centroid units = raw / scale; assign to the nearest centroid"
)


def log(msg: str) -> None:
    print(f"[build_profile {datetime.now():%H:%M:%S}] {msg}", flush=True)


def san_moves(game_text: str, plies: int | None = None) -> list[str]:
    """SAN tokens of the main line straight from the movetext (no board replay)."""
    parts = game_text.split("\n\n", 1)
    body = _COMMENT.sub(" ", parts[1] if len(parts) > 1 else "")
    out = []
    for tok in body.split():
        if _MOVE_NO.match(tok) or tok in _RESULTS:
            continue
        tok = re.sub(r"^\d+\.+", "", tok)
        if tok:
            out.append(tok)
            if plies is not None and len(out) >= plies:
                break
    return out


def game_stats(bot: str, opening_plies: int) -> tuple[list[dict], dict[str, Any]]:
    """Opening repertoire (first `opening_plies` plies, grouped per colour) and result stats."""
    key = bot_key(bot)
    groups: dict[tuple[str, str], list[float]] = defaultdict(list)
    names: dict[tuple[str, str], Counter] = defaultdict(Counter)
    res = Counter()
    vs_bot = 0
    n = 0
    for g in iter_games(games_path(key)):
        h = pgn_headers(g)
        if bot_key(h.get("White", "")) == key:
            color, opp = "white", "Black"
        elif bot_key(h.get("Black", "")) == key:
            color, opp = "black", "White"
        else:
            continue
        r = {"1-0": 1.0, "0-1": 0.0, "1/2-1/2": 0.5}.get(h.get("Result", ""))
        if r is None:
            continue
        score = r if color == "white" else 1.0 - r
        n += 1
        vs_bot += h.get(f"{opp}Title") == "BOT"
        moves = san_moves(g)
        k = (color, " ".join(moves[:opening_plies]))
        groups[k].append(score)
        names[k][(h.get("ECO", ""), h.get("Opening", ""))] += 1
        outcome = "win" if score == 1 else ("draw" if score == 0.5 else "loss")
        term = h.get("Termination", "")
        if outcome == "loss":
            how = (
                "time" if "Time" in term else
                "mate" if moves and moves[-1].endswith("#") else
                "resign_or_other"
            )  # fmt: skip
            res[f"loss_{how}"] += 1
        elif outcome == "win":
            res["win_time" if "Time" in term else "win"] += 1
        else:
            res["draw"] += 1
        res["plies_total"] += len(moves)
    openings = []
    for (color, moves), scores in groups.items():
        (eco, name), _ = names[(color, moves)].most_common(1)[0]
        openings.append(
            {
                "color": color,
                "eco": eco,
                "name": name,
                "moves": moves,
                "count": len(scores),
                "score": round(float(np.mean(scores)), 4),
            }
        )
    openings.sort(key=lambda o: (-o["count"], o["moves"]))
    stats = {k: v for k, v in res.items() if k != "plies_total"}
    stats.update(
        {
            "n_games": n,
            "vs_bot_fraction": round(vs_bot / n, 4) if n else 0.0,
            "mean_plies": round(res["plies_total"] / n, 1) if n else 0.0,
        }
    )
    return openings, stats


def bot_rating(bot: str, df: pd.DataFrame | None) -> int | None:
    info = ((read_json(bots_json_path(), {}) or {}).get("bots") or {}).get(bot_key(bot)) or {}
    perfs = [p for p in (info.get("perfs") or {}).items() if p[0] in ("bullet", "blitz")]
    perfs = [p for p in perfs if p[1].get("rating") and p[1].get("games")]
    if perfs:
        return int(max(perfs, key=lambda p: p[1]["games"])[1]["rating"])
    if df is not None and "bot_rating" in df and df["bot_rating"].notna().any():
        return int(df["bot_rating"].dropna().median())
    return None


def profile_depth_agreement(fp: dict) -> dict[int, float]:
    """Imputed all-data curve over well-covered depths, so argmax == effective_depth."""
    c = fp["curves"]["all"]
    min_cov = fp.get("min_coverage", 0.5)
    return {
        d: round(float(v), 5)
        for d, (v, cov) in enumerate(zip(c["imputed"], c["coverage"], strict=True), start=1)
        if cov >= min_cov or d == 1
    }


def weak_clusters(cl: dict) -> list[WeakCluster]:
    return [
        WeakCluster(
            label=c["label"],
            centroid=[float(v) for v in c["centroid"]],
            scale=[float(v) for v in cl["scale"]],
            uplift=round(float(c["uplift"]), 4),
            blunder_rate=round(float(c["blunder_rate"]), 4),
            n=int(c["n"]),
        )
        for c in cl["clusters"]
        if c["kept"]
    ]


def assemble(name: str, df: pd.DataFrame, fp: dict, cl: dict, openings: list, stats: dict,
             rating: int | None, extra_notes: dict | None = None) -> Profile:  # fmt: skip
    notes = {
        "source": "mining v1",
        "nodes": sorted(int(v) for v in df["nodes"].dropna().unique()) if "nodes" in df else [],
        "feature_pov": FEATURE_POV_NOTE,
        "final_agreement": round(fp["final_agreement"], 5),
        "effective_depth_train": fp["effective_depth_train"],
        "test_agreement_effective": round(fp["test_agreement_effective"], 5),
        "test_agreement_se": round(fp["test_agreement_se"], 5),
        "test_best_fixed_depth": fp["test_best_fixed_depth"],
        "test_best_fixed_agreement": round(fp["test_best_fixed_agreement"], 5),
        "gate_pass": fp["gate_pass"],
        "depth_agreement_raw": fp["curves"]["all"]["raw"],
        "depth_coverage": fp["curves"]["all"]["coverage"],
        "by_phase": fp["by_phase"],
        "blunder_cp": cl.get("blunder_cp"),
        "clip_cp": cl.get("clip_cp"),
        "k": cl.get("k"),
        "feature_mean": cl.get("mean"),
        "all_clusters": [
            {k: c[k] for k in ("label", "n", "blunder_rate", "uplift", "z", "kept")}
            for c in cl["clusters"]
        ],
        "results": stats,
        **(extra_notes or {}),
    }
    return Profile(
        name=name,
        built_at=date.today().isoformat(),
        n_games=int(df["game_id"].nunique()),
        n_positions=len(df),
        rating=rating,
        proxy="stockfish_depth",
        effective_depth=int(fp["effective_depth"]),
        depth_agreement=profile_depth_agreement(fp),
        base_blunder_rate=round(float(cl["base_blunder_rate"]), 5),
        weak_clusters=weak_clusters(cl),
        openings=openings,
        notes=notes,
    )


def build_bot(bot: str, opening_plies: int, max_openings: int) -> Profile | None:
    fp, cl = read_json(fingerprint_path(bot)), read_json(clusters_path(bot))
    if not fp or not cl or not annot_path(bot).exists():
        log(f"{bot}: missing fingerprint/clusters/annotations, skipping")
        return None
    df = pd.read_parquet(annot_path(bot))
    openings, stats = game_stats(bot, opening_plies)
    return assemble(bot, df, fp, cl, openings[:max_openings], stats, bot_rating(bot, df))


def build_generic(cfg: dict, opening_plies: int, max_openings: int, max_positions: int) -> Profile:
    bots = bots_with("annot")
    df = pd.concat([pd.read_parquet(annot_path(b)) for b in bots], ignore_index=True)
    df["game_id"] = df["bot"] + ":" + df["game_id"]
    fp = fingerprint_frame(df, min_coverage=float(cfg["min_coverage"]))
    sample = df.sample(n=min(len(df), max_positions), random_state=0) if len(df) else df
    cl = cluster_frame(
        sample, k=int(cfg["k"]), blunder_cp=int(cfg["blunder_cp"]), clip_cp=int(cfg["clip_cp"]),
        min_cluster=int(cfg["min_cluster"]),
    )  # fmt: skip
    cl.pop("labels", None)
    write_json(clusters_path("_generic"), {"bot": "_generic", "bots": bots, **cl})
    write_json(fingerprint_path("_generic"), {"bot": "_generic", "bots": bots, **fp})
    openings: Counter = Counter()
    pooled: dict[tuple[str, str], dict] = {}
    totals: Counter = Counter()
    for b in bots:
        ops, stats = game_stats(b, opening_plies)
        totals.update({k: v for k, v in stats.items() if isinstance(v, int)})
        for o in ops:
            k = (o["color"], o["moves"])
            p = pooled.setdefault(k, {**o, "count": 0, "score_sum": 0.0})
            p["count"] += o["count"]
            p["score_sum"] += o["score"] * o["count"]
            openings[k] += o["count"]
    ops = []
    for k, _ in openings.most_common(max_openings):
        p = pooled[k]
        ops.append({**{x: p[x] for x in ("color", "eco", "name", "moves", "count")},
                    "score": round(p["score_sum"] / p["count"], 4)})  # fmt: skip
    ratings = [r for r in (bot_rating(b, None) for b in bots) if r]
    return assemble(
        "_generic", df, fp, cl, ops, dict(totals),
        int(np.median(ratings)) if ratings else None,
        {"bots": bots, "cluster_sample": len(sample)},
    )  # fmt: skip


def main(argv: list[str] | None = None) -> int:
    cfg = mining_config()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--bots", default="", help="'all' or comma-separated bot ids")
    ap.add_argument("--generic", action="store_true", help="build profiles/_generic.json")
    ap.add_argument("--opening-plies", type=int, default=int(cfg["opening_plies"]))
    ap.add_argument("--max-openings", type=int, default=40)
    ap.add_argument("--max-positions", type=int, default=60000, help="cluster sample (generic)")
    args = ap.parse_args(argv)
    if not args.bots and not args.generic:
        ap.error("give --bots and/or --generic")
    if args.bots:
        for bot in select_bots(args.bots, "fingerprints"):
            prof = build_bot(bot, args.opening_plies, args.max_openings)
            if prof is None:
                continue
            path = save_profile(prof, None)
            top = prof.weak_clusters[0] if prof.weak_clusters else None
            log(
                f"{bot}: depth {prof.effective_depth}, base blunder {prof.base_blunder_rate:.3f}, "
                + (f"top cluster x{top.uplift:.2f} '{top.label}'" if top else "no clusters")
                + f" -> {path}"
            )
    if args.generic:
        prof = build_generic(cfg, args.opening_plies, args.max_openings, args.max_positions)
        path = save_profile(prof, None)
        log(f"_generic: {prof.n_positions} positions, depth {prof.effective_depth} -> {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
