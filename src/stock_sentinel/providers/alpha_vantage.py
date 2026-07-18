from __future__ import annotations

import os

import httpx
import pandas as pd
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from stock_sentinel.models import MarketData

from .base import MarketDataProvider, ProviderError
from .common import normalize_frame


class AlphaVantageProvider(MarketDataProvider):
    name = "alpha_vantage"

    @retry(
        retry=retry_if_exception_type(ProviderError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=3, max=30),
        reraise=True,
    )
    def fetch(self, symbol: str, period: str = "2y") -> MarketData:
        api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
        if not api_key:
            raise ProviderError("未设置 ALPHA_VANTAGE_API_KEY")
        try:
            response = httpx.get(
                "https://www.alphavantage.co/query",
                params={
                    "function": "TIME_SERIES_DAILY",
                    "symbol": symbol,
                    "outputsize": "compact",
                    "apikey": api_key,
                },
                timeout=25,
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ProviderError(f"Alpha Vantage 请求失败: {type(exc).__name__}") from exc
        if payload.get("Note") or payload.get("Information"):
            raise ProviderError("Alpha Vantage 达到调用额度或当前端点不可用")
        series = payload.get("Time Series (Daily)")
        if not isinstance(series, dict):
            raise ProviderError("Alpha Vantage 返回的数据结构不正确")
        rows = {
            date: {
                "open": values.get("1. open"),
                "high": values.get("2. high"),
                "low": values.get("3. low"),
                "close": values.get("4. close"),
                "volume": values.get("5. volume"),
            }
            for date, values in series.items()
        }
        frame = normalize_frame(pd.DataFrame.from_dict(rows, orient="index"))
        return MarketData(
            symbol=symbol,
            frame=frame,
            provider=self.name,
            updated_at=frame.index[-1].to_pydatetime(),
            delayed=True,
            delay_minutes=None,
            delay_note="Alpha Vantage 免费日线通常为收盘/历史数据，不应视为实时行情。",
            mode="live",
        )
