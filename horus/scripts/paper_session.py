#!/usr/bin/env python3
import json
from datetime import datetime, UTC
from pathlib import Path

signals = [
  {"symbol": "AAPL", "setup": "breakout_v1", "confidence": 0.72, "risk": "0.5%", "status": "candidate"},
  {"symbol": "NVDA", "setup": "breakout_v1", "confidence": 0.67, "risk": "0.5%", "status": "candidate"}
]

now = datetime.now(UTC)
out = Path('/home/marten/.openclaw/workspace/horus/data/signals') / f"signals_{now.strftime('%Y%m%d_%H%M%S')}.json"
out.parent.mkdir(parents=True, exist_ok=True)
payload = {
    "generated_at": now.isoformat(),
    "signals": signals
}
out.write_text(json.dumps(payload, indent=2))

ledger = Path('/home/marten/.openclaw/workspace/horus/data/journal/signal_ledger.jsonl')
ledger.parent.mkdir(parents=True, exist_ok=True)
with ledger.open('a') as f:
    for s in signals:
        row = {
            "logged_at": now.isoformat(),
            **s
        }
        f.write(json.dumps(row) + '\n')

print(out)
