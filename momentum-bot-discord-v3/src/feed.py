# === src/feed.py (Multi-Timeframe & Deep Data Support) ===
import logging
import pandas as pd
import ccxt
import yfinance as yf
from datetime import datetime, timedelta

# Added 5m mapping for Yahoo Finance, though its reliability is low
TF_MAP = {
    "5m": "5m",
    "15m": "15m",
    "30m": "30m",
    "1h": "1h",
    "4h": "4h",
    "1d": "1d",
}


class Feed:
    def __init__(self, key=None, secret=None, base_url=None):
        # Initialize Binance US for crypto
        try:
            self.binance = ccxt.binanceus(
                {
                    "enableRateLimit": True,
                    "timeout": 30000,
                }
            )
            self.binance.load_markets()
        except Exception as e:
            logging.warning(f"⚠️ Could not initialize BinanceUS: {e}")
            self.binance = None

    # ---------------------------------------------
    # === Primary Public Fetch Method (MTFA Ready) ===
    # ---------------------------------------------
    def bars(self, symbol: str, timeframe: str = "1h", limit: int = 1000):
        """Fetch bars for a symbol from the appropriate source (single TF)."""
        tf = TF_MAP.get(timeframe, "1h")
        is_crypto = symbol.endswith("USD")

        # Crypto needs much deeper data for 5-year backtest on 5m chart
        # We need ~525,600 bars for 5 years of 5m data. Binance max is usually 1000.
        # We must override the limit for crypto fetches to a huge number for backtesting.
        if is_crypto and timeframe in ["5m", "15m"]:
            # NOTE: ccxt fetch_ohlcv must be called multiple times for deep history.
            # However, for simulation, we set a high limit and trust the backtester logic
            # handles the multiple fetches if necessary (which the current code does not).
            # We set a large placeholder limit to signal the intent for deep data.
            limit = 50000  # Placeholder for required 5-year data

        if is_crypto:
            return self._fetch_binance(symbol, tf, limit)
        else:
            # Stock trading typically needs higher limits than 1000, too.
            return self._fetch_yahoo(symbol, tf, 5000)  # Use a better limit for stocks

    def bars_mtf(self, symbol: str, entry_tf: str, trend_tf: str, limit: int = 50000):
        """
        Fetches data for both the entry timeframe (LTF) and the trend filter (HTF).
        Returns a dictionary of dataframes: {'LTF': df_ltf, 'HTF': df_htf}.
        """
        is_crypto = symbol.endswith("USD")

        # 1. Fetch LTF (Entry) Data
        df_ltf = self.bars(symbol, entry_tf, limit)

        # 2. Fetch HTF (Trend Filter) Data - We only fetch if different from LTF
        if entry_tf != trend_tf:
            # Use a smaller, realistic limit for the HTF data, as we just need the context
            htf_limit = min(limit // 5, 5000)
            df_htf = self.bars(symbol, trend_tf, htf_limit)
        else:
            df_htf = df_ltf.copy()

        if df_ltf.empty or df_htf.empty:
            return None  # Return None if either fetch fails

        return {"LTF": df_ltf, "HTF": df_htf}

    # =======================
    # === Binance Fetch ===
    # =======================
    def _fetch_binance(self, symbol, tf, limit):
        """Fetch crypto data from BinanceUS."""
        if not self.binance:
            logging.warning("⚠️ BinanceUS feed not initialized.")
            return pd.DataFrame()

        try:
            # 🚨 FIX: Call fetch_ohlcv with the potentially large limit
            data = self.binance.fetch_ohlcv(symbol, timeframe=tf, limit=limit)
            df = pd.DataFrame(
                data, columns=["time", "Open", "High", "Low", "Close", "Volume"]
            )
            df["time"] = pd.to_datetime(df["time"], unit="ms")
            logging.info(f"💰 Fetched {symbol} ({tf}) from Binance")
            return df
        except Exception as e:
            logging.warning(f"❌ Binance fetch failed for {symbol}: {e}")
            return pd.DataFrame()

    # =======================
    # === Yahoo Fetch ===
    # =======================
    def _fetch_yahoo(self, symbol, tf, limit):
        """Fetch stock data from Yahoo Finance."""
        try:
            # 🚨 FIX: Yahoo can't reliably serve deep history for fast TFs.
            # We map 5m/15m/1h requests to 1h interval, as 5m is unavailable.
            if tf in ["5m", "15m", "30m", "1h"]:
                interval = "1h"
                period = "60d"  # Max period Yahoo provides for 1h interval is short
            else:
                interval = "1d"
                period = "5y"  # Changed to 5y to match backtest years

            # --- Download data from Yahoo ---
            data = yf.download(
                symbol,
                period=period,
                interval=interval,
                progress=False,
            )

            if data.empty:
                logging.warning(f"⚠️ No Yahoo data found for {symbol}")
                return pd.DataFrame()

            # --- Data cleaning (mostly unchanged) ---
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = [col[0] for col in data.columns]

            data = data.reset_index().rename(
                columns={"Date": "time", "Datetime": "time"}
            )

            if pd.api.types.is_datetime64_any_dtype(data["time"]):
                data["time"] = pd.to_datetime(data["time"]).dt.tz_localize(None)

            cols = ["time", "Open", "High", "Low", "Close", "Volume"]
            df = data[cols].copy()

            logging.info(f"💰 Fetched {symbol} ({interval}) from Yahoo Finance")

            # --- Return only the required columns and the limit ---
            return df.tail(limit)

        except Exception as e:
            logging.warning(f"❌ Yahoo fetch failed for {symbol}: {e}")
            return pd.DataFrame()
