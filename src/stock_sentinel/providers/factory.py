from __future__ import annotations

from .alpha_vantage import AlphaVantageProvider
from .base import MarketDataProvider, ProviderError
from .sample import SampleProvider
from .twelve_data import TwelveDataProvider
from .yfinance_source import YFinanceProvider


def create_provider(name: str) -> MarketDataProvider:
    providers: dict[str, type[MarketDataProvider]] = {
        "sample": SampleProvider,
        "yfinance": YFinanceProvider,
        "alpha_vantage": AlphaVantageProvider,
        "twelve_data": TwelveDataProvider,
    }
    try:
        return providers[name.lower()]()
    except KeyError as exc:
        raise ProviderError(f"未知数据源: {name}") from exc
