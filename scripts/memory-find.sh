#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: memory-find \"query\""
  exit 1
fi

Q="$*"

# Lightweight query normalization for better recall.
EXPANDED="$Q"
EXPANDED="${EXPANDED//ssh/tailnet ssh}"
EXPANDED="${EXPANDED//tailnet/tailscale tailnet}"
EXPANDED="${EXPANDED//school/guided drafting school}"

openclaw memory search "$EXPANDED"
