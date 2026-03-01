from __future__ import annotations

import json
import os
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Iterator

import psycopg2
from psycopg2.extras import Json, RealDictCursor


@dataclass
class PostgresSettings:
    database_url: str


class PostgresDB:
    def __init__(self, settings: PostgresSettings | None = None):
        settings = settings or PostgresSettings(database_url=os.getenv("DATABASE_URL", ""))
        if not settings.database_url.startswith("postgresql://"):
            raise RuntimeError("DATABASE_URL must be postgresql://")
        self._database_url = settings.database_url

    @contextmanager
    def connection(self):
        con = psycopg2.connect(self._database_url)
        try:
            con.autocommit = False
            yield con
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()

    def healthcheck(self) -> dict[str, Any]:
        with self.connection() as con:
            with con.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT NOW() as now_utc")
                row = cur.fetchone()
        return dict(row)

    def insert_risk_event(self, event_type: str, payload: dict[str, Any]) -> None:
        with self.connection() as con:
            with con.cursor() as cur:
                cur.execute(
                    "INSERT INTO risk_events(type, payload) VALUES(%s, %s::jsonb)",
                    (event_type, json.dumps(payload)),
                )

    def insert_execution_log(self, event_type: str, payload: dict[str, Any]) -> None:
        with self.connection() as con:
            with con.cursor() as cur:
                cur.execute(
                    "INSERT INTO execution_logs(event_type, payload) VALUES(%s, %s::jsonb)",
                    (event_type, Json(payload)),
                )

    def insert_trade(self, trade: dict[str, Any]) -> None:
        with self.connection() as con:
            with con.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO trades(
                        id, strategy_version, side, entry_price, stop_price, target_price,
                        size, status, risk_ticket_hash, entry_timestamp, exit_timestamp,
                        pnl, fees, slippage, regime_snapshot
                    ) VALUES (
                        %(id)s, %(strategy_version)s, %(side)s, %(entry_price)s, %(stop_price)s, %(target_price)s,
                        %(size)s, %(status)s, %(risk_ticket_hash)s, %(entry_timestamp)s, %(exit_timestamp)s,
                        %(pnl)s, %(fees)s, %(slippage)s, %(regime_snapshot)s::jsonb
                    )
                    """,
                    {
                        **trade,
                        "regime_snapshot": json.dumps(trade.get("regime_snapshot", {})),
                    },
                )
