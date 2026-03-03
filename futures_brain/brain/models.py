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
