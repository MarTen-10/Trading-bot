#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import random
import signal
import sys
import time
import uuid
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path

import requests

sys.path.append(str(Path(__file__).resolve().parents[1]))

from core.db.postgres import PostgresDB
from core.execution.paper_engine import PaperEngine
from core.execution.router import HorusRouter
from core.risk.validator import RiskValidator


RUN_STATE = {"stop": False}


def on_term(*_):
    RUN_STATE["stop"] = True


class RuntimeWriter:
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


def fetch_price(symbol="BTC-USD") -> float:
    r = requests.get(f"https://api.exchange.coinbase.com/products/{symbol}/ticker", timeout=10)
    j = r.json()
    return float(j["price"])


def build_ticket(validator: RiskValidator, trade_id: str, entry: float, stop: float, allowed_risk: float = 5.0):
    size = allowed_risk / abs(entry - stop)
    ticket = {
        "trade_id": trade_id,
        "allowed_size": round(size, 8),
        "allowed_risk_amount": allowed_risk,
        "stop_price": round(stop, 2),
        "max_slippage": 1.0,
        "expiry_timestamp": (datetime.now(UTC) + timedelta(minutes=30)).isoformat(),
    }
    ticket["signature_hash"] = validator.compute_signature_hash(ticket)
    return ticket


def max_drawdown(curve: list[dict]) -> float:
    peak = -1e18
    mdd = 0.0
    for p in curve:
        eq = float(p["equity"])
        peak = max(peak, eq)
        dd = (peak - eq)
        mdd = max(mdd, dd)
    return mdd


def run_continuous(duration_hours: float = 24.0, poll_seconds: int = 30, simulate_kill_once: bool = False):
    db = PostgresDB()
    writer = RuntimeWriter(db)
    validator = RiskValidator(writer, "paper-secret")
    router = HorusRouter(validator, FakeAdapter(), db_writer=writer)
    engine = PaperEngine(starting_equity=500.0, fee_bps=4.0, slippage_bps=2.0, risk_tolerance=1.0, db_writer=writer)

    # Recovery bootstrap: reconstruct open trades from DB
    recovered = db.fetch_open_trades()
    for t in recovered:
        engine.open_positions[t["trade_id"]] = engine.open_positions.get(t["trade_id"]) or type(
            "Recovered", (), {
                "trade_id": t["trade_id"], "symbol": "BTC-PERP", "side": t["side"], "size": float(t["size"]),
                "entry_price": float(t["entry_price"]), "stop_price": float(t["stop_price"]), "target_price": float(t["target_price"]),
                "allowed_risk_amount": 5.0, "fee_paid": 0.0, "slippage_paid": 0.0, "opened_at": datetime.now(UTC)
            }
        )

    start = datetime.now(UTC)
    end_target = start + timedelta(hours=duration_hours)
    denies = Counter()
    total_trades = 0
    crashes = 0
    killed = False

    while datetime.now(UTC) < end_target and not RUN_STATE["stop"]:
        try:
            price = fetch_price("BTC-USD")
            ts = datetime.now(UTC)
            candle = {
                "symbol": "BTC-USD", "timeframe": "1m", "timestamp": ts.replace(second=0, microsecond=0),
                "open": price, "high": price, "low": price, "close": price, "volume": random.uniform(0.1, 1.5), "source": "coinbase_public"
            }
            db.insert_candle(candle)

            # open one trade if none open
            if not engine.open_positions:
                stop = price - 500.0
                target = price + 1000.0
                tid = str(uuid.uuid4())
                ticket = build_ticket(validator, tid, price, stop, allowed_risk=5.0)
                decision = router.route_market_order(risk_ticket=ticket, symbol="BTC-PERP", side="BUY", size=str(ticket["allowed_size"]))
                if decision.decision == "ALLOW":
                    opened = engine.open_trade_from_risk_ticket(
                        risk_ticket=ticket, symbol="BTC-PERP", side="BUY", entry_mid_price=price, target_price=target
                    )
                    # Router already persists OPEN trade row via create_open_trade_if_absent.
                    # Only track count here.
                    total_trades += 1
                else:
                    denies[decision.reason] += 1

            closed = engine.on_price_tick("BTC-PERP", price)
            for c in closed:
                db.update_trade_close(
                    c["trade_id"],
                    exit_price=float(c["exit_price"]),
                    pnl=float(c["net_pnl"]),
                    fees=float(c["fees"]),
                    slippage=float(c["slippage"]),
                )

            db.insert_execution_log("paper.tick", {"price": price, "equity": engine.equity, "open_positions": len(engine.open_positions)})

            if simulate_kill_once and (not killed) and total_trades >= 1 and engine.open_positions:
                killed = True
                db.insert_execution_log("paper.simulated_kill", {"at": datetime.now(UTC).isoformat()})
                raise KeyboardInterrupt("simulated kill mid-trade")

            if engine.equity < 0:
                db.insert_risk_event("DENY", {"reason": "negative_equity", "equity": engine.equity})
                break

            time.sleep(poll_seconds)
        except KeyboardInterrupt:
            crashes += 1
            break
        except Exception as e:
            crashes += 1
            db.insert_execution_log("paper.error", {"error": str(e)})
            time.sleep(min(poll_seconds, 10))

    report = {
        "start_utc": start.isoformat(),
        "end_utc": datetime.now(UTC).isoformat(),
        "start_equity": 500.0,
        "end_equity": engine.equity,
        "max_drawdown": max_drawdown(engine.equity_curve),
        "total_trades": total_trades,
        "total_denies": sum(denies.values()),
        "router_denies_by_reason": dict(denies),
        "risk_events_count": None,
        "crash_count": crashes,
    }
    out = Path("artifacts/paper_forward_run_latest.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--continuous", action="store_true")
    parser.add_argument("--duration-hours", type=float, default=24.0)
    parser.add_argument("--poll-seconds", type=int, default=30)
    parser.add_argument("--simulate-kill-once", action="store_true")
    args = parser.parse_args()

    signal.signal(signal.SIGTERM, on_term)
    signal.signal(signal.SIGINT, on_term)

    if args.continuous:
        run_continuous(args.duration_hours, args.poll_seconds, args.simulate_kill_once)
    else:
        run_continuous(0.01, 1, False)


if __name__ == "__main__":
    main()
