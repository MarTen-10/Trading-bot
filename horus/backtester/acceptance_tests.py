#!/usr/bin/env python3
import json, subprocess, tempfile
from pathlib import Path

BASE = Path('/home/marten/.openclaw/workspace/horus')
BT = BASE/'backtester'/'universal_backtester.py'
MC = BASE/'backtester'/'monte_carlo_calibrated.py'
GE = BASE/'backtester'/'gate_engine.py'
CAL = BASE/'backtester'/'calibration_loop.py'
POL = BASE/'config'/'promotion_rollback_policy.json'
PARITY = BASE/'tests'/'replay_parity.py'


def run(cmd):
    return subprocess.run(cmd, check=True, capture_output=True, text=True)


def load(p):
    return json.loads(Path(p).read_text())


def test_deterministic(csv_path):
    with tempfile.TemporaryDirectory() as td:
        r1 = Path(td)/'r1.json'
        r2 = Path(td)/'r2.json'
        common = ['python3', str(BT), 'backtest', '--csv', csv_path, '--strategy', 'sma_cross',
                  '--params', '{"fast":30,"slow":80,"initial_equity":1000,"risk_pct":0.01,"target_r_mult":2.5,"stop_atr_mult":1.0}',
                  '--costs', '{"fee_bps":1.0,"slippage_bps":2.0}']
        run(common + ['--out', str(r1)])
        run(common + ['--out', str(r2)])
        j1, j2 = load(r1), load(r2)

        keys = ['trades','win_rate','expectancy_r','profit_factor','return_pct','max_drawdown_pct']
        for k in keys:
            if j1['summary'][k] != j2['summary'][k]:
                raise AssertionError(f'determinism_failed:{k}')


def test_risk_governor(csv_path):
    with tempfile.TemporaryDirectory() as td:
        out = Path(td)/'risk.json'
        run(['python3', str(BT), 'backtest', '--csv', csv_path, '--strategy', 'sma_cross',
             '--params', '{"fast":30,"slow":80,"initial_equity":1000,"risk_pct":0.01,"target_r_mult":2.5,"stop_atr_mult":1.0}',
             '--costs', '{"fee_bps":1.0,"slippage_bps":2.0}', '--out', str(out)])
        j = load(out)
        bad = []
        for t in j.get('trades', []):
            eq = t.get('entry_equity', 0)
            rd = t.get('risk_dollars', 0)
            if eq <= 0:
                continue
            if rd > eq * 0.0105:  # 1% risk + tolerance
                bad.append((rd, eq))
        if bad:
            raise AssertionError(f'risk_governor_failed:violations={len(bad)} sample={bad[0]}')


def test_calibration_loop():
    with tempfile.TemporaryDirectory() as td:
        out = Path(td)/'cal.json'
        fills = BASE/'tests'/'sample_fills.csv'
        run(['python3', str(CAL), '--fills-csv', str(fills), '--out-json', str(out)])
        j = load(out)
        if 'instrument_summary' not in j or 'BTCUSD' not in j['instrument_summary']:
            raise AssertionError('calibration_failed:missing_instrument_summary')
        if j['instrument_summary']['BTCUSD']['p75'] is None:
            raise AssertionError('calibration_failed:missing_percentiles')


def test_circuit_breaker_reconciliation_trigger():
    import importlib.util
    mod_path = BASE/'runtime'/'circuit_breakers.py'
    spec = importlib.util.spec_from_file_location('cb', mod_path)
    cb = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cb)

    snap = cb.RuntimeSnapshot(
        stale_seconds=0,
        latency_p95_ms=100,
        spread_bps=5,
        daily_median_spread_bps=5,
        spread_shock_minutes=0,
        reject_count_10m=0,
        fill_mismatch_polls=2,
        realized_r_day=0,
    )
    events = cb.evaluate(snap)
    if not any(e.get('trigger') == 'fill_mismatch' for e in events):
        raise AssertionError('circuit_breaker_failed:fill_mismatch_not_triggered')


def test_replay_parity():
    run(['python3', str(PARITY)])


def test_rollback_trigger(csv_path):
    with tempfile.TemporaryDirectory() as td:
        bt = Path(td)/'bt.json'
        mc = Path(td)/'mc.json'
        gate = Path(td)/'gate.json'

        # intentionally weak config to force reject/disable
        run(['python3', str(BT), 'backtest', '--csv', csv_path, '--strategy', 'mean_reversion_z',
             '--params', '{"lookback":20,"z_in":-1.2,"z_out":-0.1,"initial_equity":1000,"risk_pct":0.01,"target_r_mult":2.0,"stop_atr_mult":1.2}',
             '--costs', '{"fee_bps":1.0,"slippage_bps":2.0}', '--out', str(bt)])
        run(['python3', str(MC), '--backtest-report', str(bt), '--out', str(mc), '--equity', '1000', '--risk-pct', '0.01'])
        run(['python3', str(GE), '--backtest-report', str(bt), '--mc-report', str(mc), '--policy', str(POL), '--out', str(gate)])

        g = load(gate)
        if g.get('promotion_status') != 'REJECT':
            raise AssertionError('rollback_trigger_failed:promotion_not_reject')


def main():
    csv_files = sorted((BASE/'data'/'raw').glob('BTCUSD_15mo_1h_*.csv'))
    if not csv_files:
        raise SystemExit('No BTC 15mo CSV found for acceptance tests.')
    csv_path = str(csv_files[-1])

    test_deterministic(csv_path)
    test_risk_governor(csv_path)
    test_calibration_loop()
    test_circuit_breaker_reconciliation_trigger()
    test_replay_parity()
    test_rollback_trigger(csv_path)
    print('ACCEPTANCE_OK')


if __name__ == '__main__':
    main()
