#!/usr/bin/env python3
import argparse, csv, json
from pathlib import Path
from statistics import mean
from datetime import datetime, UTC


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
    if i < n:
        return None
    trs = []
    for k in range(i - n + 1, i + 1):
        h, l = bars[k]['high'], bars[k]['low']
        pc = bars[k - 1]['close'] if k > 0 else bars[k]['close']
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    return sum(trs) / len(trs)


def apply_costs(entry, exit_price, side, fee_bps, slippage_bps):
    total_bps = fee_bps + slippage_bps
    if side == 'long':
        entry_eff = entry * (1 + total_bps / 10000)
        exit_eff = exit_price * (1 - total_bps / 10000)
    else:
        entry_eff = entry * (1 - total_bps / 10000)
        exit_eff = exit_price * (1 + total_bps / 10000)
    return entry_eff, exit_eff


def detect_regime(bars, i, lookback=20):
    if i < lookback:
        return 'unknown'
    start = bars[i - lookback]['close']
    end = bars[i]['close']
    change = (end - start) / start if start else 0
    if change > 0.01:
        return 'trend_up'
    if change < -0.01:
        return 'trend_down'
    return 'chop'


def backtest_breakout(bars, strat, fee_bps=1.0, slippage_bps=2.0):
    lookback = strat['entry']['lookback_bars']
    stop_mult = strat['exit']['stop_atr_mult']
    target_mult = strat['exit']['target_r_mult']
    max_bars = strat['exit']['max_bars_in_trade']
    min_vol = strat['filters'].get('min_volume', 0)

    trades = []
    i = lookback
    trade_id = 1
    while i < len(bars) - 1:
        window = bars[i - lookback:i]
        range_high = max(x['high'] for x in window)
        b = bars[i]
        regime = detect_regime(bars, i)

        if b['volume'] >= min_vol and b['close'] > range_high and regime == 'trend_up':
            a = atr(bars, i)
            if not a:
                i += 1
                continue

            entry_raw = b['close']
            stop_raw = entry_raw - a * stop_mult
            risk_raw = entry_raw - stop_raw
            target_raw = entry_raw + risk_raw * target_mult

            exit_raw = None
            exit_reason = 'time'
            exit_i = min(i + max_bars, len(bars) - 1)

            for j in range(i + 1, min(i + max_bars + 1, len(bars))):
                bj = bars[j]
                if bj['low'] <= stop_raw:
                    exit_raw, exit_reason, exit_i = stop_raw, 'stop', j
                    break
                if bj['high'] >= target_raw:
                    exit_raw, exit_reason, exit_i = target_raw, 'target', j
                    break

            if exit_raw is None:
                exit_raw = bars[exit_i]['close']

            entry, exit_price = apply_costs(entry_raw, exit_raw, 'long', fee_bps, slippage_bps)
            stop = stop_raw
            risk = max(1e-9, entry - stop)
            r_mult = (exit_price - entry) / risk

            trades.append({
                'trade_id': trade_id,
                'entry_ts': b['ts'],
                'exit_ts': bars[exit_i]['ts'],
                'bars_held': max(1, exit_i - i),
                'entry': round(entry, 6),
                'exit': round(exit_price, 6),
                'reason': exit_reason,
                'regime': regime,
                'fee_bps': fee_bps,
                'slippage_bps': slippage_bps,
                'r': round(r_mult, 6)
            })
            trade_id += 1
            i = exit_i + 1
        else:
            i += 1

    return trades


def backtest_mean_reversion(bars, strat, fee_bps=1.0, slippage_bps=2.0):
    lookback = strat['entry']['lookback_bars']
    z_th = abs(strat['entry']['zscore_threshold'])
    stop_mult = strat['exit']['stop_atr_mult']
    target_mult = strat['exit']['target_r_mult']
    max_bars = strat['exit']['max_bars_in_trade']
    min_vol = strat['filters'].get('min_volume', 0)

    trades = []
    trade_id = 1
    i = lookback
    while i < len(bars) - 1:
        closes = [b['close'] for b in bars[i - lookback:i]]
        mu = mean(closes)
        var = mean([(x - mu) ** 2 for x in closes]) if closes else 0
        sd = var ** 0.5
        b = bars[i]
        regime = detect_regime(bars, i)

        z = (b['close'] - mu) / sd if sd > 1e-9 else 0
        if b['volume'] >= min_vol and z <= -z_th and regime == 'chop':
            a = atr(bars, i)
            if not a:
                i += 1
                continue

            entry_raw = b['close']
            stop_raw = entry_raw - a * stop_mult
            risk_raw = entry_raw - stop_raw
            target_raw = entry_raw + risk_raw * target_mult

            exit_raw = None
            exit_reason = 'time'
            exit_i = min(i + max_bars, len(bars) - 1)
            for j in range(i + 1, min(i + max_bars + 1, len(bars))):
                bj = bars[j]
                if bj['low'] <= stop_raw:
                    exit_raw, exit_reason, exit_i = stop_raw, 'stop', j
                    break
                if bj['high'] >= target_raw:
                    exit_raw, exit_reason, exit_i = target_raw, 'target', j
                    break
            if exit_raw is None:
                exit_raw = bars[exit_i]['close']

            entry, exit_price = apply_costs(entry_raw, exit_raw, 'long', fee_bps, slippage_bps)
            risk = max(1e-9, entry - stop_raw)
            r_mult = (exit_price - entry) / risk

            trades.append({
                'trade_id': trade_id,
                'entry_ts': b['ts'],
                'exit_ts': bars[exit_i]['ts'],
                'bars_held': max(1, exit_i - i),
                'entry': round(entry, 6),
                'exit': round(exit_price, 6),
                'reason': exit_reason,
                'regime': regime,
                'fee_bps': fee_bps,
                'slippage_bps': slippage_bps,
                'r': round(r_mult, 6)
            })
            trade_id += 1
            i = exit_i + 1
        else:
            i += 1

    return trades


def summarize(trades):
    if not trades:
        return {
            'trades': 0, 'win_rate': 0, 'avg_r': 0, 'expectancy_r': 0,
            'profit_factor': 0, 'max_dd_r': 0, 'stop_rate': 0,
            'target_rate': 0, 'time_exit_rate': 0
        }

    rs = [t['r'] for t in trades]
    wins = [x for x in rs if x > 0]
    losses = [x for x in rs if x <= 0]

    eq, peak, maxdd = 0.0, 0.0, 0.0
    for r in rs:
        eq += r
        peak = max(peak, eq)
        maxdd = min(maxdd, eq - peak)

    gp = sum(wins)
    gl = abs(sum(losses)) if losses else 1e-9
    total = len(trades)

    stop_rate = sum(1 for t in trades if t['reason'] == 'stop') / total
    target_rate = sum(1 for t in trades if t['reason'] == 'target') / total
    time_rate = sum(1 for t in trades if t['reason'] == 'time') / total

    return {
        'trades': total,
        'win_rate': round(len(wins) / total, 4),
        'avg_r': round(mean(rs), 4),
        'expectancy_r': round(mean(rs), 4),
        'profit_factor': round(gp / gl, 4),
        'max_dd_r': round(maxdd, 4),
        'stop_rate': round(stop_rate, 4),
        'target_rate': round(target_rate, 4),
        'time_exit_rate': round(time_rate, 4)
    }


def append_ledger(ledger_path: Path, strategy_name: str, trades):
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    with ledger_path.open('a') as f:
        for t in trades:
            row = {'logged_at': datetime.now(UTC).isoformat(), 'strategy': strategy_name, **t}
            f.write(json.dumps(row) + '\n')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--csv', required=True)
    ap.add_argument('--strategy', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--ledger', default='/home/marten/.openclaw/workspace/horus/data/journal/trade_ledger.jsonl')
    ap.add_argument('--fee-bps', type=float, default=1.0)
    ap.add_argument('--slippage-bps', type=float, default=2.0)
    args = ap.parse_args()

    bars = load_bars(args.csv)
    strat = json.loads(Path(args.strategy).read_text())
    et = strat['entry']['type']

    if et == 'range_breakout':
        trades = backtest_breakout(bars, strat, fee_bps=args.fee_bps, slippage_bps=args.slippage_bps)
    elif et == 'zscore_revert':
        trades = backtest_mean_reversion(bars, strat, fee_bps=args.fee_bps, slippage_bps=args.slippage_bps)
    else:
        raise SystemExit(f'Unsupported entry type: {et}')

    summary = summarize(trades)
    report = {
        'generated_at': datetime.now(UTC).isoformat(),
        'strategy': strat['name'],
        'entry_type': et,
        'costs': {'fee_bps': args.fee_bps, 'slippage_bps': args.slippage_bps},
        'summary': summary,
        'trades': trades
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2))

    append_ledger(Path(args.ledger), strat['name'], trades)
    print(json.dumps(summary))


if __name__ == '__main__':
    main()
