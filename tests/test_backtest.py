from __future__ import annotations

import pandas as pd

from stock_sentinel.backtest import run_backtest
from stock_sentinel.models import StockConfig


def test_backtest_completes_with_next_open_execution(sample_frame: pd.DataFrame) -> None:
    result = run_backtest(
        sample_frame,
        StockConfig(symbol="TEST", name="Test"),
        {"buy_alert_threshold": 55, "sell_alert_threshold": 55},
        {"initial_cash": 100000, "fee_rate": 0.001, "slippage_rate": 0.0005},
    )
    assert result["status"] == "completed"
    assert result["assumptions"]["lookahead_protection"] is True
    assert "下一交易日开盘价" in result["assumptions"]["execution_rule"]
    assert result["metrics"]["final_equity"] > 0
    assert result["metrics"]["trade_count"] >= 0
