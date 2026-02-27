import json
import os
from datetime import datetime, timezone
from pathlib import Path


SENSITIVE_KEYS = {"api_key", "token", "password", "secret", "authorization", "gateway_token"}


def _redact(obj):
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if str(k).lower() in SENSITIVE_KEYS:
                out[k] = "__REDACTED__"
            else:
                out[k] = _redact(v)
        return out
    if isinstance(obj, list):
        return [_redact(x) for x in obj]
    return obj


class JsonlLogger:
    def __init__(self, run_id: str, base_dir: str = "/home/marten/.openclaw/workspace/logs/anubis_l0_runs"):
        self.run_id = run_id
        self.path = Path(base_dir) / f"{run_id}.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        os.chmod(self.path.parent, 0o700)

    def event(self, event_type: str, **fields):
        rec = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "run_id": self.run_id,
            "event": event_type,
            **_redact(fields),
        }
        line = json.dumps(rec, separators=(",", ":")) + "\n"
        with self.path.open("a", encoding="utf-8") as f:
            f.write(line)
            f.flush()
            os.fsync(f.fileno())

    def tail(self, lines: int = 10):
        if not self.path.exists():
            return []
        return self.path.read_text().splitlines()[-lines:]
