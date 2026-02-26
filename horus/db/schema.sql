-- Horus runtime PostgreSQL schema (paper)
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS signals (
  signal_id TEXT PRIMARY KEY,
  timestamp TIMESTAMPTZ NOT NULL,
  instrument TEXT NOT NULL,
  strategy TEXT NOT NULL,
  decision TEXT NOT NULL,
  veto_reason TEXT
);
CREATE INDEX IF NOT EXISTS idx_signals_timestamp ON signals(timestamp);

CREATE TABLE IF NOT EXISTS orders (
  order_id TEXT PRIMARY KEY,
  signal_id TEXT NOT NULL REFERENCES signals(signal_id),
  status TEXT NOT NULL,
  sent_at TIMESTAMPTZ,
  ack_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS fills (
  fill_id TEXT PRIMARY KEY,
  order_id TEXT NOT NULL REFERENCES orders(order_id),
  timestamp TIMESTAMPTZ NOT NULL,
  fill_px DOUBLE PRECISION,
  fill_qty DOUBLE PRECISION,
  mid_at_send DOUBLE PRECISION,
  bid_at_send DOUBLE PRECISION,
  ask_at_send DOUBLE PRECISION,
  slippage_bps DOUBLE PRECISION
);

CREATE TABLE IF NOT EXISTS trades (
  trade_id TEXT PRIMARY KEY,
  signal_id TEXT NOT NULL REFERENCES signals(signal_id),
  entry_timestamp TIMESTAMPTZ,
  exit_timestamp TIMESTAMPTZ,
  realized_r DOUBLE PRECISION,
  realized_pnl DOUBLE PRECISION,
  mfe_r DOUBLE PRECISION,
  mae_r DOUBLE PRECISION,
  exit_reason TEXT
);
CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(entry_timestamp);

CREATE TABLE IF NOT EXISTS governance_events (
  event_id TEXT PRIMARY KEY DEFAULT encode(gen_random_bytes(16), 'hex'),
  timestamp TIMESTAMPTZ NOT NULL DEFAULT now(),
  kind TEXT NOT NULL,
  instrument TEXT,
  setup_type TEXT,
  action TEXT NOT NULL,
  reason TEXT,
  stats JSONB
);
CREATE INDEX IF NOT EXISTS idx_governance_events_timestamp ON governance_events(timestamp);

CREATE TABLE IF NOT EXISTS circuit_breaker_events (
  event_id TEXT PRIMARY KEY DEFAULT encode(gen_random_bytes(16), 'hex'),
  timestamp TIMESTAMPTZ NOT NULL DEFAULT now(),
  trigger_name TEXT NOT NULL,
  threshold TEXT NOT NULL,
  action TEXT NOT NULL,
  details JSONB
);
CREATE INDEX IF NOT EXISTS idx_circuit_breaker_events_timestamp ON circuit_breaker_events(timestamp);

CREATE TABLE IF NOT EXISTS candles (
  instrument TEXT NOT NULL,
  timeframe TEXT NOT NULL,
  timestamp TIMESTAMPTZ NOT NULL,
  open DOUBLE PRECISION,
  high DOUBLE PRECISION,
  low DOUBLE PRECISION,
  close DOUBLE PRECISION,
  volume DOUBLE PRECISION,
  PRIMARY KEY (instrument, timeframe, timestamp)
);
CREATE INDEX IF NOT EXISTS idx_candles_instrument_timeframe_timestamp ON candles(instrument, timeframe, timestamp);
