from __future__ import annotations

from abc import ABC, abstractmethod

from stock_sentinel.models import MarketData


class ProviderError(RuntimeError):
    """A safe, user-facing market data provider error."""


class MarketDataProvider(ABC):
    name: str

    @abstractmethod
    def fetch(self, symbol: str, period: str = "2y") -> MarketData:
        """Return causal daily OHLCV history ordered from oldest to newest."""
