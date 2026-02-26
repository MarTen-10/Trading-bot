# Universal Backtester (Plug-and-Play)

Free data + no API key required (Yahoo chart endpoint).

## Supports
- Any ticker with Yahoo symbol support (stocks, ETFs, many crypto tickers)
- CSV input for any custom market feed
- Strategies: `sma_cross`, `breakout`, `mean_reversion_z`, `rsi_reversion`
- Backtest, walk-forward, and parameter optimization
- Costs model: `fee_bps`, `slippage_bps`

## Quick examples

### 1) Fetch data
```bash
python3 horus/backtester/universal_backtester.py fetch \
  --ticker AAPL --interval 1d --range 2y \
  --out horus/data/raw/AAPL_1d.csv
```

### 2) Backtest from ticker directly
```bash
python3 horus/backtester/universal_backtester.py backtest \
  --ticker AAPL --interval 1d --range 2y \
  --strategy sma_cross \
  --params '{"fast":20,"slow":50,"initial_equity":10000,"risk_pct":0.005,"stop_atr_mult":1.5,"target_r_mult":2.0}' \
  --costs '{"fee_bps":1.0,"slippage_bps":2.0}' \
  --out horus/data/backtests/AAPL_sma_cross.json
```

### 3) Walk-forward
```bash
python3 horus/backtester/universal_backtester.py walkforward \
  --csv horus/data/raw/AAPL_1d.csv \
  --strategy breakout \
  --params '{"lookback":20,"exit_lookback":10,"initial_equity":10000,"risk_pct":0.005}' \
  --out horus/data/backtests/AAPL_breakout_walkforward.json
```

### 4) Optimize params
```bash
python3 horus/backtester/universal_backtester.py optimize \
  --csv horus/data/raw/AAPL_1d.csv \
  --strategy sma_cross \
  --params '{"initial_equity":10000,"risk_pct":0.005}' \
  --grid '{"fast":[10,20,30],"slow":[50,100,150]}' \
  --out horus/data/backtests/AAPL_sma_opt.json
```

## Output
Each backtest JSON includes:
- `summary`: trades, win rate, expectancy, profit factor, return, drawdown
- `diagnostics`: execution integrity counters (signals, entries, exits, ATR fallbacks)
- `comparison`: with-cost vs no-cost expectancy impact
- `trades`: trade-by-trade ledger
- `equity_curve`: timestamped equity points

### Diagnostic formatter (human-readable)
```bash
python3 horus/backtester/format_report.py \
  --report horus/data/backtests/AAPL_sma_cross.json \
  --out-md horus/data/reports/AAPL_sma_cross_diagnostic.md
```
This report tells you whether failure is likely from:
- execution/integration issues, or
- weak strategy edge.

### Calibrated Monte Carlo (from actual backtest stats)
```bash
python3 horus/backtester/monte_carlo_calibrated.py \
  --backtest-report horus/data/backtests/AAPL_sma_cross.json \
  --out horus/data/reports/AAPL_sma_mc.json \
  --equity 1000 --risk-pct 0.01
```

### Promotion / disable gate engine
```bash
python3 horus/backtester/gate_engine.py \
  --backtest-report horus/data/backtests/AAPL_sma_cross.json \
  --mc-report horus/data/reports/AAPL_sma_mc.json \
  --out horus/data/reports/AAPL_sma_gate.json
```

### Acceptance tests (must pass)
```bash
python3 horus/backtester/acceptance_tests.py
```
Covers:
- deterministic replay parity
- risk governor enforcement
- rollback/reject trigger path
