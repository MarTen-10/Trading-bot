#!/usr/bin/env python3
import argparse, csv, json, urllib.request
from datetime import datetime, UTC
from pathlib import Path

BASE = "https://api.binance.com/api/v3/klines"

def fetch(symbol, interval='5m', limit=1000):
    url = f"{BASE}?symbol={symbol}&interval={interval}&limit={limit}"
    with urllib.request.urlopen(url, timeout=20) as r:
        return json.loads(r.read().decode())


def write_csv(rows, out_path):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open('w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['timestamp','open','high','low','close','volume'])
        for k in rows:
            ts = datetime.fromtimestamp(k[0]/1000, tz=UTC).isoformat()
            w.writerow([ts, k[1], k[2], k[3], k[4], k[5]])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--symbols', nargs='+', default=['BTCUSDT','ETHUSDT','SOLUSDT'])
    ap.add_argument('--interval', default='5m')
    ap.add_argument('--limit', type=int, default=1000)
    ap.add_argument('--outdir', default='/home/marten/.openclaw/workspace/horus/data/raw/crypto')
    args = ap.parse_args()

    out = []
    for s in args.symbols:
        rows = fetch(s, args.interval, args.limit)
        p = Path(args.outdir) / f"{s}_{args.interval}.csv"
        write_csv(rows, p)
        out.append(str(p))
    print('\n'.join(out))

if __name__ == '__main__':
    main()
