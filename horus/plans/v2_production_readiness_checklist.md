# Horus v2 Production Readiness Checklist (Mandatory)

Source: user-provided Patch Addendum + Master Build Directive (2026-02-26)

## A) Cost Calibration Loop
- [ ] Log fill quality fields: `mid_at_send,bid_at_send,ask_at_send,fill_px,fill_qty,maker_taker,fee`
- [ ] Compute `slippage_bps` per fill
- [ ] Daily p50/p75/p90 by instrument x hour x regime
- [ ] Export calibration JSON + parquet
- [ ] Backtester reads latest calibration (default p75)
- [ ] Incident alert: p90 > 2x 20-day median

## B) Regime Contract
- [ ] Implement deterministic regime labels:
  - CHOP_LOW_VOL
  - TREND_NORMAL
  - VOL_SHOCK
- [ ] Use only online features (ATR percentile, trend score, chop score)
- [ ] Strategy gate: breakout only in TREND_NORMAL

## C) Replay Parity
- [ ] Canonical event stream format with sequence IDs
- [ ] Deterministic signal_id hash
- [ ] Replay parity tests: signals/orders/trades hash equality
- [ ] Trade parity tolerance <= 0.02R in simulation mode

## D) Circuit Breakers
- [ ] Data stale >3s -> SAFE mode
- [ ] Latency p95 >1000ms -> SAFE + alert
- [ ] Spread shock rule
- [ ] Reject streak rule
- [ ] Fill mismatch reconciliation rule
- [ ] Daily PnL stop <= -3R

## E) Promotion + Tail Risk Gates
- [ ] Expectancy uplift >= +0.05R OOS
- [ ] PF >= 1.15 OOS
- [ ] DD degradation <= 2pp vs baseline
- [ ] MC p95 maxDD <= 20%
- [ ] Ruin proxy P(DD>=30% in 60d) <= 10%

## F) Correlation Cap
- [ ] Rolling 2-day correlation matrix (5m returns)
- [ ] Effective exposure cap using cluster penalty
- [ ] BTC/ETH cluster rule when corr>0.7

## G) Disable Protocol
- [ ] Disable setup if expectancy_50 < 0 for 2 consecutive daily evals
- [ ] Re-enable only after expectancy_20 > 0 and >=10 trades
- [ ] Governance event log for all disable/enable changes

## H) Acceptance Tests
- [x] Determinism test scaffolded
- [x] Risk governor non-bypass test scaffolded
- [x] Rollback trigger test scaffolded
- [ ] Reconciliation SAFE-mode test
- [ ] Calibration loop export/read test

## Build order lock
1) DB + ingestion
2) Event runtime parity
3) Breakout+retest implementation
4) Risk engine
5) Backtest + MC + gates
6) Paper runtime
7) Learning layer after >=500 labeled trades
