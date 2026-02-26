-- Horus v2 PostgreSQL Schema (core)
-- UUID extension
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS exchanges (
  exchange_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT UNIQUE NOT NULL,
  type TEXT NOT NULL CHECK (type IN ('spot','perp')),
  tz TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS instruments (
  instrument_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  exchange_id UUID NOT NULL REFERENCES exchanges(exchange_id),
  symbol TEXT NOT NULL,
  base_asset TEXT NOT NULL,
  quote_asset TEXT NOT NULL,
  tick_size NUMERIC(18,10) NOT NULL,
  lot_size NUMERIC(18,10) NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('active','inactive')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(exchange_id, symbol)
);
CREATE INDEX IF NOT EXISTS idx_instruments_exchange_status ON instruments(exchange_id, status);

CREATE TABLE IF NOT EXISTS timeframes (
  timeframe_id SMALLINT PRIMARY KEY,
  name TEXT UNIQUE NOT NULL,
  seconds INT NOT NULL
);

CREATE TABLE IF NOT EXISTS candles (
  exchange_id UUID NOT NULL REFERENCES exchanges(exchange_id),
  instrument_id UUID NOT NULL REFERENCES instruments(instrument_id),
  timeframe_id SMALLINT NOT NULL REFERENCES timeframes(timeframe_id),
  ts TIMESTAMPTZ NOT NULL,
  open NUMERIC(18,10) NOT NULL,
  high NUMERIC(18,10) NOT NULL,
  low NUMERIC(18,10) NOT NULL,
  close NUMERIC(18,10) NOT NULL,
  volume NUMERIC(28,10) NOT NULL,
  vwap NUMERIC(18,10),
  spread_bps NUMERIC(10,4),
  ingest_latency_ms INT,
  PRIMARY KEY(exchange_id, instrument_id, timeframe_id, ts)
);
CREATE INDEX IF NOT EXISTS idx_candles_inst_tf_ts ON candles(instrument_id, timeframe_id, ts);

CREATE TABLE IF NOT EXISTS strategies (
  strategy_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT UNIQUE NOT NULL,
  version TEXT NOT NULL,
  enabled BOOLEAN NOT NULL DEFAULT true,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS strategy_configs (
  config_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  strategy_id UUID NOT NULL REFERENCES strategies(strategy_id),
  params JSONB NOT NULL,
  gates JSONB NOT NULL,
  active_from TIMESTAMPTZ NOT NULL,
  active_to TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_strategy_configs_strategy_active ON strategy_configs(strategy_id, active_from);

CREATE TABLE IF NOT EXISTS signals (
  signal_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  exchange_id UUID NOT NULL REFERENCES exchanges(exchange_id),
  instrument_id UUID NOT NULL REFERENCES instruments(instrument_id),
  strategy_id UUID NOT NULL REFERENCES strategies(strategy_id),
  config_id UUID NOT NULL REFERENCES strategy_configs(config_id),
  ts TIMESTAMPTZ NOT NULL,
  side TEXT NOT NULL CHECK (side IN ('long','short')),
  entry_px NUMERIC(18,10) NOT NULL,
  stop_px NUMERIC(18,10) NOT NULL,
  target_r NUMERIC(10,4) NOT NULL,
  decision TEXT NOT NULL CHECK (decision IN ('taken','vetoed')),
  veto_reason TEXT,
  features_hash TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_signals_inst_ts ON signals(instrument_id, ts);
CREATE INDEX IF NOT EXISTS idx_signals_strategy_ts ON signals(strategy_id, ts);
CREATE INDEX IF NOT EXISTS idx_signals_decision_ts ON signals(decision, ts);

CREATE TABLE IF NOT EXISTS orders (
  order_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  signal_id UUID NOT NULL REFERENCES signals(signal_id),
  broker_order_id TEXT,
  type TEXT NOT NULL CHECK (type IN ('market','limit','stop')),
  side TEXT NOT NULL CHECK (side IN ('buy','sell')),
  qty NUMERIC(28,10) NOT NULL,
  limit_px NUMERIC(18,10),
  tif TEXT NOT NULL CHECK (tif IN ('GTC','IOC','FOK')),
  status TEXT NOT NULL,
  sent_at TIMESTAMPTZ,
  ack_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_orders_signal_status ON orders(signal_id, status);

CREATE TABLE IF NOT EXISTS fills (
  fill_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id UUID NOT NULL REFERENCES orders(order_id),
  ts TIMESTAMPTZ NOT NULL,
  fill_px NUMERIC(18,10) NOT NULL,
  fill_qty NUMERIC(28,10) NOT NULL,
  fee NUMERIC(18,10),
  fee_asset TEXT,
  liquidity TEXT CHECK (liquidity IN ('maker','taker')),
  mid_at_send NUMERIC(18,10),
  bid_at_send NUMERIC(18,10),
  ask_at_send NUMERIC(18,10),
  slippage_bps NUMERIC(10,4)
);
CREATE INDEX IF NOT EXISTS idx_fills_order_ts ON fills(order_id, ts);

CREATE TABLE IF NOT EXISTS trades (
  trade_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  signal_id UUID NOT NULL REFERENCES signals(signal_id),
  entry_ts TIMESTAMPTZ NOT NULL,
  exit_ts TIMESTAMPTZ,
  avg_entry_px NUMERIC(18,10) NOT NULL,
  avg_exit_px NUMERIC(18,10),
  realized_r NUMERIC(10,4),
  realized_pnl NUMERIC(18,10),
  mfe_r NUMERIC(10,4),
  mae_r NUMERIC(10,4),
  exit_reason TEXT,
  slippage_bps NUMERIC(10,4)
);
CREATE INDEX IF NOT EXISTS idx_trades_signal ON trades(signal_id);

CREATE TABLE IF NOT EXISTS circuit_breaker_events (
  event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  ts TIMESTAMPTZ NOT NULL DEFAULT now(),
  trigger_name TEXT NOT NULL,
  threshold TEXT NOT NULL,
  action TEXT NOT NULL,
  details JSONB
);

CREATE TABLE IF NOT EXISTS governance_events (
  event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  ts TIMESTAMPTZ NOT NULL DEFAULT now(),
  kind TEXT NOT NULL,
  instrument TEXT,
  setup_type TEXT,
  action TEXT NOT NULL,
  reason TEXT,
  stats JSONB
);
