# Power Setup (Marten)

## Defaults now set
- Model: `strong` (already active).
- Automation jobs enabled:
  1. `healthcheck:security-audit` — daily 10:00 AM America/New_York
  2. `healthcheck:update-status` — Mondays 10:15 AM America/New_York
  3. `assistant:daily-priority-reset` — Sun-Thu 9:30 PM America/New_York

## Fast commands
- List jobs: `openclaw cron list`
- Run now (debug): `openclaw cron run <job-id>`
- Disable job: `openclaw cron disable <job-id>`
- Enable job: `openclaw cron enable <job-id>`
- Remove job: `openclaw cron rm <job-id>`

## Suggested daily usage
1. "Health check" → security + update snapshot.
2. "Plan my top 3" → execution plan for the day.
3. "Ship this" + repo task → edit/test/commit loop.
