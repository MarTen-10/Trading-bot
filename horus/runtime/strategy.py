#!/usr/bin/env python3
import hashlib
from collections import defaultdict, deque

from horus.runtime.event_bus import MarketEvent


class StrategyEngine:
    def __init__(self):
        self.buffers = defaultdict(lambda: deque(maxlen=40))

    def generate(self, event: MarketEvent) -> dict | None:
        b = self.buffers[event.instrument]
        b.append(event)
        if len(b) < 25:
            return None

        highs = [x.high for x in list(b)[-24:-1]]
        hh = max(highs)
        # simple deterministic breakout trigger
        if event.close > hh:
            sig_key = f"{event.instrument}|{event.timeframe}|{event.timestamp.isoformat()}|{event.sequence_id}|long"
            signal_id = hashlib.sha256(sig_key.encode()).hexdigest()[:32]
            return {
                'signal_id': signal_id,
                'instrument': event.instrument,
                'ts': event.timestamp.isoformat(),
                'side': 'buy',
                'entry_px': event.close,
                'stop_px': event.close * 0.99,
                'target_r': 2.5,
                'event_sequence_id': event.sequence_id,
            }
        return None
