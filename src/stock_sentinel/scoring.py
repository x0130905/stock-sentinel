from __future__ import annotations

import math
from typing import Any

import pandas as pd

from .models import Criterion, ScoreResult, StockConfig


def _number(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
        return number if math.isfinite(number) else default
    except (TypeError, ValueError):
        return default


def _criterion(key: str, label: str, triggered: bool, weight: float, detail: str) -> Criterion:
    return Criterion(
        key=key,
        label=label,
        triggered=bool(triggered),
        score=weight if triggered else 0,
        max_score=weight,
        detail=detail,
    )


def calculate_scores(
    indicators: pd.DataFrame, stock: StockConfig, params: dict[str, Any]
) -> tuple[ScoreResult, ScoreResult]:
    row = indicators.iloc[-1]
    previous = indicators.iloc[-2]
    price = _number(row["close"])
    atr = max(_number(row.get("atr_14")), price * 0.01)
    rsi = _number(row.get("rsi_14"), 50)
    previous_rsi = _number(previous.get("rsi_14"), 50)
    macd = _number(row.get("macd"))
    macd_signal = _number(row.get("macd_signal"))
    previous_macd = _number(previous.get("macd"))
    previous_macd_signal = _number(previous.get("macd_signal"))
    sma_5 = _number(row.get("sma_5"), price)
    sma_20 = _number(row.get("sma_20"), price)
    sma_60 = _number(row.get("sma_60"), price)
    prev_sma_5 = _number(previous.get("sma_5"), sma_5)
    prev_sma_20 = _number(previous.get("sma_20"), sma_20)
    support = _number(row.get("support"), price)
    resistance = _number(row.get("resistance"), price)
    volume_ratio = _number(row.get("volume_ratio"), 1)
    return_20d = _number(row.get("return_20d"))
    volatility = _number(row.get("volatility_annualized"))
    max_drawdown = _number(row.get("rolling_max_drawdown_60d", row.get("max_drawdown")))

    oversold = float(params.get("rsi_oversold", 30))
    overbought = float(params.get("rsi_overbought", 70))
    near_multiple = float(params.get("near_level_atr_multiple", 1.0))
    high_volatility = float(params.get("high_volatility_annualized", 0.45))
    high_drawdown = float(params.get("high_drawdown_percent", 25)) / 100

    bullish_cross = sma_5 > sma_20 and prev_sma_5 <= prev_sma_20
    bullish_alignment = sma_5 > sma_20 > sma_60
    macd_bullish = macd > macd_signal and previous_macd <= previous_macd_signal
    rsi_rebound = rsi > previous_rsi and previous_rsi <= oversold + 5
    near_support = abs(price - support) <= atr * near_multiple and price >= support * 0.985
    volume_confirmed = 1.05 <= volume_ratio <= 2.5
    trend_allowed = return_20d > 0 and price >= sma_60
    risk_allowed = volatility < high_volatility and max_drawdown > -high_drawdown

    buy = [
        _criterion(
            "ma_bullish",
            "短期均线转强",
            bullish_cross or bullish_alignment,
            20,
            f"SMA5 {sma_5:.2f} / SMA20 {sma_20:.2f} / SMA60 {sma_60:.2f}",
        ),
        _criterion(
            "macd_bullish",
            "MACD 金叉",
            macd_bullish,
            15,
            f"MACD {macd:.3f} / 信号线 {macd_signal:.3f}",
        ),
        _criterion(
            "rsi_rebound",
            "RSI 从偏低区域回升",
            rsi_rebound,
            15,
            f"RSI14 {rsi:.1f}，前值 {previous_rsi:.1f}",
        ),
        _criterion(
            "near_support",
            "价格接近支撑位",
            near_support,
            15,
            f"价格 {price:.2f} / 支撑 {support:.2f} / ATR {atr:.2f}",
        ),
        _criterion(
            "volume_confirmed",
            "成交量适度放大",
            volume_confirmed,
            10,
            f"当前量为 20 日均量的 {volume_ratio:.2f} 倍",
        ),
        _criterion(
            "trend_allowed",
            "中期趋势允许",
            trend_allowed,
            15,
            f"20 日涨跌 {return_20d:.2f}% / 价格相对 SMA60 {price - sma_60:+.2f}",
        ),
        _criterion(
            "risk_allowed",
            "波动与回撤在阈值内",
            risk_allowed,
            10,
            f"年化波动 {volatility:.1%} / 最大回撤 {max_drawdown:.1%}",
        ),
    ]

    bearish_cross = sma_5 < sma_20 and prev_sma_5 >= prev_sma_20
    bearish_alignment = sma_5 < sma_20 < sma_60
    macd_bearish = macd < macd_signal and previous_macd >= previous_macd_signal
    rsi_falling = rsi < previous_rsi and previous_rsi >= overbought - 5
    near_resistance = abs(resistance - price) <= atr * near_multiple and price <= resistance * 1.015
    take_profit = bool(stock.take_profit_price and price >= stock.take_profit_price)
    stop_loss = bool(stock.stop_loss_price and price <= stock.stop_loss_price)
    risk_exceeded = volatility >= high_volatility or max_drawdown <= -high_drawdown

    sell = [
        _criterion(
            "ma_bearish",
            "短期均线转弱",
            bearish_cross or bearish_alignment,
            15,
            f"SMA5 {sma_5:.2f} / SMA20 {sma_20:.2f} / SMA60 {sma_60:.2f}",
        ),
        _criterion(
            "macd_bearish",
            "MACD 死叉",
            macd_bearish,
            15,
            f"MACD {macd:.3f} / 信号线 {macd_signal:.3f}",
        ),
        _criterion(
            "rsi_falling",
            "RSI 高位回落",
            rsi_falling,
            10,
            f"RSI14 {rsi:.1f}，前值 {previous_rsi:.1f}",
        ),
        _criterion(
            "near_resistance",
            "价格接近压力位",
            near_resistance,
            10,
            f"价格 {price:.2f} / 压力 {resistance:.2f} / ATR {atr:.2f}",
        ),
        _criterion(
            "take_profit",
            "达到用户止盈价",
            take_profit,
            15,
            f"止盈价 {stock.take_profit_price if stock.take_profit_price else '未设置'}",
        ),
        _criterion(
            "stop_loss",
            "跌破用户止损价",
            stop_loss,
            20,
            f"止损价 {stock.stop_loss_price if stock.stop_loss_price else '未设置'}",
        ),
        _criterion(
            "risk_exceeded",
            "波动或回撤超过阈值",
            risk_exceeded,
            15,
            f"年化波动 {volatility:.1%} / 最大回撤 {max_drawdown:.1%}",
        ),
    ]
    return (
        ScoreResult(score=round(sum(item.score for item in buy)), criteria=buy),
        ScoreResult(score=round(sum(item.score for item in sell)), criteria=sell),
    )


def score_band(score: int) -> str:
    if score < 30:
        return "风险较高"
    if score < 45:
        return "偏弱，谨慎观察"
    if score < 60:
        return "中性，继续观察"
    if score < 75:
        return "偏强，可能存在机会"
    return "强信号，仍需人工确认"
