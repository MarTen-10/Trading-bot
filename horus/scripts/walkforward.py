#!/usr/bin/env python3
import argparse, csv, json, subprocess, tempfile
from pathlib import Path


def load_rows(path):
    with open(path, newline='') as f:
        return list(csv.DictReader(f))


def write_rows(path, rows):
    if not rows:
        return
    with open(path, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)


def run_bt(csv_path, strategy, out_path, fee_bps, slip_bps):
    cmd = [
        'python3', '/home/marten/.openclaw/workspace/horus/scripts/backtest_engine.py',
        '--csv', csv_path,
        '--strategy', strategy,
        '--out', out_path,
        '--fee-bps', str(fee_bps),
        '--slippage-bps', str(slip_bps),
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    return json.loads(Path(out_path).read_text())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--csv', required=True)
    ap.add_argument('--strategy', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--folds', type=int, default=4)
    ap.add_argument('--fee-bps', type=float, default=1.0)
    ap.add_argument('--slippage-bps', type=float, default=2.0)
    args = ap.parse_args()

    rows = load_rows(args.csv)
    n = len(rows)
    fold_size = max(50, n // args.folds)

    results = []
    with tempfile.TemporaryDirectory() as td:
        for i in range(args.folds):
            start = i * fold_size
            end = min((i + 1) * fold_size, n)
            if end - start < 30:
                continue
            test_rows = rows[start:end]
            csv_tmp = str(Path(td) / f'fold_{i}.csv')
            out_tmp = str(Path(td) / f'fold_{i}.json')
            write_rows(csv_tmp, test_rows)
            rep = run_bt(csv_tmp, args.strategy, out_tmp, args.fee_bps, args.slippage_bps)
            s = rep.get('summary', {})
            results.append({
                'fold': i,
                'rows': len(test_rows),
                'trades': s.get('trades', 0),
                'expectancy_r': s.get('expectancy_r', 0),
                'profit_factor': s.get('profit_factor', 0),
                'max_dd_r': s.get('max_dd_r', 0)
            })

    agg = {
        'folds': len(results),
        'avg_expectancy_r': round(sum(r['expectancy_r'] for r in results) / max(1, len(results)), 4),
        'avg_profit_factor': round(sum(r['profit_factor'] for r in results) / max(1, len(results)), 4),
        'worst_max_dd_r': min((r['max_dd_r'] for r in results), default=0),
    }

    out = {'walkforward': results, 'aggregate': agg}
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=2))
    print(json.dumps(agg))


if __name__ == '__main__':
    main()
