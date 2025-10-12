# Momentum Bot (Discord Alerts, Paper/Live via Alpaca)

A rule-based, multi-strategy momentum trading bot for U.S. stocks and crypto.

## Quick Start (Paper)
1) Python 3.10+ installed.
2) Create venv & install deps:
   ```
   python -m venv .venv
   .venv\Scripts\activate    # Windows
   pip install -r requirements.txt
   ```
3) Copy `.env.example` → `.env`, fill Alpaca paper keys and `DISCORD_WEBHOOK_URL`.
4) Optional sanity backtest:
   ```
   python -m src.backtest --symbol NVDA --tf 15m --days 120
   ```
5) Run bot:
   ```
   python -m src.run --tf 15m --interval 300
   ```

## Discord Alerts
Create a webhook (Server Settings → Integrations → Webhooks) and put the URL in `.env` as `DISCORD_WEBHOOK_URL=`.
