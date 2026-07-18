from __future__ import annotations

import pandas as pd

from .base import ProviderError

REQUIRED_COLUMNS = ("open", "high", "low", "close", "volume")


def normalize_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        raise ProviderError("行情数据为空")
    result = frame.copy()
    result.columns = [str(c).lower().replace(" ", "_") for c in result.columns]
    if "adjusted_close" in result and "close" not in result:
        result["close"] = result["adjusted_close"]
    missing = [column for column in REQUIRED_COLUMNS if column not in result]
    if missing:
        raise ProviderError(f"行情缺少字段: {', '.join(missing)}")
    result = result.loc[:, list(REQUIRED_COLUMNS)].apply(pd.to_numeric, errors="coerce")
    result.index = pd.to_datetime(result.index, utc=True)
    result = result[~result.index.duplicated(keep="last")].sort_index().dropna(subset=["close"])
    result = result[(result["close"] > 0) & (result["high"] >= result["low"])]
    if len(result) < 70:
        raise ProviderError(f"有效历史行情不足 70 条，当前只有 {len(result)} 条")
    return result


def period_to_outputsize(period: str) -> int:
    return {"6mo": 140, "1y": 260, "2y": 520, "5y": 1260}.get(period, 520)
