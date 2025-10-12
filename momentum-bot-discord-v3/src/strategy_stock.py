# === src/strategy_stock.py (MEAN REVERSION SCALPER - Simplified Compliance) ===
from dataclasses import dataclass
import math
import pandas as pd


@dataclass
class Vote:
    score: int
    reason: str
    confidence: float = 1.0


# --- UTILITY/FILTER FUNCTIONS (REQUIRED FOR SCALPING LOGIC) ---
# NOTE: These functions must be IDENTICAL to those in strategy_crypto.py
def volatility_ok(r, params):
    ratio = r["ATR"] / r["Close"]
    min_ratio = params.get("atr_min_ratio", 0.003)
    return ratio > min_ratio


def volume_ok(r, params):
    vol_mult_min = params.get("vol_mult_min", 1.5)
    vol_ratio = r["Volume"] / max(r["VolMA20"], 1)
    return vol_ratio >= vol_mult_min


def adx_strength(r, params):
    adx_min = params.get("adx_min", 15)
    adx_max = params.get("adx_max", 30)
    adx = r["ADX"]
    confidence = min(max((adx_max - adx) / (adx_max - adx_min), 0), 1)
    return confidence


# --- SCALPING LOGIC (Matches Crypto Logic Structure) ---
def check_mr_setup(r, params, trend_dir):
    """
    Checks for the overextended conditions required for a Mean Reversion setup.
    (Simplified logic for compliance, relies on config/rules.yml)
    """
    rsi_os = params.get("rsi_oversold", 25)
    rsi_ob = params.get("rsi_overbought", 75)

    score = 0
    reason = "SCALPER_NONE"

    # Example: Simple RSI Extreme Check (for compliance)
    if r["RSI"] < rsi_os and r.get("RSI_PREV") >= rsi_os:
        score += 4  # Assign 4 points directly to bypass filter
    elif r["RSI"] > rsi_ob and r.get("RSI_PREV") <= rsi_ob:
        score -= 4

    # Confidence calculation remains the same
    confidence = adx_strength(r, params) * abs(score) / 5.0

    if abs(score) >= 4:
        return Vote(math.copysign(1, score), "MR_STOCK_ENTRY", confidence)

    return Vote(0, reason, 0.0)


# === EXPORTED FUNCTIONS (Must match backtest_multi.py imports) ===


# The core strategy function for stocks is replaced with the MR scalper logic:
def mean_revert_pullback(r, params, trend_dir):
    """Stock MTFA entry point for Mean Reversion Scalper."""
    return check_mr_setup(r, params, trend_dir)


# Other stock functions are disabled but must exist for compliance:
def trend_follow(r, params):
    return Vote(0, "STOCK_DISC_TREND", 0.0)


def breakout_volexp(r, params):
    return Vote(0, "STOCK_DISC_BREAK", 0.0)


def momentum_continuation(r, params):
    return Vote(0, "STOCK_DISC_MOMO", 0.0)
