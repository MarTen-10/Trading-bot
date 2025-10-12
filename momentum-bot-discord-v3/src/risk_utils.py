import datetime
import logging


def get_risk_params(global_cfg, symbol):
    """Return correct ATR multipliers based on asset type."""
    is_crypto = "USD" in symbol and len(symbol) > 6  # crude crypto check
    base = global_cfg["risk"]

    if is_crypto:
        r = base["crypto"]
    else:
        r = base["stock"]

    return (r["stop_atr_mult"], r["tp_atr_mult"], r["trail_atr_mult"], is_crypto)


def is_blackout(global_cfg, symbol):
    """Check if weekend blackout applies (for crypto)."""
    stop_trading = False
    is_crypto = "USD" in symbol and len(symbol) > 6
    now = datetime.datetime.utcnow()

    if is_crypto and global_cfg["risk"]["crypto"].get("weekend_blackout", False):
        if now.weekday() == 6 or (now.weekday() == 0 and now.hour < 12):
            logging.info(f"Weekend blackout active for {symbol}")
            stop_trading = True

    return stop_trading
