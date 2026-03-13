#!/usr/bin/env bash
set -euo pipefail
python3 - <<'PY'
import json, subprocess, re
out=subprocess.check_output(['openclaw','cron','list'], text=True, stderr=subprocess.STDOUT)
lines=out.splitlines()
jobs=[]
for ln in lines:
    if re.match(r'^[0-9a-f]{8}-', ln):
        jobs.append(ln)
print('cron_health_report')
print(f'jobs_total={len(jobs)}')
for j in jobs:
    print('job_line=' + j.strip())
print('done')
PY