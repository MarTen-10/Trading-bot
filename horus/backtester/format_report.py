#!/usr/bin/env python3
import argparse, json
from pathlib import Path


def verdict(summary, diag, comp):
    issues = []
    if diag.get('bars', 0) < 80:
        issues.append('Low data size (bars < 80)')
    if diag.get('entry_signals', 0) == 0:
        issues.append('No entry signals generated (strategy/params too strict or data mismatch)')
    if diag.get('entry_signals', 0) > 0 and summary.get('trades', 0) == 0:
        issues.append('Signals generated but no trades executed (execution logic issue possible)')
    if summary.get('trades', 0) < 3:
        issues.append('Too few trades for statistical confidence')
    if summary.get('expectancy_r', 0) <= 0:
        issues.append('Negative/zero expectancy (strategy edge not proven)')
    if summary.get('profit_factor') is not None and summary.get('profit_factor', 0) < 1.1:
        issues.append('Profit factor below threshold (<1.1)')
    if summary.get('max_drawdown_pct', 0) < -5:
        issues.append('Drawdown high (< -5%)')
    if comp.get('cost_impact_expectancy_r', 0) < -0.15:
        issues.append('Execution costs materially degrade expectancy')
    return issues


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--report', required=True)
    ap.add_argument('--out-md', required=True)
    args = ap.parse_args()

    r = json.loads(Path(args.report).read_text())
    s = r.get('summary', {})
    d = r.get('diagnostics', {})
    c = r.get('comparison', {})

    issues = verdict(s, d, c)
    status = 'PASS' if not issues else 'REVIEW'

    lines = []
    lines.append('# Backtest Diagnostic Report')
    lines.append('')
    lines.append(f"Status: **{status}**")
    lines.append('')
    lines.append('## 1) Execution Integrity')
    lines.append(f"- Bars loaded: {d.get('bars')}")
    lines.append(f"- Entry signals: {d.get('entry_signals')}")
    lines.append(f"- Exit signals: {d.get('exit_signals')}")
    lines.append(f"- Entries opened: {d.get('entries_opened')}")
    ex = d.get('exits', {})
    lines.append(f"- Exits (stop/target/signal/eod): {ex.get('stop',0)}/{ex.get('target',0)}/{ex.get('signal',0)}/{ex.get('eod',0)}")
    lines.append(f"- ATR fallback entries: {d.get('entries_fallback_no_atr',0)}")
    lines.append('')
    lines.append('## 2) Strategy Performance')
    lines.append(f"- Trades: {s.get('trades')}")
    lines.append(f"- Win rate: {s.get('win_rate')}")
    lines.append(f"- Expectancy (R): {s.get('expectancy_r')}")
    lines.append(f"- Avg win/Avg loss (R): {s.get('avg_win_r')}/{s.get('avg_loss_r')}")
    lines.append(f"- Profit factor: {s.get('profit_factor')}")
    lines.append(f"- Net PnL: {s.get('net_pnl')}")
    lines.append(f"- Return %: {s.get('return_pct')}")
    lines.append(f"- Max drawdown %: {s.get('max_drawdown_pct')}")
    lines.append('')
    lines.append('## 3) Cost Impact')
    lines.append(f"- Expectancy with costs: {c.get('with_costs_expectancy_r')}")
    lines.append(f"- Expectancy without costs: {c.get('no_cost_expectancy_r')}")
    lines.append(f"- Cost impact on expectancy: {c.get('cost_impact_expectancy_r')}")
    lines.append('')
    lines.append('## 4) Diagnosis')
    if issues:
        for x in issues:
            lines.append(f"- ⚠️ {x}")
    else:
        lines.append('- ✅ No critical execution/strategy warnings detected.')
    lines.append('')
    lines.append('## 5) Next Actions')
    if d.get('entry_signals', 0) == 0:
        lines.append('- Loosen trigger parameters or verify timeframe/data compatibility.')
    if s.get('trades', 0) < 3:
        lines.append('- Increase sample window and/or lower strictness to get sufficient trades.')
    if s.get('expectancy_r', 0) <= 0:
        lines.append('- Re-tune entry/exit logic; test alternate strategy family.')
    if c.get('cost_impact_expectancy_r', 0) < -0.15:
        lines.append('- Improve execution assumptions and reduce turnover.')
    if not issues:
        lines.append('- Promote to walk-forward + multi-ticker validation stage.')

    Path(args.out_md).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out_md).write_text('\n'.join(lines) + '\n')
    print(args.out_md)


if __name__ == '__main__':
    main()
