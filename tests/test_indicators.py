from __future__ import annotations

import pandas as pd

from stock_sentinel.indicators import calculate_indicators


def test_all_required_indicators_are_calculated(sample_frame: pd.DataFrame) -> None:
    result = calculate_indicators(sample_frame)
    expected = {
        "sma_5", "sma_10", "sma_20", "sma_60", "ema_12", "ema_26", "macd",
        "macd_signal", "rsi_14", "kdj_k", "kdj_d", "kdj_j", "bollinger_upper",
        "bollinger_lower", "atr_14", "volume_sma_20", "volume_ratio", "return_5d",
        "return_20d", "return_60d", "max_drawdown", "volatility_annualized", "support",
        "resistance", "rolling_max_drawdown_60d",
    }
    assert expected.issubset(result.columns)
    assert result.iloc[-1]["close"] > 0
    assert 0 <= result.iloc[-1]["rsi_14"] <= 100


def test_indicators_do_not_change_when_future_rows_are_appended(sample_frame: pd.DataFrame) -> None:
    short = calculate_indicators(sample_frame.iloc[:120])
    full = calculate_indicators(sample_frame)
    columns = ["sma_20", "macd", "rsi_14", "atr_14", "support", "resistance"]
    pd.testing.assert_series_equal(short.iloc[-1][columns], full.iloc[119][columns])
