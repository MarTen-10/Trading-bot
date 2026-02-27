# Anubis Workspace

This workspace is the control center for Marten's OpenClaw operations.

## What this repo contains

- `horus/` — Trading runtime, backtests, risk engine, lifecycle logic, and operational scripts.
- `memory/` — Persistent notes, decisions, daily logs, and follow-ups.
- `runbooks/` — Operational playbooks (incident response, deployments, cost control, lean context).
- `scripts/` — Utility scripts for monitoring, memory checks, and automation.
- `tools/` — Local tooling setup (ex: SearXNG local search).
- `logs/` — Operational logs generated during runs.

## Current architecture (high level)

### Anubis (master operator)
- Orchestrates infra, validations, and runbooks.
- Owns system-level coordination and quality gates.

### Horus (autonomous runtime)
- Executes deterministic paper-trading runtime loops.
- Enforces governance + risk invariants.
- Uses DB-backed lifecycle and restart-safe exposure reconstruction.

## Horus lifecycle flow

1. Ingest candles
2. Generate signals
3. Apply SAFE/gate/risk/exposure checks
4. Emit ENTRY/EXIT intents
5. Execute deterministic paper fills
6. Persist orders/fills/trades/governance
7. Reconcile + breaker evaluation
8. Export status snapshots

## Validation model

- **Infra Soak**: stability only (uptime, memory, db health, no random SAFE)
- **Trading-Path Soak**: open/close lifecycle integrity under controlled settings

## Source-of-truth policy

- Runtime decisions: event data + deterministic engine logic.
- Exposure safety: engine state + DB alignment (`exposure_drift` flag in status CLI).
- Audit evidence: DB tables + journal logs.

## Automation

- OpenClaw cron jobs drive periodic health checks and briefings.
- Local git autosync (every 30 minutes) commits and pushes workspace changes.

## Safety rules

- No destructive/system-level changes without explicit approval.
- Risk/finance invariants are non-bypassable unless intentionally in controlled validation mode.
- All lifecycle and soak conclusions require evidence (logs + SQL + status snapshots).
