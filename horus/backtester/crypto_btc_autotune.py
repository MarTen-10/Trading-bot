#!/usr/bin/env python3
import json
import subprocess
from datetime import datetime, UTC
from pathlib import Path

BASE = Path('/home/marten/.openclaw/workspace/horus')
BT = BASE / 'backtester' / 'universal_backtester.py'
FMT = BASE / 'backtester' / 'format_report.py'
OUT = BASE / 'data' / 'reports'
RAW = BASE / 'data' / 'raw'
BACKTESTS = BASE / 'data' / 'backtests'

RAW.mkdir(parents=True, exist_ok=True)
OUT.mkdir(parents=True, exist_ok=True)
BACKTESTS.mkdir(parents=True, exist_ok=True)

run_ts = datetime.now(UTC).strftime('%Y%m%d_%H%M%S')
csv_path = RAW / f'BTCUSD_15mo_1h_{run_ts}.csv'

# Fetch 15 months of BTC data (tries Yahoo 1h)
subprocess.run([
    'python3', str(BT), 'fetch',
    '--ticker', 'BTC-USD',
    '--interval', '1h',
    '--range', '15mo',
    '--out', str(csv_path)
], check=True)

criteria = {
    'return_pct_min': 0.0,
    'expectancy_r_min': 0.0,
    'profit_factor_min': 1.1,
    'trades_min': 8
}

runs = []
best_final = None

# Each phase = issue-driven automatic fix plan
phases = [
    {
        'name': 'run1_breakout_baseline',
        'strategy': 'breakout',
        'params': {
            'initial_equity': 1000,
            'risk_pct': 0.01,
            'target_r_mult': 2.0,
            'stop_atr_mult': 1.0,
            'lookback': 24,
            'exit_lookback': 12
        },
        'grid': {
            'lookback': [12, 18, 24, 36],
            'exit_lookback': [6, 12, 18],
            'stop_atr_mult': [0.8, 1.0, 1.2],
            'target_r_mult': [2.0, 2.5, 3.0]
        },
        'fix_note': 'If weak/negative edge, widen breakout sensitivity and tune ATR stop/target.'
    },
    {
        'name': 'run2_rsi_reversion_fix',
        'strategy': 'rsi_reversion',
        'params': {
            'initial_equity': 1000,
            'risk_pct': 0.01,
            'target_r_mult': 2.0,
            'stop_atr_mult': 0.9,
            'rsi_n': 14,
            'buy_below': 28,
            'sell_above': 60
        },
        'grid': {
            'rsi_n': [7, 10, 14],
            'buy_below': [20, 25, 30],
            'sell_above': [55, 60, 65],
            'stop_atr_mult': [0.7, 0.9, 1.1],
            'target_r_mult': [2.0, 2.5, 3.0]
        },
        'fix_note': 'Switch strategy family to mean-reversion RSI when breakout underperforms.'
    },
    {
        'name': 'run3_sma_cross_fix',
        'strategy': 'sma_cross',
        'params': {
            'initial_equity': 1000,
            'risk_pct': 0.01,
            'target_r_mult': 2.0,
            'stop_atr_mult': 1.2,
            'fast': 20,
            'slow': 80
        },
        'grid': {
            'fast': [8, 12, 20, 30],
            'slow': [40, 60, 80, 120],
            'stop_atr_mult': [1.0, 1.2, 1.5],
            'target_r_mult': [2.0, 2.5, 3.0]
        },
        'fix_note': 'Switch to trend-following crossover when reversion/breakout quality is poor.'
    }
]


def passes(summary):
    pf = summary.get('profit_factor')
    return (
        summary.get('return_pct', -999) > criteria['return_pct_min'] and
        summary.get('expectancy_r', -999) > criteria['expectancy_r_min'] and
        (pf is not None and pf >= criteria['profit_factor_min']) and
        summary.get('trades', 0) >= criteria['trades_min']
    )

for i, ph in enumerate(phases, 1):
    opt_out = BACKTESTS / f"btc_autotune_opt_{ph['name']}_{run_ts}.json"
    bt_out = BACKTESTS / f"btc_autotune_bt_{ph['name']}_{run_ts}.json"
    diag_out = OUT / f"btc_autotune_diag_{ph['name']}_{run_ts}.md"

    # optimize
    subprocess.run([
        'python3', str(BT), 'optimize',
        '--csv', str(csv_path),
        '--strategy', ph['strategy'],
        '--params', json.dumps(ph['params']),
        '--grid', json.dumps(ph['grid']),
        '--costs', json.dumps({'fee_bps': 1.0, 'slippage_bps': 2.0}),
        '--out', str(opt_out)
    ], check=True)

    opt = json.loads(opt_out.read_text())
    top = (opt.get('results') or [{}])[0]

    chosen = dict(ph['params'])
    for k in ph['grid'].keys():
        if k in top:
            chosen[k] = top[k]
    if chosen.get('target_r_mult', 2.0) < 2.0:
        chosen['target_r_mult'] = 2.0

    # backtest chosen
    subprocess.run([
        'python3', str(BT), 'backtest',
        '--csv', str(csv_path),
        '--strategy', ph['strategy'],
        '--params', json.dumps(chosen),
        '--costs', json.dumps({'fee_bps': 1.0, 'slippage_bps': 2.0}),
        '--out', str(bt_out)
    ], check=True)

    # diagnostic formatting
    subprocess.run([
        'python3', str(FMT),
        '--report', str(bt_out),
        '--out-md', str(diag_out)
    ], check=True)

    rep = json.loads(bt_out.read_text())
    summary = rep.get('summary', {})
    ok = passes(summary)

    run_info = {
        'run': i,
        'name': ph['name'],
        'strategy': ph['strategy'],
        'fix_applied': ph['fix_note'] if i > 1 else 'baseline run',
        'params_used': chosen,
        'summary': summary,
        'diagnostic_md': str(diag_out),
        'status': 'PASS' if ok else 'FAIL'
    }
    runs.append(run_info)

    if best_final is None or summary.get('expectancy_r', -999) > best_final['summary'].get('expectancy_r', -999):
        best_final = run_info

    if ok:
        break

master = {
    'generated_at': datetime.now(UTC).isoformat(),
    'ticker': 'BTC-USD',
    'data_csv': str(csv_path),
    'objective': {
        'initial_equity': 1000,
        'risk_pct_per_trade': 0.01,
        'target_r_mult_min': 2.0
    },
    'pass_criteria': criteria,
    'runs': runs,
    'best_run': best_final
}

master_json = OUT / f'btc_autotune_master_{run_ts}.json'
master_md = OUT / 'btc_autotune_latest.md'
master_json.write_text(json.dumps(master, indent=2))

lines = [
    '# BTC Autotune Backtest Master Report',
    '',
    f"Generated: {master['generated_at']}",
    f"Data: `{csv_path.name}`",
    '',
    '## Objective',
    '- Starting equity: $1,000',
    '- Risk per trade: 1%',
    '- Target reward/risk: >= 2.0',
    '',
    '## Run-by-run status'
]
for r in runs:
    s = r['summary']
    lines.append(f"- Run {r['run']} | {r['strategy']} | {r['status']} | Trades {s.get('trades')} | ExpR {s.get('expectancy_r')} | PF {s.get('profit_factor')} | Return% {s.get('return_pct')}")
    lines.append(f"  - Fix applied: {r['fix_applied']}")

lines += ['', '## Best run', f"- Strategy: {best_final['strategy']}", f"- Params: `{json.dumps(best_final['params_used'])}`"]
bs = best_final['summary']
lines += [
    f"- Trades: {bs.get('trades')}",
    f"- Win rate: {bs.get('win_rate')}",
    f"- Expectancy (R): {bs.get('expectancy_r')}",
    f"- Profit factor: {bs.get('profit_factor')}",
    f"- Return %: {bs.get('return_pct')}",
    f"- Net PnL: {bs.get('net_pnl')}",
    f"- Max DD %: {bs.get('max_drawdown_pct')}",
    f"- Diagnostic: `{best_final['diagnostic_md']}`"
]

if any(r['status'] == 'PASS' for r in runs):
    lines += ['', '## Verdict', '- ✅ Pass criteria met for at least one run. Ready for joint first run review.']
else:
    lines += ['', '## Verdict', '- ⚠️ No run met full pass gate yet. Additional strategy modules/tuning required before first joint run.']

master_md.write_text('\n'.join(lines) + '\n')
print(str(master_json))
print(str(master_md))
