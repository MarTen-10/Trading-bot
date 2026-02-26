# Backtest Diagnostic Report

Status: **REVIEW**

## 1) Execution Integrity
- Bars loaded: 251
- Entry signals: 3
- Exit signals: 2
- Entries opened: 3
- Exits (stop/target/signal/eod): 2/0/0/1
- ATR fallback entries: 0

## 2) Strategy Performance
- Trades: 3
- Win rate: 0.3333
- Expectancy (R): -0.4143
- Avg win/Avg loss (R): 0.7754/-1.0091
- Profit factor: 0.3842
- Net PnL: -62.2806
- Return %: -0.6228
- Max drawdown %: -1.0066

## 3) Cost Impact
- Expectancy with costs: -0.4143
- Expectancy without costs: -0.4029
- Cost impact on expectancy: -0.0114

## 4) Diagnosis
- ⚠️ Negative/zero expectancy (strategy edge not proven)
- ⚠️ Profit factor below threshold (<1.1)

## 5) Next Actions
- Re-tune entry/exit logic; test alternate strategy family.
