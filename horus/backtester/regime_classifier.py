#!/usr/bin/env python3
import argparse, csv, json
from pathlib import Path


def load_csv(path):
    rows = []
    with open(path, newline='') as f:
        r = csv.DictReader(f)
        for row in r:
            rows.append({
                'timestamp': row['timestamp'],
                'open': float(row['open']),
                'high': float(row['high']),
                'low': float(row['low']),
                'close': float(row['close']),
                'volume': float(row.get('volume', 0) or 0),
                'spread_bps': float(row.get('spread_bps', 0) or 0),
            })
    return rows


def sma(vals, n):
    out = [None]*len(vals)
    s = 0.0
    for i,v in enumerate(vals):
        s += v
        if i >= n:
            s -= vals[i-n]
        if i >= n-1:
            out[i] = s/n
    return out


def atr(rows, n=14):
    tr = [0.0]*len(rows)
    for i, r in enumerate(rows):
        if i == 0:
            tr[i] = r['high'] - r['low']
        else:
            pc = rows[i-1]['close']
            tr[i] = max(r['high']-r['low'], abs(r['high']-pc), abs(r['low']-pc))
    return sma(tr, n)


def percentile_rank(seq, i, w):
    if i < w:
        return None
    x = seq[i]
    if x is None:
        return None
    win = [v for v in seq[i-w+1:i+1] if v is not None]
    if not win:
        return None
    less = sum(1 for v in win if v <= x)
    return 100.0 * less / len(win)


def classify(rows):
    closes = [r['close'] for r in rows]
    a = atr(rows, 14)
    e20 = sma(closes, 20)
    e50 = sma(closes, 50)

    spreads = [r['spread_bps'] for r in rows]
    median_spread = sorted(spreads)[len(spreads)//2] if spreads else 0.0

    out = []
    for i, r in enumerate(rows):
        vol_pctl = percentile_rank(a, i, 2016) if a[i] is not None else None
        trend = None
        chop = None
        label = 'UNKNOWN'

        if a[i] not in (None, 0) and e20[i] is not None and e50[i] is not None and i >= 12:
            trend = abs(e20[i] - e50[i]) / a[i]
            retn = [abs((closes[k]-closes[k-1])) for k in range(i-11, i+1)]
            avg_retn = sum(retn)/len(retn)
            chop = 1 - min(1.0, (avg_retn / a[i]))

            spread_shock = r['spread_bps'] > 2*median_spread if median_spread > 0 else False

            if (vol_pctl is not None and vol_pctl < 35) or (chop is not None and chop > 0.65):
                label = 'CHOP_LOW_VOL'
            elif (vol_pctl is not None and 35 <= vol_pctl <= 85) and trend > 0.35 and chop <= 0.65 and not spread_shock:
                label = 'TREND_NORMAL'
            elif (vol_pctl is not None and vol_pctl > 85) or spread_shock:
                label = 'VOL_SHOCK'
            else:
                label = 'CHOP_LOW_VOL'

        out.append({
            'timestamp': r['timestamp'],
            'vol_pctl': round(vol_pctl, 4) if vol_pctl is not None else None,
            'trend': round(trend, 6) if trend is not None else None,
            'chop': round(chop, 6) if chop is not None else None,
            'regime': label
        })
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--csv', required=True)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()

    rows = load_csv(args.csv)
    labels = classify(rows)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps({'labels': labels}, indent=2))
    print(args.out)


if __name__ == '__main__':
    main()
