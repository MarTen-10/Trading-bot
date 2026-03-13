# Automation Guardrails (Pass 1)

## Limits
- Max retries per run: 2
- Retry backoff: exponential (30s -> 120s)
- Circuit breaker: after 3 consecutive failures, stop active remediation for that run and alert operator
- Timeout per scheduled agent turn: set explicitly per job

## Concurrency
- One routed task at a time on Jarvis (`active_run.json` lock)
- Reject concurrent runs with reason: `concurrent_execution_active`

## Cost/Usage Discipline
- Pin recurring jobs to `fast`
- Keep prompts short and deterministic
- Return compact summaries for cron jobs

## Observability
Track daily:
- run count (success/failed/timeout/rejected)
- consecutive error streaks
- stale lock recoveries
- average duration per job

## Anti-Runaway Rules
- No infinite retry loops
- No nested automation recursion
- On repeated failure: alert + pause escalation, do not spam
