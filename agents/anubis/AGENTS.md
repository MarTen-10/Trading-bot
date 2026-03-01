# Anubis Agent Contract

Inputs:
- Research reports from Amun
- Data integrity reports from Thoth
- Risk policy attestations from Ma’at
- Execution state snapshots from Horus

Outputs:
- Promotion decisions
- Parameter approvals
- Allocation updates

Output format (JSON):
{
  "type": "anubis_decision",
  "decision_id": "uuid",
  "timestamp_utc": "ISO8601",
  "strategy_id": "string",
  "strategy_version": "string",
  "action": "APPROVE|REJECT|HOLD",
  "reason": "string",
  "constraints": {},
  "artifacts": []
}
