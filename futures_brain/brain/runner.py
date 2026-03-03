from __future__ import annotations

from .config import load_config
from .exchanges import get_exchange, journal
from .risk import AccountState, can_trade, build_intent
from .strategy import generate_signal


def run_once(config_path: str = "config/default.yaml") -> dict:
    cfg = load_config(config_path)

    if cfg.runtime.kill_switch:
        out = {"status": "blocked", "reason": "kill switch enabled"}
        journal({"event": "run_blocked", **out})
        return out

    ex = get_exchange(cfg.runtime.exchange)
    mark = ex.get_mark_price(cfg.runtime.symbol)

    # TODO: replace equity/daily_pnl with live account fetch
    state = AccountState(equity=10_000.0, daily_pnl_pct=0.0, mark_price=mark)

    ok, why = can_trade(state, cfg.risk)
    if not ok:
        out = {"status": "blocked", "reason": why}
        journal({"event": "run_blocked", **out})
        return out

    sig = generate_signal(cfg.runtime.symbol, cfg.runtime.timeframe)
    intent = build_intent(sig, state, cfg.risk, cfg.runtime.symbol)

    if intent is None:
        out = {"status": "no_trade", "signal": sig.kind, "reason": sig.reason}
        journal({"event": "run_no_trade", **out})
        return out

    if cfg.runtime.mode == "live" and not cfg.runtime.confirm_live:
        out = {"status": "blocked", "reason": "confirm_live is false in live mode"}
        journal({"event": "run_blocked", **out})
        return out

    order = ex.place_order(intent, cfg.runtime.mode)
    out = {"status": "ok", "signal": sig.kind, "order": order}
    journal({"event": "run_order", **out})
    return out
