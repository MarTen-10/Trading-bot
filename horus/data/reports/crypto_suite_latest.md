# Horus Crypto Paper Suite

Generated: 2026-02-26T02:46:45.957996+00:00

## Results
- BTCUSD | breakout_v1 | PF 0 | ExpR 0 | MaxDD 0 | Trades 0 | FAIL
- BTCUSD | mean_reversion_v1 | PF 0 | ExpR 0 | MaxDD 0 | Trades 0 | FAIL
- BTCUSD | breakout_crypto_v1 | PF 2.2909 | ExpR 0.4352 | MaxDD -1.15 | Trades 9 | PASS
- BTCUSD | mean_reversion_crypto_v1 | PF 0.2596 | ExpR -0.5731 | MaxDD -10.5217 | Trades 17 | FAIL
- ETHUSD | breakout_v1 | PF 0 | ExpR 0 | MaxDD 0 | Trades 0 | FAIL
- ETHUSD | mean_reversion_v1 | PF 0 | ExpR 0 | MaxDD 0 | Trades 0 | FAIL
- ETHUSD | breakout_crypto_v1 | PF 2.1475 | ExpR 0.422 | MaxDD -1.2923 | Trades 12 | PASS
- ETHUSD | mean_reversion_crypto_v1 | PF 0.6451 | ExpR -0.2076 | MaxDD -5.2884 | Trades 16 | FAIL
- SOLUSD | breakout_v1 | PF 0 | ExpR 0 | MaxDD 0 | Trades 0 | FAIL
- SOLUSD | mean_reversion_v1 | PF 0 | ExpR 0 | MaxDD 0 | Trades 0 | FAIL
- SOLUSD | breakout_crypto_v1 | PF 1.5694 | ExpR 0.2639 | MaxDD -2.2597 | Trades 12 | PASS
- SOLUSD | mean_reversion_crypto_v1 | PF 0.1834 | ExpR -0.6614 | MaxDD -8.112 | Trades 11 | FAIL

## What is working
- BTCUSD breakout_crypto_v1 passes current gate.
- ETHUSD breakout_crypto_v1 passes current gate.
- SOLUSD breakout_crypto_v1 passes current gate.

## What is not working
- BTCUSD breakout_v1: weak PF, non-positive expectancy, insufficient trades
- BTCUSD mean_reversion_v1: weak PF, non-positive expectancy, insufficient trades
- BTCUSD mean_reversion_crypto_v1: weak PF, non-positive expectancy, drawdown too high
- ETHUSD breakout_v1: weak PF, non-positive expectancy, insufficient trades
- ETHUSD mean_reversion_v1: weak PF, non-positive expectancy, insufficient trades
- ETHUSD mean_reversion_crypto_v1: weak PF, non-positive expectancy, drawdown too high
- SOLUSD breakout_v1: weak PF, non-positive expectancy, insufficient trades
- SOLUSD mean_reversion_v1: weak PF, non-positive expectancy, insufficient trades
- SOLUSD mean_reversion_crypto_v1: weak PF, non-positive expectancy, drawdown too high

## Immediate system issues found
- BTCUSD: strict templates produce zero trades on sampled Coinbase window (over-filtered for this market window).
- ETHUSD: strict templates produce zero trades on sampled Coinbase window (over-filtered for this market window).
- SOLUSD: strict templates produce zero trades on sampled Coinbase window (over-filtered for this market window).
