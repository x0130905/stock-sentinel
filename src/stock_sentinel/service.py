from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo

from . import DISCLAIMER
from .alerts import build_alerts
from .analysis import analyze_market_data
from .backtest import run_backtest
from .config import PROJECT_ROOT, AppConfig
from .market_hours import should_run_for_markets
from .models import AnalysisResult
from .notifier import EmailNotifier, NotificationError
from .providers import create_provider
from .storage import load_json, mirror_json, save_json

DATA_DIR = PROJECT_ROOT / "data"
PUBLIC_DATA_DIR = PROJECT_ROOT / "frontend" / "public" / "data"
SHANGHAI = ZoneInfo("Asia/Shanghai")
NEW_YORK = ZoneInfo("America/New_York")


def _write_shared(name: str, payload: Any) -> None:
    mirror_json(payload, DATA_DIR / name, PUBLIC_DATA_DIR / name)


def run_backtests_for_data(
    config: AppConfig, market_data: dict[str, Any], logger: logging.Logger
) -> dict[str, Any]:
    existing = load_json(DATA_DIR / "backtests.json", {"results": {}})
    results = existing.setdefault("results", {})
    for stock in config.stocks:
        data = market_data.get(stock.symbol)
        if data is None:
            continue
        try:
            results[stock.symbol] = run_backtest(data.frame, stock, config.scoring, config.backtest)
        except Exception as exc:
            logger.exception("%s 回测失败", stock.symbol)
            results[stock.symbol] = {
                "status": "failed",
                "symbol": stock.symbol,
                "error": str(exc),
            }
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "results": results,
        "disclaimer": "历史回测不代表未来表现，分析结果不构成投资建议。",
    }
    _write_shared("backtests.json", payload)
    return payload


def _backtest_ready(backtests: dict[str, Any], symbol: str) -> bool:
    return backtests.get("results", {}).get(symbol, {}).get("status") == "completed"


def _alert_local_date(item: dict[str, Any], timezone: ZoneInfo) -> str | None:
    try:
        created_at = datetime.fromisoformat(str(item.get("created_at", "")))
    except ValueError:
        return None
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=UTC)
    return created_at.astimezone(timezone).date().isoformat()


def run_monitor(config: AppConfig, logger: logging.Logger, force: bool = False) -> dict[str, Any]:
    markets = {stock.market for stock in config.stocks}
    if not force and config.provider != "sample" and not should_run_for_markets(markets):
        logger.info("当前不在收盘分析窗口，跳过行情请求以节省免费额度")
        return {"status": "skipped", "reason": "outside_market_window"}

    provider = create_provider(config.provider)
    state_path = DATA_DIR / "state.json"
    state = load_json(state_path, {"symbols": {}, "last_alerts": {}, "failures": {}})
    history = load_json(DATA_DIR / "alerts.json", {"alerts": []})
    market_data: dict[str, Any] = {}
    market_dates: dict[str, str] = {}
    fresh_symbols: set[str] = set()
    results: list[AnalysisResult] = []
    errors: list[dict[str, str]] = []
    notifier = EmailNotifier()
    failure_threshold = int(config.alerts.get("consecutive_failure_threshold", 3))

    for stock in config.stocks:
        try:
            data = provider.fetch(stock.symbol, config.history_period)
            result = analyze_market_data(data, stock, config.scoring)
            market_date = data.frame.index[-1].date().isoformat()
            previous_market_date = (
                state.setdefault("symbols", {}).get(stock.symbol, {}).get("market_data_date")
            )
            if market_date != previous_market_date:
                fresh_symbols.add(stock.symbol)
            market_dates[stock.symbol] = market_date
            market_data[stock.symbol] = data
            results.append(result)
            state.setdefault("failures", {})[stock.symbol] = 0
            logger.info(
                "%s 分析完成：数据日期 %s，价格 %.3f，买入评分 %d，卖出评分 %d",
                stock.symbol,
                market_date,
                result.price,
                result.buy_score,
                result.sell_score,
            )
        except Exception as exc:
            logger.exception("%s 行情分析失败", stock.symbol)
            count = int(state.setdefault("failures", {}).get(stock.symbol, 0)) + 1
            state["failures"][stock.symbol] = count
            errors.append({"symbol": stock.symbol, "message": str(exc), "count": str(count)})
            if count == failure_threshold:
                try:
                    notifier.send_failure(stock.symbol, count, str(exc))
                except NotificationError:
                    logger.exception("数据源失败邮件发送失败")

    backtests = load_json(DATA_DIR / "backtests.json", {"results": {}})
    missing_backtest = any(
        not _backtest_ready(backtests, result.symbol)
        for result in results
        if result.symbol in market_data
    )
    if missing_backtest:
        logger.info("提醒启用前先执行无未来函数回测")
        backtests = run_backtests_for_data(config, market_data, logger)

    stock_lookup = {stock.symbol: stock for stock in config.stocks}
    new_events = []
    for result in results:
        stock = stock_lookup[result.symbol]
        if result.symbol not in fresh_symbols:
            logger.info("%s 数据日期未变化，本次只刷新页面，不重复累计或发送信号", result.symbol)
            continue
        if config.alerts.get("backtest_required", True) and not _backtest_ready(
            backtests, result.symbol
        ):
            logger.warning("%s 回测未完成，本次不产生提醒", result.symbol)
            continue
        if not config.alerts.get("simulation_mode", True) and not config.alerts.get(
            "live_alerts_enabled", False
        ):
            continue
        events = build_alerts(result, stock, config.scoring, config.alerts, state)
        for event in events:
            event.simulated = not bool(config.alerts.get("live_alerts_enabled", False))
            if stock.email_enabled:
                try:
                    notifier.send_event(event, result)
                except NotificationError:
                    logger.exception("%s 的提醒邮件发送失败", result.symbol)
            history.setdefault("alerts", []).insert(0, event.to_dict())
            new_events.append(event)

    for symbol, market_date in market_dates.items():
        state.setdefault("symbols", {}).setdefault(symbol, {})["market_data_date"] = market_date

    history["alerts"] = history.get("alerts", [])[:500]
    _write_shared("alerts.json", history)

    now_utc = datetime.now(UTC)
    summary_timezone = SHANGHAI if markets.intersection({"CN", "HK"}) else NEW_YORK
    summary_local = now_utc.astimezone(summary_timezone)
    summary_date = summary_local.date().isoformat()
    summary_close_hour = 15 if summary_timezone == SHANGHAI else 16
    if (
        summary_local.weekday() < 5
        and summary_local.hour >= summary_close_hour
        and state.get("last_summary_date") != summary_date
        and any(stock.daily_summary_enabled for stock in config.stocks)
    ):
        try:
            notifier.send_summary(results)
            state["last_summary_date"] = summary_date
        except NotificationError:
            logger.exception("每日总结邮件发送失败")

    generated_at = now_utc.isoformat()
    today_signals = sum(
        1
        for item in history["alerts"]
        if _alert_local_date(item, summary_timezone) == summary_date
    )
    stocks_payload = [result.to_dict() for result in results]
    if config.frequency_minutes >= 1440:
        schedule_note = (
            "交易日收盘后每日分析一次；Alpha Vantage 免费层为日线数据，"
            "GitHub Actions 可能延迟，不是实时行情。"
        )
    else:
        schedule_note = (
            f"配置频率为每 {config.frequency_minutes} 分钟；GitHub Actions 定时可能延迟，"
            "这不是交易所级实时监控。"
        )
    dashboard = {
        "schema_version": 2,
        "generated_at": generated_at,
        "generated_at_local": now_utc.astimezone(SHANGHAI).isoformat(),
        "provider": config.provider,
        "mode": "sample" if config.provider == "sample" else "live",
        "provider_status": "正常" if not errors else ("部分失败" if results else "失败"),
        "schedule_note": schedule_note,
        "summary": {
            "monitored_count": len(config.stocks),
            "successful_count": len(results),
            "today_signal_count": today_signals,
            "high_risk_count": sum(1 for result in results if result.risk_level == "高"),
            "latest_run": generated_at,
            "new_signal_count": len(new_events),
        },
        "stocks": stocks_payload,
        "errors": errors,
        "disclaimer": DISCLAIMER,
    }
    _write_shared("dashboard.json", dashboard)
    state["last_run"] = generated_at
    save_json(state_path, state)
    return dashboard
