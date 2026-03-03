from __future__ import annotations

from dataclasses import dataclass
from .config import RiskConfig
from .models import Signal, PositionIntent


@dataclass
class AccountState:
    equity: float
    daily_pnl_pct: float
    mark_price: float


def can_trade(state: AccountState, cfg: RiskConfig) -> tuple[bool, str]:
    if state.daily_pnl_pct <= -abs(cfg.max_daily_loss_pct):
        return False, "daily loss limit breached"
    return True, "ok"


def build_intent(signal: Signal, state: AccountState, cfg: RiskConfig, symbol: str) -> PositionIntent | None:
    if signal.kind == "flat":
        return None

    risk_usd = state.equity * (cfg.per_trade_risk_pct / 100.0)
    max_notional = min(cfg.max_position_notional, state.equity * cfg.max_leverage)
    if state.mark_price <= 0:
        return None

    qty = max(0.0, min(risk_usd / (state.mark_price * 0.005), max_notional / state.mark_price))
    if qty <= 0:
        return None

    side = "buy" if signal.kind == "long" else "sell"
    sl_mult = 0.995 if side == "buy" else 1.005
    tp_mult = 1.01 if side == "buy" else 0.99

    return PositionIntent(
        side=side,
        qty=round(qty, 6),
        stop_loss=round(state.mark_price * sl_mult, 2),
        take_profit=round(state.mark_price * tp_mult, 2),
        leverage=min(3.0, cfg.max_leverage),
        symbol=symbol,
    )
