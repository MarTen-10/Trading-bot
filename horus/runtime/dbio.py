#!/usr/bin/env python3
import json
import os
import psycopg2
from psycopg2.extras import RealDictCursor

DB_URL = os.getenv('DATABASE_URL', '')
if not DB_URL.startswith('postgresql://'):
    raise RuntimeError('DATABASE_URL must be postgresql:// (sqlite disabled)')


def with_conn(fn):
    con = psycopg2.connect(DB_URL)
    try:
        con.autocommit = False
        return fn(con)
    finally:
        con.commit()
        con.close()


def ensure_schema_extensions():
    def _do(con):
        with con.cursor() as cur:
            cur.execute("ALTER TABLE trades ADD COLUMN IF NOT EXISTS instrument TEXT")
            cur.execute("ALTER TABLE trades ADD COLUMN IF NOT EXISTS status TEXT")
            cur.execute("ALTER TABLE trades ADD COLUMN IF NOT EXISTS side TEXT")
            cur.execute("ALTER TABLE trades ADD COLUMN IF NOT EXISTS qty DOUBLE PRECISION")
            cur.execute("ALTER TABLE trades ADD COLUMN IF NOT EXISTS entry_price DOUBLE PRECISION")
            cur.execute("ALTER TABLE trades ADD COLUMN IF NOT EXISTS exit_price DOUBLE PRECISION")
            cur.execute("ALTER TABLE trades ADD COLUMN IF NOT EXISTS risk_r DOUBLE PRECISION")
            cur.execute("ALTER TABLE trades ADD COLUMN IF NOT EXISTS entry_sequence_id BIGINT")
            cur.execute("ALTER TABLE trades ADD COLUMN IF NOT EXISTS stop_price DOUBLE PRECISION")
            cur.execute("ALTER TABLE trades ADD COLUMN IF NOT EXISTS take_price DOUBLE PRECISION")
            cur.execute("UPDATE trades SET status='CLOSED' WHERE status IS NULL AND exit_timestamp IS NOT NULL")
            cur.execute("UPDATE trades SET status='OPEN' WHERE status IS NULL AND exit_timestamp IS NULL")
            cur.execute("UPDATE trades SET instrument=COALESCE(instrument, 'UNKNOWN')")
            cur.execute("UPDATE trades SET risk_r=COALESCE(risk_r, 0.0)")
    return with_conn(_do)


def insert_governance(kind, instrument, setup_type, action, reason, stats_json):
    stats = json.loads(stats_json) if isinstance(stats_json, str) else stats_json
    def _do(con):
        with con.cursor() as cur:
            cur.execute(
                "INSERT INTO governance_events(event_id,timestamp,kind,instrument,setup_type,action,reason,stats) VALUES(encode(gen_random_bytes(16),'hex'),now(),%s,%s,%s,%s,%s,%s::jsonb)",
                (kind, instrument, setup_type, action, reason, json.dumps(stats or {}))
            )
    return with_conn(_do)


def insert_cb(trigger_name, threshold, action, details_json):
    details = json.loads(details_json) if isinstance(details_json, str) else details_json
    def _do(con):
        with con.cursor() as cur:
            cur.execute(
                "INSERT INTO circuit_breaker_events(event_id,timestamp,trigger_name,threshold,action,details) VALUES(encode(gen_random_bytes(16),'hex'),now(),%s,%s,%s,%s::jsonb)",
                (trigger_name, threshold, action, json.dumps(details or {}))
            )
    return with_conn(_do)


def insert_signal(signal_id, ts, instrument, strategy, decision, veto_reason=''):
    def _do(con):
        with con.cursor() as cur:
            cur.execute(
                "INSERT INTO signals(signal_id, timestamp, instrument, strategy, decision, veto_reason) VALUES(%s,%s,%s,%s,%s,%s) ON CONFLICT(signal_id) DO UPDATE SET timestamp=EXCLUDED.timestamp,instrument=EXCLUDED.instrument,strategy=EXCLUDED.strategy,decision=EXCLUDED.decision,veto_reason=EXCLUDED.veto_reason",
                (signal_id, ts, instrument, strategy, decision, veto_reason)
            )
    return with_conn(_do)


def fetch_open_trades():
    def _do(con):
        with con.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT trade_id, signal_id, instrument, side, entry_timestamp, entry_price, qty, risk_r,
                       stop_price, take_price
                FROM trades
                WHERE COALESCE(status, CASE WHEN exit_timestamp IS NULL THEN 'OPEN' ELSE 'CLOSED' END)='OPEN'
                ORDER BY entry_timestamp ASC
                """
            )
            return [dict(r) for r in cur.fetchall()]
    return with_conn(_do)


def open_exposure_r_db():
    def _do(con):
        with con.cursor() as cur:
            cur.execute(
                "SELECT COALESCE(SUM(risk_r),0) FROM trades WHERE COALESCE(status, CASE WHEN exit_timestamp IS NULL THEN 'OPEN' ELSE 'CLOSED' END)='OPEN'"
            )
            row = cur.fetchone()
            return float(row[0] or 0.0)
    return with_conn(_do)


def counts():
    def _do(con):
        out = {}
        with con.cursor(cursor_factory=RealDictCursor) as cur:
            for t in ('signals', 'orders', 'fills', 'trades'):
                try:
                    cur.execute(f"select count(*) c from {t}")
                    out[t] = cur.fetchone()['c']
                except Exception:
                    out[t] = 0
        return out
    return with_conn(_do)
