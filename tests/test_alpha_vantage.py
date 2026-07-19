from __future__ import annotations

from datetime import date, timedelta

import pytest

from stock_sentinel.providers.alpha_vantage import AlphaVantageProvider
from stock_sentinel.providers.base import ProviderError


class FakeResponse:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self.payload


def test_quota_message_is_not_retried(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = 0

    def fake_get(*args: object, **kwargs: object) -> FakeResponse:
        nonlocal calls
        calls += 1
        return FakeResponse({"Note": "daily limit reached"})

    monkeypatch.setenv("ALPHA_VANTAGE_API_KEY", "test-only")
    monkeypatch.setattr("stock_sentinel.providers.alpha_vantage.httpx.get", fake_get)

    with pytest.raises(ProviderError, match="不再重试"):
        AlphaVantageProvider().fetch("510300.SHH", "6mo")
    assert calls == 1


def test_daily_series_is_normalized(monkeypatch: pytest.MonkeyPatch) -> None:
    start = date(2026, 1, 1)
    series = {}
    for index in range(75):
        close = 4 + index * 0.01
        series[(start + timedelta(days=index)).isoformat()] = {
            "1. open": str(close - 0.01),
            "2. high": str(close + 0.03),
            "3. low": str(close - 0.02),
            "4. close": str(close),
            "5. volume": str(900000 + index * 1000),
        }
    payload = {"Time Series (Daily)": series}
    monkeypatch.setenv("ALPHA_VANTAGE_API_KEY", "test-only")
    monkeypatch.setattr(
        "stock_sentinel.providers.alpha_vantage.httpx.get",
        lambda *args, **kwargs: FakeResponse(payload),
    )

    data = AlphaVantageProvider().fetch("510300.SHH", "6mo")

    assert list(data.frame.columns) == ["open", "high", "low", "close", "volume"]
    assert data.frame.index.is_monotonic_increasing
    assert data.frame.iloc[-1]["close"] == pytest.approx(4.74)
    assert data.delayed is True


def test_provider_spaces_sequential_requests(monkeypatch: pytest.MonkeyPatch) -> None:
    monotonic_values = iter([100.0, 105.0])
    waits: list[float] = []
    provider = AlphaVantageProvider()

    monkeypatch.setattr(
        "stock_sentinel.providers.alpha_vantage.time.monotonic",
        lambda: next(monotonic_values),
    )
    monkeypatch.setattr(
        "stock_sentinel.providers.alpha_vantage.time.sleep", waits.append
    )

    provider._wait_for_rate_limit()
    provider._wait_for_rate_limit()

    assert waits == [pytest.approx(8.0)]
