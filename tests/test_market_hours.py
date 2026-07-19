from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from stock_sentinel.market_hours import (
    is_cn_analysis_window,
    is_cn_intraday_check_window,
    is_cn_trading_window,
    should_run_for_markets,
)

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


def test_cn_trading_window_has_lunch_break_and_weekend_guard() -> None:
    assert is_cn_trading_window(datetime(2026, 7, 20, 10, 15, tzinfo=SHANGHAI))
    assert not is_cn_trading_window(datetime(2026, 7, 20, 12, 0, tzinfo=SHANGHAI))
    assert is_cn_trading_window(datetime(2026, 7, 20, 14, 45, tzinfo=SHANGHAI))
    assert not is_cn_trading_window(datetime(2026, 7, 19, 10, 15, tzinfo=SHANGHAI))


def test_intraday_check_waits_for_first_completed_bar() -> None:
    assert not is_cn_intraday_check_window(datetime(2026, 7, 20, 9, 30, tzinfo=SHANGHAI))
    assert is_cn_intraday_check_window(datetime(2026, 7, 20, 9, 45, tzinfo=SHANGHAI))
    assert not is_cn_intraday_check_window(datetime(2026, 7, 20, 13, 0, tzinfo=SHANGHAI))
    assert is_cn_intraday_check_window(datetime(2026, 7, 20, 13, 15, tzinfo=SHANGHAI))
