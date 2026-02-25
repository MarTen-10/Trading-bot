#!/usr/bin/env python3
import json
from datetime import datetime, UTC
from pathlib import Path

BASE = Path('/home/marten/.openclaw/workspace/horus')
reg = json.loads((BASE/'config/strategy_registry.json').read_text())

signals = []
skipped = []

for coin, cfg in reg['coins'].items():
    allowed = cfg.get('allowed', [])
    if not allowed:
        skipped.append({'symbol': coin, 'reason': 'no strategy passed promotion gate'})
        continue
    strat = allowed[0]
    signals.append({
        'symbol': coin,
        'setup': strat,
        'confidence': 0.65,
        'risk': '0.5%',
        'status': 'candidate',
        'mode': 'paper'
    })

now = datetime.now(UTC)
out = BASE/'data/signals'/f"signals_livefeed_{now.strftime('%Y%m%d_%H%M%S')}.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps({'generated_at': now.isoformat(), 'signals': signals, 'skipped': skipped}, indent=2))

ledger = BASE/'data/journal/signal_ledger.jsonl'
with ledger.open('a') as f:
    for s in signals:
        f.write(json.dumps({'logged_at': now.isoformat(), **s})+'\n')
    for s in skipped:
        f.write(json.dumps({'logged_at': now.isoformat(), 'symbol': s['symbol'], 'status': 'skipped', 'reason': s['reason']})+'\n')

print(out)
