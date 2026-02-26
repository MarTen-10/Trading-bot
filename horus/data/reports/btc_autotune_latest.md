# BTC Autotune Backtest Master Report

Generated: 2026-02-26T01:24:43.877687+00:00
Data: `BTCUSD_15mo_1h_20260226_012427.csv`

## Objective
- Starting equity: $1,000
- Risk per trade: 1%
- Target reward/risk: >= 2.0

## Run-by-run status
- Run 1 | breakout | FAIL | Trades 232 | ExpR -0.0512 | PF 0.9282 | Return% -13.8278
  - Fix applied: baseline run
- Run 2 | rsi_reversion | FAIL | Trades 321 | ExpR 0.0386 | PF 1.056 | Return% 8.7029
  - Fix applied: Switch strategy family to mean-reversion RSI when breakout underperforms.
- Run 3 | sma_cross | PASS | Trades 78 | ExpR 0.2824 | PF 1.4488 | Return% 23.2735
  - Fix applied: Switch to trend-following crossover when reversion/breakout quality is poor.

## Best run
- Strategy: sma_cross
- Params: `{"initial_equity": 1000, "risk_pct": 0.01, "target_r_mult": 2.5, "stop_atr_mult": 1.0, "fast": 30, "slow": 80}`
- Trades: 78
- Win rate: 0.3974
- Expectancy (R): 0.2824
- Profit factor: 1.4488
- Return %: 23.2735
- Net PnL: 232.7348
- Max DD %: -8.8482
- Diagnostic: `/home/marten/.openclaw/workspace/horus/data/reports/btc_autotune_diag_run3_sma_cross_fix_20260226_012427.md`

## Verdict
- ✅ Pass criteria met for at least one run. Ready for joint first run review.
