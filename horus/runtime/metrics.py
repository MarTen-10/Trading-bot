#!/usr/bin/env python3
import json
from dataclasses import dataclass, asdict
from pathlib import Path

STATE = Path('/home/marten/.openclaw/workspace/horus/data/reports/runtime_metrics_latest.json')

@dataclass
class RuntimeMetrics:
    signals_generated: int = 0
    signals_vetoed: int = 0
    orders_sent: int = 0
    fills: int = 0
    avg_latency_ms: float = 0.0
    _latency_samples: int = 0
    current_regime: str = 'UNKNOWN'
    current_drawdown_R: float = 0.0

    def add_latency(self, ms: float):
        self._latency_samples += 1
        if self._latency_samples == 1:
            self.avg_latency_ms = ms
        else:
            self.avg_latency_ms = ((self.avg_latency_ms * (self._latency_samples - 1)) + ms) / self._latency_samples

    def save(self):
        STATE.parent.mkdir(parents=True, exist_ok=True)
        STATE.write_text(json.dumps(asdict(self), indent=2))


def load() -> RuntimeMetrics:
    if not STATE.exists():
        return RuntimeMetrics()
    j = json.loads(STATE.read_text())
    return RuntimeMetrics(**j)
