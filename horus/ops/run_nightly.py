#!/usr/bin/env python3
import json
import subprocess
from datetime import datetime, UTC
from pathlib import Path

BASE = Path('/home/marten/.openclaw/workspace/horus')


def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"cmd_failed: {' '.join(cmd)} :: {p.stderr.strip()[:400]}")
    return p.stdout.strip()


def freeze_universe():
    # placeholder deterministic top-5 snapshot until volume-ranker is wired
    symbols = ['BTCUSD', 'ETHUSD', 'SOLUSD', 'BNBUSD', 'XRPUSD']
    ts = datetime.now(UTC).strftime('%Y%m%d')
    out = BASE/'data'/'reports'/f'universe_{ts}.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({'date_utc': ts, 'symbols': symbols, 'source': 'frozen-default'}, indent=2))
    return out


def main():
    # 1) freeze universe at 00:00 UTC equivalent nightly snapshot
    uni = freeze_universe()

    # 2) refresh suite + selection
    run(['python3', str(BASE/'scripts/fetch_crypto_coinbase.py')])
    run(['python3', str(BASE/'scripts/run_crypto_paper_suite.py')])
    run(['python3', str(BASE/'scripts/select_strategies.py')])

    # 3) calibrated MC + gate on latest best known config
    best_bt = sorted(BASE.glob('data/backtests/btc_autotune_bt_run3_sma_cross_fix_*.json'))
    if best_bt:
        best_bt = best_bt[-1]
        run(['python3', str(BASE/'backtester/monte_carlo_calibrated.py'), '--backtest-report', str(best_bt), '--out', str(BASE/'data/reports/nightly_mc_latest.json'), '--equity', '1000', '--risk-pct', '0.01'])
        run(['python3', str(BASE/'backtester/gate_engine.py'), '--backtest-report', str(best_bt), '--mc-report', str(BASE/'data/reports/nightly_mc_latest.json'), '--out', str(BASE/'data/reports/nightly_gate_latest.json')])

    # 4) acceptance tests nightly
    run(['python3', str(BASE/'backtester/acceptance_tests.py')])

    print(json.dumps({'status': 'ok', 'universe_snapshot': str(uni), 'generated_at': datetime.now(UTC).isoformat()}))


if __name__ == '__main__':
    main()
