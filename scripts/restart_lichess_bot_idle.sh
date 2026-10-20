#!/usr/bin/env bash
# Restart lichess-bot once no game is in progress (so the switch never aborts a live game).
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$ROOT"
TOKEN="$(sed -nE 's/^[[:space:]]*(export[[:space:]]+)?LICHESS_BOT_TOKEN[[:space:]]*=[[:space:]]*//p' .env | tail -n1 | tr -d '"'"'"' ')"
while :; do
  N="$(curl -s -H "Authorization: Bearer $TOKEN" https://lichess.org/api/account/playing | .venv/bin/python -c 'import sys,json; print(len(json.load(sys.stdin).get("nowPlaying",[])))' 2>/dev/null || echo 1)"
  [[ "$N" == "0" ]] && break
  sleep 20
done
pkill -f "lichess-bot.py" && sleep 3
nohup scripts/run_lichess_bot.sh > logs/lichess-bot.log 2>&1 &
echo "[$(date '+%F %T')] lichess-bot restarted (pid $!) with Steering=$(grep -oE 'Steering: (true|false)' configs/lichess-bot.config.yml | cut -d' ' -f2)"
