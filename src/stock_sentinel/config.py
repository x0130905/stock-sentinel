from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from .models import StockConfig

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class ConfigError(ValueError):
    """Raised when user configuration is unsafe or invalid."""


@dataclass(slots=True)
class AppConfig:
    raw: dict[str, Any]
    path: Path

    @property
    def provider(self) -> str:
        return os.getenv("STOCK_DATA_PROVIDER", self.raw.get("provider", "sample")).lower()

    @property
    def stocks(self) -> list[StockConfig]:
        return [StockConfig(**item) for item in self.raw.get("stocks", [])]

    @property
    def scoring(self) -> dict[str, Any]:
        return self.raw.get("scoring", {})

    @property
    def alerts(self) -> dict[str, Any]:
        return self.raw.get("alerts", {})

    @property
    def backtest(self) -> dict[str, Any]:
        return self.raw.get("backtest", {})

    @property
    def history_period(self) -> str:
        return str(self.raw.get("history_period", "2y"))

    @property
    def frequency_minutes(self) -> int:
        return int(self.raw.get("analysis_frequency_minutes", 15))


def load_config(path: str | Path | None = None) -> AppConfig:
    load_dotenv(PROJECT_ROOT / ".env")
    config_path = Path(path) if path else PROJECT_ROOT / "config" / "settings.json"
    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigError(f"无法读取配置文件 {config_path}: {exc}") from exc
    validate_config(raw)
    return AppConfig(raw=raw, path=config_path)


def validate_config(raw: dict[str, Any]) -> None:
    providers = {"sample", "yfinance", "alpha_vantage", "twelve_data"}
    provider = str(raw.get("provider", "sample")).lower()
    env_provider = os.getenv("STOCK_DATA_PROVIDER", provider).lower()
    if env_provider not in providers:
        raise ConfigError(f"不支持的数据源: {env_provider}")
    stocks = raw.get("stocks")
    if not isinstance(stocks, list) or not stocks:
        raise ConfigError("至少需要配置一只股票")
    seen: set[str] = set()
    for item in stocks:
        symbol = str(item.get("symbol", "")).strip().upper()
        if not symbol or len(symbol) > 20 or not all(c.isalnum() or c in ".-" for c in symbol):
            raise ConfigError(f"股票代码不合法: {symbol!r}")
        if symbol in seen:
            raise ConfigError(f"股票代码重复: {symbol}")
        seen.add(symbol)
        market = str(item.get("market", "US")).upper()
        if market not in {"US", "CN", "HK"}:
            raise ConfigError(f"市场必须是 US、CN 或 HK: {symbol}")
        for key in ("cost_basis", "quantity", "target_return_percent", "max_loss_percent"):
            if float(item.get(key, 0)) < 0:
                raise ConfigError(f"{symbol} 的 {key} 不能为负数")
    frequency = int(raw.get("analysis_frequency_minutes", 15))
    if frequency < 5 or frequency > 1440:
        raise ConfigError("分析频率应在 5 到 1440 分钟之间")
    scoring = raw.get("scoring", {})
    for key in ("buy_alert_threshold", "sell_alert_threshold"):
        value = int(scoring.get(key, 65))
        if not 0 <= value <= 100:
            raise ConfigError(f"{key} 必须在 0 到 100 之间")
    confirmation_runs = int(raw.get("alerts", {}).get("score_confirmation_runs", 1))
    if not 1 <= confirmation_runs <= 5:
        raise ConfigError("score_confirmation_runs 必须在 1 到 5 之间")
