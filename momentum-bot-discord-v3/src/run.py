# === run.py — unified stock + crypto bot ===
import argparse, logging, time, os, csv
import pandas as pd
from src.utils import setup_logging, load_env
from src.config import load_all
from src.alerts import Alerts
from src.feed import Feed
from src.broker import Broker
from src.indicators import add_indicators, last_row
from src.strategy import (
    trend_follow,
    breakout_volexp,
    mean_revert_pullback,
    momentum_continuation,
)
from src.regime import classify
from src.risk import position_size, calc_exits


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tf", default="15m")
    ap.add_argument("--interval", type=int, default=300, help="seconds between scans")
    return ap.parse_args()


def filter_by_dollar_volume(feed, symbols, min_vol, timeframe):
    """Return only symbols with avg dollar volume above threshold."""
    active = []
    for s in symbols:
        df = feed.bars(s, timeframe=timeframe, limit=60)
        if df.empty or len(df) < 5:
            continue
        df["DollarVol"] = df["Close"] * df["Volume"]
        avg_vol = df["DollarVol"].tail(30).mean()
        if avg_vol >= min_vol:
            active.append(s)
    return active


def main():
    args = parse_args()
    setup_logging()
    env = load_env()
    global_cfg, rules_cfg, uni_cfg, opt_cfg = load_all()

    alerts = Alerts(env.get("DISCORD_WEBHOOK_URL"))
    feed = Feed(
        env["APCA_API_KEY_ID"], env["APCA_API_SECRET_KEY"], env["APCA_API_BASE_URL"]
    )
    broker = Broker(
        env["APCA_API_KEY_ID"],
        env["APCA_API_SECRET_KEY"],
        env["APCA_API_BASE_URL"],
        env["MODE"],
    )

    tf = args.tf
    stocks = uni_cfg["universe"]["stocks"]
    crypto = uni_cfg["universe"]["crypto"]
    keep_top = uni_cfg["rotation"]["keep_top"]
    min_dollar_vol_stock = uni_cfg["rotation"]["min_dollar_vol_stock"]
    min_dollar_vol_crypto = uni_cfg["rotation"]["min_dollar_vol_crypto"]

    while True:
        try:
            # === Regime detection for stocks ===
            spy = feed.bars("SPY", timeframe="1D", limit=300)
            vix = feed.bars("VIX", timeframe="1D", limit=300)
            if not spy.empty and not vix.empty:
                regime = classify(
                    add_indicators(spy).iloc[-1],
                    add_indicators(vix).iloc[-1],
                    global_cfg["regime"]["bull_vix_lt"],
                    global_cfg["regime"]["bear_vix_gt"],
                )
            else:
                logging.warning("SPY/VIX missing — skipping regime check")
                regime = 0

            acct = broker.account()
            equity = float(acct.equity)

            # === Liquidity rotation ===
            active_stocks = filter_by_dollar_volume(
                feed, stocks, min_dollar_vol_stock, "1D"
            )
            active_crypto = filter_by_dollar_volume(
                feed, crypto, min_dollar_vol_crypto, "1h"
            )

            active_stocks = active_stocks[:keep_top]
            active_crypto = active_crypto[:keep_top]

            # === Combined scan ===
            for symbol in active_stocks + active_crypto:
                is_crypto = symbol in active_crypto
                df = feed.bars(symbol, timeframe=tf, limit=300)
                if df.empty or len(df) < 60:
                    continue

                feats = add_indicators(df)
                if feats.empty:
                    continue
                r = last_row(feats)

                votes, reasons = 0, []
                v1 = trend_follow(r, rules_cfg["trend_follow"])
                votes += v1.score
                reasons.append(v1.reason)
                v2 = breakout_volexp(r, rules_cfg["breakout_volexp"])
                votes += v2.score
                reasons.append(v2.reason)
                v3 = mean_revert_pullback(r, rules_cfg["mean_revert_pullback"], regime)
                votes += v3.score
                reasons.append(v3.reason)
                v4 = momentum_continuation(r, rules_cfg["momentum_continuation"])
                votes += v4.score
                reasons.append(v4.reason)

                if abs(votes) < global_cfg["strategy_trigger"]:
                    continue

                side = "buy" if votes > 0 else "sell"
                atr, price = r["ATR"], r["Close"]

                # === Risk block ===
                risk_block = (
                    global_cfg["risk"]["crypto"]
                    if is_crypto
                    else global_cfg["risk"]["stock"]
                )
                stop, tp, trail = calc_exits(
                    price,
                    atr,
                    risk_block["stop_atr_mult"],
                    risk_block["tp_atr_mult"],
                    risk_block["trail_atr_mult"],
                    +1 if votes > 0 else -1,
                )

                shares = position_size(
                    equity,
                    atr,
                    risk_block["stop_atr_mult"],
                    global_cfg["risk"]["risk_per_trade_pct"],
                    price,
                    1.0,
                )
                if shares <= 0:
                    continue

                bps = global_cfg["exec"]["limit_slip_bps"]
                limit_px = (
                    price * (1 - bps / 10000)
                    if side == "buy"
                    else price * (1 + bps / 10000)
                )

                # === Execute or alert only ===
                if env["MODE"].lower() == "paper":
                    broker.place_order(
                        symbol,
                        shares,
                        side,
                        type=global_cfg["exec"]["order_type"],
                        limit_price=round(limit_px, 2),
                    )

                # === Discord alert ===
                emoji = "🪙" if is_crypto else "📈"
                alerts.send(
                    f"{emoji} {symbol} {side.upper()} {shares} @~{round(limit_px,2)} | "
                    f"votes={votes} reasons={','.join(reasons)} stop={round(stop,2)} tp={round(tp,2)}"
                )

                # === Log trade ===
                os.makedirs("logs", exist_ok=True)
                log_file = "logs/trades.csv"
                write_header = not os.path.exists(log_file)
                with open(log_file, "a", newline="") as f:
                    writer = csv.writer(f)
                    if write_header:
                        writer.writerow(
                            [
                                "time",
                                "symbol",
                                "type",
                                "side",
                                "shares",
                                "price",
                                "stop",
                                "tp",
                                "votes",
                                "reasons",
                            ]
                        )
                    writer.writerow(
                        [
                            time.strftime("%Y-%m-%d %H:%M:%S"),
                            symbol,
                            "CRYPTO" if is_crypto else "STOCK",
                            side,
                            shares,
                            round(price, 2),
                            round(stop, 2),
                            round(tp, 2),
                            votes,
                            ",".join(reasons),
                        ]
                    )

            alerts.send("✅ Heartbeat OK")

        except Exception as e:
            logging.exception(e)
            alerts.send(f"❌ Bot error: {e}")

        time.sleep(args.interval)


if __name__ == "__main__":
    main()
