from __future__ import annotations

from datetime import datetime, time
from zoneinfo import ZoneInfo

NEW_YORK = ZoneInfo("America/New_York")


def is_us_analysis_window(now: datetime | None = None) -> bool:
    current = (now or datetime.now(tz=NEW_YORK)).astimezone(NEW_YORK)
    if current.weekday() >= 5:
        return False
    return time(9, 25) <= current.time() <= time(16, 20)


def should_run_for_markets(markets: set[str], now: datetime | None = None) -> bool:
    if markets == {"US"}:
        return is_us_analysis_window(now)
    current = now or datetime.now().astimezone()
    return current.weekday() < 5
