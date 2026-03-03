from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .config import load_config
from .exchanges import journal
from .models import TradingViewAlert
from .runner import run_from_tv_alert


DEDUPE_CACHE = Path("data/dedupe_cache.json")


def _load_dedupe() -> dict[str, float]:
    if not DEDUPE_CACHE.exists():
        return {}
    try:
        return json.loads(DEDUPE_CACHE.read_text())
    except Exception:
        return {}


def _save_dedupe(cache: dict[str, float]) -> None:
    DEDUPE_CACHE.parent.mkdir(parents=True, exist_ok=True)
    DEDUPE_CACHE.write_text(json.dumps(cache))


def _dedupe_key(payload: dict[str, Any]) -> str:
    base = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(base.encode()).hexdigest()


class TradingViewWebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/webhook/tradingview":
            self._send(404, {"error": "not found"})
            return

        cfg = load_config()
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length) if length > 0 else b"{}"

        try:
            payload = json.loads(body.decode("utf-8"))
        except Exception:
            self._send(400, {"error": "invalid json"})
            return

        header_secret = self.headers.get("X-Webhook-Secret", "")
        payload_secret = str(payload.get("secret", ""))
        expected = cfg.webhook.secret

        if not expected:
            self._send(500, {"error": "webhook secret not configured"})
            return

        if header_secret != expected and payload_secret != expected:
            self._send(401, {"error": "unauthorized"})
            return

        dedupe = _load_dedupe()
        now = time.time()
        key = _dedupe_key(payload)
        ttl = cfg.webhook.dedupe_window_sec

        # cleanup expired
        dedupe = {k: v for k, v in dedupe.items() if v > now}
        if key in dedupe:
            out = {"status": "ignored", "reason": "duplicate signal"}
            journal({"event": "tv_duplicate", "payload": payload, **out})
            self._send(200, out)
            return
        dedupe[key] = now + ttl
        _save_dedupe(dedupe)

        try:
            alert = TradingViewAlert(
                secret=payload_secret or header_secret,
                symbol=str(payload["symbol"]),
                side=str(payload["side"]).lower(),
                timeframe=str(payload.get("timeframe", "5m")),
                price=float(payload["price"]) if payload.get("price") is not None else None,
                strategy_id=str(payload.get("strategy_id", "tv-default")),
                exchange=str(payload.get("exchange")) if payload.get("exchange") else None,
                leverage=float(payload["leverage"]) if payload.get("leverage") is not None else None,
            )
        except Exception as exc:
            self._send(400, {"error": f"invalid payload: {exc}"})
            return

        result = run_from_tv_alert(alert)
        journal({"event": "tv_received", "alert": asdict(alert), "result": result})
        self._send(200, result)

    def log_message(self, fmt: str, *args: Any) -> None:
        return

    def _send(self, code: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run_server() -> None:
    cfg = load_config()
    server = ThreadingHTTPServer((cfg.webhook.host, cfg.webhook.port), TradingViewWebhookHandler)
    print(f"TradingView webhook listening on http://{cfg.webhook.host}:{cfg.webhook.port}/webhook/tradingview")
    server.serve_forever()
