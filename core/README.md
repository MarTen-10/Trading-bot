# Quant Micro-Firm Core

Modules:
- `data/` → ingestion + normalization + candle correctness
- `features/` → deterministic feature pipeline (EMA/ATR/volume)
- `backtest/` → event-driven backtester with fees/slippage
- `risk/` → Ma’at enforcement gate
- `execution/` → Horus order routing/reconciliation
- `contracts/` → JSON schemas for inter-agent packets

Invariant:
No order may be routed unless a valid `risk_ticket` is attached and verified.
