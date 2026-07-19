from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any

from . import DISCLAIMER
from .config import PROJECT_ROOT, AppConfig
from .market_hours import SHANGHAI, is_cn_intraday_check_window
from .models import AlertEvent, StockConfig
from .notifier import EmailNotifier, NotificationError
from .providers.akshare_intraday import (
    IntradayProviderError,
    IntradayQuote,
    fetch_etf_intraday_quotes,
)
from .storage import load_json, mirror_json, save_json

DATA_DIR = PROJECT_ROOT / "data"
PUBLIC_DATA_DIR = PROJECT_ROOT / "frontend" / "public" / "data"


@dataclass(slots=True)
class IntradayRiskCheck:
    alert_type: str
    label: str
    reason: str
    triggered: bool


def evaluate_intraday_risks(
    stock: StockConfig,
    quote: IntradayQuote,
    daily: dict[str, Any],
    settings: dict[str, Any],
) -> list[IntradayRiskCheck]:
    abnormal_drop = float(settings.get("abnormal_drop_percent", 3.0))
    pullback_limit = float(settings.get("pullback_from_high_percent", 2.0))
    support_buffer = float(settings.get("support_break_percent", 0.5))
    support = float(daily.get("support") or 0)
    pullback = (quote.price / quote.high - 1) * 100 if quote.high > 0 else 0
    has_position = stock.quantity > 0

    stop_triggered = bool(
        has_position and stock.stop_loss_price and quote.price <= stock.stop_loss_price
    )
    take_profit_triggered = bool(
        has_position and stock.take_profit_price and quote.price >= stock.take_profit_price
    )
    support_triggered = bool(
        support > 0 and quote.price <= support * (1 - support_buffer / 100)
    )
    pullback_triggered = bool(pullback <= -pullback_limit) if pullback_limit > 0 else False
    abnormal_triggered = (
        bool(quote.change_percent <= -abnormal_drop) if abnormal_drop > 0 else False
    )

    return [
        IntradayRiskCheck(
            "intraday_stop_loss",
            "盘中触发止损参考价",
            f"当前价 {quote.price:.3f} ≤ 设定止损价 {stock.stop_loss_price or 0:.3f}",
            stop_triggered,
        ),
        IntradayRiskCheck(
            "intraday_take_profit",
            "盘中触发止盈参考价",
            f"当前价 {quote.price:.3f} ≥ 设定止盈价 {stock.take_profit_price or 0:.3f}",
            take_profit_triggered,
        ),
        IntradayRiskCheck(
            "intraday_support_break",
            "盘中跌破日线支撑参考位",
            f"当前价 {quote.price:.3f}，日线支撑 {support:.3f}，缓冲 {support_buffer:.1f}%",
            support_triggered,
        ),
        IntradayRiskCheck(
            "intraday_pullback",
            "盘中从高点明显回落",
            f"当前价较盘中高点 {quote.high:.3f} 回落 {pullback:.2f}%",
            pullback_triggered,
        ),
        IntradayRiskCheck(
            "intraday_abnormal_drop",
            "盘中异常下跌",
            f"相对昨收跌幅 {quote.change_percent:.2f}%，阈值 -{abnormal_drop:.2f}%",
            abnormal_triggered,
        ),
    ]


def _event(stock: StockConfig, quote: IntradayQuote, check: IntradayRiskCheck) -> AlertEvent:
    return AlertEvent(
        id=str(uuid.uuid4()),
        symbol=stock.symbol,
        name=stock.name,
        alert_type=check.alert_type,
        label=check.label,
        reason=check.reason,
        price=quote.price,
        score=None,
        created_at=datetime.now(UTC).isoformat(),
        simulated=True,
    )


def _is_today_alert(item: dict[str, Any], today: date) -> bool:
    try:
        created_at = datetime.fromisoformat(str(item.get("created_at", "")))
    except ValueError:
        return False
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=UTC)
    return created_at.astimezone(SHANGHAI).date() == today


def _accept_new_risks(
    stock: StockConfig,
    quote: IntradayQuote,
    checks: list[IntradayRiskCheck],
    state: dict[str, Any],
    cooldown_minutes: float,
) -> list[AlertEvent]:
    active = state.setdefault("intraday_active", {})
    last_alerts = state.setdefault("last_alerts", {})
    now = datetime.now(UTC)
    cooldown = timedelta(minutes=cooldown_minutes)
    accepted: list[AlertEvent] = []

    for check in checks:
        key = f"{stock.symbol}:{check.alert_type}"
        if not check.triggered:
            active.pop(key, None)
            continue
        if active.get(key):
            continue
        last_time = last_alerts.get(key)
        allowed = True
        if last_time:
            try:
                allowed = now - datetime.fromisoformat(last_time) >= cooldown
            except ValueError:
                allowed = True
        if allowed:
            accepted.append(_event(stock, quote, check))
            active[key] = True
            last_alerts[key] = now.isoformat()
    return accepted


def run_intraday_risk_check(
    config: AppConfig, logger: logging.Logger, force: bool = False
) -> dict[str, Any]:
    settings = config.intraday
    if not bool(settings.get("enabled", False)):
        return {"status": "skipped", "reason": "intraday_disabled"}
    if not force and not is_cn_intraday_check_window():
        logger.info("当前不在国内交易时段，跳过免费盘中快照请求")
        return {"status": "skipped", "reason": "outside_cn_trading_window"}

    stocks = [stock for stock in config.stocks if stock.market in {"CN", "HK"}]
    generated_at = datetime.now(UTC).isoformat()
    state_path = DATA_DIR / "state.json"
    state = load_json(state_path, {"symbols": {}, "last_alerts": {}, "failures": {}})
    history = load_json(DATA_DIR / "alerts.json", {"alerts": []})
    dashboard = load_json(DATA_DIR / "dashboard.json", {"stocks": []})
    daily_lookup = {item.get("symbol"): item for item in dashboard.get("stocks", [])}
    stock_lookup = {stock.symbol: stock for stock in stocks}
    notifier = EmailNotifier()

    try:
        quotes, errors = fetch_etf_intraday_quotes(
            [stock.symbol for stock in stocks],
            int(settings.get("interval_minutes", 15)),
        )
    except IntradayProviderError as exc:
        logger.exception("AKShare 免费盘中快照失败")
        errors = [{"symbol": stock.symbol, "message": str(exc)} for stock in stocks]
        quotes = []

    today = datetime.now(tz=SHANGHAI).date()
    fresh_symbols: set[str] = set()
    for quote in quotes:
        quote_date = datetime.fromisoformat(quote.updated_at).astimezone(SHANGHAI).date()
        if quote_date == today:
            fresh_symbols.add(quote.symbol)
            continue
        errors.append(
            {
                "symbol": quote.symbol,
                "message": (
                    f"免费分钟线尚未更新到今天，最新日期 {quote_date.isoformat()}；"
                    "不触发风险提醒"
                ),
            }
        )

    new_events: list[AlertEvent] = []
    cooldown = float(settings.get("cooldown_minutes", 60))
    for quote in quotes:
        stock = stock_lookup[quote.symbol]
        quote.name = stock.name
        if quote.symbol not in fresh_symbols:
            continue
        checks = evaluate_intraday_risks(stock, quote, daily_lookup.get(quote.symbol, {}), settings)
        events = _accept_new_risks(stock, quote, checks, state, cooldown)
        for event in events:
            if stock.email_enabled:
                try:
                    notifier.send_intraday_event(event, quote)
                except NotificationError:
                    logger.exception("%s 的盘中风险邮件发送失败", stock.symbol)
            history.setdefault("alerts", []).insert(0, event.to_dict())
            new_events.append(event)
        logger.info(
            "%s 盘中检查：价格 %.3f，涨跌 %.2f%%，新增风险 %d",
            quote.symbol,
            quote.price,
            quote.change_percent,
            len(events),
        )

    history["alerts"] = history.get("alerts", [])[:500]
    dashboard_summary = dashboard.get("summary")
    if isinstance(dashboard_summary, dict):
        dashboard_summary["today_signal_count"] = sum(
            1 for item in history["alerts"] if _is_today_alert(item, today)
        )
        dashboard_summary["new_signal_count"] = len(new_events)
        dashboard["intraday_status"] = {
            "provider": "akshare",
            "experimental": True,
            "latest_run": generated_at,
        }
        mirror_json(
            dashboard,
            DATA_DIR / "dashboard.json",
            PUBLIC_DATA_DIR / "dashboard.json",
        )
    payload = {
        "schema_version": 1,
        "generated_at": generated_at,
        "provider": "akshare",
        "experimental": True,
        "status": "正常" if not errors else ("部分失败" if quotes else "失败"),
        "market_open_check": not force,
        "interval_minutes": int(settings.get("interval_minutes", 15)),
        "successful_count": len(quotes),
        "monitored_count": len(stocks),
        "new_risk_count": len(new_events),
        "quotes": [quote.to_dict() for quote in quotes],
        "errors": errors,
        "delay_note": "AKShare 聚合公开网页行情，仅作实验性辅助，可能延迟、中断或发生字段变化。",
        "disclaimer": DISCLAIMER,
    }
    mirror_json(payload, DATA_DIR / "intraday.json", PUBLIC_DATA_DIR / "intraday.json")
    mirror_json(history, DATA_DIR / "alerts.json", PUBLIC_DATA_DIR / "alerts.json")
    state["last_intraday_run"] = generated_at
    save_json(state_path, state)
    return payload
