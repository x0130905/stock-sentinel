from __future__ import annotations

import sys
from types import SimpleNamespace

import pandas as pd

from stock_sentinel.intraday import _accept_new_risks, evaluate_intraday_risks
from stock_sentinel.models import StockConfig
from stock_sentinel.providers.akshare_intraday import IntradayQuote, fetch_etf_intraday_quotes


def _quote(**overrides: float) -> IntradayQuote:
    values = {
        "price": 3.95,
        "previous_close": 4.08,
        "open": 4.05,
        "high": 4.05,
        "low": 3.94,
        "change_percent": -3.2,
        "volume": 1_000_000.0,
        "amount": 4_000_000.0,
    }
    values.update(overrides)
    return IntradayQuote(
        symbol="510300.SHH",
        name="沪深300ETF",
        updated_at="2026-07-20T10:15:00+08:00",
        **values,
    )


def test_akshare_batch_snapshot_is_normalized(monkeypatch) -> None:
    frame = pd.DataFrame(
        [
            {
                "时间": "2026-07-17 15:00:00",
                "开盘": 4.0,
                "收盘": 4.0,
                "最高": 4.02,
                "最低": 3.98,
                "成交量": 1000,
                "成交额": 4000,
            },
            {
                "时间": "2026-07-20 09:45:00",
                "开盘": 4.02,
                "收盘": 4.1,
                "最高": 4.12,
                "最低": 4.01,
                "成交量": 1200,
                "成交额": 4900,
            },
        ]
    )
    def fake_minute_frame(**kwargs):
        return frame if kwargs["symbol"] == "510300" else pd.DataFrame()

    monkeypatch.setitem(
        sys.modules,
        "akshare",
        SimpleNamespace(fund_etf_hist_min_em=fake_minute_frame),
    )

    quotes, errors = fetch_etf_intraday_quotes(["510300.SHH", "159915.SHZ"])

    assert len(quotes) == 1
    assert quotes[0].symbol == "510300.SHH"
    assert quotes[0].price == 4.1
    assert errors[0]["symbol"] == "159915.SHZ"


def test_intraday_risk_rules_and_deduplication() -> None:
    stock = StockConfig(
        symbol="510300.SHH",
        name="沪深300ETF",
        quantity=100,
        stop_loss_price=4.0,
    )
    settings = {
        "abnormal_drop_percent": 3,
        "pullback_from_high_percent": 2,
        "support_break_percent": 0.5,
    }
    checks = evaluate_intraday_risks(stock, _quote(), {"support": 4.0}, settings)
    triggered = {check.alert_type for check in checks if check.triggered}

    assert triggered == {
        "intraday_stop_loss",
        "intraday_support_break",
        "intraday_pullback",
        "intraday_abnormal_drop",
    }

    state: dict = {}
    first = _accept_new_risks(stock, _quote(), checks, state, cooldown_minutes=60)
    second = _accept_new_risks(stock, _quote(), checks, state, cooldown_minutes=60)
    assert len(first) == 4
    assert second == []


def test_position_rules_do_not_trigger_without_a_position() -> None:
    stock = StockConfig(
        symbol="510300.SHH",
        name="沪深300ETF",
        quantity=0,
        stop_loss_price=4.0,
        take_profit_price=3.9,
    )
    checks = evaluate_intraday_risks(stock, _quote(), {}, {})
    position_types = {"intraday_stop_loss", "intraday_take_profit"}
    assert not any(check.triggered for check in checks if check.alert_type in position_types)
