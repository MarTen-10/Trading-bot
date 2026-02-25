# Runbook — Backtesting System

1. Ingest historical OHLCV + corporate actions.
2. Normalize symbols and sessions (market/pre/post).
3. Apply strategy rules with fixed risk model.
4. Include slippage + fees.
5. Run in-sample and out-of-sample windows.
6. Export metrics: expectancy, PF, DD, win rate, avg R.
7. Store report in data/backtests/ and data/reports/.
