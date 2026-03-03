from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Side = Literal["buy", "sell"]
SignalType = Literal["long", "short", "flat"]


@dataclass
class Signal:
    kind: SignalType
    confidence: float
    reason: str


@dataclass
class PositionIntent:
    side: Side
    qty: float
    stop_loss: float
    take_profit: float
    leverage: float
    symbol: str


@dataclass
class TradingViewAlert:
    secret: str
    symbol: str
    side: Literal["buy", "sell", "flat"]
    timeframe: str = "5m"
    price: float | None = None
    strategy_id: str = "tv-default"
    exchange: str | None = None
    leverage: float | None = None
