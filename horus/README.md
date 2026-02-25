# Horus — Quant Day-Trading Agent

Primary objective: maximize net profit while preserving capital.

## Scope (current)
- Paper trading only
- Backtesting + validation
- Signal generation + journaling
- No live order execution without explicit human approval

## Status
- Environment scaffolded
- Risk policy defined
- Master plan initialized
- Backtesting v1 scripts + strategy templates in place

## Quick run
```bash
python3 horus/scripts/generate_sample_data.py
python3 horus/scripts/backtest_engine.py \
  --csv horus/data/raw/sample_5m.csv \
  --strategy horus/strategies/breakout_v1.json \
  --out horus/data/backtests/sample_breakout_report.json
python3 horus/scripts/paper_session.py
python3 horus/scripts/report_daily.py
python3 horus/scripts/learn_loop.py
```

## Validation (must pass)
```bash
python3 horus/scripts/validate_horus.py
```

## Learning + logging outputs
- Trade ledger: `horus/data/journal/trade_ledger.jsonl`
- Signal ledger: `horus/data/journal/signal_ledger.jsonl`
- Learning state: `horus/data/journal/learning_state.json`
- Latest lessons: `horus/data/journal/lessons_latest.md`
