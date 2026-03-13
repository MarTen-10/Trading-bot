# Model Routing Policy (Pass 1)

## Objective
Prevent runaway usage and preserve strong-model capacity for high-value work.

## Routing Classes

### Class A — Cheap/Fast Ops (default)
Use `fast`:
- status checks
- heartbeat/health summaries
- cron reporting
- formatting/transform tasks

### Class B — Standard Automation Control
Use `fast` first, escalate to `strong` only on failure or low confidence:
- node orchestration
- routine diagnostics
- safe remediation planning

### Class C — Deep Reasoning
Use `strong`:
- architecture decisions
- postmortems
- high-impact tradeoff analysis

### Class D — High-Frequency Background Loops
Use `fast` only:
- monitoring loops
- repetitive scheduled checks

## Hard Guards
- No recursive self-calls.
- No unbounded retries.
- No model escalation loops.
- Always prefer concise outputs for scheduled jobs.

## Escalation Rule
Escalate `fast` → `strong` only when:
1) same task fails twice with non-transient reason, or
2) output confidence is explicitly low for a critical decision.
