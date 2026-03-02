#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from core.data.csv_bootstrap import load_validate_csv, persist_bootstrap
from core.db.postgres import PostgresDB


def main():
    path = Path("data/history/btc_perp_1m.csv")
    db = PostgresDB()
    candles, gaps = load_validate_csv(path, expected_symbol="BTCUSDT")
    report = persist_bootstrap(db, candles, gaps)
    print(json.dumps(asdict(report), indent=2))


if __name__ == "__main__":
    main()
