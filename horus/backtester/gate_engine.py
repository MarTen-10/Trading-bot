#!/usr/bin/env python3
import argparse, json, statistics
from datetime import datetime, UTC
from pathlib import Path


def rolling_windows(vals, n):
    if len(vals) < n:
        return []
    return [vals[i-n:i] for i in range(n, len(vals)+1)]


def evaluate(backtest_report, mc_report, policy):
    bt = json.loads(Path(backtest_report).read_text())
    mc = json.loads(Path(mc_report).read_text())
    pol = json.loads(Path(policy).read_text())

    s = bt.get('summary', {})
    trades = bt.get('trades', [])
    rs = [t.get('r', 0.0) for t in trades]

    pg = pol['promotion_gate']
    dg = pol['disable_rules']

    windows = rolling_windows(rs, dg['rolling_window_trades'])
    rolling_exp = [statistics.mean(w) for w in windows] if windows else []
    neg_streak = 0
    max_neg_streak = 0
    for e in rolling_exp:
        if e < 0:
            neg_streak += 1
            max_neg_streak = max(max_neg_streak, neg_streak)
        else:
            neg_streak = 0

    p95_dd = mc.get('drawdown_pct', {}).get('p95_worst')

    reasons = []
    if s.get('trades', 0) < pg['min_trades']:
        reasons.append('trades_below_min')
    if s.get('expectancy_r', -999) < pg['min_expectancy_r']:
        reasons.append('expectancy_below_min')
    pf = s.get('profit_factor')
    if pf is None or pf < pg['min_profit_factor']:
        reasons.append('profit_factor_below_min')
    if s.get('max_drawdown_pct', 0) < pg['max_drawdown_pct']:
        reasons.append('drawdown_below_limit')
    if p95_dd is not None and p95_dd < pg['max_p95_drawdown_pct']:
        reasons.append('mc_p95_drawdown_below_limit')
    if max_neg_streak > pg['max_rolling50_negative_windows']:
        reasons.append('too_many_negative_rolling_windows')

    disable = False
    disable_reasons = []
    if max_neg_streak >= dg['disable_if_expectancy_below_zero_for_consecutive_windows']:
        disable = True
        disable_reasons.append('rolling_expectancy_negative_consecutive')
    if pf is None or pf < dg['disable_if_profit_factor_below']:
        disable = True
        disable_reasons.append('profit_factor_disable_rule')
    if s.get('max_drawdown_pct', 0) < dg['disable_if_drawdown_below_pct']:
        disable = True
        disable_reasons.append('drawdown_disable_rule')

    status = 'PROMOTE' if not reasons else 'REJECT'

    return {
      'generated_at': datetime.now(UTC).isoformat(),
      'inputs': {
        'backtest_report': backtest_report,
        'mc_report': mc_report,
        'policy': policy
      },
      'promotion_status': status,
      'promotion_reasons': reasons,
      'disable_status': 'DISABLE' if disable else 'KEEP',
      'disable_reasons': disable_reasons,
      'rolling_expectancy': {
        'window_size': dg['rolling_window_trades'],
        'num_windows': len(rolling_exp),
        'max_negative_consecutive': max_neg_streak,
        'latest': round(rolling_exp[-1], 4) if rolling_exp else None
      },
      'metrics': {
        'trades': s.get('trades'),
        'expectancy_r': s.get('expectancy_r'),
        'profit_factor': s.get('profit_factor'),
        'max_drawdown_pct': s.get('max_drawdown_pct'),
        'mc_p95_drawdown_pct': p95_dd
      }
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--backtest-report', required=True)
    ap.add_argument('--mc-report', required=True)
    ap.add_argument('--policy', default='/home/marten/.openclaw/workspace/horus/config/promotion_rollback_policy.json')
    ap.add_argument('--out', required=True)
    args = ap.parse_args()

    out = evaluate(args.backtest_report, args.mc_report, args.policy)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=2))
    print(args.out)


if __name__ == '__main__':
    main()
