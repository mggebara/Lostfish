#!/usr/bin/env bash
# Run gauntlets one after another, each after the previous finishes; skip ones that already have RESULT.md.
#   nohup scripts/run_queue.sh experiments/a experiments/b ... > logs/queue.log 2>&1 &
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
# wait for any running fastchess to exit first
while pgrep -x fastchess >/dev/null; do sleep 60; done
for EXP in "$@"; do
  if [[ -f "$EXP/RESULT.md" ]]; then echo "skip $EXP (has RESULT.md)"; continue; fi
  echo "[$(date '+%F %T')] start $EXP"
  scripts/run_gauntlet.sh "$EXP" > "$EXP/run.log" 2>&1
  echo "[$(date '+%F %T')] done $EXP (exit $?)"
done
