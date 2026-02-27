import json
from datetime import datetime, timezone
from pathlib import Path


class JsonlLogger:
    def __init__(self, run_id: str, base_dir: str = "/home/marten/.openclaw/workspace/logs/anubis_l0_runs"):
        self.run_id = run_id
        self.path = Path(base_dir) / f"{run_id}.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def event(self, event_type: str, **fields):
        rec = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "run_id": self.run_id,
            "event": event_type,
            **fields,
        }
        self.path.write_text(self.path.read_text() + json.dumps(rec) + "\n" if self.path.exists() else json.dumps(rec) + "\n")

    def tail(self, lines: int = 10):
        if not self.path.exists():
            return []
        return self.path.read_text().splitlines()[-lines:]
