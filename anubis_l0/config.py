from dataclasses import dataclass


@dataclass
class L0Limits:
    max_tool_calls_per_run: int = 20
    max_seconds_per_run: int = 300
    max_tokens_per_run: int = 60000
    max_usd_per_run: float = 5.0
    max_usd_per_day: float = 25.0
    max_retries_per_action: int = 2
    max_concurrency: int = 1
    default_temperature: float = 0.2
    cache_ttl_seconds: int = 3600
