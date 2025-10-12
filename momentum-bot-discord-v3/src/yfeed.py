import subprocess
import json
import sys
import os
import pandas as pd


def fetch_yahoo(symbol, timeframe="1h", years=3):
    """Run yfinance in isolated env and return DataFrame."""
    script = f"""
import yfinance as yf, datetime as dt, pandas as pd, json
start = dt.datetime.now() - dt.timedelta(days={years}*365)
end = dt.datetime.now()
data = yf.download("{symbol}", start=start, end=end, interval="{timeframe}", progress=False)
if data.empty:
    print("{{}}")
else:
    data.reset_index(inplace=True)
    print(data.to_json(orient='records', date_format='iso'))
"""
    result = subprocess.run(
        [
            os.path.join(os.getcwd(), ".yahoo_env", "Scripts", "python.exe"),
            "-c",
            script,
        ],
        capture_output=True,
        text=True,
    )
    out = result.stdout.strip()
    if not out or out == "{}":
        return pd.DataFrame(columns=["time", "Open", "High", "Low", "Close", "Volume"])
    df = pd.read_json(out)
    df.rename(columns={"Datetime": "time"}, inplace=True)
    return df[["time", "Open", "High", "Low", "Close", "Volume"]]
