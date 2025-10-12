import math

def position_size(equity: float, atr: float, stop_mult: float, risk_pct: float, price: float, vol_scale: float=1.0):
    risk_dollars = equity * risk_pct
    stop_dist = max(atr * stop_mult, price * 0.002)
    shares = math.floor((risk_dollars / stop_dist) * vol_scale)
    return max(shares, 0)

def calc_exits(price: float, atr: float, stop_mult: float, tp_mult: float, trail_mult: float, side: int):
    if side > 0:
        stop = price - stop_mult * atr
        tp = price + tp_mult * atr
    else:
        stop = price + stop_mult * atr
        tp = price - tp_mult * atr
    trail = trail_mult * atr
    return stop, tp, trail
