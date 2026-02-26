#!/usr/bin/env python3
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
import psycopg2


BASE = Path(__file__).resolve().parents[1]
STATE_PATH = BASE / "data" / "reports" / "runtime_state_latest.json"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _service_running() -> bool:
    try:
        p = subprocess.run(
            ["systemctl", "--user", "is-active", "horus-paper.service"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        return p.stdout.strip() == "active"
    except Exception:
        return False


def _read_state() -> dict:
    try:
        if STATE_PATH.exists():
            return json.loads(STATE_PATH.read_text())
    except Exception:
        pass
    return {}


def _safe_count(cur, sql: str, params=(), default=0):
    try:
        cur.execute(sql, params)
        row = cur.fetchone()
        if not row or row[0] is None:
            return default
        return row[0]
    except Exception:
        return default


def main() -> None:
    load_dotenv(BASE / ".env", override=False)

    state = _read_state()
    output = {
        "timestamp_utc": _utc_now_iso(),
        "service_running": _service_running(),
        "signals_last_1h": 0,
        "orders_last_1h": 0,
        "fills_last_1h": 0,
        "open_exposure_r": float(state.get("open_exposure_r", 0.0) or 0.0),
        "safe_mode": bool(state.get("safe_mode", False)),
        "governance_blocks_last_1h": 0,
        "breaker_active": False,
        "db_connection": "missing_DATABASE_URL",
    }

    db_url = os.getenv("DATABASE_URL", "")
    if not db_url:
        print(json.dumps(output, sort_keys=True))
        return

    try:
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        cur = conn.cursor()
        output["db_connection"] = "ok"

        output["signals_last_1h"] = int(
            _safe_count(cur, "SELECT COUNT(*) FROM signals WHERE timestamp >= NOW() - INTERVAL '1 hour'")
        )
        output["orders_last_1h"] = int(
            _safe_count(cur, "SELECT COUNT(*) FROM orders WHERE timestamp >= NOW() - INTERVAL '1 hour'")
        )
        output["fills_last_1h"] = int(
            _safe_count(cur, "SELECT COUNT(*) FROM fills WHERE timestamp >= NOW() - INTERVAL '1 hour'")
        )
        output["governance_blocks_last_1h"] = int(
            _safe_count(
                cur,
                "SELECT COUNT(*) FROM governance_events WHERE action='BLOCK' AND timestamp >= NOW() - INTERVAL '1 hour'",
            )
        )

        recent_safe = int(
            _safe_count(
                cur,
                "SELECT COUNT(*) FROM governance_events WHERE reason='SAFE_MODE_ACTIVE' AND timestamp >= NOW() - INTERVAL '10 minutes'",
            )
        )
        recent_breaker = int(
            _safe_count(
                cur,
                "SELECT COUNT(*) FROM circuit_breaker_events WHERE timestamp >= NOW() - INTERVAL '10 minutes'",
            )
        )
        output["breaker_active"] = bool(recent_safe > 0 or recent_breaker > 0)

        cur.close()
        conn.close()
    except Exception:
        output["db_connection"] = "failed"

    print(json.dumps(output, sort_keys=True))


if __name__ == "__main__":
    main()
