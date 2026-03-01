#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from core.execution.paper_engine import PaperEngine
from core.execution.router import HorusRouter
from core.risk.validator import RiskValidator


class InMemoryWriter:
    def __init__(self):
        self.risk_events = []
        self.execution_logs = []
        self.trades = {}

    def insert_risk_event(self, event_type, payload):
        self.risk_events.append({"event_type": event_type, "payload": payload})

    def insert_execution_log(self, event_type, payload):
        self.execution_logs.append({"event_type": event_type, "payload": payload})

    def get_trade_by_trade_id(self, trade_id):
        return self.trades.get(trade_id)

    def create_open_trade_if_absent(self, trade):
        tid = trade["trade_id"]
        if tid in self.trades:
            return False
        self.trades[tid] = {"trade_id": tid, "status": "OPEN"}
        return True


class FakeAdapter:
    def place_market_order(self, **kwargs):
        return {"ok": True, "status_code": 200, "kwargs": kwargs}


def make_ticket(validator: RiskValidator, trade_id: str, minutes: int = 30):
    ticket = {
        "trade_id": trade_id,
        "allowed_size": 0.1,
        "allowed_risk_amount": 25.0,
        "stop_price": 98000.0,
        "max_slippage": 0.001,
        "expiry_timestamp": (datetime.now(UTC) + timedelta(minutes=minutes)).isoformat(),
    }
    ticket["signature_hash"] = validator.compute_signature_hash(ticket)
    return ticket


def main():
    start = datetime.now(UTC)
    writer = InMemoryWriter()
    validator = RiskValidator(writer, "paper-secret")
    router = HorusRouter(validator, FakeAdapter(), db_writer=writer)
    paper = PaperEngine(mode="paper")

    # Signal -> RiskTicket -> Router
    ticket = make_ticket(validator, "00000000-0000-0000-0000-000000000001")
    route = router.route_market_order(risk_ticket=ticket, symbol="BTC-PERP", side="BUY", size="0.1")

    # Duplicate trade_id check (must DENY + reconciliation)
    duplicate = router.route_market_order(risk_ticket=ticket, symbol="BTC-PERP", side="BUY", size="0.1")

    opened = paper.open_trade(
        trade_id=ticket["trade_id"],
        symbol="BTC-PERP",
        side="BUY",
        size=0.1,
        mid_price=100000.0,
        stop_price=98000.0,
        target_price=102000.0,
    )

    ticks = [100500.0, 101000.0, 102100.0]
    closed = []
    for px in ticks:
        closed.extend(paper.on_price_tick("BTC-PERP", px))

    end = datetime.now(UTC)
    report = {
        "start_utc": start.isoformat(),
        "end_utc": end.isoformat(),
        "router_first": route.__dict__,
        "router_duplicate": duplicate.__dict__,
        "trades_opened": 1 if opened.get("status") == "OPEN" else 0,
        "trades_closed": len(closed),
        "realized_pnl": paper.realized_pnl,
        "equity": paper.equity,
        "deny_count": len(writer.risk_events),
        "deny_reasons": [e["payload"].get("reason") for e in writer.risk_events],
        "execution_log_count": len(writer.execution_logs),
        "equity_curve_points": len(paper.equity_curve),
    }
    out = Path("artifacts/paper_forward_run_latest.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
