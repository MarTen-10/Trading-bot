#!/usr/bin/env python3
from pathlib import Path
import re
import sys

ROOT = Path('/home/marten/.openclaw/workspace/anubis_l0')

# Disallow direct bounded_retry usage outside tool_executor
bad = []
for p in ROOT.glob('*.py'):
    txt = p.read_text(encoding='utf-8')
    if p.name not in ('tool_executor.py', 'retry.py') and 'bounded_retry(' in txt:
        bad.append(f"{p}: direct bounded_retry usage")

# Disallow direct gate_step usage outside tool_executor
for p in ROOT.glob('*.py'):
    txt = p.read_text(encoding='utf-8')
    if p.name not in ('tool_executor.py', 'router.py') and 'gate_step(' in txt:
        bad.append(f"{p}: direct gate_step usage")

# Enforce executor usage in runner
runner = (ROOT / 'runner.py').read_text(encoding='utf-8')
if 'ToolExecutor' not in runner:
    bad.append('runner.py: ToolExecutor not used')

if bad:
    print('L0_BYPASS_CHECK_FAILED')
    for b in bad:
        print(b)
    sys.exit(1)

print('L0_BYPASS_CHECK_OK')
