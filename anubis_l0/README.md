# Anubis L0

L0 is the baseline safety controller for execution.

## Includes
- BudgetController (run + daily limits)
- Structured JSONL logging
- Cheap-first model routing with explicit escalation reason
- Bounded retry policy (max 2 retries)
- Simple cache with TTL
- Kill switches: `ANUBIS_DISABLE_TOOLS=1` or `ANUBIS_READONLY=1`

## Run
```bash
PYTHONPATH=/home/marten/.openclaw/workspace python -m anubis_l0.runner
```

## Failure test (budget exceed)
```bash
PYTHONPATH=/home/marten/.openclaw/workspace L0_SIM_OVER=1 python -m anubis_l0.runner
```

Logs:
`/home/marten/.openclaw/workspace/logs/anubis_l0_runs/<run_id>.jsonl`
