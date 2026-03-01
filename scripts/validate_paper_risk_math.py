#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from core.execution.paper_engine import PaperEngine


class RiskEventCollector:
    def __init__(self):
        self.events = []

    def insert_risk_event(self, event_type, payload):
        self.events.append({"event_type": event_type, "payload": payload})


def main():
    collector = RiskEventCollector()
    engine = PaperEngine(starting_equity=500.0, fee_bps=0.0, slippage_bps=0.0, risk_tolerance=0.01, db_writer=collector)

    entry_mid = 100000.0
    stop_price = 99500.0  # 500 distance
    allowed_risk_amount = 5.0
    allowed_size = allowed_risk_amount / (entry_mid - stop_price)  # 5/500 = 0.01

    risk_ticket = {
        "trade_id": "11111111-1111-1111-1111-111111111111",
        "allowed_size": allowed_size,
        "allowed_risk_amount": allowed_risk_amount,
        "stop_price": stop_price,
        "max_slippage": 0.0,
        "expiry_timestamp": (datetime.now(UTC) + timedelta(minutes=30)).isoformat(),
        "signature_hash": "0" * 64,
    }

    opened = engine.open_trade_from_risk_ticket(
        risk_ticket=risk_ticket,
        symbol="BTC-PERP",
        side="BUY",
        entry_mid_price=entry_mid,
        target_price=101000.0,
    )

    closed = engine.close_trade(trade_id=risk_ticket["trade_id"], exit_mid=stop_price, reason="STOP")

    out = {
        "entry_price": opened["fill_price"],
        "stop_price": stop_price,
        "size": opened["size"],
        "calculated_risk": abs((opened["fill_price"] - stop_price) * opened["size"]),
        "allowed_risk_amount": allowed_risk_amount,
        "realized_pnl": closed["net_pnl"],
        "equity_after_trade": engine.equity,
        "risk_events": collector.events,
    }
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
