#!/usr/bin/env python3
import csv, time
from datetime import datetime
from pathlib import Path

from horus.runtime.event_bus import BUS, MarketEvent

RAW = Path('/home/marten/.openclaw/workspace/horus/data/raw/crypto')


class MarketStream:
    def __init__(self, universe):
        self.universe = universe
        self.last_ts = {}  # per symbol
        self.metrics = {
            'decision_latency_ms': 0.0,
            'feed_latency_ms': 0.0,
            'event_queue_depth': 0
        }

    def _load_rows(self, symbol):
        p = RAW / f'{symbol}_5m.csv'
        if not p.exists():
            return []
        rows = []
        with p.open(newline='') as f:
            r = csv.DictReader(f)
            for row in r:
                rows.append(row)
        return rows

    def poll(self):
        produced = 0
        t0 = time.time()
        for s in self.universe:
            rows = self._load_rows(s)
            if not rows:
                continue
            last = self.last_ts.get(s)
            new_rows = [x for x in rows if last is None or x['timestamp'] > last]
            if not new_rows:
                continue
            # emit all unseen rows in strict timestamp order
            for row in new_rows:
                ts = datetime.fromisoformat(row['timestamp'].replace('Z', '+00:00'))
                seq = BUS.next_sequence(s, '5m')
                ev = MarketEvent(
                    instrument=s,
                    timeframe='5m',
                    timestamp=ts,
                    open=float(row['open']),
                    high=float(row['high']),
                    low=float(row['low']),
                    close=float(row['close']),
                    volume=float(row.get('volume', 0) or 0),
                    sequence_id=seq,
                )
                BUS.emit(ev)
                self.last_ts[s] = row['timestamp']
                produced += 1

        dt_ms = (time.time() - t0) * 1000.0
        self.metrics['feed_latency_ms'] = round(dt_ms, 3)
        self.metrics['event_queue_depth'] = BUS.depth()
        return produced
