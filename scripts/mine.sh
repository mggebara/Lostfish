#!/usr/bin/env bash
# Phase 1 mining pipeline: fetch -> annotate -> fingerprint -> cluster -> profiles.
#
#   scripts/mine.sh --top 40                       # top-40 active online bots
#   scripts/mine.sh --bots maia1,maia5 --nodes 20000 --workers 4
#
# Options: --top N | --bots a,b   --max-games N (300)   --nodes N (20000)   --workers N (4)
#          --skip-fetch   --no-generic
# Every step is resumable; re-running only does the missing work.
set -euo pipefail
cd "$(dirname "$0")/.."
PY="${PYTHON:-.venv/bin/python}"

TOP=""; BOTS=""; MAX_GAMES=300; NODES=20000; WORKERS=4; FETCH=1; GENERIC=1
while [[ $# -gt 0 ]]; do
  case "$1" in
    --top) TOP="$2"; shift 2 ;;
    --bots) BOTS="$2"; shift 2 ;;
    --max-games) MAX_GAMES="$2"; shift 2 ;;
    --nodes) NODES="$2"; shift 2 ;;
    --workers) WORKERS="$2"; shift 2 ;;
    --skip-fetch) FETCH=0; shift ;;
    --no-generic) GENERIC=0; shift ;;
    -h|--help) sed -n '2,8p' "$0"; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done
if [[ -z "$TOP" && -z "$BOTS" ]]; then
  echo "usage: scripts/mine.sh --top N | --bots a,b [options]" >&2; exit 2
fi
mkdir -p logs

if [[ "$FETCH" == 1 ]]; then
  if [[ -n "$BOTS" ]]; then
    "$PY" -m mining.fetch_games --bots "$BOTS" --max-games "$MAX_GAMES"
  else
    "$PY" -m mining.fetch_games --top "$TOP" --max-games "$MAX_GAMES"
  fi
fi

# with --top, operate on the bots the fetch step selected
if [[ -z "$BOTS" ]]; then
  BOTS="$("$PY" -c 'import json; print(",".join(json.load(open("data/last_selection.json"))))')"
fi

"$PY" -m mining.annotate --bots "$BOTS" --nodes "$NODES" --workers "$WORKERS"
"$PY" -m mining.fingerprint --bots "$BOTS"
"$PY" -m mining.cluster --bots "$BOTS"
"$PY" -m mining.build_profile --bots "$BOTS"
if [[ "$GENERIC" == 1 ]]; then
  "$PY" -m mining.build_profile --generic
fi
echo "profiles written to profiles/"
