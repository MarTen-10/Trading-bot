from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import time
import tempfile
import fcntl
import os


@dataclass
class Usage:
    tool_calls: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    usd: float = 0.0


class BudgetExceeded(Exception):
    pass


class BudgetController:
    def __init__(self, limits, run_id: str, state_path: str = "/home/marten/.openclaw/workspace/logs/anubis_l0_daily.json"):
        self.limits = limits
        self.run_id = run_id
        self.started_at = time.time()
        self.usage = Usage()
        self.state_path = Path(state_path)
        self._daily = self._load_daily()

    def _today(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def _load_daily(self):
        if self.state_path.exists():
            try:
                data = json.loads(self.state_path.read_text())
                if data.get("date") == self._today():
                    return data
            except Exception:
                pass
        return {"date": self._today(), "usd": 0.0}

    def _save_daily(self):
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        lock_path = self.state_path.with_suffix('.lock')
        with lock_path.open('w') as lk:
            fcntl.flock(lk.fileno(), fcntl.LOCK_EX)
            fd, tmp = tempfile.mkstemp(prefix='anubis_l0_daily_', dir=str(self.state_path.parent))
            try:
                with open(fd, 'w', encoding='utf-8') as f:
                    f.write(json.dumps(self._daily))
                    f.flush()
                    os.fsync(f.fileno())
                Path(tmp).replace(self.state_path)
            finally:
                if Path(tmp).exists():
                    Path(tmp).unlink(missing_ok=True)
            fcntl.flock(lk.fileno(), fcntl.LOCK_UN)

    def check_or_raise(self, context: str = ""):
        elapsed = time.time() - self.started_at
        total_tokens = self.usage.tokens_in + self.usage.tokens_out
        if self.usage.tool_calls > self.limits.max_tool_calls_per_run:
            raise BudgetExceeded(f"tool_calls_exceeded:{context}")
        if elapsed > self.limits.max_seconds_per_run:
            raise BudgetExceeded(f"time_exceeded:{context}")
        if total_tokens > self.limits.max_tokens_per_run:
            raise BudgetExceeded(f"tokens_exceeded:{context}")
        if self.usage.usd > self.limits.max_usd_per_run:
            raise BudgetExceeded(f"run_cost_exceeded:{context}")
        if self._daily.get("usd", 0.0) > self.limits.max_usd_per_day:
            raise BudgetExceeded(f"daily_cost_exceeded:{context}")

    def record_usage(self, *, tool_calls=0, tokens_in=0, tokens_out=0, usd=0.0):
        self.usage.tool_calls += int(tool_calls)
        self.usage.tokens_in += int(tokens_in)
        self.usage.tokens_out += int(tokens_out)
        self.usage.usd += float(usd)
        self._daily["usd"] = float(self._daily.get("usd", 0.0)) + float(usd)
        self._save_daily()

    def summarize(self):
        total_tokens = self.usage.tokens_in + self.usage.tokens_out
        return {
            "run_id": self.run_id,
            "usage": asdict(self.usage),
            "tokens_total": total_tokens,
            "daily_usd": self._daily.get("usd", 0.0),
            "limits": {
                "max_tool_calls_per_run": self.limits.max_tool_calls_per_run,
                "max_seconds_per_run": self.limits.max_seconds_per_run,
                "max_tokens_per_run": self.limits.max_tokens_per_run,
                "max_usd_per_run": self.limits.max_usd_per_run,
                "max_usd_per_day": self.limits.max_usd_per_day,
                "max_retries_per_action": self.limits.max_retries_per_action,
                "max_concurrency": self.limits.max_concurrency,
            },
        }
