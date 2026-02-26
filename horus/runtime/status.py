#!/usr/bin/env python3
import json
from pathlib import Path

from horus.runtime import dbio

BASE = Path('/home/marten/.openclaw/workspace/horus')
RUNTIME = BASE/'data/reports/runtime_state_latest.json'
METRICS = BASE/'data/reports/runtime_metrics_latest.json'
GATE = BASE/'data/reports/runtime_gate_latest.json'


def main():
    state = json.loads(RUNTIME.read_text()) if RUNTIME.exists() else {}
    metrics = json.loads(METRICS.read_text()) if METRICS.exists() else {}
    gate = json.loads(GATE.read_text()) if GATE.exists() else {}
    counts = dbio.counts()

    print('SAFE mode:', state.get('safe_mode', False))
    print('active model id:', state.get('active_model_id', 'rule_based_v2'))
    print('disable flags:', state.get('disable_flags', {}))
    print("today's realized R:", state.get('realized_r_day', 0.0))
    print('open positions:', state.get('positions', {}).get('open_positions', 0))
    print('current regime:', metrics.get('current_regime', 'UNKNOWN'))
    print('counts:', counts)
    if gate:
        print('gate promotion_status:', gate.get('promotion_status'))
        print('gate disable_status:', gate.get('disable_status'))


if __name__ == '__main__':
    main()
