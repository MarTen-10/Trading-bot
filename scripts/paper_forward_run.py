#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import signal
import sys
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import requests

sys.path.append(str(Path(__file__).resolve().parents[1]))

from core.data.aggregator import Candle, aggregate_1m_to_1h, aggregate_1m_to_30m, atr, ema
from core.db.postgres import PostgresDB
from core.execution.paper_engine import PaperEngine
from core.execution.router import HorusRouter
from core.risk.validator import RiskValidator

RUN = {"stop": False}


def _stop(*_):
    RUN["stop"] = True


@dataclass
class MarketState:
    watermark: datetime
    candles_30m: list[Candle]
    candles_1h: list[Candle]
    atr14_30m: float
    ema200_1h: float
    regime_label: str
    trade_allowed: bool
    risk_multiplier: float


class Writer:
    def __init__(self, db: PostgresDB):
        self.db = db

    def insert_risk_event(self, event_type, payload):
        self.db.insert_risk_event(event_type, payload)

    def insert_execution_log(self, event_type, payload):
        self.db.insert_execution_log(event_type, payload)

    def get_trade_by_trade_id(self, trade_id):
        return self.db.get_trade_by_trade_id(trade_id)

    def create_open_trade_if_absent(self, trade):
        return self.db.create_open_trade_if_absent(trade)


class FakeAdapter:
    def place_market_order(self, **kwargs):
        return {"ok": True, "status_code": 200, "kwargs": kwargs}


def fetch_perp_price(inst_id="BTC-USDT-SWAP") -> float:
    r = requests.get(f"https://www.okx.com/api/v5/market/ticker?instId={inst_id}", timeout=10)
    r.raise_for_status()
    return float(r.json()["data"][0]["last"])


def to_candles(rows: list[dict]) -> list[Candle]:
    return [
        Candle(
            symbol=r["symbol"], timeframe=r["timeframe"], timestamp=r["timestamp"],
            open=float(r["open"]), high=float(r["high"]), low=float(r["low"]), close=float(r["close"]), volume=float(r["volume"]), source=r.get("source", "db")
        )
        for r in rows
    ]


def build_market_state(db: PostgresDB, symbol: str) -> MarketState | None:
    c1m = to_candles(db.fetch_candles(symbol, "1m", 15000))
    c30 = aggregate_1m_to_30m(c1m)
    c1h = aggregate_1m_to_1h(c1m)

    if len(c1h) < 200 or len(c30) < 50:
        return None

    atr14 = atr(c30, period=14)[-1]
    ema200 = ema([x.close for x in c1h], period=200)[-1]
    slope = ema([x.close for x in c1h], period=200)[-1] - ema([x.close for x in c1h], period=200)[-2]
    regime = "TREND_UP" if slope > 0 else "TREND_DOWN"

    return MarketState(
        watermark=c30[-1].timestamp,
        candles_30m=c30,
        candles_1h=c1h,
        atr14_30m=atr14,
        ema200_1h=ema200,
        regime_label=regime,
        trade_allowed=True,
        risk_multiplier=1.0,
    )


def generate_intent(ms: MarketState):
    # 30m breakout over previous 20 closed bars (excluding latest for threshold)
    lookback = ms.candles_30m[-21:-1]
    latest = ms.candles_30m[-1]
    hh = max(c.high for c in lookback)
    if latest.close <= hh:
        return None
    side = "BUY" if latest.close > ms.ema200_1h else None
    if not side:
        return None
    stop = latest.close - (1.5 * ms.atr14_30m)
    return {"side": side, "entry": latest.close, "stop": stop, "target": latest.close + (2.0 * ms.atr14_30m)}


def run(args):
    db = PostgresDB()
    writer = Writer(db)
    risk = RiskValidator(writer, "paper-secret")
    router = HorusRouter(risk, FakeAdapter(), db_writer=writer)
    engine = PaperEngine(starting_equity=500.0, fee_bps=4.0, slippage_bps=2.0, db_writer=writer)

    symbol = args.market_symbol
    last_eval = None
    start = datetime.now(UTC)
    end = start.timestamp() + (args.duration_hours * 3600)

    while time.time() < end and not RUN["stop"]:
        now_min = datetime.now(UTC).replace(second=0, microsecond=0)
        if db.latest_candle_ts(symbol, "1m") is None or now_min > db.latest_candle_ts(symbol, "1m"):
            px = fetch_perp_price(symbol)
            db.insert_candle({"symbol": symbol, "timeframe": "1m", "timestamp": now_min, "open": px, "high": px, "low": px, "close": px, "volume": 0.0, "source": "live_poll"})

        ms = build_market_state(db, symbol)
        if ms is None:
            writer.insert_execution_log("insufficient_context", {"need_h1": 200, "need_30m": 50})
            time.sleep(args.poll_seconds)
            continue

        if last_eval == ms.watermark:
            time.sleep(args.poll_seconds)
            continue
        last_eval = ms.watermark

        writer.insert_execution_log("evaluation", {"watermark": ms.watermark.isoformat(), "regime": ms.regime_label, "atr14_30m": ms.atr14_30m, "ema200_1h": ms.ema200_1h})
        intent = generate_intent(ms) if ms.trade_allowed else None
        if not intent:
            writer.insert_execution_log("no_intent", {"watermark": ms.watermark.isoformat()})
            continue

        allowed_risk = 5.0 * ms.risk_multiplier
        size = allowed_risk / max(1e-9, abs(intent["entry"] - intent["stop"]))
        ticket = {
            "trade_id": str(uuid.uuid4()),
            "allowed_size": size,
            "allowed_risk_amount": allowed_risk,
            "stop_price": intent["stop"],
            "max_slippage": 1.0,
            "expiry_timestamp": (datetime.now(UTC) + timedelta(minutes=30)).isoformat(),
        }
        ticket["signature_hash"] = risk.compute_signature_hash(ticket)

        if args.dry_run_audit:
            writer.insert_execution_log("dryrun_intent", {"ticket": ticket, "intent": intent, "regime": ms.regime_label})
            continue

        d = router.route_market_order(risk_ticket=ticket, symbol="BTC-PERP", side=intent["side"], size=str(size))
        if d.decision != "ALLOW":
            writer.insert_execution_log("deny", {"reason": d.reason})
            continue

        engine.open_trade_from_risk_ticket(risk_ticket=ticket, symbol="BTC-PERP", side=intent["side"], entry_mid_price=float(intent["entry"]), target_price=float(intent["target"]))
        closed = engine.on_price_tick("BTC-PERP", float(intent["target"]))
        for c in closed:
            db.update_trade_close(c["trade_id"], exit_price=float(c["exit_price"]), pnl=float(c["net_pnl"]), fees=float(c["fees"]), slippage=float(c["slippage"]))

    print(json.dumps({"status": "done", "dry_run_audit": args.dry_run_audit, "start": start.isoformat(), "end": datetime.now(UTC).isoformat(), "equity": engine.equity}, indent=2))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--duration-hours", type=float, default=2.0)
    ap.add_argument("--poll-seconds", type=int, default=20)
    ap.add_argument("--market-symbol", default="BTC-USDT-SWAP")
    ap.add_argument("--dry-run-audit", action="store_true")
    args = ap.parse_args()

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    run(args)


if __name__ == "__main__":
    main()
