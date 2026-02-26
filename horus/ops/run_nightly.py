#!/usr/bin/env python3
import csv
import json
import hashlib
import os
import subprocess
from datetime import datetime, UTC
from pathlib import Path

from horus.runtime import dbio

BASE = Path('/home/marten/.openclaw/workspace/horus')


def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"cmd_failed: {' '.join(cmd)} :: {p.stderr.strip()[:400]}")
    return p.stdout.strip()


def freeze_universe_top5():
    crypto_dir = BASE / 'data' / 'raw' / 'crypto'
    totals = []
    for p in sorted(crypto_dir.glob('*_5m.csv')):
        symbol = p.name.replace('_5m.csv', '')
        rows = []
        with p.open(newline='') as f:
            r = csv.DictReader(f)
            rows = list(r)
        if not rows:
            continue
        last = rows[-288:]  # previous 24h for 5m bars
        vol_sum = sum(float(x.get('volume', 0) or 0) for x in last)
        totals.append((symbol, vol_sum))

    totals.sort(key=lambda x: x[1], reverse=True)
    symbols = [s for s, _ in totals[:5]]
    if not symbols:
        symbols = ['BTCUSD', 'ETHUSD', 'SOLUSD', 'BNBUSD', 'XRPUSD']

    ts = datetime.now(UTC).strftime('%Y%m%d')
    out = BASE / 'data' / 'reports' / f'universe_{ts}.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {'date_utc': ts, 'symbols': symbols, 'source': 'volume_top5_24h', 'ranked': totals[:10]}
    out.write_text(json.dumps(payload, indent=2))

    dbio.insert_governance('UNIVERSE_FREEZE', None, None, 'SNAPSHOT', 'nightly_top5_by_volume', json.dumps(payload))
    return out


def main():
    run(['python3', str(BASE/'scripts/fetch_crypto_coinbase.py')])
    uni = freeze_universe_top5()

    run(['python3', str(BASE/'scripts/run_crypto_paper_suite.py')])
    run(['python3', str(BASE/'scripts/select_strategies.py')])

    best_bt = sorted(BASE.glob('data/backtests/btc_autotune_bt_run3_sma_cross_fix_*.json'))
    if best_bt:
        best_bt = best_bt[-1]
        seed = os.getenv('CALIBRATION_SEED', '7')
        mc_out = BASE/'data/reports/nightly_mc_latest.json'
        run(['python3', str(BASE/'backtester/monte_carlo_calibrated.py'), '--backtest-report', str(best_bt), '--out', str(mc_out), '--equity', '1000', '--risk-pct', '0.01'])
        mc_hash = hashlib.sha256(mc_out.read_bytes()).hexdigest()
        dbio.insert_governance('CALIBRATION_ARTIFACT', None, None, 'SNAPSHOT', 'mc_hash', {'seed': seed, 'path': str(mc_out), 'sha256': mc_hash})
        run(['python3', str(BASE/'backtester/gate_engine.py'), '--backtest-report', str(best_bt), '--mc-report', str(mc_out), '--out', str(BASE/'data/reports/nightly_gate_latest.json')])

    run(['python3', str(BASE/'backtester/acceptance_tests.py')])

    print(json.dumps({'status': 'ok', 'universe_snapshot': str(uni), 'generated_at': datetime.now(UTC).isoformat()}))


if __name__ == '__main__':
    main()
