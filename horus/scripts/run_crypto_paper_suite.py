#!/usr/bin/env python3
import json, subprocess
from pathlib import Path
from datetime import datetime, UTC

BASE = Path('/home/marten/.openclaw/workspace/horus')
coins = ['BTCUSD','ETHUSD','SOLUSD']
strategies = {
    'breakout_v1': BASE/'strategies/breakout_v1.json',
    'mean_reversion_v1': BASE/'strategies/mean_reversion_v1.json',
    'breakout_crypto_v1': BASE/'strategies/breakout_crypto_v1.json',
    'mean_reversion_crypto_v1': BASE/'strategies/mean_reversion_crypto_v1.json',
}
results = []

for c in coins:
    csv_path = BASE/f'data/raw/crypto/{c}_5m.csv'
    for sname, spath in strategies.items():
        out = BASE/f'data/backtests/{c}_{sname}.json'
        cmd = [
            'python3', str(BASE/'scripts/backtest_engine.py'),
            '--csv', str(csv_path),
            '--strategy', str(spath),
            '--out', str(out),
            '--fee-bps', '1.5',
            '--slippage-bps', '3.0'
        ]
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        rep = json.loads(out.read_text())
        results.append({'coin': c, 'strategy': sname, **rep['summary']})

# walkforward breakout variants
for c in coins:
    for strat in ['breakout_v1', 'breakout_crypto_v1']:
        out = BASE/f'data/backtests/{c}_walkforward_{strat}.json'
        cmd = [
            'python3', str(BASE/'scripts/walkforward.py'),
            '--csv', str(BASE/f'data/raw/crypto/{c}_5m.csv'),
            '--strategy', str(BASE/f'strategies/{strat}.json'),
            '--out', str(out),
            '--folds', '4',
            '--fee-bps', '1.5',
            '--slippage-bps', '3.0'
        ]
        subprocess.run(cmd, check=True, capture_output=True, text=True)

summary = {
    'generated_at': datetime.now(UTC).isoformat(),
    'cost_model': {'fee_bps': 1.5, 'slippage_bps': 3.0},
    'results': results,
}

for r in summary['results']:
    r['status'] = 'pass' if (r['profit_factor'] >= 1.15 and r['expectancy_r'] > 0 and r['max_dd_r'] > -3.0 and r['trades'] >= 3) else 'fail'

out_json = BASE/f"data/reports/crypto_suite_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.json"
out_json.write_text(json.dumps(summary, indent=2))

lines = ['# Horus Crypto Paper Suite', '', f"Generated: {summary['generated_at']}", '', '## Results']
for r in summary['results']:
    lines.append(f"- {r['coin']} | {r['strategy']} | PF {r['profit_factor']} | ExpR {r['expectancy_r']} | MaxDD {r['max_dd_r']} | Trades {r['trades']} | {r['status'].upper()}")

lines += ['', '## What is working']
works = [x for x in summary['results'] if x['status']=='pass']
for r in works:
    lines.append(f"- {r['coin']} {r['strategy']} passes current gate.")
if not works:
    lines.append('- None pass strict gate yet.')

lines += ['', '## What is not working']
for r in [x for x in summary['results'] if x['status']=='fail']:
    reasons=[]
    if r['profit_factor'] < 1.15: reasons.append('weak PF')
    if r['expectancy_r'] <= 0: reasons.append('non-positive expectancy')
    if r['max_dd_r'] <= -3.0: reasons.append('drawdown too high')
    if r['trades'] < 3: reasons.append('insufficient trades')
    lines.append(f"- {r['coin']} {r['strategy']}: {', '.join(reasons)}")

lines += ['', '## Immediate system issues found']
for c in coins:
    strict = [x for x in summary['results'] if x['coin']==c and x['strategy'] in ('breakout_v1','mean_reversion_v1')]
    if all(x['trades']==0 for x in strict):
        lines.append(f"- {c}: strict templates produce zero trades on sampled Coinbase window (over-filtered for this market window).")

out_md = BASE/'data/reports/crypto_suite_latest.md'
out_md.write_text('\n'.join(lines)+'\n')
print(str(out_json))
print(str(out_md))
