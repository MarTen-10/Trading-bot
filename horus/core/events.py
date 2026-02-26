from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class CandleEvent:
    instrument: str
    timeframe: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    sequence_id: int


@dataclass(frozen=True)
class OrderIntent:
    intent_id: str
    signal_id: str
    instrument: str
    side: str
    entry_px: float
    stop_px: float
    qty: float
    risk_dollars: float
    event_ts: str


@dataclass
class EngineDecision:
    signal: dict[str, Any] | None
    intents: list[OrderIntent]
    veto_reason: str | None = None

    def as_dict(self):
        return {
            'signal': self.signal,
            'intents': [asdict(i) for i in self.intents],
            'veto_reason': self.veto_reason,
        }
