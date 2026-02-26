#!/usr/bin/env bash
set -euo pipefail

VENV="/home/marten/horus/.venv_local/bin/python"
LOG_DIR="/home/marten/horus/logs"
mkdir -p "$LOG_DIR"
SOAK_FILE="$LOG_DIR/soak_12h_$(date -u +%Y%m%dT%H%M%SZ).jsonl"

echo "Starting 12h soak monitor -> $SOAK_FILE"
for i in {1..12}; do
  echo "Snapshot $i / 12 at $(date -u)"
  (cd /home/marten && "$VENV" -m horus.cli.status) >> "$SOAK_FILE"
  sleep 3600
done

echo "Soak complete."
