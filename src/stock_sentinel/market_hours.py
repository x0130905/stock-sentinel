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


def should_run_for_markets(markets: set[str], now: datetime | None = None) -> bool:
    normalized = {market.upper() for market in markets}
    return bool(
        ("US" in normalized and is_us_analysis_window(now))
        or (normalized.intersection({"CN", "HK"}) and is_cn_analysis_window(now))
    )
