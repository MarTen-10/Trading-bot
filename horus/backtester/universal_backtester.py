#!/usr/bin/env python3
import argparse, csv, itertools, json, math, statistics, time, urllib.parse, urllib.request
from datetime import datetime, UTC
from pathlib import Path


def now_iso():
    return datetime.now(UTC).isoformat()


def fetch_yahoo(ticker: str, interval: str = "1d", range_: str = "1y"):
    q = urllib.parse.urlencode({"interval": interval, "range": range_})
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?{q}"
    data = None
    last_err = None
    for wait in (0, 1, 2, 4):
        try:
            if wait:
                time.sleep(wait)
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 horus-backtester/1.0"})
            with urllib.request.urlopen(req, timeout=20) as r:
                data = json.loads(r.read().decode())
            break
        except Exception as e:
            last_err = e
    if data is None:
        raise last_err

    result = data["chart"]["result"][0]
    ts = result.get("timestamp", [])
    qte = result["indicators"]["quote"][0]
    bars = []
    for i, t in enumerate(ts):
        o, h, l, c = qte["open"][i], qte["high"][i], qte["low"][i], qte["close"][i]
        v = qte.get("volume", [None] * len(ts))[i]
        if None in (o, h, l, c):
            continue
        bars.append({
            "timestamp": datetime.fromtimestamp(t, tz=UTC).isoformat(),
            "open": float(o), "high": float(h), "low": float(l), "close": float(c),
            "volume": float(v or 0)
        })
    return bars


def fetch_stooq_daily(ticker: str):
    # Stooq expects lower-case with .us for many US equities
    sym = ticker.lower()
    if "." not in sym and "-" not in sym and "=" not in sym:
        sym = f"{sym}.us"
    q = urllib.parse.urlencode({"s": sym, "i": "d"})
    url = f"https://stooq.com/q/d/l/?{q}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 horus-backtester/1.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        raw = r.read().decode().strip().splitlines()
    if len(raw) <= 1:
        return []
    bars = []
    for line in raw[1:]:
        parts = line.split(',')
        if len(parts) < 6:
            continue
        dt, o, h, l, c, v = parts[:6]
        try:
            bars.append({
                "timestamp": f"{dt}T00:00:00+00:00",
                "open": float(o), "high": float(h), "low": float(l), "close": float(c),
                "volume": float(v or 0)
            })
        except ValueError:
            continue
    return bars


def load_csv(path: str):
    out = []
    with open(path, newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            out.append({
                "timestamp": row["timestamp"],
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": float(row.get("volume", 0) or 0),
            })
    return out


def save_csv(path: str, rows, fieldnames):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def sma(values, n):
    out = [None] * len(values)
    if n <= 0:
        return out
    s = 0.0
    for i, v in enumerate(values):
        s += v
        if i >= n:
            s -= values[i - n]
        if i >= n - 1:
            out[i] = s / n
    return out


def stddev(values, n):
    out = [None] * len(values)
    for i in range(n - 1, len(values)):
        win = values[i - n + 1:i + 1]
        out[i] = statistics.pstdev(win)
    return out


def rsi(values, n=14):
    out = [None] * len(values)
    gains = [0.0] * len(values)
    losses = [0.0] * len(values)
    for i in range(1, len(values)):
        d = values[i] - values[i - 1]
        gains[i] = max(0, d)
        losses[i] = max(0, -d)
    ag = sma(gains, n)
    al = sma(losses, n)
    for i in range(len(values)):
        if ag[i] is None or al[i] is None:
            continue
        if al[i] == 0:
            out[i] = 100.0
        else:
            rs = ag[i] / al[i]
            out[i] = 100 - (100 / (1 + rs))
    return out


def atr(bars, n=14):
    trs = [None] * len(bars)
    for i, b in enumerate(bars):
        if i == 0:
            trs[i] = b["high"] - b["low"]
        else:
            pc = bars[i - 1]["close"]
            trs[i] = max(b["high"] - b["low"], abs(b["high"] - pc), abs(b["low"] - pc))
    out = [None] * len(bars)
    s = 0.0
    for i, t in enumerate(trs):
        s += t
        if i >= n:
            s -= trs[i - n]
        if i >= n - 1:
            out[i] = s / n
    return out


def signals(strategy, bars, p):
    c = [b["close"] for b in bars]
    h = [b["high"] for b in bars]
    l = [b["low"] for b in bars]
    sig = [0] * len(bars)

    if strategy == "sma_cross":
        fast = sma(c, int(p.get("fast", 20)))
        slow = sma(c, int(p.get("slow", 50)))
        for i in range(1, len(bars)):
            if None in (fast[i], slow[i], fast[i - 1], slow[i - 1]):
                continue
            if fast[i] > slow[i] and fast[i - 1] <= slow[i - 1]:
                sig[i] = 1
            elif fast[i] < slow[i] and fast[i - 1] >= slow[i - 1]:
                sig[i] = -1

    elif strategy == "breakout":
        n = int(p.get("lookback", 20))
        exit_n = int(p.get("exit_lookback", n))
        for i in range(max(n, exit_n), len(bars)):
            hh = max(h[i - n:i])
            ll = min(l[i - exit_n:i])
            if c[i] > hh:
                sig[i] = 1
            elif c[i] < ll:
                sig[i] = -1

    elif strategy == "mean_reversion_z":
        n = int(p.get("lookback", 30))
        z_in = float(p.get("z_in", -2.0))
        z_out = float(p.get("z_out", -0.2))
        m = sma(c, n)
        sd = stddev(c, n)
        for i in range(n, len(bars)):
            if m[i] is None or sd[i] in (None, 0):
                continue
            z = (c[i] - m[i]) / sd[i]
            if z <= z_in:
                sig[i] = 1
            elif z >= z_out:
                sig[i] = -1

    elif strategy == "rsi_reversion":
        n = int(p.get("rsi_n", 14))
        buy = float(p.get("buy_below", 30))
        sell = float(p.get("sell_above", 55))
        rr = rsi(c, n)
        for i in range(1, len(bars)):
            if rr[i] is None:
                continue
            if rr[i] <= buy:
                sig[i] = 1
            elif rr[i] >= sell:
                sig[i] = -1
    else:
        raise ValueError(f"Unknown strategy: {strategy}")

    return sig


def run_backtest(bars, strategy, p, costs):
    init_equity = float(p.get("initial_equity", 10000))
    risk_pct = float(p.get("risk_pct", 0.005))
    notional_pct = float(p.get("notional_pct", 0.2))
    atr_n = int(p.get("atr_n", 14))
    stop_atr = float(p.get("stop_atr_mult", 1.5))
    take_r = float(p.get("target_r_mult", 2.0))

    fee_bps = float(costs.get("fee_bps", 1.0))
    slippage_bps = float(costs.get("slippage_bps", 2.0))

    sig = signals(strategy, bars, p)
    a = atr(bars, atr_n)

    equity = init_equity
    peak = equity
    max_dd = 0.0
    pos = None
    trades = []
    curve = []

    def apply_cost(price, side):
        bps = (fee_bps + slippage_bps) / 10000.0
        return price * (1 + bps) if side == "buy" else price * (1 - bps)

    for i, b in enumerate(bars):
        ts = b["timestamp"]
        px = b["close"]

        if pos is not None:
            stop_hit = b["low"] <= pos["stop"]
            target_hit = b["high"] >= pos["target"]
            exit_reason = None
            exit_px = None

            if stop_hit:
                exit_reason = "stop"
                exit_px = pos["stop"]
            elif target_hit:
                exit_reason = "target"
                exit_px = pos["target"]
            elif sig[i] == -1:
                exit_reason = "signal"
                exit_px = px

            if exit_reason:
                eff_exit = apply_cost(exit_px, "sell")
                pnl = (eff_exit - pos["entry"]) * pos["qty"]
                equity += pnl
                r = pnl / max(1e-9, pos["risk_dollars"])
                trades.append({
                    "entry_ts": pos["entry_ts"], "exit_ts": ts,
                    "entry": round(pos["entry"], 6), "exit": round(eff_exit, 6),
                    "qty": round(pos["qty"], 8), "pnl": round(pnl, 4),
                    "r": round(r, 4), "reason": exit_reason
                })
                pos = None

        if pos is None and sig[i] == 1:
            atr_v = a[i]
            eff_entry = apply_cost(px, "buy")
            if atr_v is not None and atr_v > 0:
                stop = eff_entry - stop_atr * atr_v
                risk_per_unit = max(1e-9, eff_entry - stop)
                risk_dollars = equity * risk_pct
                qty = max(0.0, risk_dollars / risk_per_unit)
                target = eff_entry + take_r * risk_per_unit
            else:
                qty = (equity * notional_pct) / max(1e-9, eff_entry)
                risk_dollars = equity * risk_pct
                stop = eff_entry * 0.98
                target = eff_entry * 1.03

            pos = {
                "entry_ts": ts,
                "entry": eff_entry,
                "qty": qty,
                "stop": stop,
                "target": target,
                "risk_dollars": risk_dollars,
            }

        peak = max(peak, equity)
        dd = (equity - peak)
        max_dd = min(max_dd, dd)
        curve.append({"timestamp": ts, "equity": round(equity, 4)})

    if pos is not None:
        eff_exit = apply_cost(bars[-1]["close"], "sell")
        pnl = (eff_exit - pos["entry"]) * pos["qty"]
        equity += pnl
        r = pnl / max(1e-9, pos["risk_dollars"])
        trades.append({
            "entry_ts": pos["entry_ts"], "exit_ts": bars[-1]["timestamp"],
            "entry": round(pos["entry"], 6), "exit": round(eff_exit, 6),
            "qty": round(pos["qty"], 8), "pnl": round(pnl, 4),
            "r": round(r, 4), "reason": "eod"
        })

    rs = [t["r"] for t in trades]
    wins = [x for x in rs if x > 0]
    losses = [x for x in rs if x <= 0]
    gp = sum(wins)
    gl = abs(sum(losses)) if losses else 0.0
    pf = None if gl == 0 else round(gp / gl, 4)

    summary = {
        "generated_at": now_iso(),
        "strategy": strategy,
        "trades": len(trades),
        "win_rate": round((len(wins) / len(rs)) if rs else 0, 4),
        "expectancy_r": round((statistics.mean(rs) if rs else 0), 4),
        "profit_factor": pf,
        "net_pnl": round(equity - init_equity, 4),
        "return_pct": round(((equity / init_equity) - 1) * 100, 4),
        "max_drawdown_$": round(max_dd, 4),
        "max_drawdown_pct": round((max_dd / init_equity) * 100, 4),
        "final_equity": round(equity, 4),
        "costs": costs,
    }
    return summary, trades, curve


def walkforward(bars, strategy, p, costs, folds=4):
    n = len(bars)
    fold = max(50, n // folds)
    out = []
    for i in range(folds):
        s = i * fold
        e = min((i + 1) * fold, n)
        if e - s < 40:
            continue
        sm, _, _ = run_backtest(bars[s:e], strategy, p, costs)
        out.append({"fold": i, **sm})
    pf_vals = [x["profit_factor"] for x in out if x.get("profit_factor") is not None]
    agg = {
        "folds": len(out),
        "avg_expectancy_r": round(statistics.mean([x["expectancy_r"] for x in out]), 4) if out else 0,
        "avg_profit_factor": round(statistics.mean(pf_vals), 4) if pf_vals else None,
        "avg_return_pct": round(statistics.mean([x["return_pct"] for x in out]), 4) if out else 0,
    }
    return {"walkforward": out, "aggregate": agg, "generated_at": now_iso()}


def optimize(bars, strategy, base_params, grid, costs):
    keys = list(grid.keys())
    combos = list(itertools.product(*[grid[k] for k in keys]))
    rows = []
    for vals in combos:
        p = dict(base_params)
        for k, v in zip(keys, vals):
            p[k] = v
        s, _, _ = run_backtest(bars, strategy, p, costs)
        rows.append({**{k: p[k] for k in keys}, **s})
    rows.sort(key=lambda x: (x["expectancy_r"], x["profit_factor"], x["return_pct"]), reverse=True)
    return rows


def main():
    ap = argparse.ArgumentParser(description="Universal plug-and-play backtester")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_fetch = sub.add_parser("fetch")
    p_fetch.add_argument("--ticker", required=True)
    p_fetch.add_argument("--interval", default="1d")
    p_fetch.add_argument("--range", dest="range_", default="1y")
    p_fetch.add_argument("--out", required=True)

    p_bt = sub.add_parser("backtest")
    p_bt.add_argument("--csv")
    p_bt.add_argument("--ticker")
    p_bt.add_argument("--interval", default="1d")
    p_bt.add_argument("--range", dest="range_", default="1y")
    p_bt.add_argument("--strategy", required=True)
    p_bt.add_argument("--params", default="{}")
    p_bt.add_argument("--costs", default='{"fee_bps":1.0,"slippage_bps":2.0}')
    p_bt.add_argument("--out", required=True)

    p_wf = sub.add_parser("walkforward")
    p_wf.add_argument("--csv")
    p_wf.add_argument("--ticker")
    p_wf.add_argument("--interval", default="1d")
    p_wf.add_argument("--range", dest="range_", default="1y")
    p_wf.add_argument("--strategy", required=True)
    p_wf.add_argument("--params", default="{}")
    p_wf.add_argument("--costs", default='{"fee_bps":1.0,"slippage_bps":2.0}')
    p_wf.add_argument("--folds", type=int, default=4)
    p_wf.add_argument("--out", required=True)

    p_opt = sub.add_parser("optimize")
    p_opt.add_argument("--csv")
    p_opt.add_argument("--ticker")
    p_opt.add_argument("--interval", default="1d")
    p_opt.add_argument("--range", dest="range_", default="1y")
    p_opt.add_argument("--strategy", required=True)
    p_opt.add_argument("--params", default="{}")
    p_opt.add_argument("--grid", required=True, help='JSON like {"fast":[10,20],"slow":[50,100]}')
    p_opt.add_argument("--costs", default='{"fee_bps":1.0,"slippage_bps":2.0}')
    p_opt.add_argument("--out", required=True)

    args = ap.parse_args()

    if args.cmd == "fetch":
        try:
            bars = fetch_yahoo(args.ticker, args.interval, args.range_)
        except Exception:
            if args.interval != "1d":
                raise
            bars = fetch_stooq_daily(args.ticker)
        save_csv(args.out, bars, ["timestamp", "open", "high", "low", "close", "volume"])
        print(args.out)
        return

    if args.csv:
        bars = load_csv(args.csv)
    else:
        try:
            bars = fetch_yahoo(args.ticker, args.interval, args.range_)
        except Exception:
            if args.interval != "1d":
                raise
            bars = fetch_stooq_daily(args.ticker)

    params = json.loads(args.params)
    costs = json.loads(args.costs)

    if args.cmd == "backtest":
        summary, trades, curve = run_backtest(bars, args.strategy, params, costs)
        out = {
            "summary": summary,
            "trades": trades,
            "equity_curve": curve,
        }
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(out, indent=2))
        print(json.dumps(summary))

    elif args.cmd == "walkforward":
        out = walkforward(bars, args.strategy, params, costs, folds=args.folds)
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(out, indent=2))
        print(json.dumps(out["aggregate"]))

    elif args.cmd == "optimize":
        grid = json.loads(args.grid)
        rows = optimize(bars, args.strategy, params, grid, costs)
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps({"generated_at": now_iso(), "results": rows}, indent=2))
        print(json.dumps(rows[0] if rows else {}))


if __name__ == "__main__":
    main()
