#!/usr/bin/env bash
set -euo pipefail

REPO="/home/marten/.openclaw/workspace"
LOG_DIR="$REPO/logs"
LOCK_FILE="/tmp/anubis-git-autosync.lock"
mkdir -p "$LOG_DIR"

exec 9>"$LOCK_FILE"
if ! flock -n 9; then
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] skip: lock held" >> "$LOG_DIR/git-autosync.log"
  exit 0
fi

cd "$REPO"

# Keep noisy build/runtime artifacts out of autosync commits when possible
if [ -f .gitignore ]; then
  :
fi

git add -A

if git diff --cached --quiet; then
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] no changes" >> "$LOG_DIR/git-autosync.log"
  exit 0
fi

branch="$(git rev-parse --abbrev-ref HEAD)"
msg="chore(autosync): snapshot $(date -u +%Y-%m-%dT%H:%M:%SZ)"

git commit -m "$msg" >/dev/null 2>&1 || {
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] commit failed" >> "$LOG_DIR/git-autosync.log"
  exit 1
}

if git remote get-url origin >/dev/null 2>&1; then
  if git push origin "$branch" >/dev/null 2>&1; then
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] pushed $branch" >> "$LOG_DIR/git-autosync.log"
  else
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] push failed" >> "$LOG_DIR/git-autosync.log"
    exit 1
  fi
else
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] no origin remote" >> "$LOG_DIR/git-autosync.log"
fi
