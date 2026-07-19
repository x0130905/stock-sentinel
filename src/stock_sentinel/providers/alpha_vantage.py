from __future__ import annotations

import os

import httpx
import pandas as pd
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from stock_sentinel.models import MarketData

from .base import MarketDataProvider, ProviderError
from .common import normalize_frame


class _TransientAlphaVantageError(ProviderError):
    """Only errors that are safe to retry without wasting the daily quota."""


class AlphaVantageProvider(MarketDataProvider):
    name = "alpha_vantage"

    @retry(
        retry=retry_if_exception_type(_TransientAlphaVantageError),
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=2, min=2, max=8),
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
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            raise _TransientAlphaVantageError(
                f"Alpha Vantage 临时网络错误: {type(exc).__name__}"
            ) from exc
        except httpx.HTTPStatusError as exc:
            if 500 <= exc.response.status_code < 600:
                raise _TransientAlphaVantageError(
                    f"Alpha Vantage 服务端暂时异常: HTTP {exc.response.status_code}"
                ) from exc
            raise ProviderError(
                f"Alpha Vantage 请求失败: HTTP {exc.response.status_code}"
            ) from exc
        except ValueError as exc:
            raise _TransientAlphaVantageError("Alpha Vantage 临时返回了无效 JSON") from exc

        if payload.get("Note") or payload.get("Information"):
            raise ProviderError("Alpha Vantage 达到调用额度或当前端点不可用，本次不再重试")
        if payload.get("Error Message"):
            raise ProviderError(f"Alpha Vantage 不接受代码 {symbol}，请检查市场后缀")
        series = payload.get("Time Series (Daily)")
        if not isinstance(series, dict):
            raise ProviderError("Alpha Vantage 返回的数据结构不正确，本次不再重试")
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
            delay_note=(
                "Alpha Vantage 免费层为日线收盘数据，compact 通常只含最近约 100 个交易日；"
                "不应视为实时行情。"
            ),
            mode="live",
        )
