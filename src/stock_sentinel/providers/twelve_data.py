from __future__ import annotations

import os

import httpx
import pandas as pd
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from stock_sentinel.models import MarketData

from .base import MarketDataProvider, ProviderError
from .common import normalize_frame, period_to_outputsize


class TwelveDataProvider(MarketDataProvider):
    name = "twelve_data"

    @retry(
        retry=retry_if_exception_type(ProviderError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=3, max=30),
        reraise=True,
    )
    def fetch(self, symbol: str, period: str = "2y") -> MarketData:
        api_key = os.getenv("TWELVE_DATA_API_KEY")
        if not api_key:
            raise ProviderError("未设置 TWELVE_DATA_API_KEY")
        try:
            response = httpx.get(
                "https://api.twelvedata.com/time_series",
                params={
                    "symbol": symbol,
                    "interval": "1day",
                    "outputsize": min(period_to_outputsize(period), 5000),
                    "order": "ASC",
                    "apikey": api_key,
                },
                timeout=25,
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ProviderError(f"Twelve Data 请求失败: {type(exc).__name__}") from exc
        if payload.get("status") == "error":
            raise ProviderError(f"Twelve Data 返回错误: {payload.get('message', '未知错误')}")
        values = payload.get("values")
        if not isinstance(values, list):
            raise ProviderError("Twelve Data 返回的数据结构不正确")
        frame = normalize_frame(pd.DataFrame(values).set_index("datetime"))
        return MarketData(
            symbol=symbol,
            frame=frame,
            provider=self.name,
            updated_at=frame.index[-1].to_pydatetime(),
            delayed=True,
            delay_minutes=None,
            delay_note=(
                "页面按保守口径标记为可能延迟；实际新鲜度取决于 Twelve Data 套餐、市场和交易时段。"
            ),
            mode="live",
        )
