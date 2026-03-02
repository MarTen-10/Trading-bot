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
                        id, trade_id, strategy_version, side, entry_price, stop_price, target_price,
                        size, status, risk_ticket_hash, entry_timestamp, exit_timestamp,
                        pnl, fees, slippage, regime_snapshot
                    ) VALUES (
                        %(id)s, %(trade_id)s, %(strategy_version)s, %(side)s, %(entry_price)s, %(stop_price)s, %(target_price)s,
                        %(size)s, %(status)s, %(risk_ticket_hash)s, %(entry_timestamp)s, %(exit_timestamp)s,
                        %(pnl)s, %(fees)s, %(slippage)s, %(regime_snapshot)s::jsonb
                    )
                    """,
                    {
                        **trade,
                        "trade_id": trade.get("trade_id", trade["id"]),
                        "regime_snapshot": json.dumps(trade.get("regime_snapshot", {})),
                    },
                )

    def get_trade_by_trade_id(self, trade_id: str) -> dict[str, Any] | None:
        with self.connection() as con:
            with con.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT trade_id::text as trade_id, status, risk_ticket_hash, entry_timestamp, exit_timestamp FROM trades WHERE trade_id=%s",
                    (trade_id,),
                )
                row = cur.fetchone()
                return dict(row) if row else None

    def create_open_trade_if_absent(self, trade: dict[str, Any]) -> bool:
        with self.connection() as con:
            with con.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO trades(
                        id, trade_id, strategy_version, side, entry_price, stop_price, target_price,
                        size, status, risk_ticket_hash, entry_timestamp, exit_timestamp,
                        pnl, fees, slippage, regime_snapshot
                    ) VALUES (
                        %(id)s, %(trade_id)s, %(strategy_version)s, %(side)s, %(entry_price)s, %(stop_price)s, %(target_price)s,
                        %(size)s, %(status)s, %(risk_ticket_hash)s, %(entry_timestamp)s, %(exit_timestamp)s,
                        %(pnl)s, %(fees)s, %(slippage)s, %(regime_snapshot)s::jsonb
                    )
                    ON CONFLICT (trade_id) DO NOTHING
                    """,
                    {
                        **trade,
                        "trade_id": trade.get("trade_id", trade["id"]),
                        "regime_snapshot": json.dumps(trade.get("regime_snapshot", {})),
                    },
                )
                return cur.rowcount == 1

    def update_trade_close(self, trade_id: str, *, exit_price: float, pnl: float, fees: float, slippage: float, status: str = "CLOSED") -> None:
        with self.connection() as con:
            with con.cursor() as cur:
                cur.execute(
                    """
                    UPDATE trades
                    SET status=%s, exit_timestamp=NOW(), pnl=%s, fees=COALESCE(fees,0)+%s, slippage=COALESCE(slippage,0)+%s
                    WHERE trade_id=%s
                    """,
                    (status, pnl, fees, slippage, trade_id),
                )

    def fetch_open_trades(self) -> list[dict[str, Any]]:
        with self.connection() as con:
            with con.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT trade_id::text as trade_id, side, size::float8 as size, entry_price::float8 as entry_price, stop_price::float8 as stop_price, target_price::float8 as target_price, risk_ticket_hash FROM trades WHERE status='OPEN' ORDER BY entry_timestamp"
                )
                return [dict(r) for r in cur.fetchall()]

    def insert_candle(self, candle: dict[str, Any]) -> None:
        with self.connection() as con:
            with con.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO candles(symbol,timeframe,timestamp,open,high,low,close,volume,source)
                    VALUES(%(symbol)s,%(timeframe)s,%(timestamp)s,%(open)s,%(high)s,%(low)s,%(close)s,%(volume)s,%(source)s)
                    ON CONFLICT(symbol,timeframe,timestamp) DO NOTHING
                    """,
                    candle,
                )

    def fetch_candles(self, symbol: str, timeframe: str, limit: int = 5000) -> list[dict[str, Any]]:
        with self.connection() as con:
            with con.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT symbol,timeframe,timestamp,open::float8 as open,high::float8 as high,low::float8 as low,close::float8 as close,volume::float8 as volume,source
                    FROM candles
                    WHERE symbol=%s AND timeframe=%s
                    ORDER BY timestamp DESC
                    LIMIT %s
                    """,
                    (symbol, timeframe, limit),
                )
                rows = [dict(r) for r in cur.fetchall()]
                rows.reverse()
                return rows

    def latest_candle_ts(self, symbol: str, timeframe: str) -> Any:
        with self.connection() as con:
            with con.cursor() as cur:
                cur.execute("SELECT MAX(timestamp) FROM candles WHERE symbol=%s AND timeframe=%s", (symbol, timeframe))
                return cur.fetchone()[0]
