from __future__ import annotations

import numpy as np
import pandas as pd


def calculate_indicators(frame: pd.DataFrame) -> pd.DataFrame:
    """Calculate causal indicators; every row depends only on current/past bars."""
    result = frame.copy()
    close = result["close"]
    high = result["high"]
    low = result["low"]
    volume = result["volume"]

    for window in (5, 10, 20, 60):
        result[f"sma_{window}"] = close.rolling(window, min_periods=window).mean()
    result["ema_12"] = close.ewm(span=12, adjust=False, min_periods=12).mean()
    result["ema_26"] = close.ewm(span=26, adjust=False, min_periods=26).mean()
    result["macd"] = result["ema_12"] - result["ema_26"]
    result["macd_signal"] = result["macd"].ewm(span=9, adjust=False, min_periods=9).mean()
    result["macd_hist"] = result["macd"] - result["macd_signal"]

    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    relative_strength = gain / loss.replace(0, np.nan)
    result["rsi_14"] = (100 - (100 / (1 + relative_strength))).fillna(50)

    low_9 = low.rolling(9, min_periods=9).min()
    high_9 = high.rolling(9, min_periods=9).max()
    rsv = ((close - low_9) / (high_9 - low_9).replace(0, np.nan) * 100).fillna(50)
    result["kdj_k"] = rsv.ewm(alpha=1 / 3, adjust=False).mean()
    result["kdj_d"] = result["kdj_k"].ewm(alpha=1 / 3, adjust=False).mean()
    result["kdj_j"] = 3 * result["kdj_k"] - 2 * result["kdj_d"]

    middle = close.rolling(20, min_periods=20).mean()
    std = close.rolling(20, min_periods=20).std(ddof=0)
    result["bollinger_middle"] = middle
    result["bollinger_upper"] = middle + 2 * std
    result["bollinger_lower"] = middle - 2 * std

    true_range = pd.concat(
        [(high - low), (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1
    ).max(axis=1)
    result["atr_14"] = true_range.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    result["volume_sma_20"] = volume.rolling(20, min_periods=20).mean()
    result["volume_ratio"] = volume / result["volume_sma_20"].replace(0, np.nan)

    for days in (5, 20, 60):
        result[f"return_{days}d"] = close.pct_change(days) * 100
    daily_return = close.pct_change()
    result["volatility_annualized"] = (
        daily_return.rolling(60, min_periods=20).std(ddof=0) * np.sqrt(252)
    )
    expanding_peak = close.cummax()
    result["drawdown"] = close / expanding_peak - 1
    result["max_drawdown"] = result["drawdown"].cummin()
    rolling_peak = close.rolling(60, min_periods=20).max()
    result["rolling_drawdown_60d"] = close / rolling_peak - 1
    result["rolling_max_drawdown_60d"] = result["rolling_drawdown_60d"].rolling(
        60, min_periods=20
    ).min()
    result["support"] = low.rolling(20, min_periods=20).min()
    result["resistance"] = high.rolling(20, min_periods=20).max()
    return result.replace([np.inf, -np.inf], np.nan)
