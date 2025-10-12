# === src/strategy_crypto.py (PURE MEAN REVERSION SCALPER LOGIC) ===
from dataclasses import dataclass
import math
import pandas as pd


@dataclass
class Vote:
    score: int
    reason: str
    confidence: float = 1.0


# --- UTILITY/FILTER FUNCTIONS (Copied for dependency) ---


def volatility_ok(r, params):
    """Checks for minimum volatility (ATR/Close) to ensure market is tradable."""
    ratio = r["ATR"] / r["Close"]
    min_ratio = params.get("atr_min_ratio", 0.003)
    return ratio > min_ratio


def volume_ok(r, params):
    """Checks for volume spike relative to 20-bar average."""
    vol_mult_min = params.get("vol_mult_min", 1.5)
    vol_ratio = r["Volume"] / max(r["VolMA20"], 1)
    return vol_ratio >= vol_mult_min


def adx_strength(r, params):
    """Confidence filter: High confidence when ADX is LOW (raging market)."""
    adx_min = params.get("adx_min", 15)
    adx_max = params.get("adx_max", 30)
    adx = r["ADX"]
    # We want ADX in the non-trending range (below 30)
    confidence = min(max((adx_max - adx) / (adx_max - adx_min), 0), 1)
    return confidence


# ==================================
# === HIGH-FREQUENCY SCALPING LOGIC (Pattern-Driven) ===
# ==================================


def check_mr_setup(r, params, trend_dir):
    """
    Checks for the overextended conditions required for a Mean Reversion setup.
    This replaces the old crypto_pullback_mr function.
    """
    rsi_os = params.get("rsi_oversold", 25)
    rsi_ob = params.get("rsi_overbought", 75)

    volume_surge = volume_ok(r, params)

    # --- BULLISH SETUP (Oversold Extreme) ---
    bullish_setup = (
        r["RSI"] < rsi_os
        and r["Close"] < r["BB_LOWER"]  # Below lower BB
        and r["PRICE_Z_SCORE"] < -1.8  # Extreme low Z-score
        and r["ADX"] < 30  # Must not be strongly trending
    )

    # --- BEARISH SETUP (Overbought Extreme) ---
    bearish_setup = (
        r["RSI"] > rsi_ob
        and r["Close"] > r["BB_UPPER"]  # Above upper BB
        and r["PRICE_Z_SCORE"] > 1.8  # Extreme high Z-score
        and r["ADX"] < 30  # Must not be strongly trending
    )

    # --- Pattern Simulation: RSI Divergence (A simple check over 2 bars) ---
    # Low price, higher RSI = Bullish Divergence (New low in price, but RSI bottomed 1 bar ago)
    bullish_div = r["Low"] < r.get("Low_PREV", r["Low"]) and r["RSI"] > r.get(
        "RSI_PREV", r["RSI"]
    )
    # High price, lower RSI = Bearish Divergence
    bearish_div = r["High"] > r.get("High_PREV", r["High"]) and r["RSI"] < r.get(
        "RSI_PREV", r["RSI"]
    )

    score = 0
    reason = "SCALPER_NONE"

    if bullish_setup:
        score += 3
        if volume_surge:
            score += 1
        if bullish_div:
            score += 1
        reason = "MR_LONG_SETUP"

    elif bearish_setup:
        score -= 3
        if volume_surge:
            score -= 1
        if bearish_div:
            score -= 1
        reason = "MR_SHORT_SETUP"

    # Confidence is driven by the inverse of trend strength (ADX)
    confidence = adx_strength(r, params) * abs(score) / 5.0

    # Trade only if score is high enough (e.g., 4 points based on the blueprint)
    if abs(score) >= 4:
        return Vote(math.copysign(1, score), reason, confidence)

    return Vote(0, reason, 0.0)


# 🚨 Strategy functions must match the expected imports in backtest_multi.py 🚨


# Pure Mean Reversion Logic is consolidated into check_mr_setup
def crypto_pullback_mr(r, params, trend_dir):
    """MTFA entry point for Mean Reversion Scalper."""
    return check_mr_setup(r, params, trend_dir)


# The crypto_momentum_trend function is unused but must exist for compliance
def crypto_momentum_trend(r, params):
    """Disabled: We are focusing only on Mean Reversion."""
    return Vote(0, "SCALPER_MOMO_DISC", 0.0)


# NOTE: You must also update src/strategy_stock.py to contain similar logic
# and utility functions for the stock backtest path to function.
