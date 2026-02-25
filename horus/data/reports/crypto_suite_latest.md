# Horus Crypto Paper Suite

Generated: 2026-02-25T14:47:12.189852+00:00

## Results
- BTCUSD | breakout_v1 | PF 0 | ExpR 0 | MaxDD 0 | Trades 0 | FAIL
- BTCUSD | mean_reversion_v1 | PF 0 | ExpR 0 | MaxDD 0 | Trades 0 | FAIL
- BTCUSD | breakout_crypto_v1 | PF 1.7455 | ExpR 0.2878 | MaxDD -1.15 | Trades 5 | PASS
- BTCUSD | mean_reversion_crypto_v1 | PF 0.4162 | ExpR -0.385 | MaxDD -10.0916 | Trades 24 | FAIL
- ETHUSD | breakout_v1 | PF 0 | ExpR 0 | MaxDD 0 | Trades 0 | FAIL
- ETHUSD | mean_reversion_v1 | PF 0 | ExpR 0 | MaxDD 0 | Trades 0 | FAIL
- ETHUSD | breakout_crypto_v1 | PF 0.9843 | ExpR -0.0087 | MaxDD -1.2923 | Trades 8 | FAIL
- ETHUSD | mean_reversion_crypto_v1 | PF 0.5747 | ExpR -0.2665 | MaxDD -5.2884 | Trades 17 | FAIL
- SOLUSD | breakout_v1 | PF 0 | ExpR 0 | MaxDD 0 | Trades 0 | FAIL
- SOLUSD | mean_reversion_v1 | PF 0 | ExpR 0 | MaxDD 0 | Trades 0 | FAIL
- SOLUSD | breakout_crypto_v1 | PF 1.0395 | ExpR 0.022 | MaxDD -1.1774 | Trades 6 | FAIL
- SOLUSD | mean_reversion_crypto_v1 | PF 0.616 | ExpR -0.2358 | MaxDD -4.5574 | Trades 13 | FAIL

## What is working
- BTCUSD breakout_crypto_v1 passes current gate.

## What is not working
- BTCUSD breakout_v1: weak PF, non-positive expectancy, insufficient trades
- BTCUSD mean_reversion_v1: weak PF, non-positive expectancy, insufficient trades
- BTCUSD mean_reversion_crypto_v1: weak PF, non-positive expectancy, drawdown too high
- ETHUSD breakout_v1: weak PF, non-positive expectancy, insufficient trades
- ETHUSD mean_reversion_v1: weak PF, non-positive expectancy, insufficient trades
- ETHUSD breakout_crypto_v1: weak PF, non-positive expectancy
- ETHUSD mean_reversion_crypto_v1: weak PF, non-positive expectancy, drawdown too high
- SOLUSD breakout_v1: weak PF, non-positive expectancy, insufficient trades
- SOLUSD mean_reversion_v1: weak PF, non-positive expectancy, insufficient trades
- SOLUSD breakout_crypto_v1: weak PF
- SOLUSD mean_reversion_crypto_v1: weak PF, non-positive expectancy, drawdown too high

## Immediate system issues found
- BTCUSD: strict templates produce zero trades on sampled Coinbase window (over-filtered for this market window).
- ETHUSD: strict templates produce zero trades on sampled Coinbase window (over-filtered for this market window).
- SOLUSD: strict templates produce zero trades on sampled Coinbase window (over-filtered for this market window).
