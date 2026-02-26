#!/usr/bin/env python3
import json
from pathlib import Path

from horus.runtime import dbio

STATE = Path('/home/marten/.openclaw/workspace/horus/data/reports/runtime_state_latest.json')


def run_check() -> dict:
    # local state counts vs DB counts consistency check
    local = {'open_positions': 0}
    if STATE.exists():
        try:
            local = json.loads(STATE.read_text()).get('positions', local)
        except Exception:
            pass

    c = dbio.counts()
    mismatch = False
    reason = None

    # lightweight check: fills should not be less than trades if trades exist in this simplified runtime
    if c.get('trades', 0) > c.get('fills', 0):
        mismatch = True
        reason = 'trades_exceed_fills'

    return {
        'mismatch': mismatch,
        'reason': reason,
        'db_counts': c,
        'local_positions': local
    }
