from __future__ import annotations

import asyncio
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Callable


@dataclass
class Candle:
    symbol: str
    timeframe: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    source: str


class CandleBuilder:
    """No partial candle overwrite: finalized buckets are immutable."""

    def __init__(self):
        self._active: dict[tuple[str, str], Candle] = {}
        self._finalized_keys: set[tuple[str, str, datetime]] = set()

    def on_trade(
        self,
        *,
        symbol: str,
        timeframe: str,
        trade_ts: datetime,
        price: float,
        size: float,
        source: str,
    ) -> list[Candle]:
        bucket_ts = self._bucketize(trade_ts, timeframe)
        key = (symbol, timeframe)
        finalized: list[Candle] = []

        current = self._active.get(key)
        if current and current.timestamp != bucket_ts:
            self._finalized_keys.add((current.symbol, current.timeframe, current.timestamp))
            finalized.append(current)
            current = None

        immutable_key = (symbol, timeframe, bucket_ts)
        if immutable_key in self._finalized_keys:
            # drop late tick instead of mutating finalized candle
            return finalized

        if current is None:
            self._active[key] = Candle(
                symbol=symbol,
                timeframe=timeframe,
                timestamp=bucket_ts,
                open=price,
                high=price,
                low=price,
                close=price,
                volume=size,
                source=source,
            )
            return finalized

        current.high = max(current.high, price)
        current.low = min(current.low, price)
        current.close = price
        current.volume += size
        return finalized

    def _bucketize(self, ts: datetime, timeframe: str) -> datetime:
        minutes = int(timeframe.rstrip("m"))
        ts_utc = ts.astimezone(UTC).replace(second=0, microsecond=0)
        minute = (ts_utc.minute // minutes) * minutes
        return ts_utc.replace(minute=minute)


class MarketDataFeed:
    def __init__(self, rest_client, ws_client_factory, gap_callback: Callable[[dict[str, Any]], None]):
        self.rest_client = rest_client
        self.ws_client_factory = ws_client_factory
        self.gap_callback = gap_callback
        self._last_candle_ts: dict[tuple[str, str], datetime] = {}

    async def bootstrap_historical(self, symbol: str, timeframe: str, limit: int = 500) -> list[dict[str, Any]]:
        return await self.rest_client.fetch_candles(symbol=symbol, timeframe=timeframe, limit=limit)

    async def stream_live(self, symbols: list[str], on_message: Callable[[dict[str, Any]], None]) -> None:
        backoff = 1
        while True:
            try:
                ws_client = self.ws_client_factory(symbols)
                async for msg in ws_client:
                    on_message(msg)
                backoff = 1
            except Exception:
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 30)

    def detect_gap(self, symbol: str, timeframe: str, timestamp: datetime, expected_delta_seconds: int) -> None:
        key = (symbol, timeframe)
        prev = self._last_candle_ts.get(key)
        if prev is not None:
            delta = int((timestamp - prev).total_seconds())
            if delta > expected_delta_seconds:
                self.gap_callback(
                    {
                        "symbol": symbol,
                        "timeframe": timeframe,
                        "previous": prev.isoformat(),
                        "current": timestamp.isoformat(),
                        "gap_seconds": delta,
                    }
                )
        self._last_candle_ts[key] = timestamp
