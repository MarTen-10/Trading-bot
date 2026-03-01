# Agent Stack (Phase 1)

- `anubis/` orchestration + approvals
- `thoth/` data + feature integrity
- `amun/` backtesting + walk-forward evaluation
- `maat/` hard risk gate
- `horus/` execution only

Communication contract:
- Structured JSON packets only
- Deterministic logs
- No free-form memory mutation
- Required trade fields: `strategy_id`, `risk_approval_id`, `regime_state`, `feature_snapshot_hash`
