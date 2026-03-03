from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import yaml
from dotenv import load_dotenv


@dataclass
class RiskConfig:
    per_trade_risk_pct: float
    max_daily_loss_pct: float
    max_leverage: float
    max_position_notional: float


@dataclass
class RuntimeConfig:
    mode: str
    exchange: str
    symbol: str
    timeframe: str
    kill_switch: bool
    confirm_live: bool


@dataclass
class WebhookConfig:
    host: str
    port: int
    secret: str
    dedupe_window_sec: int


@dataclass
class BrainConfig:
    risk: RiskConfig
    runtime: RuntimeConfig
    webhook: WebhookConfig


def load_config(path: str | Path = "config/default.yaml") -> BrainConfig:
    load_dotenv(dotenv_path=Path('.env'), override=False)
    raw = yaml.safe_load(Path(path).read_text())
    runtime = raw["runtime"]
    webhook = raw.get("webhook", {})

    mode = os.getenv("BRAIN_MODE", runtime["mode"])
    exchange = os.getenv("BRAIN_EXCHANGE", runtime["exchange"])
    webhook_secret = os.getenv("TV_WEBHOOK_SECRET", webhook.get("secret", ""))

    return BrainConfig(
        risk=RiskConfig(**raw["risk"]),
        runtime=RuntimeConfig(
            mode=mode,
            exchange=exchange,
            symbol=runtime["symbol"],
            timeframe=runtime["timeframe"],
            kill_switch=bool(runtime["kill_switch"]),
            confirm_live=bool(runtime["confirm_live"]),
        ),
        webhook=WebhookConfig(
            host=webhook.get("host", "0.0.0.0"),
            port=int(webhook.get("port", 8090)),
            secret=webhook_secret,
            dedupe_window_sec=int(webhook.get("dedupe_window_sec", 90)),
        ),
    )
