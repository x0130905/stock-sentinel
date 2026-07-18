from __future__ import annotations

import hashlib
from datetime import UTC, datetime

import numpy as np
import pandas as pd

from stock_sentinel.models import MarketData

from .base import MarketDataProvider
from .common import normalize_frame, period_to_outputsize


class SampleProvider(MarketDataProvider):
    name = "sample"

    def fetch(self, symbol: str, period: str = "2y") -> MarketData:
        size = period_to_outputsize(period)
        seed = int(hashlib.sha256(symbol.encode("utf-8")).hexdigest()[:8], 16)
        rng = np.random.default_rng(seed)
        index = pd.bdate_range(end=pd.Timestamp.now(tz="UTC").normalize(), periods=size)
        base = 80 + (seed % 160)
        drift = 0.00035 + (seed % 7) / 100_000
        daily_return = rng.normal(drift, 0.018, size)
        close = base * np.exp(np.cumsum(daily_return))
        overnight = rng.normal(0, 0.004, size)
        open_price = close * (1 + overnight)
        spread = rng.uniform(0.004, 0.025, size)
        high = np.maximum(open_price, close) * (1 + spread)
        low = np.minimum(open_price, close) * (1 - spread)
        volume = rng.integers(8_000_000, 95_000_000, size).astype(float)
        volume[-1] *= 1.35
        frame = normalize_frame(
            pd.DataFrame(
                {"open": open_price, "high": high, "low": low, "close": close, "volume": volume},
                index=index,
            )
        )
        return MarketData(
            symbol=symbol,
            frame=frame,
            provider=self.name,
            updated_at=datetime.now(UTC),
            delayed=True,
            delay_minutes=None,
            delay_note="演示数据由固定随机种子生成，不是真实行情，严禁据此进行交易。",
            mode="sample",
        )
