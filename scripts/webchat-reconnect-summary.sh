#!/usr/bin/env bash
set -euo pipefail
SINCE="${1:-2 hours ago}"
echo "since=$SINCE"
journalctl --user -u openclaw-gateway.service --since "$SINCE" --no-pager \
| awk '
/webchat connected/ {c++}
/webchat disconnected/ {d++}
END {
  printf("webchat_connected=%d\n", c+0)
  printf("webchat_disconnected=%d\n", d+0)
  if ((d+0) > (c+0)) print "note=more disconnects than connects"
}'