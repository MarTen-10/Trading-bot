from __future__ import annotations

from .models import Signal


def generate_signal(symbol: str, timeframe: str) -> Signal:
    """Stub strategy: replace with your real logic.

    Current behavior intentionally conservative: no-trade.
    """
    return Signal(kind="flat", confidence=0.0, reason=f"No strategy loaded for {symbol} {timeframe}")
