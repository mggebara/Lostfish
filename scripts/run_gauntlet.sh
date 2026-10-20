#!/usr/bin/env bash
# Run a fastchess gauntlet described by experiments/<name>/config.toml.
#
#   scripts/run_gauntlet.sh experiments/<name>            # or .../config.toml
#
# Writes experiments/<name>/games.pgn (previous one rotated), fastchess.log (full output) and
# RESULT.md (exact command + fastchess's final summary + error counts).
#
# config.toml schema (paths are relative to the repo root; "{root}" in option values expands):
#   rounds = 5              # fastchess -rounds
#   games = 2               # games per round (2 = same opening, colours reversed)
#   concurrency = 4         # keep <= 4 on this machine
#   openings = "experiments/openings/8moves_v3.pgn"   # optional; fetch with scripts/fetch_openings.sh
#   openings_format = "pgn" ; openings_order = "random" ; openings_plies = 16 ; srand = 42
#   ratinginterval = 10 ; recover = false ; maxmoves = 0 ; tb = "tb/syzygy" ; tbpieces = 5
#   sprt = { elo0 = 0, elo1 = 5, alpha = 0.05, beta = 0.05, model = "normalized" }
#   draw = { movenumber = 34, movecount = 8, score = 20 }      # adjudication (optional)
#   resign = { movecount = 3, score = 600, twosided = true }
#   extra_args = []         # raw fastchess arguments appended verbatim
#   [each]                  # applied to all engines: nodes = N | tc = "10+0.1" | st = 1 | depth = D
#   [[engine]]              # two or more
#   name = "LostFish" ; cmd = "scripts/lostfish" ; args = "" ; [engine.options] Steering = false
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ARG="${1:?usage: scripts/run_gauntlet.sh experiments/<name>}"
[[ "$ARG" == *.toml ]] && ARG="$(dirname "$ARG")"
EXP="$(cd "$ARG" && pwd)"
CFG="$EXP/config.toml"
[[ -f "$CFG" ]] || { echo "missing $CFG" >&2; exit 2; }
PY="$ROOT/.venv/bin/python"
FASTCHESS="${FASTCHESS:-$ROOT/engines/fastchess}"
[[ -x "$FASTCHESS" ]] || { echo "fastchess not found at $FASTCHESS (run scripts/setup_engines.sh)" >&2; exit 2; }

# TOML -> fastchess argv (NUL-separated so values may contain spaces).
read -r -d '' TOML2ARGS <<'PYEOF' || true
import os, sys, tomllib
root, exp, cfg_path, pgn = sys.argv[1:5]
cfg = tomllib.load(open(cfg_path, "rb"))
def path(p):
    p = os.path.expanduser(str(p))
    return p if os.path.isabs(p) else os.path.join(root, p)
def val(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    return str(v).replace("{root}", root)
def kv(d):
    return [f"{k}={val(v)}" for k, v in d.items()]
engines = cfg.get("engine") or []
if len(engines) < 2:
    sys.exit("config.toml needs at least two [[engine]] tables")
out = []
for e in engines:
    if "cmd" not in e:
        sys.exit(f"engine {e.get('name', '?')} has no cmd")
    out += ["-engine", f"cmd={path(e['cmd'])}", f"name={e.get('name', os.path.basename(e['cmd']))}"]
    if e.get("args"):
        out.append(f"args={e['args']}")
    for k in ("nodes", "tc", "st", "depth", "timemargin", "restart"):
        if k in e:
            out.append(f"{k}={val(e[k])}")
    out += [f"option.{k}={val(v)}" for k, v in (e.get("options") or {}).items()]
each = dict(cfg.get("each") or {})
each.setdefault("proto", "uci")
out += ["-each"] + kv(each)
if cfg.get("openings"):
    out += ["-openings", f"file={path(cfg['openings'])}", f"format={cfg.get('openings_format', 'pgn')}",
            f"order={cfg.get('openings_order', 'random')}"]
    if "openings_plies" in cfg:
        out.append(f"plies={cfg['openings_plies']}")
    if "srand" in cfg:
        out += ["-srand", str(cfg["srand"])]
out += ["-rounds", str(cfg.get("rounds", 2)), "-games", str(cfg.get("games", 2))]
if cfg.get("games", 2) == 2:
    out.append("-repeat")
out += ["-concurrency", str(cfg.get("concurrency", 4))]
out += ["-ratinginterval", str(cfg.get("ratinginterval", 10))]
for k in ("sprt", "draw", "resign"):
    if cfg.get(k):
        out += [f"-{k}"] + kv(cfg[k])
if cfg.get("maxmoves"):
    out += ["-maxmoves", str(cfg["maxmoves"])]
if cfg.get("tb"):
    out += ["-tb", path(cfg["tb"])]
    if cfg.get("tbpieces"):
        out += ["-tbpieces", str(cfg["tbpieces"])]
if cfg.get("recover"):
    out.append("-recover")
out += ["-pgnout", f"file={pgn}", "notation=san", "nodes=true"]
out += [str(a) for a in cfg.get("extra_args", [])]
sys.stdout.write("\0".join(out) + "\0")
PYEOF

if [[ -s "$EXP/games.pgn" ]]; then
  mv "$EXP/games.pgn" "$EXP/games.$(date +%Y%m%d-%H%M%S).pgn"
fi
ARGS=()
while IFS= read -r -d '' a; do ARGS+=("$a"); done < <("$PY" -c "$TOML2ARGS" "$ROOT" "$EXP" "$CFG" "$EXP/games.pgn")
[[ ${#ARGS[@]} -gt 0 ]] || { echo "could not build fastchess arguments from $CFG" >&2; exit 2; }

CMD_STR="$(printf '%q ' "$FASTCHESS" "${ARGS[@]}")"
echo "$CMD_STR" > "$EXP/command.txt"
echo "+ $CMD_STR"
START="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
# fastchess writes its resume state (config.json) to the cwd: keep it inside the experiment dir.
set +e
(cd "$EXP" && "$FASTCHESS" "${ARGS[@]}") 2>&1 | tee "$EXP/fastchess.log"
STATUS=${PIPESTATUS[0]}
set -e
END="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

LOG="$EXP/fastchess.log"
count() { grep -ciE "$1" "$LOG" || true; }
SUMMARY="$(awk '/^Results of /{buf=""; on=1} on{buf=buf $0 "\n"} END{printf "%s", buf}' "$LOG")"
GAMES="$(grep -c '^\[Result ' "$EXP/games.pgn" 2>/dev/null || echo 0)"
{
  echo "# $(basename "$EXP") — gauntlet result"
  echo
  echo "- Started: $START, finished: $END, fastchess exit status: $STATUS"
  echo "- Config: \`experiments/$(basename "$EXP")/config.toml\`; LostFish commit: \`$(git -C "$ROOT" rev-parse --short HEAD 2>/dev/null || echo unknown)\`$(git -C "$ROOT" diff --quiet 2>/dev/null || echo ' (dirty tree)')"
  echo "- Games in games.pgn: $GAMES"
  echo "- Problems in fastchess output: time losses $(count 'loses on time'), illegal moves $(count 'illegal move'), disconnects/crashes $(count 'disconnect|crash|stall'), warnings $(count 'warning')"
  echo
  echo "## Command"
  echo
  echo '```bash'
  echo "$CMD_STR"
  echo '```'
  echo
  echo "## fastchess final summary"
  echo
  echo '```'
  if [[ -n "$SUMMARY" ]]; then echo "$SUMMARY"; else tail -n 30 "$LOG"; fi
  echo '```'
} > "$EXP/RESULT.md"
echo "wrote $EXP/RESULT.md"
exit "$STATUS"
