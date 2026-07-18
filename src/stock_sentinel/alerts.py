from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from .models import AlertEvent, AnalysisResult, StockConfig


def _event(
    result: AnalysisResult, alert_type: str, label: str, reason: str, score: int | None
) -> AlertEvent:
    now = datetime.now(UTC)
    return AlertEvent(
        id=str(uuid.uuid4()),
        symbol=result.symbol,
        name=result.name,
        alert_type=alert_type,
        label=label,
        reason=reason,
        price=result.price,
        score=score,
        created_at=now.isoformat(),
    )


def build_alerts(
    result: AnalysisResult,
    stock: StockConfig,
    scoring: dict[str, Any],
    alert_settings: dict[str, Any],
    state: dict[str, Any],
) -> list[AlertEvent]:
    symbol_state = state.setdefault("symbols", {}).setdefault(result.symbol, {})
    previous_buy = int(symbol_state.get("buy_score", 0))
    previous_sell = int(symbol_state.get("sell_score", 0))
    buy_threshold = int(scoring.get("buy_alert_threshold", 65))
    sell_threshold = int(scoring.get("sell_alert_threshold", 65))
    candidates: list[AlertEvent] = []

    if stock.buy_alert_enabled and previous_buy < buy_threshold <= result.buy_score:
        reasons = "；".join(item.label for item in result.buy_criteria if item.triggered)
        candidates.append(_event(result, "buy_score", "可能适合买入", reasons, result.buy_score))
    if stock.sell_alert_enabled and previous_sell < sell_threshold <= result.sell_score:
        reasons = "；".join(item.label for item in result.sell_criteria if item.triggered)
        candidates.append(_event(result, "sell_score", "可能适合卖出", reasons, result.sell_score))
    if stock.take_profit_price and result.price >= stock.take_profit_price:
        candidates.append(
            _event(
                result,
                "take_profit",
                "触发止盈参考价",
                f"当前价 {result.price:.2f} ≥ 止盈价 {stock.take_profit_price:.2f}",
                result.sell_score,
            )
        )
    if stock.stop_loss_price and result.price <= stock.stop_loss_price:
        candidates.append(
            _event(
                result,
                "stop_loss",
                "触发止损参考价",
                f"当前价 {result.price:.2f} ≤ 止损价 {stock.stop_loss_price:.2f}",
                result.sell_score,
            )
        )
    abnormal = float(scoring.get("abnormal_daily_change_percent", 7))
    if abs(result.change_percent) >= abnormal:
        candidates.append(
            _event(
                result,
                "abnormal_move",
                "单日异常涨跌",
                f"单日涨跌 {result.change_percent:+.2f}%，超过 {abnormal:.2f}% 阈值",
                None,
            )
        )

    accepted: list[AlertEvent] = []
    cooldown = timedelta(hours=float(alert_settings.get("cooldown_hours", 4)))
    last_alerts = state.setdefault("last_alerts", {})
    now = datetime.now(UTC)
    for candidate in candidates:
        key = f"{result.symbol}:{candidate.alert_type}"
        last_time = last_alerts.get(key)
        allowed = candidate.alert_type == "stop_loss"
        if last_time and not allowed:
            try:
                allowed = now - datetime.fromisoformat(last_time) >= cooldown
            except ValueError:
                allowed = True
        elif not last_time:
            allowed = True
        if allowed:
            accepted.append(candidate)
            last_alerts[key] = now.isoformat()

    symbol_state.update(
        {"buy_score": result.buy_score, "sell_score": result.sell_score, "price": result.price}
    )
    return accepted
