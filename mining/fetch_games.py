"""Fetch active Lichess BOT accounts and their rated bullet/blitz games.

    python -m mining.fetch_games --top 40 --max-games 300 --perf bullet,blitz
    python -m mining.fetch_games --bots maia1,maia5 --max-games 300

Good-citizen rules: one request at a time, an identifying User-Agent, 60 s back-off on HTTP 429,
and the token (Authorization: Bearer $LICHESS_BOT_TOKEN) only when that env var is set.
Resumable and idempotent: games are de-duplicated by id via data/games/<bot>.meta.json, newer
games are fetched with `since=newest+1`, and older ones are back-filled with `until=oldest-1`.
"""

from __future__ import annotations

import argparse
import calendar
import json
import os
import sys
import time
from datetime import UTC, datetime
from typing import Any

import requests

from mining.common import (
    USER_AGENT,
    append_pgn_zst,
    bot_key,
    bots_json_path,
    game_id_from_headers,
    games_meta_path,
    games_path,
    mining_config,
    pgn_headers,
    read_json,
    split_pgn,
    write_json,
)

API = "https://lichess.org"
SEED_BOTS = [
    "maia1", "maia5", "maia9", "Nikitosik-ai", "Weiawaga", "Boris-Trapsky", "likeawizard-bot",
    "ToromBot", "Endogenetic-Bot", "Dark_Nebula", "ArasanX", "YoBot_v2", "turochamp",
]  # fmt: skip


def log(msg: str) -> None:
    print(f"[fetch {datetime.now():%H:%M:%S}] {msg}", flush=True)


def now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


class Lichess:
    """Sequential, polite HTTP client."""

    def __init__(self, min_interval_s: float = 1.0) -> None:
        self.s = requests.Session()
        self.s.headers["User-Agent"] = USER_AGENT
        token = os.environ.get("LICHESS_BOT_TOKEN")
        if token:
            self.s.headers["Authorization"] = f"Bearer {token}"
        self.min_interval_s = min_interval_s
        self._last = 0.0

    def request(self, method: str, path: str, **kw: Any) -> requests.Response:
        for attempt in range(6):
            wait = self.min_interval_s - (time.monotonic() - self._last)
            if wait > 0:
                time.sleep(wait)
            try:
                r = self.s.request(method, API + path, timeout=(15, 120), **kw)
            except requests.RequestException as e:
                log(f"network error on {path}: {e}; retry in {10 * (attempt + 1)} s")
                time.sleep(10 * (attempt + 1))
                continue
            finally:
                self._last = time.monotonic()
            if r.status_code == 429:
                log(f"429 on {path}; sleeping 60 s")
                time.sleep(60)
                continue
            return r
        raise RuntimeError(f"giving up on {path}")

    def online_bots(self, nb: int = 300) -> list[dict]:
        r = self.request("GET", "/api/bot/online", params={"nb": nb}, stream=True)
        r.raise_for_status()
        return [json.loads(line) for line in r.iter_lines() if line]

    def users(self, ids: list[str]) -> list[dict]:
        out: list[dict] = []
        for i in range(0, len(ids), 300):
            r = self.request("POST", "/api/users", data=",".join(ids[i : i + 300]))
            if r.ok:
                out.extend(r.json())
        return out

    def games(self, username: str, params: dict[str, Any]) -> tuple[int, str]:
        r = self.request(
            "GET",
            f"/api/games/user/{username}",
            params=params,
            headers={"Accept": "application/x-chess-pgn"},
            stream=True,
        )
        if r.status_code != 200:
            return r.status_code, ""
        chunks = [c for c in r.iter_content(chunk_size=1 << 16) if c]
        return 200, b"".join(chunks).decode("utf-8", errors="replace")


# ---------------------------------------------------------------------------------------------
# bots.json


def slim_user(u: dict) -> dict:
    perfs = u.get("perfs") or {}
    return {
        "id": u.get("id") or bot_key(u.get("username", "")),
        "username": u.get("username") or u.get("id"),
        "title": u.get("title"),
        "perfs": {
            p: {"rating": perfs[p].get("rating"), "games": perfs[p].get("games", 0)}
            for p in ("bullet", "blitz", "rapid")
            if p in perfs
        },
        "disabled": bool(u.get("disabled")),
        "tosViolation": bool(u.get("tosViolation")),
    }


def merge_bot(bots: dict[str, dict], user: dict, source: str) -> None:
    info = slim_user(user)
    key = bot_key(info["id"])
    cur = bots.setdefault(key, {"id": key, "sources": [], "first_seen": now_iso()})
    for k, v in info.items():
        if v or k not in cur:
            cur[k] = v
    if source not in cur["sources"]:
        cur["sources"].append(source)
    if source == "online":
        cur["last_online"] = now_iso()


def activity(bot: dict, perfs: list[str]) -> int:
    return sum(int((bot.get("perfs") or {}).get(p, {}).get("games") or 0) for p in perfs)


def eligible(bot: dict) -> bool:
    return bot.get("title") == "BOT" and not bot.get("disabled") and not bot.get("tosViolation")


# ---------------------------------------------------------------------------------------------
# games


def created_ms(headers: dict[str, str]) -> int | None:
    try:
        dt = datetime.strptime(f"{headers['UTCDate']} {headers['UTCTime']}", "%Y.%m.%d %H:%M:%S")
    except (KeyError, ValueError):
        return None
    return calendar.timegm(dt.timetuple()) * 1000


def fetch_bot(
    api: Lichess,
    bot: dict,
    *,
    target: int,
    perf: str,
    since_days: int,
    min_games: int,
    refresh: bool,
    crawled: dict[str, str],
) -> dict:
    """Download games for one bot until `target` games are stored. Returns the meta dict."""
    key, username = bot_key(bot["id"]), bot.get("username") or bot["id"]
    meta_path = games_meta_path(key)
    meta = read_json(meta_path, {}) or {}
    ids: set[str] = set(meta.get("game_ids", []))
    window_ms = int((time.time() - since_days * 86400) * 1000)
    base = {
        "rated": "true", "perfType": perf, "moves": "true", "clocks": "true",
        "opening": "true", "evals": "false",
    }  # fmt: skip

    def pull(extra: dict[str, Any], n: int) -> int:
        t0 = time.monotonic()
        status, text = api.games(username, {**base, "max": n, **extra})
        if status != 200:
            log(f"  {username}: HTTP {status}")
            meta["last_status"] = status
            return -1
        fresh: list[str] = []
        returned = split_pgn(text)
        for g in returned:
            if len(fresh) >= n:  # the export may return more than `max` (seen: 300 for 288)
                break
            h = pgn_headers(g)
            gid = game_id_from_headers(h)
            if not gid or gid in ids or h.get("Variant", "Standard") != "Standard":
                continue
            ids.add(gid)
            fresh.append(g)
            ms = created_ms(h)
            if ms is not None:
                meta["newest_ms"] = max(meta.get("newest_ms") or 0, ms)
                meta["oldest_ms"] = min(meta.get("oldest_ms") or ms, ms)
            for side in ("White", "Black"):
                if h.get(f"{side}Title") == "BOT" and bot_key(h.get(side, "")) != key:
                    crawled.setdefault(bot_key(h[side]), h[side])
        append_pgn_zst(games_path(key), fresh)
        dt = time.monotonic() - t0
        log(f"  {username}: +{len(fresh)} games ({len(fresh) / max(dt, 1e-6):.1f}/s)")
        return len(returned)

    stored = len(ids)
    if stored >= target and not refresh:
        log(f"{username}: {stored} games stored, skipping")
        return meta
    # newer games first (also the first fetch), then back-fill older ones
    since = max(window_ms, (meta.get("newest_ms") or 0) + 1) if stored else window_ms
    got = pull({"since": since}, target if refresh else target - stored)
    if got >= 0 and len(ids) < target and stored and not meta.get("old_exhausted"):
        need = target - len(ids)
        got_old = pull({"since": window_ms, "until": (meta.get("oldest_ms") or 0) - 1}, need)
        if 0 <= got_old < need:
            meta["old_exhausted"] = True
    elif got >= 0 and not stored and got < target:
        meta["old_exhausted"] = True
    meta.update(
        {
            "bot": key,
            "username": username,
            "perf": perf,
            "since_days": since_days,
            "n_games": len(ids),
            "game_ids": sorted(ids),
            "fetched_at": now_iso(),
            "insufficient": len(ids) < min_games,
        }
    )
    write_json(meta_path, meta)
    return meta


def main(argv: list[str] | None = None) -> int:
    cfg = mining_config()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--top", type=int, default=40, help="number of bots to fetch")
    ap.add_argument("--bots", default="", help="comma-separated usernames (overrides --top)")
    ap.add_argument("--max-games", type=int, default=int(cfg["max_games"]))
    ap.add_argument("--min-games", type=int, default=int(cfg["min_games"]))
    ap.add_argument("--perf", default=str(cfg["perf"]))
    ap.add_argument("--since-days", type=int, default=int(cfg["since_days"]))
    ap.add_argument("--refresh", action="store_true", help="also pull games newer than stored")
    ap.add_argument("--no-seed", action="store_true", help="do not merge the built-in seed list")
    args = ap.parse_args(argv)
    perfs = [p.strip() for p in args.perf.split(",") if p.strip()]

    api = Lichess()
    store = read_json(bots_json_path(), {}) or {}
    bots: dict[str, dict] = store.get("bots", {})
    online = api.online_bots(300)
    for u in online:
        merge_bot(bots, u, "online")
    online_ids = {bot_key(u["id"]) for u in online}
    log(f"{len(online)} bots online; {len(bots)} known")

    wanted = [bot_key(b) for b in args.bots.split(",") if b.strip()]
    lookup = set(wanted) | ({bot_key(b) for b in SEED_BOTS} if not args.no_seed else set())
    lookup |= {k for k, b in bots.items() if not b.get("perfs")}
    lookup -= online_ids
    for u in api.users(sorted(lookup)):
        merge_bot(bots, u, "seed" if bot_key(u["id"]) in lookup else "crawl")

    if wanted:
        queue = [k for k in wanted if k in bots]
        for k in sorted(set(wanted) - set(queue)):
            log(f"{k}: not found on Lichess, skipping")
    else:
        ranked = sorted(
            (k for k, b in bots.items() if eligible(b)),
            key=lambda k: (k not in online_ids, -activity(bots[k], perfs)),
        )
        queue = ranked
    crawled: dict[str, str] = {}
    done: list[str] = []
    limit = len(queue) if wanted else args.top
    t0 = time.monotonic()
    for k in queue:
        if len(done) >= limit:
            break
        b = bots[k]
        if not wanted and activity(b, perfs) < args.min_games:
            continue
        log(f"[{len(done) + 1}/{limit}] {b.get('username')} activity={activity(b, perfs)}")
        meta = fetch_bot(
            api, b, target=args.max_games, perf=",".join(perfs), since_days=args.since_days,
            min_games=args.min_games, refresh=args.refresh, crawled=crawled,
        )  # fmt: skip
        if meta.get("last_status") == 404:
            continue
        if meta.get("insufficient"):
            log(f"  {b.get('username')}: only {meta.get('n_games', 0)} games, below --min-games")
            continue
        done.append(k)
        write_json(bots_json_path(), {"updated_at": now_iso(), "bots": bots})

    new = {k: v for k, v in crawled.items() if k not in bots}
    for u in api.users(sorted(new)):
        merge_bot(bots, u, "crawl")
    write_json(bots_json_path(), {"updated_at": now_iso(), "bots": bots})
    total = sum(int((read_json(games_meta_path(k), {}) or {}).get("n_games", 0)) for k in done)
    log(
        f"done: {len(done)} bots, {total} games stored for them, {len(new)} new bots crawled, "
        f"{time.monotonic() - t0:.0f} s"
    )
    write_json(bots_json_path().with_name("last_selection.json"), done)
    return 0


if __name__ == "__main__":
    sys.exit(main())
