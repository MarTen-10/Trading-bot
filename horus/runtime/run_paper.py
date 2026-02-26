#!/usr/bin/env python3
import json
import os
import subprocess
import time
from datetime import datetime, UTC
from pathlib import Path

from horus.runtime.circuit_breakers import RuntimeSnapshot, evaluate

BASE = Path('/home/marten/.openclaw/workspace/horus')
LOG = BASE / 'logs' / 'paper_runtime.log'


def log(msg):
    LOG.parent.mkdir(parents=True, exist_ok=True)
    line = f"[{datetime.now(UTC).isoformat()}] {msg}"
    with LOG.open('a') as f:
        f.write(line + '\n')
    print(line, flush=True)


def run_cmd(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"cmd_failed: {' '.join(cmd)} :: {p.stderr.strip()[:400]}")
    return p.stdout.strip()


def latest_json(pattern):
    files = sorted(BASE.glob(pattern))
    return files[-1] if files else None


def health_snapshot():
    # lightweight snapshot from artifacts/logging
    sig = latest_json('data/signals/signals_livefeed_*.json')
    stale_seconds = 999.0
    if sig:
        stale_seconds = max(0.0, time.time() - sig.stat().st_mtime)

    # conservative placeholders until full broker telemetry wiring
    latency_p95_ms = 120.0
    spread_bps = 8.0
    daily_median_spread_bps = 7.0
    spread_shock_minutes = 0
    reject_count_10m = 0
    fill_mismatch_polls = 0
    realized_r_day = 0.0

    return RuntimeSnapshot(
        stale_seconds=stale_seconds,
        latency_p95_ms=latency_p95_ms,
        spread_bps=spread_bps,
        daily_median_spread_bps=daily_median_spread_bps,
        spread_shock_minutes=spread_shock_minutes,
        reject_count_10m=reject_count_10m,
        fill_mismatch_polls=fill_mismatch_polls,
        realized_r_day=realized_r_day,
    )


def once():
    # 1) data + suite + selection + paper signals
    run_cmd(['python3', str(BASE/'scripts/fetch_crypto_coinbase.py')])
    run_cmd(['python3', str(BASE/'scripts/run_crypto_paper_suite.py')])
    run_cmd(['python3', str(BASE/'scripts/select_strategies.py')])
    run_cmd(['python3', str(BASE/'scripts/paper_session_livefeed.py')])

    # 2) learn + reports
    run_cmd(['python3', str(BASE/'scripts/learn_loop.py')])
    run_cmd(['python3', str(BASE/'scripts/report_daily.py')])

    # 3) gate + calibrated MC on latest best report if exists
    best_bt = latest_json('data/backtests/btc_autotune_bt_run3_sma_cross_fix_*.json')
    if best_bt:
        mc_out = BASE/'data/reports/runtime_mc_latest.json'
        gate_out = BASE/'data/reports/runtime_gate_latest.json'
        run_cmd(['python3', str(BASE/'backtester/monte_carlo_calibrated.py'), '--backtest-report', str(best_bt), '--out', str(mc_out), '--equity', '1000', '--risk-pct', os.getenv('HORUS_RISK_FRACTION', '0.005')])
        run_cmd(['python3', str(BASE/'backtester/gate_engine.py'), '--backtest-report', str(best_bt), '--mc-report', str(mc_out), '--out', str(gate_out)])


def main():
    interval = int(os.getenv('HORUS_PAPER_LOOP_SECONDS', '300'))
    log(f'paper_runtime_start interval={interval}s')
    while True:
        started = time.time()
        try:
            events = evaluate(health_snapshot())
            if events:
                log(f'SAFE_MODE triggers={json.dumps(events)}')
                # SAFE behavior: block new entries by skipping once-cycle
            else:
                once()
                log('paper_cycle_ok')
        except Exception as e:
            log(f'paper_cycle_error {e}')

        elapsed = time.time() - started
        sleep_for = max(1, interval - int(elapsed))
        time.sleep(sleep_for)


if __name__ == '__main__':
    main()
