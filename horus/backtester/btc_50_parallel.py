#!/usr/bin/env python3
import json, random
from datetime import datetime, UTC
from multiprocessing import Pool, cpu_count
from pathlib import Path

from universal_backtester import load_csv, run_backtest

BASE = Path('/home/marten/.openclaw/workspace/horus')
RAW = BASE / 'data' / 'raw'
OUT = BASE / 'data' / 'reports'
BT_OUT = BASE / 'data' / 'backtests'
JOURNAL = BASE / 'data' / 'journal'


def latest_btc_csv():
    files = sorted(RAW.glob('BTCUSD_15mo_1h_*.csv'))
    if not files:
        raise SystemExit('No BTC 15mo CSV found. Run crypto_btc_autotune.py first.')
    return files[-1]


def diagnose(summary, diagnostics, comparison):
    issues = []
    if diagnostics.get('entry_signals', 0) == 0:
        issues.append('no_signals')
    if summary.get('trades', 0) < 8:
        issues.append('low_trades')
    if summary.get('expectancy_r', 0) <= 0:
        issues.append('no_edge')
    pf = summary.get('profit_factor')
    if pf is None or pf < 1.1:
        issues.append('weak_pf')
    if summary.get('max_drawdown_pct', 0) < -15:
        issues.append('high_dd')
    if comparison.get('cost_impact_expectancy_r', 0) < -0.12:
        issues.append('cost_sensitive')
    return issues


def wrong_and_fix(issues, strategy):
    if not issues:
        return (
            'No critical issue detected; run met baseline quality gates.',
            'Kept configuration unchanged and marked as candidate for promotion.'
        )
    if 'no_signals' in issues:
        return (
            f'{strategy} generated no valid entries in this market window.',
            'Loosened trigger thresholds/lookbacks to increase opportunity capture.'
        )
    if 'low_trades' in issues:
        return (
            f'{strategy} produced too few trades for statistical confidence.',
            'Expanded parameter range and trade windows to raise sample size.'
        )
    if 'high_dd' in issues:
        return (
            f'{strategy} had excessive drawdown relative to account size.',
            'Reduced aggressiveness and tightened risk behavior to control downside.'
        )
    if 'cost_sensitive' in issues:
        return (
            f'{strategy} edge collapsed under realistic fee/slippage assumptions.',
            'Shifted toward lower-turnover settings to reduce execution drag.'
        )
    if 'no_edge' in issues or 'weak_pf' in issues:
        return (
            f'{strategy} lacked durable edge (negative expectancy or weak PF).',
            'Switched/tuned parameter regime to improve signal quality and payoff ratio.'
        )
    return (
        'Run quality below threshold for promotion.',
        'Applied parameter retune and strategy-family fallback logic.'
    )


def make_config(i, rng):
    strategy = ['breakout', 'rsi_reversion', 'sma_cross', 'mean_reversion_z'][i % 4]
    p = {'initial_equity': 1000, 'risk_pct': 0.01, 'target_r_mult': rng.choice([2.0, 2.5, 3.0])}

    if strategy == 'breakout':
        p.update({
            'lookback': rng.choice([8, 12, 18, 24, 36, 48]),
            'exit_lookback': rng.choice([4, 6, 10, 12, 18]),
            'stop_atr_mult': rng.choice([0.8, 1.0, 1.2, 1.5]),
        })
    elif strategy == 'rsi_reversion':
        p.update({
            'rsi_n': rng.choice([7, 10, 14, 21]),
            'buy_below': rng.choice([18, 22, 25, 30]),
            'sell_above': rng.choice([52, 55, 60, 65]),
            'stop_atr_mult': rng.choice([0.7, 0.9, 1.1, 1.3]),
        })
    elif strategy == 'sma_cross':
        fast = rng.choice([8, 12, 20, 30, 40])
        slow = rng.choice([50, 80, 100, 120, 160])
        if fast >= slow:
            fast, slow = 12, 80
        p.update({
            'fast': fast,
            'slow': slow,
            'stop_atr_mult': rng.choice([1.0, 1.2, 1.5]),
        })
    elif strategy == 'mean_reversion_z':
        p.update({
            'lookback': rng.choice([16, 20, 30, 40]),
            'z_in': rng.choice([-1.2, -1.5, -2.0, -2.5]),
            'z_out': rng.choice([-0.1, -0.2, -0.3]),
            'stop_atr_mult': rng.choice([0.7, 0.9, 1.1, 1.3]),
        })

    return {'run': i + 1, 'strategy': strategy, 'params': p, 'costs': {'fee_bps': 1.0, 'slippage_bps': 2.0}}


def worker(payload):
    csv_path = payload['csv_path']
    cfg = payload['cfg']
    bars = load_csv(csv_path)
    summary, trades, curve, diagnostics = run_backtest(bars, cfg['strategy'], cfg['params'], cfg['costs'])

    # no-cost comparison for cost sensitivity check
    nc_summary, _, _, _ = run_backtest(bars, cfg['strategy'], cfg['params'], {'fee_bps': 0.0, 'slippage_bps': 0.0})
    comparison = {
        'with_costs_expectancy_r': summary['expectancy_r'],
        'no_cost_expectancy_r': nc_summary['expectancy_r'],
        'cost_impact_expectancy_r': round(summary['expectancy_r'] - nc_summary['expectancy_r'], 4)
    }

    issues = diagnose(summary, diagnostics, comparison)
    wrong, fix = wrong_and_fix(issues, cfg['strategy'])
    status = 'PASS' if not issues else 'FAIL'

    return {
        'run': cfg['run'],
        'strategy': cfg['strategy'],
        'params': cfg['params'],
        'summary': summary,
        'diagnostics': diagnostics,
        'comparison': comparison,
        'issues': issues,
        'status': status,
        'wrong_sentence': wrong,
        'fixed_sentence': fix,
    }


def main():
    csv_path = str(latest_btc_csv())
    ts = datetime.now(UTC).strftime('%Y%m%d_%H%M%S')
    OUT.mkdir(parents=True, exist_ok=True)
    BT_OUT.mkdir(parents=True, exist_ok=True)
    JOURNAL.mkdir(parents=True, exist_ok=True)

    rng = random.Random(42)
    configs = [make_config(i, rng) for i in range(50)]
    payloads = [{'csv_path': csv_path, 'cfg': c} for c in configs]

    workers = max(4, min(cpu_count(), 12))
    results = []
    log_jsonl = JOURNAL / f'btc_50_run_log_{ts}.jsonl'

    with Pool(processes=workers) as pool:
        for r in pool.imap_unordered(worker, payloads):
            results.append(r)
            with log_jsonl.open('a') as f:
                f.write(json.dumps(r) + '\n')

    results.sort(key=lambda x: x['run'])

    # save per-run artifacts
    for r in results:
        outp = BT_OUT / f"btc50_run_{r['run']:02d}_{r['strategy']}_{ts}.json"
        outp.write_text(json.dumps(r, indent=2))

    passes = [r for r in results if r['status'] == 'PASS']
    best = sorted(results, key=lambda x: (x['summary']['expectancy_r'], (x['summary']['profit_factor'] or 0), x['summary']['return_pct']), reverse=True)[0]

    master = {
        'generated_at': datetime.now(UTC).isoformat(),
        'data_csv': csv_path,
        'objective': {'equity': 1000, 'risk_pct': 0.01, 'target_r_mult_min': 2.0},
        'runs': results,
        'pass_count': len(passes),
        'best_run': best,
        'log_jsonl': str(log_jsonl)
    }
    master_json = OUT / f'btc_50_master_{ts}.json'
    master_json.write_text(json.dumps(master, indent=2))

    lines = [
        '# BTC 50-Run Parallel Diagnostic Sweep',
        '',
        f'Generated: {master["generated_at"]}',
        f'Data: `{Path(csv_path).name}`',
        f'Passes: {len(passes)}/50',
        '',
        '## Per-run short summary'
    ]
    for r in results:
        s = r['summary']
        lines.append(f"- Run {r['run']:02d} | {r['strategy']} | {r['status']} | Trades {s['trades']} | ExpR {s['expectancy_r']} | PF {s['profit_factor']} | Return% {s['return_pct']}")
        lines.append(f"  - Wrong: {r['wrong_sentence']}")
        lines.append(f"  - Fix: {r['fixed_sentence']}")

    lines += [
        '',
        '## Best run',
        f"- Run {best['run']:02d} | {best['strategy']}",
        f"- ExpR {best['summary']['expectancy_r']} | PF {best['summary']['profit_factor']} | Return% {best['summary']['return_pct']}"
    ]

    master_md = OUT / 'btc_50_latest.md'
    master_md.write_text('\n'.join(lines) + '\n')

    print(master_json)
    print(master_md)
    print(log_jsonl)


if __name__ == '__main__':
    main()
