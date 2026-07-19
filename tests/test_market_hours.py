from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from stock_sentinel.market_hours import is_cn_analysis_window, should_run_for_markets

SHANGHAI = ZoneInfo("Asia/Shanghai")


def test_cn_analysis_window_is_after_close_on_weekdays() -> None:
    assert is_cn_analysis_window(datetime(2026, 7, 20, 16, 30, tzinfo=SHANGHAI))
    assert not is_cn_analysis_window(datetime(2026, 7, 20, 14, 0, tzinfo=SHANGHAI))
    assert not is_cn_analysis_window(datetime(2026, 7, 19, 16, 30, tzinfo=SHANGHAI))


def test_domestic_market_routes_to_cn_close_window() -> None:
    now = datetime(2026, 7, 20, 16, 30, tzinfo=SHANGHAI)
    assert should_run_for_markets({"CN"}, now)
    assert should_run_for_markets({"HK"}, now)
    assert not should_run_for_markets(set(), now)
