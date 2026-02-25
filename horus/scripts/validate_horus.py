#!/usr/bin/env python3
import json
import subprocess
from pathlib import Path

BASE = Path('/home/marten/.openclaw/workspace/horus')

cmds = [
    ['python3', str(BASE/'scripts/generate_sample_data.py')],
    ['python3', str(BASE/'scripts/backtest_engine.py'), '--csv', str(BASE/'data/raw/sample_5m.csv'), '--strategy', str(BASE/'strategies/breakout_v1.json'), '--out', str(BASE/'data/backtests/sample_breakout_report.json')],
    ['python3', str(BASE/'scripts/paper_session.py')],
    ['python3', str(BASE/'scripts/report_daily.py')],
    ['python3', str(BASE/'scripts/learn_loop.py')],
]

for c in cmds:
    subprocess.run(c, check=True)

bt = json.loads((BASE/'data/backtests/sample_breakout_report.json').read_text())
assert 'summary' in bt and 'trades' in bt, 'Backtest report missing keys'
for k in ['trades','win_rate','expectancy_r','profit_factor','max_dd_r','stop_rate']:
    assert k in bt['summary'], f'Missing summary key: {k}'

assert (BASE/'data/journal/trade_ledger.jsonl').exists(), 'trade ledger missing'
assert (BASE/'data/journal/signal_ledger.jsonl').exists(), 'signal ledger missing'
assert (BASE/'data/journal/learning_state.json').exists(), 'learning state missing'
assert (BASE/'data/journal/lessons_latest.md').exists(), 'lessons markdown missing'

print('HORUS_VALIDATION_OK')
