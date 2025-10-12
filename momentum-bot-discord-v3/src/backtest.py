import argparse
from src.utils import setup_logging, load_env
from src.config import load_all
from src.feed import Feed
from src.indicators import add_indicators

def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--tf", default="15m")
    ap.add_argument("--days", type=int, default=120)
    return ap.parse_args()

def main():
    args = parse_args()
    setup_logging()
    env = load_env()
    global_cfg, rules_cfg, uni_cfg, opt_cfg = load_all()
    feed = Feed(env["APCA_API_KEY_ID"], env["APCA_API_SECRET_KEY"], env["APCA_API_BASE_URL"])

    df = feed.bars(args.symbol, timeframe=args.tf, limit=args.days*26)
    if df.empty:
        print("No data")
        return
    feats = add_indicators(df)

    pnl = 0.0; wins=0; trades=0
    for i in range(len(feats)-1):
        r = feats.iloc[i]; r_next = feats.iloc[i+1]
        votes = 0
        # simple voter (subset)
        from src.strategy import trend_follow, breakout_volexp, momentum_continuation
        votes += trend_follow(r, rules_cfg["trend_follow"]).score
        votes += breakout_volexp(r, rules_cfg["breakout_volexp"]).score
        votes += momentum_continuation(r, rules_cfg["momentum_continuation"]).score
        if abs(votes) >= global_cfg["strategy_trigger"]:
            direction = 1 if votes>0 else -1
            ret = (r_next["Close"]/r["Close"]-1)*direction
            pnl += ret; trades += 1; wins += (ret>0)

    winrate = (wins/max(1,trades))*100
    print(f"Symbol {args.symbol} tf {args.tf}  Trades: {trades}  Win%: {winrate:.2f}%  SumNextBarPnL: {pnl:.4f}")

if __name__ == "__main__":
    main()
