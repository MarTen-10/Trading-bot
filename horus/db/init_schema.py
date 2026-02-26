#!/usr/bin/env python3
import os
import sqlite3
from pathlib import Path


def main():
    db_url = os.getenv('DATABASE_URL', 'sqlite:///home/marten/.openclaw/workspace/horus/data/horus.db')
    schema_path = Path('/home/marten/.openclaw/workspace/horus/db/schema.sql')
    sql = schema_path.read_text()

    if db_url.startswith('sqlite:///'):
        db_path = db_url.replace('sqlite:///', '')
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        con = sqlite3.connect(db_path)
        try:
            # sqlite bootstrap schema for local paper runtime smoke tests
            con.executescript('''
            CREATE TABLE IF NOT EXISTS signals (
              signal_id TEXT PRIMARY KEY,
              ts TEXT,
              instrument TEXT,
              strategy TEXT,
              decision TEXT,
              veto_reason TEXT
            );
            CREATE TABLE IF NOT EXISTS orders (
              order_id TEXT PRIMARY KEY,
              signal_id TEXT,
              status TEXT,
              sent_at TEXT,
              ack_at TEXT
            );
            CREATE TABLE IF NOT EXISTS fills (
              fill_id TEXT PRIMARY KEY,
              order_id TEXT,
              ts TEXT,
              fill_px REAL,
              fill_qty REAL,
              mid_at_send REAL,
              bid_at_send REAL,
              ask_at_send REAL,
              slippage_bps REAL
            );
            CREATE TABLE IF NOT EXISTS trades (
              trade_id TEXT PRIMARY KEY,
              signal_id TEXT,
              entry_ts TEXT,
              exit_ts TEXT,
              realized_r REAL,
              realized_pnl REAL,
              mfe_r REAL,
              mae_r REAL,
              exit_reason TEXT
            );
            CREATE TABLE IF NOT EXISTS circuit_breaker_events (
              event_id TEXT PRIMARY KEY,
              ts TEXT,
              trigger_name TEXT,
              threshold TEXT,
              action TEXT,
              details TEXT
            );
            CREATE TABLE IF NOT EXISTS governance_events (
              event_id TEXT PRIMARY KEY,
              ts TEXT,
              kind TEXT,
              instrument TEXT,
              setup_type TEXT,
              action TEXT,
              reason TEXT,
              stats TEXT
            );
            ''')
            con.commit()
            print(f'SCHEMA_OK sqlite {db_path}')
        finally:
            con.close()
    else:
        try:
            import psycopg2
        except Exception as e:
            raise SystemExit(f'psycopg2 required for postgres DATABASE_URL: {e}')

        con = psycopg2.connect(db_url)
        con.autocommit = True
        try:
            with con.cursor() as cur:
                cur.execute(sql)
            print('SCHEMA_OK postgres')
        finally:
            con.close()


if __name__ == '__main__':
    main()
