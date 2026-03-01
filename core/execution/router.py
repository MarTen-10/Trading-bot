from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from core.risk.validator import RiskValidator


@dataclass
class RouteDecision:
    decision: str
    reason: str
    details: dict[str, Any]


class HorusRouter:
    """No-shortcut path: all orders pass through RiskTicket validation.

    Exactly-once creation: duplicate OPEN trade_id will not re-send an order.
    """

    def __init__(self, risk_validator: RiskValidator, adapter, db_writer=None):
        self.risk_validator = risk_validator
        self.adapter = adapter
        self.db_writer = db_writer

    def route_market_order(self, *, risk_ticket: dict[str, Any] | None, symbol: str, side: str, size: str) -> RouteDecision:
        validation = self.risk_validator.validate(risk_ticket)
        if validation.decision != "ALLOW":
            return RouteDecision(decision="DENY", reason=validation.reason, details=validation.details)

        trade_id = str(risk_ticket["trade_id"])
        ticket_size = float(risk_ticket["allowed_size"])
        if float(size) > ticket_size:
            deny = {
                "trade_id": trade_id,
                "requested": size,
                "allowed": risk_ticket["allowed_size"],
            }
            if self.db_writer:
                self.db_writer.insert_risk_event("DENY", {"reason": "size_exceeds_ticket", **deny})
            return RouteDecision(decision="DENY", reason="size_exceeds_ticket", details=deny)

        if self.db_writer:
            existing = self.db_writer.get_trade_by_trade_id(trade_id)
            if existing and existing.get("status") == "OPEN":
                self.db_writer.insert_execution_log(
                    event_type="reconciliation.duplicate_open_trade",
                    payload={"trade_id": trade_id, "action": "no_resend", "symbol": symbol, "side": side},
                )
                return RouteDecision(
                    decision="DENY",
                    reason="duplicate_open_trade",
                    details={"trade_id": trade_id, "action": "no_resend"},
                )

            created = self.db_writer.create_open_trade_if_absent(
                {
                    "id": str(uuid.uuid4()),
                    "trade_id": trade_id,
                    "strategy_version": "unknown",
                    "side": side.upper(),
                    "entry_price": float(risk_ticket["stop_price"]),
                    "stop_price": float(risk_ticket["stop_price"]),
                    "target_price": float(risk_ticket["stop_price"]),
                    "size": float(size),
                    "status": "OPEN",
                    "risk_ticket_hash": risk_ticket["signature_hash"],
                    "entry_timestamp": datetime.now(UTC),
                    "exit_timestamp": None,
                    "pnl": None,
                    "fees": 0,
                    "slippage": 0,
                    "regime_snapshot": {},
                }
            )
            if not created:
                self.db_writer.insert_execution_log(
                    event_type="reconciliation.trade_exists",
                    payload={"trade_id": trade_id, "action": "no_resend", "symbol": symbol, "side": side},
                )
                return RouteDecision(
                    decision="DENY",
                    reason="duplicate_trade_id",
                    details={"trade_id": trade_id, "action": "no_resend"},
                )

        result = self.adapter.place_market_order(symbol=symbol, side=side, size=size, idempotency_key=trade_id)
        return RouteDecision(decision="ALLOW", reason="routed", details=result)
