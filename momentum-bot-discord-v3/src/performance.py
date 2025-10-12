import pandas as pd
import os

LOG_FILE = "logs/trades.csv"


def performance_summary():
    if not os.path.exists(LOG_FILE):
        print("No trades.csv found yet. Run the bot and generate some trades first.")
        return

    df = pd.read_csv(LOG_FILE)

    if df.empty:
        print("No trades logged yet.")
        return

    # Basic stats
    print("=== PERFORMANCE SUMMARY ===")
    print(f"Total Trades: {len(df)}")

    # Win/Loss count simulation (sell > buy = win, just as placeholder logic)
    df["pnl"] = (df["tp"] - df["price"]).where(
        df["side"] == "buy", (df["price"] - df["tp"])
    )
    df["win"] = df["pnl"] > 0

    wins = df["win"].sum()
    win_rate = (wins / len(df)) * 100

    avg_gain = df[df["win"]]["pnl"].mean()
    avg_loss = df[~df["win"]]["pnl"].mean()

    total_pnl = df["pnl"].sum()

    print(f"Wins: {wins} | Losses: {len(df) - wins}")
    print(f"Win Rate: {win_rate:.2f}%")
    print(f"Average Gain: {avg_gain:.2f}")
    print(f"Average Loss: {avg_loss:.2f}")
    print(f"Total P/L (approx): {total_pnl:.2f}")
    print("===========================")


if __name__ == "__main__":
    performance_summary()
