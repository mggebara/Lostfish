#!/usr/bin/env bash
# Run LostFish on Lichess through lichess-bot (third_party/lichess-bot, gitignored).
#
#   scripts/run_lichess_bot.sh             # play: lichess-bot.py -v
#   scripts/run_lichess_bot.sh --upgrade   # one-time: upgrade a FRESH account to BOT (-u), then play
#   scripts/run_lichess_bot.sh --setup     # only create the venv and check lichess-bot runs; no network
#
# The token comes from LICHESS_BOT_TOKEN in .env at the repo root (or the environment). It is
# never committed: configs/lichess-bot.config.yml (rendered from the .example) is gitignored.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LB="$ROOT/third_party/lichess-bot"
EXAMPLE="$ROOT/configs/lichess-bot.config.yml.example"
CONFIG="$ROOT/configs/lichess-bot.config.yml"

MODE="play"
case "${1:-}" in
  "") ;;
  --upgrade) MODE="upgrade" ;;
  --setup) MODE="setup" ;;
  -h|--help) sed -n '2,9p' "$0"; exit 0 ;;
  *) echo "unknown argument: $1 (use --upgrade, --setup or nothing)" >&2; exit 2 ;;
esac

if [[ ! -f "$LB/lichess-bot.py" ]]; then
  echo "lichess-bot not found. Clone it first:" >&2
  echo "  git clone https://github.com/lichess-bot-devs/lichess-bot $LB" >&2
  exit 2
fi

# --- lichess-bot's own venv (kept separate from LostFish's) ---------------------------------
PY="$LB/.venv/bin/python"
if [[ ! -x "$PY" ]]; then
  command -v uv >/dev/null || { echo "uv is required (https://docs.astral.sh/uv/)" >&2; exit 2; }
  echo "creating $LB/.venv"
  (cd "$LB" && uv venv .venv && uv pip install --python .venv/bin/python -r requirements.txt)
fi
if [[ "$MODE" == "setup" ]]; then
  (cd "$LB" && "$PY" lichess-bot.py --help >/dev/null) && echo "lichess-bot venv OK: $PY"
  exit 0
fi

# --- token ---------------------------------------------------------------------------------
TOKEN=""
if [[ -f "$ROOT/.env" ]]; then
  # Read only the LICHESS_BOT_TOKEN line; never `source` the file.
  TOKEN="$(sed -nE 's/^[[:space:]]*(export[[:space:]]+)?LICHESS_BOT_TOKEN[[:space:]]*=[[:space:]]*//p' "$ROOT/.env" \
    | tail -n 1 | sed -E "s/^[\"']//; s/[\"'][[:space:]]*\$//; s/[[:space:]]+\$//")"
fi
TOKEN="${TOKEN:-${LICHESS_BOT_TOKEN:-}}"
if [[ -z "$TOKEN" ]]; then
  echo "LICHESS_BOT_TOKEN not found. Put it in $ROOT/.env as:" >&2
  echo "  LICHESS_BOT_TOKEN=lip_xxxxxxxx   # token of a fresh account with scope bot:play" >&2
  exit 1
fi
export LICHESS_BOT_TOKEN="$TOKEN"  # lichess-bot also reads it from the environment

# --- config --------------------------------------------------------------------------------
if [[ ! -f "$CONFIG" ]]; then
  echo "rendering $CONFIG from $(basename "$EXAMPLE")"
  (umask 077 && "$PY" -c '
import os, sys
src, dst = sys.argv[1], sys.argv[2]
text = open(src).read().replace("${LICHESS_BOT_TOKEN}", os.environ["LICHESS_BOT_TOKEN"])
open(dst, "w").write(text)
' "$EXAMPLE" "$CONFIG")
fi
mkdir -p "$ROOT/data/lichess-bot-games"
[[ -x "$ROOT/scripts/lostfish" ]] || { echo "scripts/lostfish is not executable" >&2; exit 2; }

cd "$LB"
if [[ "$MODE" == "upgrade" ]]; then
  exec "$PY" lichess-bot.py --config "$CONFIG" -u
fi
exec "$PY" lichess-bot.py --config "$CONFIG" -v
