# Git AutoSync (Every 30 Minutes)

## What it does
- Stages all workspace changes
- Commits if there are changes
- Pushes to `origin` on current branch
- Logs activity to `logs/git-autosync.log`

## Script
- Path: `scripts/git-autosync.sh`

## Schedule
- User crontab: every 30 minutes

## Verify
```bash
crontab -l
 tail -n 50 /home/marten/.openclaw/workspace/logs/git-autosync.log
```

## Disable
```bash
crontab -l | grep -v git-autosync.sh | crontab -
```
