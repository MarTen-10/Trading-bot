#!/usr/bin/env python3
import json
from pathlib import Path
from datetime import datetime, UTC

bt_dir = Path('/home/marten/.openclaw/workspace/horus/data/backtests')
reports = sorted(bt_dir.glob('*.json'))
now = datetime.now(UTC)
summary = {"generated_at": now.isoformat(), "backtests": []}
for p in reports[-10:]:
    j = json.loads(p.read_text())
    summary["backtests"].append({"file": p.name, **j.get("summary", {})})
out = Path('/home/marten/.openclaw/workspace/horus/data/reports') / f"daily_{now.strftime('%Y%m%d')}.json"
out.write_text(json.dumps(summary, indent=2))
print(out)
