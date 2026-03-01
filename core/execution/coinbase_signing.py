from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Any

from core.secrets.provider import SecretsProvider


@dataclass
class CoinbaseSigner:
    """Coinbase request signer (HMAC variant).

    prehash = timestamp + method + request_path + body
    signature = base64(hmac_sha256(base64_decode(secret), prehash))
    """

    secrets: SecretsProvider

    def build_headers(
        self,
        *,
        method: str,
        request_path: str,
        body: dict[str, Any] | None = None,
        timestamp: str | None = None,
    ) -> dict[str, str]:
        api_key = self.secrets.get("COINBASE_API_KEY")
        api_secret = self.secrets.get("COINBASE_API_SECRET")
        passphrase = self.secrets.get("COINBASE_API_PASSPHRASE")
        if not api_key or not api_secret:
            return {}

        ts = timestamp or str(int(time.time()))
        body_text = self.canonical_body(body)
        prehash = f"{ts}{method.upper()}{request_path}{body_text}"
        signature = self.sign(api_secret, prehash)

        headers = {
            "CB-ACCESS-KEY": api_key,
            "CB-ACCESS-SIGN": signature,
            "CB-ACCESS-TIMESTAMP": ts,
            "Content-Type": "application/json",
        }
        if passphrase:
            headers["CB-ACCESS-PASSPHRASE"] = passphrase
        return headers

    @staticmethod
    def canonical_body(body: dict[str, Any] | None) -> str:
        if not body:
            return ""
        return json.dumps(body, separators=(",", ":"), sort_keys=True)

    @staticmethod
    def sign(api_secret_b64: str, prehash: str) -> str:
        secret = base64.b64decode(api_secret_b64)
        digest = hmac.new(secret, prehash.encode("utf-8"), hashlib.sha256).digest()
        return base64.b64encode(digest).decode("utf-8")
