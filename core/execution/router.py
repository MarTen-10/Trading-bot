from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.risk.validator import RiskValidator


@dataclass
class RouteDecision:
    decision: str
    reason: str
    details: dict[str, Any]


class HorusRouter:
    """No-shortcut path: all orders pass through RiskTicket validation."""

    def __init__(self, risk_validator: RiskValidator, adapter):
        self.risk_validator = risk_validator
        self.adapter = adapter

    def route_market_order(self, *, risk_ticket: dict[str, Any] | None, symbol: str, side: str, size: str) -> RouteDecision:
        validation = self.risk_validator.validate(risk_ticket)
        if validation.decision != "ALLOW":
            return RouteDecision(decision="DENY", reason=validation.reason, details=validation.details)

        ticket_size = float(risk_ticket["allowed_size"])
        if float(size) > ticket_size:
            return RouteDecision(
                decision="DENY",
                reason="size_exceeds_ticket",
                details={"requested": size, "allowed": risk_ticket["allowed_size"]},
            )

        result = self.adapter.place_market_order(symbol=symbol, side=side, size=size)
        return RouteDecision(decision="ALLOW", reason="routed", details=result)
