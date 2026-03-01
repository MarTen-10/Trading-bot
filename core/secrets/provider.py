from __future__ import annotations

import os
from pathlib import Path


class SecretsProvider:
    """Single source of truth for secrets.

    Resolution order:
    1) Process environment (systemd EnvironmentFile lands here)
    2) Local .env file (default: workspace/.env)

    Secret values are never logged.
    """

    def __init__(self, env_file: str | None = None):
        self.env_file = Path(env_file or os.getenv("ANUBIS_ENV_FILE", ".env"))
        self._cache: dict[str, str] = {}
        self._loaded = False

    def get(self, key: str, default: str = "") -> str:
        if key in os.environ:
            return os.environ[key]
        self._load_env_file_once()
        return self._cache.get(key, default)

    def _load_env_file_once(self) -> None:
        if self._loaded:
            return
        self._loaded = True

        if not self.env_file.exists():
            return

        for line in self.env_file.read_text().splitlines():
            raw = line.strip()
            if not raw or raw.startswith("#") or "=" not in raw:
                continue
            key, value = raw.split("=", 1)
            self._cache[key.strip()] = value.strip().strip('"').strip("'")
