#!/usr/bin/env python3
import argparse, csv, json, math
from pathlib import Path
from statistics import mean

def load_bars(path):
    rows = []
    with open(path, newline='') as f:
        r = csv.DictReader(f)
        for row in r:
            rows.append({
                'ts': row['timestamp'],
                'open': float(row['open']),
                'high': float(row['high']),
                'low': float(row['low']),
                'close': float(row['close']),
                'volume': float(row.get('volume', 0) or 0)
            })
    return rows

def atr(bars, i, n=14):
    if i < n: return None
    trs = []
    for k in range(i-n+1, i+1):
        h, l = bars[k]['high'], bars[k]['low']
        pc = bars[k-1]['close'] if k > 0 else bars[k]['close']
        trs.append(max(h-l, abs(h-pc), abs(l-pc)))
    return sum(trs)/len(trs)

def backtest_breakout(bars, strat):
    lookback = strat['entry']['lookback_bars']
    stop_mult = strat['exit']['stop_atr_mult']
    target_mult = strat['exit']['target_r_mult']
    max_bars = strat['exit']['max_bars_in_trade']
    min_vol = strat['filters'].get('min_volume', 0)

    trades = []
    i = lookback
    while i < len(bars)-1:
        window = bars[i-lookback:i]
        range_high = max(x['high'] for x in window)
        b = bars[i]
        if b['volume'] >= min_vol and b['close'] > range_high:
            a = atr(bars, i)
            if not a:
                i += 1
                continue
            entry = b['close']
            stop = entry - a*stop_mult
            risk = entry-stop
            target = entry + risk*target_mult
            exit_price = None
            exit_reason = 'time'
            exit_i = min(i+max_bars, len(bars)-1)
            for j in range(i+1, min(i+max_bars+1, len(bars))):
                bj = bars[j]
                if bj['low'] <= stop:
                    exit_price, exit_reason, exit_i = stop, 'stop', j
                    break
                if bj['high'] >= target:
                    exit_price, exit_reason, exit_i = target, 'target', j
                    break
            if exit_price is None:
                exit_price = bars[exit_i]['close']
            r_mult = (exit_price-entry)/risk if risk else 0
            trades.append({
                'entry_ts': b['ts'], 'exit_ts': bars[exit_i]['ts'],
                'entry': entry, 'exit': exit_price, 'reason': exit_reason, 'r': r_mult
            })
            i = exit_i + 1
        else:
            i += 1
    return trades

def summarize(trades):
    if not trades:
        return {'trades':0,'win_rate':0,'avg_r':0,'expectancy_r':0,'profit_factor':0,'max_dd_r':0}
    rs = [t['r'] for t in trades]
    wins = [x for x in rs if x > 0]
    losses = [x for x in rs if x <= 0]
    eq, peak, maxdd = 0.0, 0.0, 0.0
    for r in rs:
      eq += r
      peak = max(peak, eq)
      maxdd = min(maxdd, eq-peak)
    gp = sum(wins)
    gl = abs(sum(losses)) if losses else 1e-9
    return {
      'trades': len(rs),
      'win_rate': round(len(wins)/len(rs),4),
      'avg_r': round(mean(rs),4),
      'expectancy_r': round(mean(rs),4),
      'profit_factor': round(gp/gl,4),
      'max_dd_r': round(maxdd,4)
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--csv', required=True)
    ap.add_argument('--strategy', required=True)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()

    bars = load_bars(args.csv)
    strat = json.loads(Path(args.strategy).read_text())
    if strat['entry']['type'] != 'range_breakout':
        raise SystemExit('Only range_breakout is implemented in v1')

    trades = backtest_breakout(bars, strat)
    report = {'strategy': strat['name'], 'summary': summarize(trades), 'trades': trades}
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(report, indent=2))
    print(json.dumps(report['summary']))

if __name__ == '__main__':
    main()
