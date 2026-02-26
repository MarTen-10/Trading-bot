#!/usr/bin/env python3


class RiskEngine:
    def __init__(self, risk_fraction=0.005, max_daily_loss_r=-3.0):
        self.risk_fraction = float(risk_fraction)
        self.max_daily_loss_r = float(max_daily_loss_r)
        self.realized_r_day = 0.0

    def allow(self, signal: dict) -> tuple[bool, str | None]:
        if self.realized_r_day <= self.max_daily_loss_r:
            return False, 'daily_loss_cap'
        return True, None

    def size(self, signal: dict, equity=1000.0):
        entry = float(signal['entry_px'])
        stop = float(signal['stop_px'])
        risk_d = equity * self.risk_fraction
        d = max(1e-9, abs(entry - stop))
        qty = risk_d / d
        return qty, risk_d
