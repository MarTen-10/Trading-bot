# Thoth Agent Contract

Produces:
- Canonical candles
- Feature snapshots
- Data quality events

Output packet:
{
  "type": "data_packet",
  "dataset_id": "uuid",
  "feature_snapshot_hash": "sha256",
  "symbols": ["BTC-PERP-INTX"],
  "timeframes": ["30m","1h"],
  "status": "OK|ERROR",
  "issues": []
}
