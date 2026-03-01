from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class PaperPosition:
    trade_id: str
    symbol: str
    side: str
    size: float
    entry_price: float
    stop_price: float
    target_price: float
    fee_paid: float
    slippage_paid: float
    opened_at: datetime


@dataclass
class PaperEngine:
    fee_bps: float = 4.0
    slippage_bps: float = 2.0
    starting_equity: float = 10_000.0
    mode: str = "paper"
    equity: float = field(init=False)
    realized_pnl: float = field(default=0.0, init=False)
    equity_curve: list[dict[str, Any]] = field(default_factory=list, init=False)
    open_positions: dict[str, PaperPosition] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        self.equity = self.starting_equity
        self._record_equity("boot")

    def open_trade(
        self,
        *,
        trade_id: str,
        symbol: str,
        side: str,
        size: float,
        mid_price: float,
        stop_price: float,
        target_price: float,
    ) -> dict[str, Any]:
        self._ensure_paper_mode()

        fill_price, slippage = self._fill_price(mid_price, side, size)
        entry_notional = fill_price * size
        fees = self._fees(entry_notional)

        position = PaperPosition(
            trade_id=trade_id,
            symbol=symbol,
            side=side.upper(),
            size=size,
            entry_price=fill_price,
            stop_price=stop_price,
            target_price=target_price,
            fee_paid=fees,
            slippage_paid=slippage,
            opened_at=datetime.now(UTC),
        )
        self.open_positions[trade_id] = position
        self.realized_pnl -= fees
        self.equity -= fees
        self._record_equity("open_trade")

        return {
            "trade_id": trade_id,
            "status": "OPEN",
            "fill_price": fill_price,
            "fees": fees,
            "slippage": slippage,
            "mode": self.mode,
        }

    def on_price_tick(self, symbol: str, market_price: float) -> list[dict[str, Any]]:
        self._ensure_paper_mode()
        closed: list[dict[str, Any]] = []
        for trade_id, pos in list(self.open_positions.items()):
            if pos.symbol != symbol:
                continue
            if self._hit_stop(pos, market_price):
                closed.append(self.close_trade(trade_id=trade_id, exit_mid=pos.stop_price, reason="STOP"))
            elif self._hit_target(pos, market_price):
                closed.append(self.close_trade(trade_id=trade_id, exit_mid=pos.target_price, reason="TARGET"))
        return closed

    def close_trade(self, *, trade_id: str, exit_mid: float, reason: str = "MANUAL") -> dict[str, Any]:
        self._ensure_paper_mode()
        pos = self.open_positions.pop(trade_id)
        exit_side = "SELL" if pos.side in {"BUY", "LONG"} else "BUY"
        exit_fill, slippage = self._fill_price(exit_mid, exit_side, pos.size)

        entry_notional = pos.entry_price * pos.size
        exit_notional = exit_fill * pos.size
        gross_pnl = (exit_notional - entry_notional) if pos.side in {"BUY", "LONG"} else (entry_notional - exit_notional)

        exit_fees = self._fees(exit_notional)
        net_pnl = gross_pnl - exit_fees

        self.realized_pnl += net_pnl
        self.equity += net_pnl
        self._record_equity(f"close_{reason.lower()}")

        return {
            "trade_id": trade_id,
            "status": "CLOSED",
            "reason": reason,
            "entry_price": pos.entry_price,
            "exit_price": exit_fill,
            "gross_pnl": gross_pnl,
            "net_pnl": net_pnl,
            "fees": pos.fee_paid + exit_fees,
            "slippage": pos.slippage_paid + slippage,
            "closed_at": datetime.now(UTC).isoformat(),
            "mode": self.mode,
        }

    def _ensure_paper_mode(self) -> None:
        if self.mode != "paper":
            raise RuntimeError("PaperEngine cannot execute when mode != 'paper'")

    def _fill_price(self, mid: float, side: str, size: float) -> tuple[float, float]:
        slip_fraction = self.slippage_bps / 10_000.0
        if side.upper() in {"BUY", "LONG"}:
            fill = mid * (1 + slip_fraction)
        else:
            fill = mid * (1 - slip_fraction)
        slippage_value = abs(fill - mid) * size
        return fill, slippage_value

    def _fees(self, notional: float) -> float:
        return notional * (self.fee_bps / 10_000.0)

    def _hit_stop(self, pos: PaperPosition, market_price: float) -> bool:
        if pos.side in {"BUY", "LONG"}:
            return market_price <= pos.stop_price
        return market_price >= pos.stop_price

    def _hit_target(self, pos: PaperPosition, market_price: float) -> bool:
        if pos.side in {"BUY", "LONG"}:
            return market_price >= pos.target_price
        return market_price <= pos.target_price

    def _record_equity(self, reason: str) -> None:
        self.equity_curve.append(
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "equity": self.equity,
                "realized_pnl": self.realized_pnl,
                "reason": reason,
            }
        )
