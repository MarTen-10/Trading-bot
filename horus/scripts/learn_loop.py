#!/usr/bin/env python3
import json
from datetime import datetime, UTC
from pathlib import Path

BT_DIR = Path('/home/marten/.openclaw/workspace/horus/data/backtests')
OUT_JSON = Path('/home/marten/.openclaw/workspace/horus/data/journal/learning_state.json')
OUT_MD = Path('/home/marten/.openclaw/workspace/horus/data/journal/lessons_latest.md')

reports = sorted(BT_DIR.glob('*.json'))
if not reports:
    state = {"generated_at": datetime.now(UTC).isoformat(), "status": "no_backtests", "lessons": []}
    OUT_JSON.write_text(json.dumps(state, indent=2))
    OUT_MD.write_text('# Lessons\n\n- No backtests available yet.\n')
    print(json.dumps(state))
    raise SystemExit(0)

latest = json.loads(reports[-1].read_text())
summary = latest.get('summary', {})
lessons = []
actions = []

if summary.get('profit_factor', 0) < 1.1:
    lessons.append('Edge too weak (profit_factor < 1.1).')
    actions.append('Tighten filters and avoid marginal setups.')

if summary.get('stop_rate', 0) > 0.55:
    lessons.append('Too many stop-outs (stop_rate > 55%).')
    actions.append('Increase breakout confirmation and reduce early entries.')

if summary.get('max_dd_r', 0) < -2.5:
    lessons.append('Drawdown too high (max_dd_r < -2.5R).')
    actions.append('Lower risk/trade and add no-trade window during chop.')

if summary.get('win_rate', 0) < 0.45:
    lessons.append('Win rate below baseline (<45%).')
    actions.append('Restrict to top confidence regime only.')

if not lessons:
    lessons.append('Current metrics are within baseline thresholds.')
    actions.append('Continue paper run and collect larger sample size.')

state = {
    "generated_at": datetime.now(UTC).isoformat(),
    "source_report": reports[-1].name,
    "summary": summary,
    "lessons": lessons,
    "actions": actions
}
OUT_JSON.write_text(json.dumps(state, indent=2))

md = ['# Horus Learning Loop (latest)', '', f"Source: `{reports[-1].name}`", '']
md.append('## Metrics')
for k in ['trades', 'win_rate', 'expectancy_r', 'profit_factor', 'max_dd_r', 'stop_rate', 'target_rate', 'time_exit_rate']:
    md.append(f"- {k}: {summary.get(k)}")
md.append('')
md.append('## Lessons')
for l in lessons:
    md.append(f"- {l}")
md.append('')
md.append('## Next actions')
for a in actions:
    md.append(f"- {a}")
md.append('')
OUT_MD.write_text('\n'.join(md) + '\n')

print(json.dumps({"lessons": len(lessons), "actions": len(actions)}))
