from __future__ import annotations

from dataclasses import replace

from stock_sentinel.alerts import build_alerts
from stock_sentinel.analysis import analyze_market_data
from stock_sentinel.models import StockConfig
from stock_sentinel.providers.sample import SampleProvider


def test_regular_alert_is_deduplicated_but_stop_loss_is_not() -> None:
    stock = StockConfig(
        symbol="AAPL", name="Apple", stop_loss_price=10_000, buy_alert_enabled=True
    )
    result = analyze_market_data(SampleProvider().fetch("AAPL", "1y"), stock, {})
    result = replace(result, buy_score=90)
    state: dict = {}
    first = build_alerts(result, stock, {"buy_alert_threshold": 65}, {"cooldown_hours": 4}, state)
    second = build_alerts(result, stock, {"buy_alert_threshold": 65}, {"cooldown_hours": 4}, state)
    assert any(item.alert_type == "buy_score" for item in first)
    assert sum(item.alert_type == "stop_loss" for item in first) == 1
    assert not any(item.alert_type == "buy_score" for item in second)
    assert sum(item.alert_type == "stop_loss" for item in second) == 1
