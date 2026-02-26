#!/usr/bin/env python3
import os
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
    stale_s = int(os.getenv('HORUS_DATA_STALE_SECONDS', '3'))
    latency_ms = int(os.getenv('HORUS_LATENCY_THRESHOLD_MS', '1000'))
    spread_mult = float(os.getenv('HORUS_SPREAD_SHOCK_MULTIPLIER', '2'))
    spread_min = int(os.getenv('HORUS_SPREAD_SHOCK_MINUTES', '3'))
    reject_n = int(os.getenv('HORUS_BREAKER_REJECT_COUNT_10M', '5'))
    mismatch_n = int(os.getenv('HORUS_BREAKER_FILL_MISMATCH_POLLS', '2'))
    daily_loss = float(os.getenv('HORUS_BREAKER_DAILY_LOSS_R', '-3'))

    if snapshot.stale_seconds > stale_s:
        events.append({'trigger': 'data_stale', 'threshold': f'>{stale_s}s', 'action': 'SAFE_BLOCK_NEW_ENTRIES'})

    if snapshot.latency_p95_ms > latency_ms:
        events.append({'trigger': 'latency_spike', 'threshold': f'p95>{latency_ms}ms(5m)', 'action': 'SAFE_AND_ALERT'})

    if snapshot.daily_median_spread_bps > 0 and snapshot.spread_bps > spread_mult * snapshot.daily_median_spread_bps and snapshot.spread_shock_minutes >= spread_min:
        events.append({'trigger': 'spread_shock', 'threshold': f'spread>{spread_mult}x median for >={spread_min}m', 'action': 'VETO_ENTRIES_CANCEL_RESTING'})

    if snapshot.reject_count_10m >= reject_n:
        events.append({'trigger': 'reject_streak', 'threshold': f'>={reject_n} rejects in 10m', 'action': 'SAFE_STOP_SENDING'})

    if snapshot.fill_mismatch_polls >= mismatch_n:
        events.append({'trigger': 'fill_mismatch', 'threshold': f'mismatch >={mismatch_n} polls', 'action': 'SAFE_RECONCILE_OPTIONAL_FLATTEN'})

    if snapshot.realized_r_day <= daily_loss:
        events.append({'trigger': 'daily_loss_cap', 'threshold': f'realized_R_day<={daily_loss}', 'action': 'STOP_UNTIL_NEXT_UTC_DAY'})

    return events
