from __future__ import annotations

import hashlib
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import requests


logger = logging.getLogger(__name__)


@dataclass
class RetryPolicy:
    max_attempts: int = 3
    backoff_base_seconds: float = 0.5


class CoinbaseAdapter:
    """Coinbase adapter skeleton (paper-safe by default)."""

    def __init__(
        self,
        api_base: str = "https://api.coinbase.com/api/v3/brokerage",
        timeout_seconds: float = 10.0,
        retry_policy: RetryPolicy | None = None,
        db_writer: Any | None = None,
    ):
        self.api_base = api_base.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.retry_policy = retry_policy or RetryPolicy()
        self.db_writer = db_writer
        self.api_key = os.getenv("COINBASE_API_KEY", "")
        self.api_secret = os.getenv("COINBASE_API_SECRET", "")
        self.passphrase = os.getenv("COINBASE_API_PASSPHRASE", "")
        self.session = requests.Session()

    def connect(self) -> dict[str, Any]:
        authenticated = all([self.api_key, self.api_secret, self.passphrase])
        return {
            "connected": True,
            "authenticated": authenticated,
            "mode": "read_only" if not authenticated else "ready",
            "base_url": self.api_base,
        }

    def get_account_balance(self) -> dict[str, Any]:
        if not self._authenticated():
            return {"ok": False, "reason": "missing_api_credentials", "accounts": []}
        return self._request_with_retry("GET", "/accounts")

    def get_perp_positions(self) -> dict[str, Any]:
        if not self._authenticated():
            return {"ok": False, "reason": "missing_api_credentials", "positions": []}
        return self._request_with_retry("GET", "/cfm/positions")

    def get_market_price(self, symbol: str) -> dict[str, Any]:
        return self._request_with_retry("GET", f"/products/{symbol}")

    def place_market_order(self, *, symbol: str, side: str, size: str, idempotency_key: str | None = None) -> dict[str, Any]:
        payload = {
            "client_order_id": idempotency_key or self._idempotency_key(symbol, side, size),
            "product_id": symbol,
            "side": side.upper(),
            "order_configuration": {
                "market_market_ioc": {
                    "base_size": str(size),
                }
            },
        }
        return self._private_order(payload)

    def place_limit_order(
        self,
        *,
        symbol: str,
        side: str,
        size: str,
        limit_price: str,
        post_only: bool = False,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        payload = {
            "client_order_id": idempotency_key or self._idempotency_key(symbol, side, size, limit_price),
            "product_id": symbol,
            "side": side.upper(),
            "order_configuration": {
                "limit_limit_gtc": {
                    "base_size": str(size),
                    "limit_price": str(limit_price),
                    "post_only": bool(post_only),
                }
            },
        }
        return self._private_order(payload)

    def cancel_order(self, order_id: str) -> dict[str, Any]:
        if not self._authenticated():
            return {"ok": False, "reason": "missing_api_credentials", "order_id": order_id}
        return self._request_with_retry("POST", "/orders/batch_cancel", json_payload={"order_ids": [order_id]})

    def fetch_order_status(self, order_id: str) -> dict[str, Any]:
        if not self._authenticated():
            return {"ok": False, "reason": "missing_api_credentials", "order_id": order_id}
        return self._request_with_retry("GET", f"/orders/historical/{order_id}")

    def fetch_fills(self, order_id: str | None = None) -> dict[str, Any]:
        if not self._authenticated():
            return {"ok": False, "reason": "missing_api_credentials", "fills": []}
        path = "/orders/historical/fills"
        if order_id:
            path = f"{path}?order_id={order_id}"
        return self._request_with_retry("GET", path)

    def _private_order(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not self._authenticated():
            return {
                "ok": False,
                "reason": "missing_api_credentials",
                "client_order_id": payload.get("client_order_id"),
                "safe_mode": "paper_only",
            }
        return self._request_with_retry("POST", "/orders", json_payload=payload)

    def _request_with_retry(self, method: str, path: str, json_payload: dict[str, Any] | None = None) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(1, self.retry_policy.max_attempts + 1):
            try:
                return self._request(method, path, json_payload=json_payload)
            except (requests.Timeout, requests.ConnectionError) as err:
                last_error = err
                self._log_event(
                    "exchange.retry",
                    {
                        "attempt": attempt,
                        "max_attempts": self.retry_policy.max_attempts,
                        "path": path,
                        "error": str(err),
                    },
                )
                if attempt == self.retry_policy.max_attempts:
                    break
                time.sleep(self.retry_policy.backoff_base_seconds * (2 ** (attempt - 1)))

        return {
            "ok": False,
            "error": "request_failed",
            "path": path,
            "details": str(last_error) if last_error else "unknown",
        }

    def _request(self, method: str, path: str, json_payload: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{self.api_base}{path}"
        headers = {"Content-Type": "application/json"}

        # Authentication intentionally stubbed here. Full signing is deferred.
        if self._authenticated():
            headers["CB-ACCESS-KEY"] = self.api_key

        started = time.time()
        response = self.session.request(
            method=method,
            url=url,
            json=json_payload,
            headers=headers,
            timeout=self.timeout_seconds,
        )
        latency_ms = int((time.time() - started) * 1000)

        payload: dict[str, Any]
        try:
            payload = response.json()
        except ValueError:
            payload = {"raw": response.text}

        data = {
            "ok": response.ok,
            "status_code": response.status_code,
            "path": path,
            "latency_ms": latency_ms,
            "payload": payload,
        }
        self._log_event("exchange.response", data)
        return data

    def _log_event(self, event_type: str, payload: dict[str, Any]) -> None:
        deterministic_payload = json.loads(json.dumps(payload, sort_keys=True, default=str))
        message = json.dumps(
            {
                "event_type": event_type,
                "timestamp": datetime.now(UTC).isoformat(),
                "payload": deterministic_payload,
            },
            sort_keys=True,
        )
        logger.info(message)
        if self.db_writer is not None:
            self.db_writer.insert_execution_log(event_type=event_type, payload=deterministic_payload)

    def _authenticated(self) -> bool:
        return all([self.api_key, self.api_secret, self.passphrase])

    def _idempotency_key(self, *parts: Any) -> str:
        raw = "|".join(str(part) for part in parts) + f"|{uuid.uuid4()}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()
