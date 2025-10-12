# === src/indicators.py (Indicators for Pattern Scalping) ===
import pandas as pd
import ta
import numpy as np

# We assume standard settings based on the blueprint for Bollinger Bands and ATR
BB_WINDOW = 20
BB_STD = 2


def add_indicators(
    df_ltf: pd.DataFrame, df_htf: pd.DataFrame = None, rsi_period=14, ema_s=20, ema_l=50
):
    """
    Calculates all required indicators for the Mean Reversion Scalper,
    including Bollinger Bands, RSI Cross checks, and VWAP.
    """
    out = df_ltf.copy()

    if out is None or out.empty or len(out) < 20:
        return pd.DataFrame()

    # --- Trend & Mean Indicators ---
    out["EMA_S"] = ta.trend.ema_indicator(out["Close"], window=ema_s, fillna=False)
    out["EMA_L"] = ta.trend.ema_indicator(out["Close"], window=ema_l, fillna=False)
    out["RSI"] = ta.momentum.rsi(out["Close"], window=rsi_period, fillna=False)

    # --- Bollinger Bands (Volatility & Range) ---
    bb = ta.volatility.BollingerBands(
        out["Close"], window=BB_WINDOW, window_dev=BB_STD, fillna=False
    )
    out["BB_UPPER"] = bb.bollinger_hband()
    out["BB_LOWER"] = bb.bollinger_lband()

    # --- Price Extremity Check (Z-Score & RSI History) ---
    out["PRICE_Z_SCORE"] = (
        out["Close"] - out["Close"].rolling(BB_WINDOW).mean()
    ) / out["Close"].rolling(BB_WINDOW).std(ddof=0)
    out["RSI_PREV"] = out["RSI"].shift(1)  # Used for simple cross detection
    out["RSI_PREV2"] = out["RSI"].shift(2)  # Used for divergence/pattern check

    if len(out) < 14:
        return pd.DataFrame()

    # --- Momentum & Volatility ---
    macd = ta.trend.MACD(out["Close"])
    out["MACD"] = macd.macd()
    out["MACD_SIG"] = macd.macd_signal()

    out["ADX"] = ta.trend.adx(
        out["High"], out["Low"], out["Close"], window=14, fillna=False
    )
    out["ATR"] = ta.volatility.average_true_range(
        out["High"], out["Low"], out["Close"], window=14, fillna=False
    )

    # --- Volume Check ---
    out["VolMA20"] = out["Volume"].rolling(20).mean()
    out["ROC5"] = out["Close"].pct_change(5) * 100.0

    # --- Institutional Benchmark ---
    out["VWAP"] = (
        out["Volume"] * (out["High"] + out["Low"] + out["Close"]) / 3
    ).cumsum() / out["Volume"].cumsum()

    # We now look for trades starting at index 50, so we drop NaNs.
    out.dropna(inplace=True)
    return out


def last_row(df: pd.DataFrame):
    return df.iloc[-1].to_dict() if len(df) else {}
