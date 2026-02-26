# Backtest Diagnostic Report

Status: **REVIEW**

## 1) Execution Integrity
- Bars loaded: 10938
- Entry signals: 437
- Exit signals: 1251
- Entries opened: 232
- Exits (stop/target/signal/eod): 145/50/37/0
- ATR fallback entries: 0

## 2) Strategy Performance
- Trades: 232
- Win rate: 0.2802
- Expectancy (R): -0.0512
- Avg win/Avg loss (R): 2.362/-0.9905
- Profit factor: 0.9282
- Net PnL: -138.2781
- Return %: -13.8278
- Max drawdown %: -26.1338

## 3) Cost Impact
- Expectancy with costs: -0.0512
- Expectancy without costs: 0.0709
- Cost impact on expectancy: -0.1221

## 4) Diagnosis
- ⚠️ Negative/zero expectancy (strategy edge not proven)
- ⚠️ Profit factor below threshold (<1.1)
- ⚠️ Drawdown high (< -5%)

## 5) Next Actions
- Re-tune entry/exit logic; test alternate strategy family.
