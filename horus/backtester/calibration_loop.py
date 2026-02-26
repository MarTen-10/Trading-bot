#!/usr/bin/env python3
import argparse, csv, json
from collections import defaultdict
from datetime import datetime, UTC
from pathlib import Path


def pct(vals, p):
    if not vals:
        return None
    vals = sorted(vals)
    k = (len(vals)-1) * p
    f = int(k)
    c = min(f+1, len(vals)-1)
    if f == c:
        return vals[f]
    return vals[f] + (vals[c]-vals[f])*(k-f)


def load_fills(path):
    rows = []
    with open(path, newline='') as f:
        r = csv.DictReader(f)
        for row in r:
            side = row.get('side','buy').lower()
            fill_px = float(row['fill_px'])
            mid = float(row['mid_at_send'])
            sign = 1 if side == 'buy' else -1
            slippage_bps = sign * ((fill_px - mid) / mid) * 10000 if mid else 0.0
            ts = datetime.fromisoformat(row['ts'].replace('Z','+00:00'))
            rows.append({
                'instrument': row['instrument'],
                'hour': ts.hour,
                'regime': row.get('regime','UNKNOWN'),
                'slippage_bps': slippage_bps
            })
    return rows


def summarize(rows):
    grouped = defaultdict(list)
    by_inst = defaultdict(list)
    for r in rows:
        key = (r['instrument'], r['hour'], r['regime'])
        grouped[key].append(r['slippage_bps'])
        by_inst[r['instrument']].append(r['slippage_bps'])

    out = {'groups': [], 'instrument_summary': {}}
    for (inst, hour, regime), vals in grouped.items():
        out['groups'].append({
            'instrument': inst,
            'hour': hour,
            'regime': regime,
            'count': len(vals),
            'p50': round(pct(vals, 0.50), 4),
            'p75': round(pct(vals, 0.75), 4),
            'p90': round(pct(vals, 0.90), 4),
        })

    for inst, vals in by_inst.items():
        out['instrument_summary'][inst] = {
            'count': len(vals),
            'p50': round(pct(vals, 0.50), 4),
            'p75': round(pct(vals, 0.75), 4),
            'p90': round(pct(vals, 0.90), 4),
        }
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--fills-csv', required=True)
    ap.add_argument('--out-json', required=True)
    args = ap.parse_args()

    rows = load_fills(args.fills_csv)
    rep = summarize(rows)
    rep['generated_at'] = datetime.now(UTC).isoformat()
    rep['source'] = args.fills_csv

    Path(args.out_json).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out_json).write_text(json.dumps(rep, indent=2))
    print(args.out_json)


if __name__ == '__main__':
    main()
