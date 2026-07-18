from __future__ import annotations

from stock_sentinel.analysis import analyze_market_data
from stock_sentinel.models import StockConfig
from stock_sentinel.providers.sample import SampleProvider


def test_analysis_has_separate_scores_and_disclosure() -> None:
    data = SampleProvider().fetch("AAPL", "1y")
    stock = StockConfig(symbol="AAPL", name="Apple", cost_basis=100, quantity=2)
    result = analyze_market_data(data, stock, {})
    assert 0 <= result.buy_score <= 100
    assert 0 <= result.sell_score <= 100
    assert len(result.buy_criteria) == 7
    assert len(result.sell_criteria) == 7
    assert result.human_confirmation_required is True
    assert result.delayed is True
    assert "演示数据" in result.delay_note
    assert len(result.price_history) == 120
