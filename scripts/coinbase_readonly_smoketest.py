#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from core.db.postgres import PostgresDB
from core.execution.coinbase_adapter import CoinbaseAdapter


def classify(result: dict) -> str | None:
    if result.get("ok"):
        return None
    if "error_class" in result:
        return result.get("error_class")
    reason = str(result.get("reason", ""))
    if "credential" in reason:
        return "auth_error"
    return "unknown"


def main() -> None:
    db = None
    try:
        db = PostgresDB()
    except Exception:
        pass

    adapter = CoinbaseAdapter(db_writer=db)
    steps = [
        ("server_time", lambda: adapter.get_server_time()),
        ("accounts", lambda: adapter.get_account_balance()),
        ("products", lambda: adapter.list_products()),
        ("market_price", lambda: adapter.get_market_price("BTC-PERP")),
        ("positions", lambda: adapter.get_perp_positions()),
    ]

    summary = []
    for name, fn in steps:
        result = fn()
        row = {
            "endpoint": name,
            "ok": bool(result.get("ok")),
            "status_code": result.get("status_code"),
            "latency_ms": result.get("latency_ms"),
            "error_class": classify(result),
            "timestamp": datetime.now(UTC).isoformat(),
        }
        summary.append(row)
        if db:
            db.insert_execution_log("smoketest.readonly", row)

    print(json.dumps({"results": summary}, indent=2))


if __name__ == "__main__":
    main()
