# Ma’at Agent Contract

Produces signed RiskTicket. Horus MUST reject orders without valid ticket.

Output packet:
{
  "type": "risk_ticket",
  "risk_approval_id": "uuid",
  "timestamp_utc": "ISO8601",
  "strategy_id": "string",
  "strategy_version": "string",
  "symbol": "string",
  "side": "LONG|SHORT",
  "size": 0.0,
  "stop_price": 0.0,
  "target_price": 0.0,
  "regime_state": "string",
  "feature_snapshot_hash": "sha256",
  "constraints": {
    "max_daily_loss_pct": 3.0,
    "risk_per_trade_pct": 1.0,
    "one_open_position": true,
    "isolated_margin_only": true
  },
  "decision": "ALLOW|DENY",
  "signature": "hex"
}
