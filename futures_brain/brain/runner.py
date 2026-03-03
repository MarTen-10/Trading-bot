from __future__ import annotations

from .config import load_config
from .exchanges import get_exchange, journal
from .risk import AccountState, can_trade, build_intent
from .strategy import generate_signal
from .models import Signal, TradingViewAlert


def _execute_signal(
    sig: Signal,
    config_path: str = "config/default.yaml",
    override_exchange: str | None = None,
    override_symbol: str | None = None,
) -> dict:
    cfg = load_config(config_path)
    exchange_name = override_exchange or cfg.runtime.exchange
    symbol = override_symbol or cfg.runtime.symbol

    if cfg.runtime.kill_switch:
        out = {"status": "blocked", "reason": "kill switch enabled"}
        journal({"event": "run_blocked", **out})
        return out

    ex = get_exchange(exchange_name)
    mark = ex.get_mark_price(symbol)

    # TODO: replace equity/daily_pnl with live account fetch
    state = AccountState(equity=10_000.0, daily_pnl_pct=0.0, mark_price=mark)

    ok, why = can_trade(state, cfg.risk)
    if not ok:
        out = {"status": "blocked", "reason": why}
        journal({"event": "run_blocked", **out})
        return out

    intent = build_intent(sig, state, cfg.risk, symbol)
    if intent is None:
        out = {"status": "no_trade", "signal": sig.kind, "reason": sig.reason}
        journal({"event": "run_no_trade", **out})
        return out

    if cfg.runtime.mode == "live" and not cfg.runtime.confirm_live:
        out = {"status": "blocked", "reason": "confirm_live is false in live mode"}
        journal({"event": "run_blocked", **out})
        return out

    order = ex.place_order(intent, cfg.runtime.mode)
    out = {"status": "ok", "signal": sig.kind, "order": order, "exchange": exchange_name}
    journal({"event": "run_order", **out})
    return out


def run_once(config_path: str = "config/default.yaml") -> dict:
    cfg = load_config(config_path)
    sig = generate_signal(cfg.runtime.symbol, cfg.runtime.timeframe)
    return _execute_signal(sig, config_path=config_path)


def run_from_tv_alert(alert: TradingViewAlert, config_path: str = "config/default.yaml") -> dict:
    kind = "flat"
    if alert.side == "buy":
        kind = "long"
    elif alert.side == "sell":
        kind = "short"

    sig = Signal(
        kind=kind,
        confidence=0.7,
        reason=f"tv:{alert.strategy_id}:{alert.side}",
    )
    return _execute_signal(
        sig,
        config_path=config_path,
        override_exchange=alert.exchange,
        override_symbol=alert.symbol,
    )
