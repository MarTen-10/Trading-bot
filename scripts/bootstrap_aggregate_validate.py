#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from core.data.aggregator import Candle, aggregate_1m_to_1h, aggregate_1m_to_30m, atr, ema
from core.data.bootstrap_okx import fetch_okx_1m
from core.db.postgres import PostgresDB


def main():
    db = PostgresDB()
    rows = fetch_okx_1m("BTC-USDT-SWAP", target_count=1000)

    candles_1m = [
        Candle(
            symbol="BTC-USDT-SWAP",
            timeframe="1m",
            timestamp=r["timestamp"],
            open=r["open"],
            high=r["high"],
            low=r["low"],
            close=r["close"],
            volume=r["volume"],
            source="bootstrap",
        )
        for r in rows
    ]

    for c in candles_1m:
        db.insert_candle(
            {
                "symbol": c.symbol,
                "timeframe": c.timeframe,
                "timestamp": c.timestamp,
                "open": c.open,
                "high": c.high,
                "low": c.low,
                "close": c.close,
                "volume": c.volume,
                "source": c.source,
            }
        )

    c30 = aggregate_1m_to_30m(candles_1m)
    c1h = aggregate_1m_to_1h(candles_1m)

    for c in c30 + c1h:
        db.insert_candle(
            {
                "symbol": c.symbol,
                "timeframe": c.timeframe,
                "timestamp": c.timestamp,
                "open": c.open,
                "high": c.high,
                "low": c.low,
                "close": c.close,
                "volume": c.volume,
                "source": c.source,
            }
        )

    atr30 = atr(c30, period=14)
    ema1h = ema([x.close for x in c1h], period=200)

    sample_30 = c30[-1]
    out = {
        "bootstrap_count_1m": len(candles_1m),
        "bootstrap_first_ts": candles_1m[0].timestamp.isoformat() if candles_1m else None,
        "bootstrap_last_ts": candles_1m[-1].timestamp.isoformat() if candles_1m else None,
        "sample_30m": {
            "timestamp": sample_30.timestamp.isoformat(),
            "open": sample_30.open,
            "high": sample_30.high,
            "low": sample_30.low,
            "close": sample_30.close,
            "volume": sample_30.volume,
        },
        "sample_1h_ema200": ema1h[-1] if ema1h else None,
        "sample_30m_atr14": atr30[-1] if atr30 else None,
        "agg_counts": {"30m": len(c30), "1h": len(c1h)},
    }

    Path("artifacts/bootstrap_aggregate_validate.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
