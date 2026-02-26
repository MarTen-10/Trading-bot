#!/usr/bin/env python3
import csv
from datetime import datetime

from horus.core.engine import Engine
from horus.core.events import CandleEvent
from horus.runtime.strategy import StrategyEngine
from horus.runtime.risk_engine import RiskEngine
from horus.runtime import gate_adapter


class NullDB:
    def insert_governance(self, *args, **kwargs):
        return None


def run(csv_path: str):
    e = Engine(strategy=StrategyEngine(), risk=RiskEngine(), gate=gate_adapter, dbio=NullDB(), logger=lambda *a, **k: None)
    intents = []
    with open(csv_path, newline='') as f:
        rows = list(csv.DictReader(f))
    rows.sort(key=lambda r: (r.get('instrument', 'BTCUSD'), '5m', r['timestamp']))
    seq = 0
    for r in rows:
        seq += 1
        ev = CandleEvent(
            instrument=r.get('instrument', 'BTCUSD'),
            timeframe='5m',
            timestamp=datetime.fromisoformat(r['timestamp'].replace('Z', '+00:00')),
            open=float(r['open']), high=float(r['high']), low=float(r['low']), close=float(r['close']),
            volume=float(r.get('volume', 0) or 0),
            sequence_id=seq,
        )
        d = e.process_event(ev)
        intents.extend(d.intents)
    return intents


if __name__ == '__main__':
    import sys
    out = run(sys.argv[1])
    print(len(out))
