from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
import pandas as pd

from .indicators import calculate_indicators
from .models import StockConfig
from .scoring import calculate_scores


@dataclass(slots=True)
class Trade:
    entry_date: str
    entry_price: float
    exit_date: str | None = None
    exit_price: float | None = None
    quantity: float = 0
    pnl: float | None = None
    return_percent: float | None = None


def run_backtest(
    frame: pd.DataFrame,
    stock: StockConfig,
    scoring: dict[str, Any],
    settings: dict[str, Any],
) -> dict[str, Any]:
    """Backtest daily signals and execute at the next bar open to avoid look-ahead bias."""
    data = frame.copy()
    start_date = settings.get("start_date")
    end_date = settings.get("end_date")
    if start_date:
        data = data[data.index >= pd.Timestamp(start_date, tz="UTC")]
    if end_date:
        data = data[data.index <= pd.Timestamp(end_date, tz="UTC")]
    if len(data) < 80:
        raise ValueError("回测至少需要 80 个交易日")

    indicators = calculate_indicators(data)
    initial_cash = float(settings.get("initial_cash", 100_000))
    fee_rate = float(settings.get("fee_rate", 0.001))
    slippage = float(settings.get("slippage_rate", 0.0005))
    buy_threshold = int(scoring.get("buy_alert_threshold", 65))
    sell_threshold = int(scoring.get("sell_alert_threshold", 65))
    cash = initial_cash
    quantity = 0.0
    open_trade: Trade | None = None
    trades: list[Trade] = []
    equity_curve: list[dict[str, float | str]] = []

    for decision_index in range(60, len(indicators) - 1):
        history = indicators.iloc[: decision_index + 1]
        buy, sell = calculate_scores(history, stock, scoring)
        execution = indicators.iloc[decision_index + 1]
        execution_date = indicators.index[decision_index + 1].strftime("%Y-%m-%d")
        open_price = float(execution["open"])
        if quantity == 0 and buy.score >= buy_threshold and buy.score > sell.score:
            price = open_price * (1 + slippage)
            spendable = cash * 0.95
            quantity = spendable / (price * (1 + fee_rate))
            cost = quantity * price * (1 + fee_rate)
            cash -= cost
            open_trade = Trade(
                entry_date=execution_date,
                entry_price=round(price, 4),
                quantity=quantity,
            )
        elif quantity > 0 and sell.score >= sell_threshold and sell.score >= buy.score:
            price = open_price * (1 - slippage)
            proceeds = quantity * price * (1 - fee_rate)
            cash += proceeds
            if open_trade:
                entry_cost = open_trade.quantity * open_trade.entry_price * (1 + fee_rate)
                pnl = proceeds - entry_cost
                open_trade.exit_date = execution_date
                open_trade.exit_price = round(price, 4)
                open_trade.pnl = round(pnl, 2)
                open_trade.return_percent = round(pnl / entry_cost * 100, 2)
                trades.append(open_trade)
            quantity = 0
            open_trade = None
        close_value = cash + quantity * float(execution["close"])
        equity_curve.append({"date": execution_date, "equity": round(close_value, 2)})

    final_price = float(indicators.iloc[-1]["close"])
    final_equity = cash + quantity * final_price * (1 - fee_rate)
    if open_trade:
        entry_cost = open_trade.quantity * open_trade.entry_price * (1 + fee_rate)
        proceeds = open_trade.quantity * final_price * (1 - fee_rate)
        open_trade.exit_date = indicators.index[-1].strftime("%Y-%m-%d") + "（期末估值）"
        open_trade.exit_price = round(final_price, 4)
        open_trade.pnl = round(proceeds - entry_cost, 2)
        open_trade.return_percent = round((proceeds / entry_cost - 1) * 100, 2)
        trades.append(open_trade)
    if not equity_curve:
        equity_curve.append(
            {"date": indicators.index[-1].strftime("%Y-%m-%d"), "equity": final_equity}
        )

    equity = np.array([float(point["equity"]) for point in equity_curve])
    peaks = np.maximum.accumulate(equity)
    drawdown = equity / peaks - 1
    total_return = final_equity / initial_cash - 1
    duration_days = max((indicators.index[-1] - indicators.index[60]).days, 1)
    annualized = (1 + total_return) ** (365 / duration_days) - 1 if total_return > -1 else -1
    wins = [trade for trade in trades if (trade.pnl or 0) > 0]
    losses = [trade for trade in trades if (trade.pnl or 0) < 0]
    gross_profit = sum(trade.pnl or 0 for trade in wins)
    gross_loss = abs(sum(trade.pnl or 0 for trade in losses))
    profit_factor = gross_profit / gross_loss if gross_loss else (math.inf if gross_profit else 0)
    buy_hold = float(indicators.iloc[-1]["close"] / indicators.iloc[60]["close"] - 1)

    return {
        "status": "completed",
        "symbol": stock.symbol,
        "start_date": indicators.index[60].strftime("%Y-%m-%d"),
        "end_date": indicators.index[-1].strftime("%Y-%m-%d"),
        "assumptions": {
            "initial_cash": initial_cash,
            "fee_rate": fee_rate,
            "slippage_rate": slippage,
            "execution_rule": "使用当日收盘后产生的信号，在下一交易日开盘价成交",
            "lookahead_protection": True,
        },
        "metrics": {
            "final_equity": round(final_equity, 2),
            "total_return_percent": round(total_return * 100, 2),
            "annualized_return_percent": round(annualized * 100, 2),
            "max_drawdown_percent": round(float(drawdown.min()) * 100, 2),
            "win_rate_percent": round(len(wins) / len(trades) * 100, 2) if trades else 0,
            "profit_factor": round(profit_factor, 2) if math.isfinite(profit_factor) else None,
            "trade_count": len(trades),
            "buy_hold_return_percent": round(buy_hold * 100, 2),
        },
        "trades": [asdict(trade) for trade in trades],
        "equity_curve": equity_curve[-260:],
        "disclaimer": "历史回测不代表未来表现，且未包含税费、流动性冲击等全部真实成本。",
    }
