#!/usr/bin/env bash
set -euo pipefail

echo "== OpenClaw Memory Healthcheck =="
openclaw memory status --deep --index

echo
for q in "Marten timezone" "Tailnet SSH preference" "guided drafting" "Telegram pairing sender id"; do
  echo "-- $q"
  openclaw memory search "$q" | head -n 3
  echo
done
