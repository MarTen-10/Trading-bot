-- Migration v1: Infrastructure hardening + exchange integration foundation
-- PostgreSQL

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS candles (
    id BIGSERIAL PRIMARY KEY,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    open NUMERIC(20,10) NOT NULL,
    high NUMERIC(20,10) NOT NULL,
    low NUMERIC(20,10) NOT NULL,
    close NUMERIC(20,10) NOT NULL,
    volume NUMERIC(28,10) NOT NULL,
    source TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(symbol, timeframe, timestamp)
);

CREATE INDEX IF NOT EXISTS idx_candles_symbol_timeframe_ts
    ON candles(symbol, timeframe, timestamp DESC);

CREATE TABLE IF NOT EXISTS features (
    id BIGSERIAL PRIMARY KEY,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    feature_json JSONB NOT NULL,
    version TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(symbol, timeframe, timestamp, version)
);

CREATE INDEX IF NOT EXISTS idx_features_symbol_timeframe_ts
    ON features(symbol, timeframe, timestamp DESC);

CREATE TABLE IF NOT EXISTS trades (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_version TEXT NOT NULL,
    side TEXT NOT NULL CHECK (side IN ('BUY','SELL','LONG','SHORT')),
    entry_price NUMERIC(20,10) NOT NULL,
    stop_price NUMERIC(20,10) NOT NULL,
    target_price NUMERIC(20,10) NOT NULL,
    size NUMERIC(20,10) NOT NULL CHECK (size > 0),
    status TEXT NOT NULL CHECK (status IN ('OPEN','CLOSED','CANCELLED')),
    risk_ticket_hash TEXT NOT NULL CHECK (char_length(risk_ticket_hash) >= 16),
    entry_timestamp TIMESTAMPTZ NOT NULL,
    exit_timestamp TIMESTAMPTZ,
    pnl NUMERIC(20,10),
    fees NUMERIC(20,10) NOT NULL DEFAULT 0,
    slippage NUMERIC(20,10) NOT NULL DEFAULT 0,
    regime_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_trades_status_entry_ts ON trades(status, entry_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_trades_risk_ticket_hash ON trades(risk_ticket_hash);

CREATE TABLE IF NOT EXISTS risk_events (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    type TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_risk_events_ts ON risk_events(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_risk_events_type ON risk_events(type);

CREATE TABLE IF NOT EXISTS execution_logs (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    event_type TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_execution_logs_ts ON execution_logs(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_execution_logs_event_type ON execution_logs(event_type);
