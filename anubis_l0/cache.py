import hashlib
import json
import time
from pathlib import Path


class SimpleCache:
    def __init__(self, path: str = "/home/marten/.openclaw/workspace/logs/anubis_l0_cache.json"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = {}
        if self.path.exists():
            try:
                self.db = json.loads(self.path.read_text())
            except Exception:
                self.db = {}

    def _key(self, payload: str):
        return hashlib.sha256(payload.encode()).hexdigest()

    def get(self, payload: str, ttl_seconds: int):
        k = self._key(payload)
        v = self.db.get(k)
        if not v:
            return None
        if time.time() - v["ts"] > ttl_seconds:
            self.db.pop(k, None)
            return None
        return v["value"]

    def set(self, payload: str, value):
        k = self._key(payload)
        self.db[k] = {"ts": time.time(), "value": value}
        self.path.write_text(json.dumps(self.db))
