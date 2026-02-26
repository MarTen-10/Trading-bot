#!/usr/bin/env python3
from dataclasses import dataclass
from datetime import datetime
from collections import defaultdict, deque
from typing import Deque, Dict, Tuple


@dataclass(frozen=True)
class MarketEvent:
    instrument: str
    timeframe: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    sequence_id: int


class EventBus:
    def __init__(self):
        self._q: Deque[MarketEvent] = deque()
        self._seq: Dict[Tuple[str, str], int] = defaultdict(int)

    def next_sequence(self, instrument: str, timeframe: str) -> int:
        key = (instrument, timeframe)
        self._seq[key] += 1
        return self._seq[key]

    def emit(self, event: MarketEvent) -> None:
        self._q.append(event)

    def next(self) -> MarketEvent | None:
        return self._q.popleft() if self._q else None

    def depth(self) -> int:
        return len(self._q)


BUS = EventBus()


def emit(event: MarketEvent) -> None:
    BUS.emit(event)
