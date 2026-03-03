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
class BrainConfig:
    risk: RiskConfig
    runtime: RuntimeConfig


def load_config(path: str | Path = "config/default.yaml") -> BrainConfig:
    load_dotenv(dotenv_path=Path('.env'), override=False)
    raw = yaml.safe_load(Path(path).read_text())
    runtime = raw["runtime"]

    mode = os.getenv("BRAIN_MODE", runtime["mode"])
    exchange = os.getenv("BRAIN_EXCHANGE", runtime["exchange"])

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
    )
