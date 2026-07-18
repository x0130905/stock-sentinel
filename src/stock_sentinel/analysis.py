from __future__ import annotations

import math
from typing import Any

import pandas as pd

from .indicators import calculate_indicators
from .models import AnalysisResult, MarketData, StockConfig
from .scoring import calculate_scores


def _safe(value: Any, digits: int = 4) -> float | None:
    try:
        number = float(value)
        return round(number, digits) if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None


def analyze_market_data(
    market_data: MarketData, stock: StockConfig, params: dict[str, Any]
) -> AnalysisResult:
    indicators = calculate_indicators(market_data.frame)
    if len(indicators) < 70:
        raise ValueError(f"{stock.symbol} 历史数据不足，至少需要 70 条")
    row = indicators.iloc[-1]
    previous = indicators.iloc[-2]
    buy, sell = calculate_scores(indicators, stock, params)
    price = float(row["close"])
    previous_close = float(previous["close"])
    change_percent = (price / previous_close - 1) * 100 if previous_close else 0
    atr = float(row.get("atr_14") or price * 0.02)
    support = float(row.get("support") or price)
    resistance = float(row.get("resistance") or price)
    volatility = float(row.get("volatility_annualized") or 0)
    max_drawdown = float(row.get("rolling_max_drawdown_60d") or row.get("max_drawdown") or 0)
    high_vol = float(params.get("high_volatility_annualized", 0.45))
    high_drawdown = float(params.get("high_drawdown_percent", 25)) / 100
    stop_triggered = any(item.key == "stop_loss" and item.triggered for item in sell.criteria)
    take_profit_triggered = any(
        item.key == "take_profit" and item.triggered for item in sell.criteria
    )

    if stop_triggered or volatility >= high_vol or max_drawdown <= -high_drawdown:
        risk_level = "高"
    elif volatility >= high_vol * 0.7 or max_drawdown <= -high_drawdown * 0.7:
        risk_level = "中"
    else:
        risk_level = "低"

    buy_threshold = int(params.get("buy_alert_threshold", 65))
    sell_threshold = int(params.get("sell_alert_threshold", 65))
    if stop_triggered:
        signal_label = "风险较高"
    elif sell.score >= sell_threshold and sell.score > buy.score:
        signal_label = "可能适合卖出"
    elif buy.score >= buy_threshold and buy.score > sell.score:
        signal_label = "可能适合买入"
    elif risk_level == "高":
        signal_label = "风险较高"
    else:
        signal_label = "观察"

    difference = abs(buy.score - sell.score)
    if len(indicators) >= 120 and difference >= 25:
        confidence = "较高"
    elif len(indicators) >= 80 and difference >= 10:
        confidence = "中等"
    else:
        confidence = "较低"

    configured_stop = (
        stock.stop_loss_price if stock.stop_loss_price and stock.stop_loss_price > 0 else None
    )
    stop_reference = configured_stop or max(0.01, support - 1.5 * atr)
    attention_low = max(0.01, support)
    attention_high = min(resistance, support + max(atr, price * 0.01))
    if attention_high < attention_low:
        attention_high = attention_low

    market_value = price * stock.quantity
    invested = stock.cost_basis * stock.quantity
    unrealized = market_value - invested
    unrealized_percent = (price / stock.cost_basis - 1) * 100 if stock.cost_basis else 0

    chart_columns = [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "sma_5",
        "sma_20",
        "sma_60",
        "macd",
        "macd_signal",
        "macd_hist",
        "rsi_14",
        "bollinger_upper",
        "bollinger_middle",
        "bollinger_lower",
    ]
    price_history: list[dict[str, Any]] = []
    for index, values in indicators.tail(120).iterrows():
        item: dict[str, Any] = {"date": pd.Timestamp(index).strftime("%Y-%m-%d")}
        for column in chart_columns:
            item[column] = _safe(values.get(column))
        price_history.append(item)

    metrics = {
        "sma_5": _safe(row.get("sma_5")),
        "sma_10": _safe(row.get("sma_10")),
        "sma_20": _safe(row.get("sma_20")),
        "sma_60": _safe(row.get("sma_60")),
        "ema_12": _safe(row.get("ema_12")),
        "ema_26": _safe(row.get("ema_26")),
        "macd": _safe(row.get("macd")),
        "macd_signal": _safe(row.get("macd_signal")),
        "macd_hist": _safe(row.get("macd_hist")),
        "rsi_14": _safe(row.get("rsi_14"), 2),
        "kdj_k": _safe(row.get("kdj_k"), 2),
        "kdj_d": _safe(row.get("kdj_d"), 2),
        "kdj_j": _safe(row.get("kdj_j"), 2),
        "bollinger_upper": _safe(row.get("bollinger_upper")),
        "bollinger_middle": _safe(row.get("bollinger_middle")),
        "bollinger_lower": _safe(row.get("bollinger_lower")),
        "atr_14": _safe(row.get("atr_14")),
        "volume_sma_20": _safe(row.get("volume_sma_20"), 0),
        "volume_ratio": _safe(row.get("volume_ratio"), 2),
        "return_5d": _safe(row.get("return_5d"), 2),
        "return_20d": _safe(row.get("return_20d"), 2),
        "return_60d": _safe(row.get("return_60d"), 2),
        "max_drawdown_percent": _safe(max_drawdown * 100, 2),
        "full_period_max_drawdown_percent": _safe(float(row.get("max_drawdown") or 0) * 100, 2),
        "volatility_annualized_percent": _safe(volatility * 100, 2),
    }
    return AnalysisResult(
        symbol=stock.symbol,
        name=stock.name,
        market=stock.market,
        price=round(price, 4),
        previous_close=round(previous_close, 4),
        change_percent=round(change_percent, 2),
        updated_at=market_data.updated_at.isoformat(),
        provider=market_data.provider,
        delayed=market_data.delayed,
        delay_minutes=market_data.delay_minutes,
        delay_note=market_data.delay_note,
        mode=market_data.mode,
        buy_score=buy.score,
        sell_score=sell.score,
        signal_label=signal_label,
        risk_level=risk_level,
        confidence=confidence,
        human_confirmation_required=True,
        support=round(support, 4),
        resistance=round(resistance, 4),
        attention_range=[round(attention_low, 4), round(attention_high, 4)],
        stop_loss_reference=round(stop_reference, 4),
        metrics=metrics,
        buy_criteria=buy.criteria,
        sell_criteria=sell.criteria,
        position={
            "quantity": stock.quantity,
            "cost_basis": stock.cost_basis,
            "market_value": round(market_value, 2),
            "unrealized_pnl": round(unrealized, 2),
            "unrealized_return_percent": round(unrealized_percent, 2),
            "take_profit_triggered": float(take_profit_triggered),
            "stop_loss_triggered": float(stop_triggered),
        },
        price_history=price_history,
    )
