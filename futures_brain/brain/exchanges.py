from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
from .models import PositionIntent


class ExchangeAdapter:
    name = "base"

    def get_mark_price(self, symbol: str) -> float:
        raise NotImplementedError

    def place_order(self, intent: PositionIntent, mode: str) -> dict:
        raise NotImplementedError


class BybitAdapter(ExchangeAdapter):
    name = "bybit"

    def get_mark_price(self, symbol: str) -> float:
        # TODO: replace with real Bybit ticker call
        return 50000.0

    def place_order(self, intent: PositionIntent, mode: str) -> dict:
        # TODO: replace with real signed order call
        return {
            "exchange": self.name,
            "mode": mode,
            "status": "simulated" if mode != "live" else "queued",
            "intent": asdict(intent),
        }


class OkxAdapter(ExchangeAdapter):
    name = "okx"

    def get_mark_price(self, symbol: str) -> float:
        # TODO: replace with real OKX ticker call
        return 50000.0

    def place_order(self, intent: PositionIntent, mode: str) -> dict:
        # TODO: replace with real signed order call
        return {
            "exchange": self.name,
            "mode": mode,
            "status": "simulated" if mode != "live" else "queued",
            "intent": asdict(intent),
        }


def journal(event: dict, path: str = "data/journal.jsonl") -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    event["ts"] = datetime.now(timezone.utc).isoformat()
    with p.open("a") as f:
        f.write(json.dumps(event) + "\n")


def get_exchange(name: str) -> ExchangeAdapter:
    key = name.lower().strip()
    if key == "bybit":
        return BybitAdapter()
    if key == "okx":
        return OkxAdapter()
    raise ValueError(f"Unsupported exchange: {name}")
