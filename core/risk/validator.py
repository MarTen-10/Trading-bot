from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


REQUIRED_RISK_TICKET_FIELDS = {
    "trade_id",
    "allowed_size",
    "allowed_risk_amount",
    "stop_price",
    "max_slippage",
    "expiry_timestamp",
    "signature_hash",
}


@dataclass(frozen=True)
class ValidationResult:
    decision: str
    reason: str
    details: dict[str, Any]


class RiskValidator:
    """Ma'at hard gate: DENY if RiskTicket is invalid or missing.

    The signature hash is an HMAC-SHA256 over canonical ticket fields.
    """

    def __init__(self, db_writer, signing_secret: str):
        self._db_writer = db_writer
        self._secret = signing_secret.encode("utf-8")

    def validate(self, risk_ticket: dict[str, Any] | None) -> ValidationResult:
        if not risk_ticket:
            return self._deny("missing_risk_ticket", {"ticket": None})

        missing = REQUIRED_RISK_TICKET_FIELDS.difference(risk_ticket.keys())
        if missing:
            return self._deny(
                "invalid_risk_ticket_fields",
                {"missing_fields": sorted(list(missing))},
            )

        provided_hash = str(risk_ticket.get("signature_hash", ""))
        expected_hash = self.compute_signature_hash(risk_ticket)
        if not hmac.compare_digest(provided_hash, expected_hash):
            return self._deny(
                "signature_mismatch",
                {"provided_hash": provided_hash, "expected_hash": expected_hash},
            )

        expiry = self._parse_timestamp(str(risk_ticket["expiry_timestamp"]))
        if expiry is None:
            return self._deny(
                "invalid_expiry_timestamp",
                {"expiry_timestamp": risk_ticket.get("expiry_timestamp")},
            )

        if expiry <= datetime.now(UTC):
            return self._deny(
                "risk_ticket_expired",
                {
                    "expiry_timestamp": risk_ticket["expiry_timestamp"],
                    "now_utc": datetime.now(UTC).isoformat(),
                },
            )

        return ValidationResult(
            decision="ALLOW",
            reason="risk_ticket_valid",
            details={
                "trade_id": risk_ticket["trade_id"],
                "signature_hash": provided_hash,
                "expiry_timestamp": risk_ticket["expiry_timestamp"],
            },
        )

    def compute_signature_hash(self, risk_ticket: dict[str, Any]) -> str:
        body = {
            "trade_id": risk_ticket["trade_id"],
            "allowed_size": risk_ticket["allowed_size"],
            "allowed_risk_amount": risk_ticket["allowed_risk_amount"],
            "stop_price": risk_ticket["stop_price"],
            "max_slippage": risk_ticket["max_slippage"],
            "expiry_timestamp": risk_ticket["expiry_timestamp"],
        }
        canonical = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hmac.new(self._secret, canonical, hashlib.sha256).hexdigest()

    def _parse_timestamp(self, value: str) -> datetime | None:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=UTC)
            return parsed.astimezone(UTC)
        except ValueError:
            return None

    def _deny(self, reason: str, details: dict[str, Any]) -> ValidationResult:
        self._db_writer.insert_risk_event(event_type="DENY", payload={"reason": reason, **details})
        return ValidationResult(decision="DENY", reason=reason, details=details)
