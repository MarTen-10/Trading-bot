#!/usr/bin/env python3
import argparse, csv, json, urllib.request
from datetime import datetime, UTC
from pathlib import Path

BASE = "https://api.exchange.coinbase.com/products/{product}/candles?granularity={granularity}"

# Coinbase returns: [time, low, high, open, close, volume]
def fetch(product, granularity=300):
    url = BASE.format(product=product, granularity=granularity)
    req = urllib.request.Request(url, headers={"User-Agent": "horus/1.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())


def write_csv(rows, out_path):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # sort ascending by time
    rows = sorted(rows, key=lambda x: x[0])
    with out_path.open('w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['timestamp','open','high','low','close','volume'])
        for k in rows:
            ts = datetime.fromtimestamp(k[0], tz=UTC).isoformat()
            low, high, open_, close, vol = k[1], k[2], k[3], k[4], k[5]
            w.writerow([ts, open_, high, low, close, vol])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--products', nargs='+', default=['BTC-USD','ETH-USD','SOL-USD'])
    ap.add_argument('--granularity', type=int, default=300)
    ap.add_argument('--outdir', default='/home/marten/.openclaw/workspace/horus/data/raw/crypto')
    args = ap.parse_args()

    out = []
    for p in args.products:
        rows = fetch(p, args.granularity)
        path = Path(args.outdir) / f"{p.replace('-', '')}_5m.csv"
        write_csv(rows, path)
        out.append(str(path))
    print('\n'.join(out))

if __name__ == '__main__':
    main()
