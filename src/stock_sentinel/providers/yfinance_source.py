from __future__ import annotations

from datetime import UTC

import pandas as pd
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from stock_sentinel.models import MarketData

from .base import MarketDataProvider, ProviderError
from .common import normalize_frame


class YFinanceProvider(MarketDataProvider):
    name = "yfinance"

    @retry(
        retry=retry_if_exception_type(ProviderError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def fetch(self, symbol: str, period: str = "2y") -> MarketData:
        try:
            import yfinance as yf
        except ImportError as exc:
            raise ProviderError("缺少 yfinance，请执行 pip install -e .[yfinance]") from exc
        try:
            frame = yf.download(
                symbol,
                period=period,
                interval="1d",
                auto_adjust=True,
                progress=False,
                threads=False,
                timeout=20,
            )
        except Exception as exc:
            raise ProviderError(f"yfinance 请求失败: {type(exc).__name__}") from exc
        if isinstance(frame.columns, pd.MultiIndex):
            frame.columns = frame.columns.get_level_values(0)
        frame = normalize_frame(frame)
        timestamp = frame.index[-1].to_pydatetime()
        return MarketData(
            symbol=symbol,
            frame=frame,
            provider=self.name,
            updated_at=timestamp if timestamp.tzinfo else timestamp.replace(tzinfo=UTC),
            delayed=True,
            delay_minutes=None,
            delay_note=(
                "yfinance 免费数据不保证实时，可能延迟或仅为当日未完成日线；"
                "仅适用于个人研究，请遵守 Yahoo 数据使用条款。"
            ),
            mode="live",
        )
