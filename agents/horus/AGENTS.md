# Horus Agent Contract

Consumes:
- RiskTicket from Ma’at

Produces:
- Execution events
- Fill reconciliation packets

Output packet:
{
  "type": "execution_event",
  "event_id": "uuid",
  "trade_id": "string",
  "risk_approval_id": "uuid",
  "strategy_id": "string",
  "regime_state": "string",
  "feature_snapshot_hash": "sha256",
  "event": "ORDER_SUBMITTED|ORDER_FILLED|ORDER_CANCELLED|ERROR",
  "details": {}
}
