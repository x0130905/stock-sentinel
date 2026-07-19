from __future__ import annotations

from datetime import datetime, time
from zoneinfo import ZoneInfo

NEW_YORK = ZoneInfo("America/New_York")
SHANGHAI = ZoneInfo("Asia/Shanghai")


def is_us_analysis_window(now: datetime | None = None) -> bool:
    current = (now or datetime.now(tz=NEW_YORK)).astimezone(NEW_YORK)
    if current.weekday() >= 5:
        return False
    return time(9, 25) <= current.time() <= time(16, 20)


def is_cn_analysis_window(now: datetime | None = None) -> bool:
    current = (now or datetime.now(tz=SHANGHAI)).astimezone(SHANGHAI)
    if current.weekday() >= 5:
        return False
    return time(15, 30) <= current.time() <= time(18, 30)


def is_cn_trading_window(now: datetime | None = None) -> bool:
    current = (now or datetime.now(tz=SHANGHAI)).astimezone(SHANGHAI)
    if current.weekday() >= 5:
        return False
    current_time = current.time()
    morning = time(9, 30) <= current_time <= time(11, 30)
    afternoon = time(13, 0) <= current_time <= time(15, 0)
    return morning or afternoon


def is_cn_intraday_check_window(now: datetime | None = None) -> bool:
    current = (now or datetime.now(tz=SHANGHAI)).astimezone(SHANGHAI)
    if current.weekday() >= 5:
        return False
    current_time = current.time()
    morning = time(9, 45) <= current_time <= time(11, 30)
    afternoon = time(13, 15) <= current_time <= time(15, 0)
    return morning or afternoon


def should_run_for_markets(markets: set[str], now: datetime | None = None) -> bool:
    normalized = {market.upper() for market in markets}
    return bool(
        ("US" in normalized and is_us_analysis_window(now))
        or (normalized.intersection({"CN", "HK"}) and is_cn_analysis_window(now))
    )
