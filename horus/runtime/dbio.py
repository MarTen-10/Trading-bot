#!/usr/bin/env python3
import os, sqlite3
from pathlib import Path

DB_URL = os.getenv('DATABASE_URL', 'sqlite:///home/marten/.openclaw/workspace/horus/data/horus.db')


def sqlite_path():
    return DB_URL.replace('sqlite:///', '')


def with_sqlite(fn):
    path = sqlite_path()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    try:
        return fn(con)
    finally:
        con.commit()
        con.close()


def insert_governance(kind, instrument, setup_type, action, reason, stats_json):
    def _do(con):
        con.execute(
            "INSERT INTO governance_events(event_id,ts,kind,instrument,setup_type,action,reason,stats) VALUES(lower(hex(randomblob(16))),datetime('now'),?,?,?,?,?,?)",
            (kind, instrument, setup_type, action, reason, stats_json)
        )
    return with_sqlite(_do)


def insert_cb(trigger_name, threshold, action, details_json):
    def _do(con):
        con.execute(
            "INSERT INTO circuit_breaker_events(event_id,ts,trigger_name,threshold,action,details) VALUES(lower(hex(randomblob(16))),datetime('now'),?,?,?,?)",
            (trigger_name, threshold, action, details_json)
        )
    return with_sqlite(_do)


def insert_signal(signal_id, ts, instrument, strategy, decision, veto_reason=''):
    def _do(con):
        con.execute(
            "INSERT OR REPLACE INTO signals(signal_id, ts, instrument, strategy, decision, veto_reason) VALUES(?,?,?,?,?,?)",
            (signal_id, ts, instrument, strategy, decision, veto_reason)
        )
    return with_sqlite(_do)


def counts():
    def _do(con):
        out = {}
        for t in ('signals','orders','fills','trades'):
            try:
                out[t] = con.execute(f"select count(*) c from {t}").fetchone()['c']
            except Exception:
                out[t] = 0
        return out
    return with_sqlite(_do)
