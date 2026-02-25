#!/usr/bin/env python3
import csv, random
from datetime import datetime, timedelta
from pathlib import Path

out = Path('/home/marten/.openclaw/workspace/horus/data/raw/sample_5m.csv')
out.parent.mkdir(parents=True, exist_ok=True)
start = datetime(2026,1,2,9,30)
price = 100.0
with out.open('w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['timestamp','open','high','low','close','volume'])
    t = start
    for i in range(400):
        drift = 0.03 if (i//50)%2==0 else -0.01
        noise = random.uniform(-0.35,0.35)
        o = price
        c = max(1.0, o + drift + noise)
        h = max(o,c) + random.uniform(0,0.25)
        l = min(o,c) - random.uniform(0,0.25)
        v = random.randint(120000, 500000)
        w.writerow([t.isoformat(), round(o,4), round(h,4), round(l,4), round(c,4), v])
        price = c
        t += timedelta(minutes=5)
print(out)
