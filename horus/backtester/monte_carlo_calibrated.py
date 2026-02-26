#!/usr/bin/env python3
import argparse, json, random, statistics
from datetime import datetime, UTC
from pathlib import Path


def pct_drawdown(path):
    peak = path[0]
    worst = 0.0
    for x in path:
        peak = max(peak, x)
        dd = (x / peak - 1.0) * 100.0
        worst = min(worst, dd)
    return worst


def percentile(vals, p):
    if not vals:
        return None
    vals = sorted(vals)
    k = (len(vals)-1) * p
    f = int(k)
    c = min(f+1, len(vals)-1)
    if f == c:
        return vals[f]
    return vals[f] + (vals[c]-vals[f])*(k-f)


def calibrate_from_backtest(backtest_json):
    r = json.loads(Path(backtest_json).read_text())
    trades = r.get('trades', [])
    rs = [t.get('r', 0.0) for t in trades]
    wins = [x for x in rs if x > 0]
    losses = [abs(x) for x in rs if x <= 0]

    win_rate = len(wins)/len(rs) if rs else 0.0
    avg_win = statistics.mean(wins) if wins else 0.0
    avg_loss = statistics.mean(losses) if losses else 1.0
    stdev_win = statistics.pstdev(wins) if len(wins) > 1 else max(0.1, avg_win*0.15)
    stdev_loss = statistics.pstdev(losses) if len(losses) > 1 else max(0.1, avg_loss*0.15)

    costs = r.get('summary', {}).get('costs', {})
    friction_penalty_r = ((costs.get('fee_bps', 0.0) + costs.get('slippage_bps', 0.0)) / 10_000) * 2.0

    return {
      'source_report': backtest_json,
      'trades_count': len(rs),
      'win_rate': round(win_rate, 4),
      'avg_win_r': round(avg_win, 4),
      'avg_loss_r': round(avg_loss, 4),
      'stdev_win_r': round(stdev_win, 4),
      'stdev_loss_r': round(stdev_loss, 4),
      'friction_penalty_r': round(friction_penalty_r, 4)
    }


def run_mc(params, days=60, paths=2000, min_trades_day=3, max_trades_day=6, equity0=1000, risk_pct=0.01):
    rng = random.Random(7)
    term = []
    mdds = []
    samples = []

    for p in range(paths):
        eq = equity0
        curve = [eq]
        for _ in range(days):
            ntr = rng.randint(min_trades_day, max_trades_day)
            for _ in range(ntr):
                is_win = (rng.random() < params['win_rate'])
                if is_win:
                    r_mult = max(0.0, rng.gauss(params['avg_win_r'], params['stdev_win_r']))
                else:
                    r_mult = -max(0.0, rng.gauss(params['avg_loss_r'], params['stdev_loss_r']))
                r_mult -= params['friction_penalty_r']
                risk_dollars = eq * risk_pct
                eq += risk_dollars * r_mult
                eq = max(1.0, eq)
            curve.append(eq)
        term.append(eq)
        mdds.append(pct_drawdown(curve))
        if p < 60:
            samples.append(curve)

    out = {
      'generated_at': datetime.now(UTC).isoformat(),
      'assumptions': {
        **params,
        'days': days,
        'paths': paths,
        'trades_per_day_range': [min_trades_day, max_trades_day],
        'equity0': equity0,
        'risk_pct': risk_pct
      },
      'terminal_equity': {
        'mean': round(statistics.mean(term), 2),
        'median': round(statistics.median(term), 2),
        'p05': round(percentile(term, 0.05), 2),
        'p25': round(percentile(term, 0.25), 2),
        'p75': round(percentile(term, 0.75), 2),
        'p95': round(percentile(term, 0.95), 2)
      },
      'drawdown_pct': {
        'mean': round(statistics.mean(mdds), 2),
        'median': round(statistics.median(mdds), 2),
        'p95_worst': round(percentile(mdds, 0.95), 2),
        'p99_worst': round(percentile(mdds, 0.99), 2)
      },
      'sample_paths': samples
    }
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--backtest-report', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--days', type=int, default=60)
    ap.add_argument('--paths', type=int, default=2000)
    ap.add_argument('--equity', type=float, default=1000)
    ap.add_argument('--risk-pct', type=float, default=0.01)
    args = ap.parse_args()

    params = calibrate_from_backtest(args.backtest_report)
    out = run_mc(params, days=args.days, paths=args.paths, equity0=args.equity, risk_pct=args.risk_pct)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=2))
    print(args.out)


if __name__ == '__main__':
    main()
