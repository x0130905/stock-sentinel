from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd

SHANGHAI = ZoneInfo("Asia/Shanghai")


class IntradayProviderError(RuntimeError):
    pass


@dataclass(slots=True)
class IntradayQuote:
    symbol: str
    name: str
    price: float
    previous_close: float
    open: float
    high: float
    low: float
    change_percent: float
    volume: float
    amount: float
    updated_at: str
    provider: str = "akshare"
    experimental: bool = True
    delay_note: str = "免费公开网页来源，可能延迟、中断或发生字段变化，不可作为可靠止损依据。"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _column(frame: pd.DataFrame, *names: str) -> str:
    for name in names:
        if name in frame.columns:
            return name
    raise IntradayProviderError(f"AKShare ETF 分钟线缺少字段: {'/'.join(names)}")


def _number(value: Any, field: str, symbol: str) -> float:
    number = pd.to_numeric(value, errors="coerce")
    try:
        result = float(number)
    except (TypeError, ValueError) as exc:
        raise IntradayProviderError(f"{symbol} 的 {field} 不是有效数字") from exc
    if not math.isfinite(result):
        raise IntradayProviderError(f"{symbol} 的 {field} 不是有效数字")
    return result


def _normalize_symbol_frame(symbol: str, frame: pd.DataFrame) -> IntradayQuote:
    if not isinstance(frame, pd.DataFrame) or frame.empty:
        raise IntradayProviderError(f"{symbol} 的 AKShare 15分钟线为空")
    time_column = _column(frame, "时间")
    open_column = _column(frame, "开盘")
    close_column = _column(frame, "收盘")
    high_column = _column(frame, "最高")
    low_column = _column(frame, "最低")
    volume_column = _column(frame, "成交量")
    amount_column = _column(frame, "成交额")

    data = frame.copy()
    data[time_column] = pd.to_datetime(data[time_column], errors="coerce")
    data = data.dropna(subset=[time_column]).sort_values(time_column)
    if data.empty:
        raise IntradayProviderError(f"{symbol} 的 AKShare 15分钟线没有有效时间")
    data["_trade_date"] = data[time_column].dt.date
    dates = list(data["_trade_date"].drop_duplicates())
    if len(dates) < 2:
        raise IntradayProviderError(f"{symbol} 的 AKShare 15分钟线不足两个交易日")

    latest_date = dates[-1]
    previous_date = dates[-2]
    latest_day = data.loc[data["_trade_date"] == latest_date]
    previous_day = data.loc[data["_trade_date"] == previous_date]
    latest = latest_day.iloc[-1]
    previous_close = _number(previous_day.iloc[-1][close_column], "前收盘", symbol)
    price = _number(latest[close_column], "最新价", symbol)
    timestamp = pd.Timestamp(latest[time_column]).to_pydatetime().replace(tzinfo=SHANGHAI)

    quote = IntradayQuote(
        symbol=symbol,
        name=symbol,
        price=price,
        previous_close=previous_close,
        open=_number(latest_day.iloc[0][open_column], "今开", symbol),
        high=_number(latest_day[high_column].max(), "最高", symbol),
        low=_number(latest_day[low_column].min(), "最低", symbol),
        change_percent=(price / previous_close - 1) * 100 if previous_close else 0,
        volume=_number(latest_day[volume_column].sum(), "成交量", symbol),
        amount=_number(latest_day[amount_column].sum(), "成交额", symbol),
        updated_at=timestamp.isoformat(),
    )
    if quote.price <= 0 or quote.high < quote.low:
        raise IntradayProviderError(f"{symbol} 的 AKShare 15分钟线价格结构不合法")
    return quote


def fetch_etf_intraday_quotes(
    symbols: list[str], interval_minutes: int = 15
) -> tuple[list[IntradayQuote], list[dict[str, str]]]:
    try:
        import akshare as ak
    except ImportError as exc:
        raise IntradayProviderError("未安装 AKShare，请安装项目的 intraday 可选依赖") from exc

    quotes: list[IntradayQuote] = []
    errors: list[dict[str, str]] = []
    for symbol in symbols:
        code = symbol.split(".", maxsplit=1)[0].zfill(6)
        try:
            frame = ak.fund_etf_hist_min_em(
                symbol=code,
                period=str(interval_minutes),
                adjust="",
            )
            quotes.append(_normalize_symbol_frame(symbol, frame))
        except Exception as exc:
            message = str(exc) if isinstance(exc, IntradayProviderError) else type(exc).__name__
            errors.append({"symbol": symbol, "message": f"AKShare 15分钟线失败: {message}"})
    return quotes, errors
