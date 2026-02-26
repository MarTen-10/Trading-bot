#!/usr/bin/env python3
from dataclasses import dataclass
from typing import Dict, Any, List


@dataclass
class RuntimeSnapshot:
    stale_seconds: float
    latency_p95_ms: float
    spread_bps: float
    daily_median_spread_bps: float
    spread_shock_minutes: int
    reject_count_10m: int
    fill_mismatch_polls: int
    realized_r_day: float


def evaluate(snapshot: RuntimeSnapshot) -> List[Dict[str, Any]]:
    events = []

    if snapshot.stale_seconds > 3:
        events.append({
            'trigger': 'data_stale',
            'threshold': '>3s',
            'action': 'SAFE_BLOCK_NEW_ENTRIES'
        })

    if snapshot.latency_p95_ms > 1000:
        events.append({
            'trigger': 'latency_spike',
            'threshold': 'p95>1000ms(5m)',
            'action': 'SAFE_AND_ALERT'
        })

    if snapshot.daily_median_spread_bps > 0 and snapshot.spread_bps > 2 * snapshot.daily_median_spread_bps and snapshot.spread_shock_minutes >= 3:
        events.append({
            'trigger': 'spread_shock',
            'threshold': 'spread>2x median for >=3m',
            'action': 'VETO_ENTRIES_CANCEL_RESTING'
        })

    if snapshot.reject_count_10m >= 5:
        events.append({
            'trigger': 'reject_streak',
            'threshold': '>=5 rejects in 10m',
            'action': 'SAFE_STOP_SENDING'
        })

    if snapshot.fill_mismatch_polls >= 2:
        events.append({
            'trigger': 'fill_mismatch',
            'threshold': 'mismatch >=2 polls',
            'action': 'SAFE_RECONCILE_OPTIONAL_FLATTEN'
        })

    if snapshot.realized_r_day <= -3:
        events.append({
            'trigger': 'daily_loss_cap',
            'threshold': 'realized_R_day<=-3',
            'action': 'STOP_UNTIL_NEXT_UTC_DAY'
        })

    return events


if __name__ == '__main__':
    # smoke example
    snap = RuntimeSnapshot(4, 1200, 25, 8, 5, 0, 0, -1)
    print(evaluate(snap))
