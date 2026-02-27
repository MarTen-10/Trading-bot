#!/usr/bin/env bash
set -euo pipefail

REPO="/home/marten/.openclaw/workspace"
LOG_DIR="$REPO/logs"
LOCK_FILE="/tmp/anubis-git-autosync.lock"
INCLUDE_FILE="$REPO/scripts/autosync-include.txt"
mkdir -p "$LOG_DIR"

exec 9>"$LOCK_FILE"
if ! flock -n 9; then
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] skip: lock held" >> "$LOG_DIR/git-autosync.log"
  exit 0
fi

cd "$REPO"

# Stage only curated source paths to avoid runtime-noise commits.
if [[ -f "$INCLUDE_FILE" ]]; then
  while IFS= read -r path; do
    [[ -z "$path" ]] && continue
    [[ "$path" =~ ^# ]] && continue
    git add -A -- "$path" 2>/dev/null || true
  done < "$INCLUDE_FILE"
else
  git add -A
fi

if git diff --cached --quiet; then
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] no curated changes" >> "$LOG_DIR/git-autosync.log"
  exit 0
fi

branch="$(git rev-parse --abbrev-ref HEAD)"
msg="chore(autosync): curated snapshot $(date -u +%Y-%m-%dT%H:%M:%SZ)"

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
