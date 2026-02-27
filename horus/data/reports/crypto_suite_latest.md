# Horus Crypto Paper Suite

Generated: 2026-02-27T14:20:37.156320+00:00

## Results
- BTCUSD | breakout_v1 | PF 0 | ExpR 0 | MaxDD 0 | Trades 0 | FAIL
- BTCUSD | mean_reversion_v1 | PF 0 | ExpR 0 | MaxDD 0 | Trades 0 | FAIL
- BTCUSD | breakout_crypto_v1 | PF 0.9825 | ExpR -0.0102 | MaxDD -1.1611 | Trades 2 | FAIL
- BTCUSD | mean_reversion_crypto_v1 | PF 0.3838 | ExpR -0.4359 | MaxDD -13.4249 | Trades 29 | FAIL
- ETHUSD | breakout_v1 | PF 0 | ExpR 0 | MaxDD 0 | Trades 0 | FAIL
- ETHUSD | mean_reversion_v1 | PF 0 | ExpR 0 | MaxDD 0 | Trades 0 | FAIL
- ETHUSD | breakout_crypto_v1 | PF 2.1708 | ExpR 0.4291 | MaxDD -1.0995 | Trades 3 | PASS
- ETHUSD | mean_reversion_crypto_v1 | PF 0.1741 | ExpR -0.7577 | MaxDD -18.3422 | Trades 23 | FAIL
- SOLUSD | breakout_v1 | PF 0 | ExpR 0 | MaxDD 0 | Trades 0 | FAIL
- SOLUSD | mean_reversion_v1 | PF 0 | ExpR 0 | MaxDD 0 | Trades 0 | FAIL
- SOLUSD | breakout_crypto_v1 | PF 0.184 | ExpR -0.7571 | MaxDD -4.5429 | Trades 6 | FAIL
- SOLUSD | mean_reversion_crypto_v1 | PF 0.206 | ExpR -0.698 | MaxDD -11.8665 | Trades 17 | FAIL

## What is working
- ETHUSD breakout_crypto_v1 passes current gate.

## What is not working
- BTCUSD breakout_v1: weak PF, non-positive expectancy, insufficient trades
- BTCUSD mean_reversion_v1: weak PF, non-positive expectancy, insufficient trades
- BTCUSD breakout_crypto_v1: weak PF, non-positive expectancy, insufficient trades
- BTCUSD mean_reversion_crypto_v1: weak PF, non-positive expectancy, drawdown too high
- ETHUSD breakout_v1: weak PF, non-positive expectancy, insufficient trades
- ETHUSD mean_reversion_v1: weak PF, non-positive expectancy, insufficient trades
- ETHUSD mean_reversion_crypto_v1: weak PF, non-positive expectancy, drawdown too high
- SOLUSD breakout_v1: weak PF, non-positive expectancy, insufficient trades
- SOLUSD mean_reversion_v1: weak PF, non-positive expectancy, insufficient trades
- SOLUSD breakout_crypto_v1: weak PF, non-positive expectancy, drawdown too high
- SOLUSD mean_reversion_crypto_v1: weak PF, non-positive expectancy, drawdown too high

## Immediate system issues found
- BTCUSD: strict templates produce zero trades on sampled Coinbase window (over-filtered for this market window).
- ETHUSD: strict templates produce zero trades on sampled Coinbase window (over-filtered for this market window).
- SOLUSD: strict templates produce zero trades on sampled Coinbase window (over-filtered for this market window).
