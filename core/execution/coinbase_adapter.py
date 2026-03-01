from __future__ import annotations

import hashlib
import json
import logging
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import requests

from core.execution.coinbase_signing import CoinbaseSigner
from core.secrets.provider import SecretsProvider


logger = logging.getLogger(__name__)


@dataclass
class RetryPolicy:
    max_attempts: int = 3
    backoff_base_seconds: float = 0.5


class CoinbaseAdapter:
    """Coinbase adapter skeleton with signer injection and structured logging."""

    def __init__(
        self,
        api_base: str = "https://api.coinbase.com/api/v3/brokerage",
        timeout_seconds: float = 10.0,
        retry_policy: RetryPolicy | None = None,
        db_writer: Any | None = None,
        secrets: SecretsProvider | None = None,
        signer: CoinbaseSigner | None = None,
    ):
        self.api_base = api_base.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.retry_policy = retry_policy or RetryPolicy()
        self.db_writer = db_writer
        self.secrets = secrets or SecretsProvider()
        self.signer = signer or CoinbaseSigner(self.secrets)
        self.session = requests.Session()

    def connect(self) -> dict[str, Any]:
        authenticated = self._authenticated()
        return {
            "connected": True,
            "authenticated": authenticated,
            "mode": "read_only" if not authenticated else "ready",
            "base_url": self.api_base,
        }

    def get_server_time(self) -> dict[str, Any]:
        return self._request_with_retry("GET", "/time", auth=False, endpoint="server_time")

    def get_account_balance(self) -> dict[str, Any]:
        if not self._authenticated():
            return {"ok": False, "reason": "missing_api_credentials", "accounts": []}
        return self._request_with_retry("GET", "/accounts", endpoint="accounts")

    def list_products(self) -> dict[str, Any]:
        return self._request_with_retry("GET", "/products", auth=False, endpoint="products")

    def get_perp_positions(self) -> dict[str, Any]:
        if not self._authenticated():
            return {"ok": False, "reason": "missing_api_credentials", "positions": []}
        return self._request_with_retry("GET", "/cfm/positions", endpoint="positions")

    def get_market_price(self, symbol: str) -> dict[str, Any]:
        return self._request_with_retry("GET", f"/products/{symbol}", auth=False, endpoint="market_price")

    def place_market_order(self, *, symbol: str, side: str, size: str, idempotency_key: str | None = None) -> dict[str, Any]:
        payload = {
            "client_order_id": idempotency_key or self._idempotency_key(symbol, side, size),
            "product_id": symbol,
            "side": side.upper(),
            "order_configuration": {"market_market_ioc": {"base_size": str(size)}},
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
        return self._request_with_retry("POST", "/orders/batch_cancel", json_payload={"order_ids": [order_id]}, endpoint="cancel_order")

    def fetch_order_status(self, order_id: str) -> dict[str, Any]:
        if not self._authenticated():
            return {"ok": False, "reason": "missing_api_credentials", "order_id": order_id}
        return self._request_with_retry("GET", f"/orders/historical/{order_id}", endpoint="order_status")

    def fetch_fills(self, order_id: str | None = None) -> dict[str, Any]:
        if not self._authenticated():
            return {"ok": False, "reason": "missing_api_credentials", "fills": []}
        path = "/orders/historical/fills"
        if order_id:
            path = f"{path}?order_id={order_id}"
        return self._request_with_retry("GET", path, endpoint="fills")

    def _private_order(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not self._authenticated():
            return {
                "ok": False,
                "reason": "missing_api_credentials",
                "client_order_id": payload.get("client_order_id"),
                "safe_mode": "paper_only",
            }
        return self._request_with_retry("POST", "/orders", json_payload=payload, endpoint="place_order")

    def _request_with_retry(
        self,
        method: str,
        path: str,
        json_payload: dict[str, Any] | None = None,
        auth: bool = True,
        endpoint: str = "unknown",
    ) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(1, self.retry_policy.max_attempts + 1):
            try:
                return self._request(method, path, json_payload=json_payload, auth=auth, endpoint=endpoint)
            except (requests.Timeout, requests.ConnectionError) as err:
                last_error = err
                self._log_event(
                    "exchange.retry",
                    {
                        "attempt": attempt,
                        "max_attempts": self.retry_policy.max_attempts,
                        "path": path,
                        "endpoint": endpoint,
                        "error": str(err),
                        "error_class": "network",
                    },
                )
                if attempt == self.retry_policy.max_attempts:
                    break
                time.sleep(self.retry_policy.backoff_base_seconds * (2 ** (attempt - 1)))

        return {
            "ok": False,
            "error": "request_failed",
            "path": path,
            "endpoint": endpoint,
            "error_class": "network",
            "details": str(last_error) if last_error else "unknown",
        }

    def _request(
        self,
        method: str,
        path: str,
        json_payload: dict[str, Any] | None = None,
        auth: bool = True,
        endpoint: str = "unknown",
    ) -> dict[str, Any]:
        url = f"{self.api_base}{path}"
        headers = {"Content-Type": "application/json"}

        if auth and self._authenticated():
            signed = self.signer.build_headers(method=method, request_path=f"/api/v3/brokerage{path}", body=json_payload)
            headers.update(signed)

        started = time.time()
        response = self.session.request(method=method, url=url, json=json_payload, headers=headers, timeout=self.timeout_seconds)
        latency_ms = int((time.time() - started) * 1000)

        try:
            payload: dict[str, Any] = response.json()
            error_class = self._classify_error(response.status_code, payload)
        except ValueError:
            payload = {"raw": response.text}
            error_class = "auth_error" if response.status_code in (401, 403) else "parse_error"

        data = {
            "ok": response.ok,
            "status_code": response.status_code,
            "path": path,
            "endpoint": endpoint,
            "latency_ms": latency_ms,
            "error_class": None if response.ok else error_class,
            "payload": payload,
        }
        self._log_event("exchange.response", data)
        return data

    def _log_event(self, event_type: str, payload: dict[str, Any]) -> None:
        deterministic_payload = json.loads(json.dumps(payload, sort_keys=True, default=str))
        logger.info(
            json.dumps(
                {
                    "event_type": event_type,
                    "timestamp": datetime.now(UTC).isoformat(),
                    "payload": deterministic_payload,
                },
                sort_keys=True,
            )
        )
        if self.db_writer is not None:
            self.db_writer.insert_execution_log(event_type=event_type, payload=deterministic_payload)

    def _authenticated(self) -> bool:
        return bool(self.secrets.get("COINBASE_API_KEY") and self.secrets.get("COINBASE_API_SECRET"))

    def _idempotency_key(self, *parts: Any) -> str:
        raw = "|".join(str(part) for part in parts) + f"|{uuid.uuid4()}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @staticmethod
    def _classify_error(status_code: int, payload: dict[str, Any]) -> str:
        if status_code in (401, 403):
            return "auth_error"
        if status_code == 429:
            return "rate_limit"
        message = json.dumps(payload).lower()
        if "unauthorized" in message or "forbidden" in message:
            return "auth_error"
        return "unknown"
