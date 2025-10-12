# === src/backtest_multi.py (FINAL CRYPTO-ONLY EXECUTION) ===
import os, time, logging, argparse, csv, datetime as dt
import pandas as pd
from dataclasses import dataclass
import math
import numpy as np
from src.utils import setup_logging, load_env
from src.config import load_all
from src.feed import Feed
from src.indicators import add_indicators, last_row

# Stock strategy imports
from src.strategy_stock import (
    trend_follow,
    breakout_volexp,
    mean_revert_pullback,
    momentum_continuation,
)

# Crypto strategy imports
from src.strategy_crypto import (
    crypto_pullback_mr,
    crypto_momentum_trend,
)

from src.risk import position_size, calc_exits


@dataclass
class ActiveTrade:
    entry_price: float
    units: float
    side: int
    stop_loss: float
    take_profit: float
    trail_stop: float
    entry_time: dt.datetime
    entry_bar: int
    symbol: str
    reasons: str
    entry_equity: float


# -------------------- Trade Management Functions --------------------


def check_trade_exit(
    trade: ActiveTrade, current_bar, current_index, current_price, current_equity
):
    pnl = (current_price - trade.entry_price) * trade.side * trade.units

    # 1. Stop Loss Hit
    if trade.side > 0 and current_price <= trade.stop_loss:
        return True, pnl, "SL_HIT"
    if trade.side < 0 and current_price >= trade.stop_loss:
        return True, pnl, "SL_HIT"

    # 2. Take Profit Hit
    if trade.side > 0 and current_price >= trade.take_profit:
        return True, pnl, "TP_HIT"
    if trade.side < 0 and current_price <= trade.take_profit:
        return True, pnl, "TP_HIT"

    return False, 0, None


# -------------------- Backtesting Logic --------------------


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tf", default="5m", help="Low Timeframe (LTF) for entry")
    ap.add_argument("--years", type=int, default=5)
    return ap.parse_args()


def backtest_symbol(
    feed,
    symbol,
    tf,
    start_date,
    end_date,
    global_cfg,
    rules_cfg,
    strategy_trigger,
    mode,
):
    """Run backtest for one symbol."""

    # Use single bars fetch (LTF)
    df = feed.bars(symbol, tf)

    if df.empty or len(df) < 60:
        return [], 0, 0

    # --- Data Filtering ---
    if "time" not in df.columns:
        df = df.reset_index().rename(columns={"index": "time"})

    df["time"] = pd.to_datetime(df["time"], errors="coerce")
    df = df[(df["time"] >= start_date) & (df["time"] <= end_date)].reset_index(
        drop=True
    )
    if df.empty:
        return [], 0, 0

    # Simplified add_indicators call (single DF)
    feats = add_indicators(df)

    trades_log = []
    equity = 100000
    max_equity, min_equity = equity, equity
    active_trade: ActiveTrade = None

    # --- Backtest Loop ---
    for i in range(50, len(feats) - 1):
        r = feats.iloc[i]

        # -------------------- 1. Check for Trade Exit --------------------
        if active_trade:
            is_closed, pnl, reason = check_trade_exit(
                active_trade, r, i, r["Close"], equity
            )

            if is_closed:
                # LOGGING ADVANCED METRICS ON EXIT
                duration = r["time"] - active_trade.entry_time
                return_pct = pnl / active_trade.entry_equity

                equity += pnl
                trades_log.append(
                    {
                        "time": r["time"],
                        "symbol": symbol,
                        "side": "BUY" if active_trade.side > 0 else "SELL",
                        "entry": active_trade.entry_price,
                        "exit": r["Close"],
                        "pnl": pnl,
                        "equity": equity,
                        "units": active_trade.units,
                        "entry_time": active_trade.entry_time,
                        "entry_equity": active_trade.entry_equity,
                        "duration_min": duration.total_seconds() / 60,
                        "return_pct": return_pct,
                        "reasons": active_trade.reasons + f" | EXIT_{reason}",
                    }
                )
                active_trade = None

            # Update equity curve metrics even if trade is still open
            if active_trade:
                current_pnl = (
                    (r["Close"] - active_trade.entry_price)
                    * active_trade.side
                    * active_trade.units
                )
                current_equity = equity + current_pnl
                max_equity = max(max_equity, current_equity)
                min_equity = min(min_equity, current_equity)
                continue

        # -------------------- 2. Check for New Entry --------------------

        weighted_votes, reasons = 0.0, []
        trend_dir = 1 if r["EMA_S"] > r["EMA_L"] else -1

        # Strategy Routing Logic - ONLY MEAN REVERSION FOR NOW
        votes_list = []
        if mode == "crypto":
            v1 = crypto_pullback_mr(r, rules_cfg["mean_revert_pullback"], trend_dir)
            votes_list = [v1]
        # Stock mode is bypassed at the main function level

        # Weighted Vote Summation
        for v in votes_list:
            weighted_votes += v.score * v.confidence
            if v.score != 0:
                reasons.append(v.reason)

        # Only take a trade if the absolute weighted score exceeds the trigger
        if abs(weighted_votes) >= strategy_trigger:
            side = 1 if weighted_votes > 0 else -1
            price, atr = r["Close"], r["ATR"]

            # Calculate Exits (Uses the correct risk multipliers based on mode)
            stop, tp, trail_stop = calc_exits(
                price,
                atr,
                global_cfg["risk"][mode]["stop_atr_mult"],
                global_cfg["risk"][mode]["tp_atr_mult"],
                global_cfg["risk"][mode]["trail_atr_mult"],
                side,
            )

            # Calculate Units (Volatility-adjusted size)
            units = position_size(
                equity,
                atr,
                global_cfg["risk"][mode]["stop_atr_mult"],
                global_cfg["risk"]["risk_per_trade_pct"],
                price,
            )

            # Open the trade
            active_trade = ActiveTrade(
                entry_price=price,
                units=units,
                side=side,
                stop_loss=stop,
                take_profit=tp,
                trail_stop=trail_stop,
                entry_time=r["time"],
                entry_bar=i,
                symbol=symbol,
                reasons=",".join(reasons),
                entry_equity=equity,
            )

    # -------------------- 3. Handle Open Trade at End of Data --------------------
    if active_trade:
        # LOGGING ADVANCED METRICS ON END OF DATA
        last_price = feats.iloc[len(feats) - 1]["Close"]
        pnl = (
            (last_price - active_trade.entry_price)
            * active_trade.side
            * active_trade.units
        )
        duration = feats.iloc[len(feats) - 1]["time"] - active_trade.entry_time
        return_pct = pnl / active_trade.entry_equity
        equity += pnl

        trades_log.append(
            {
                "time": feats.iloc[len(feats) - 1]["time"],
                "symbol": symbol,
                "side": "BUY" if active_trade.side > 0 else "SELL",
                "entry": active_trade.entry_price,
                "exit": last_price,
                "pnl": pnl,
                "equity": equity,
                "units": active_trade.units,
                "entry_time": active_trade.entry_time,
                "entry_equity": active_trade.entry_equity,
                "duration_min": duration.total_seconds() / 60,
                "return_pct": return_pct,
                "reasons": active_trade.reasons + " | EXIT_END_DATA",
            }
        )

    return trades_log, max_equity, min_equity


def main():
    args = parse_args()
    setup_logging()
    env = load_env()
    global_cfg, rules_cfg, uni_cfg, _ = load_all()

    feed = Feed(
        env["APCA_API_KEY_ID"],
        env["APCA_API_SECRET_KEY"],
        env["APCA_API_BASE_URL"],
    )

    tf = args.tf
    years = args.years
    end_date = dt.datetime.now()
    start_date = end_date - dt.timedelta(days=365 * years)

    stocks = uni_cfg["universe"]["stocks"]
    crypto = uni_cfg["universe"]["crypto"]
    results = []

    all_equity_data = {"stock": [], "crypto": []}

    # 🚨 CRITICAL FIX: ITERATE ONLY OVER CRYPTO
    for symbol in crypto:
        is_crypto = symbol in crypto
        mode = "crypto" if is_crypto else "stock"
        logging.info(f"Backtesting {symbol} ({mode}) ...")

        # FIX APPLIED HERE: Strategy trigger is set to 1
        trades, max_eq, min_eq = backtest_symbol(
            feed,
            symbol,
            tf,
            start_date,
            end_date,
            global_cfg,
            rules_cfg,
            1,  # Hardcoded trigger of 1 for single-signal strategy
            mode,
        )

        if trades:
            results.extend(trades)
            df = pd.DataFrame(trades)

            all_equity_data[mode].append({"max_eq": max_eq, "min_eq": min_eq})

            total_pnl = df["pnl"].sum()
            winrate = (df["pnl"] > 0).mean() * 100
            logging.info(
                f"{symbol} done | Trades={len(df)} | Win%={winrate:.1f} | PnL={total_pnl:.2f}"
            )
        else:
            logging.warning(f"No data or trades for {symbol}")

    # save results
    os.makedirs("logs", exist_ok=True)
    out_file = "logs/backtest_results.csv"
    pd.DataFrame(results).to_csv(out_file, index=False)
    logging.info(
        f"✅ Backtest complete | {len(results)} total trades | saved to {out_file}"
    )

    # summary by type
    df = pd.DataFrame(results)
    initial_equity = 100000

    if not df.empty:
        # Note: stock_df will be empty, but we include this logic for structural integrity
        stock_df = df[df["symbol"].isin(stocks)]
        crypto_df = df[df["symbol"].isin(crypto)]

        def summary(name, data, mode):
            if data.empty:
                return

            final_pnl = data["pnl"].sum()
            total_wins = data[data["pnl"] > 0]
            total_losses = data[data["pnl"] < 0]

            # --- ADVANCED METRICS ---
            avg_profit_trade = data["pnl"].mean()
            avg_win = total_wins["pnl"].mean()
            avg_loss = total_losses["pnl"].mean()

            # Profit Factor
            profit_factor = (
                total_wins["pnl"].sum() / abs(total_losses["pnl"].sum())
                if not total_losses.empty and abs(total_losses["pnl"].sum()) > 0
                else float("inf")
            )

            # Sharpe Ratio
            daily_returns = (
                data.groupby(data["time"].dt.date)["pnl"].sum().pct_change().dropna()
            )
            sharpe_ratio = (
                daily_returns.mean() / daily_returns.std() * np.sqrt(252)
                if daily_returns.std() > 0
                else float("inf")
            )

            # Granular Holding Time
            avg_holding_min = data["duration_min"].mean() if not data.empty else 0.0
            avg_holding_hrs = avg_holding_min / 60
            avg_holding_days = avg_holding_hrs / 24

            if mode == "stock":
                max_eq = (
                    max([d["max_eq"] for d in all_equity_data["stock"]])
                    if all_equity_data["stock"]
                    else initial_equity
                )
                min_eq = (
                    min([d["min_eq"] for d in all_equity_data["stock"]])
                    if all_equity_data["stock"]
                    else initial_equity
                )
            else:
                max_eq = (
                    max([d["max_eq"] for d in all_equity_data["crypto"]])
                    if all_equity_data["crypto"]
                    else initial_equity
                )
                min_eq = (
                    min([d["min_eq"] for d in all_equity_data["crypto"]])
                    if all_equity_data["crypto"]
                    else initial_equity
                )

            # Calmar Ratio
            max_drawdown_usd = max_eq - min_eq
            calmar_ratio = (
                final_pnl / max_drawdown_usd if max_drawdown_usd > 0 else float("inf")
            )

            print(f"\n=== {name} RESULTS ===")
            print(f"Trades: {len(data)}")
            print(f"Win rate: {(data['pnl']>0).mean()*100:.2f}%")
            print(f"Total PnL: {final_pnl:.2f}")
            print(f"Max equity: {max_eq:.2f}")
            print(f"Min equity: {min_eq:.2f}")
            print(f"----------------------------------")
            print(f"Avg Profit/Trade (Expectancy): {avg_profit_trade:.2f}")
            print(f"Profit Factor: {profit_factor:.2f}")
            print(f"Sharpe Ratio (Annualized): {sharpe_ratio:.2f}")
            print(f"Calmar Ratio (Risk-Adjusted PnL): {calmar_ratio:.2f}")
            print(f"----------------------------------")
            print(f"Avg Holding Time (Min): {avg_holding_min:.2f} min")
            print(f"Avg Holding Time (Hrs): {avg_holding_hrs:.2f} hrs")
            print(f"Avg Holding Time (Days): {avg_holding_days:.2f} days")

        summary("STOCK", stock_df, "stock")
        summary("CRYPTO", crypto_df, "crypto")


if __name__ == "__main__":
    main()
