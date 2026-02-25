#!/usr/bin/env python3
import json
from pathlib import Path
from datetime import datetime, UTC

BASE = Path('/home/marten/.openclaw/workspace/horus')
reg_path = BASE/'config/strategy_registry.json'
report = BASE/'data/reports/crypto_suite_latest.md'
json_reports = sorted((BASE/'data/reports').glob('crypto_suite_*.json'))
if not json_reports:
    raise SystemExit('No crypto suite report found')
latest = json.loads(json_reports[-1].read_text())

reg = json.loads(reg_path.read_text())
g = reg['promotion_gate']
coins = reg['coins']

# reset allowed lists
for c in coins.values():
    c['allowed'] = []

for r in latest['results']:
    coin = r['coin']
    strat = r['strategy']
    if coin not in coins or not coins[coin]['enabled']:
        continue
    ok = (
        r.get('profit_factor',0) >= g['min_profit_factor'] and
        r.get('expectancy_r',0) > g['min_expectancy_r'] and
        r.get('max_dd_r',0) > g['max_drawdown_r'] and
        r.get('trades',0) >= g['min_trades']
    )
    if ok:
        coins[coin]['allowed'].append(strat)

# if none allowed for a coin keep empty (no-trade mode)
out = {
    'generated_at': datetime.now(UTC).isoformat(),
    'source_report': json_reports[-1].name,
    'registry': reg
}
reg_path.write_text(json.dumps(reg, indent=2))
(BASE/'data/reports/strategy_selection_latest.json').write_text(json.dumps(out, indent=2))
print(json.dumps({k: v['allowed'] for k,v in coins.items()}))
