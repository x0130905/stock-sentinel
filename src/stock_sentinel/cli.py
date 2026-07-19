from __future__ import annotations

import argparse
import json
import sys

from .config import PROJECT_ROOT, ConfigError, load_config
from .intraday import run_intraday_risk_check
from .logging_config import configure_logging
from .notifier import EmailNotifier, NotificationError
from .providers import create_provider
from .service import run_backtests_for_data, run_monitor


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="stock-sentinel", description="股票行情监测、规则评分、回测与提醒系统"
    )
    parser.add_argument("--config", help="配置文件路径，默认 config/settings.json")
    commands = parser.add_subparsers(dest="command", required=True)
    monitor = commands.add_parser("monitor", help="抓取行情并生成分析和提醒")
    monitor.add_argument("--force", action="store_true", help="忽略交易时段限制（本地测试用）")
    intraday = commands.add_parser("intraday-risk", help="使用免费辅助行情执行盘中风险检查")
    intraday.add_argument("--force", action="store_true", help="忽略交易时段限制（本地测试用）")
    commands.add_parser("backtest", help="对配置中的全部股票执行历史回测")
    commands.add_parser("test-email", help="发送一封测试邮件")
    commands.add_parser("notify-failure", help="发送自动任务失败通知")
    commands.add_parser("validate", help="验证配置和数据源设置")
    commands.add_parser("demo", help="使用演示数据跑通回测、分析和前端数据")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logger = configure_logging(PROJECT_ROOT / "logs")
    try:
        config = load_config(args.config)
        if args.command == "validate":
            provider = create_provider(config.provider)
            print(f"配置有效：{len(config.stocks)} 只股票，数据源 {provider.name}")
            return 0
        if args.command == "test-email":
            sent = EmailNotifier().send_test()
            print("测试邮件已发送" if sent else "EMAIL_ENABLED=false，未实际发送测试邮件")
            return 0
        if args.command == "notify-failure":
            sent = EmailNotifier().send_failure(
                "SYSTEM", 1, "GitHub Actions 自动任务失败，请查看运行日志"
            )
            print("失败通知已发送" if sent else "EMAIL_ENABLED=false，未实际发送失败通知")
            return 0
        if args.command == "backtest":
            provider = create_provider(config.provider)
            market_data = {
                stock.symbol: provider.fetch(stock.symbol, config.history_period)
                for stock in config.stocks
            }
            payload = run_backtests_for_data(config, market_data, logger)
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 0
        if args.command == "demo":
            config.raw["provider"] = "sample"
            dashboard = run_monitor(config, logger, force=True)
            print(f"演示数据已生成：{dashboard['summary']['successful_count']} 只股票")
            return 0
        if args.command == "intraday-risk":
            payload = run_intraday_risk_check(config, logger, force=args.force)
            if payload.get("status") == "skipped":
                print("当前不在国内交易时段，已跳过免费盘中快照请求")
                return 0
            print(
                f"盘中检查完成：成功 {payload['successful_count']}/"
                f"{payload['monitored_count']}，新增风险 {payload['new_risk_count']}"
            )
            return 0
        dashboard = run_monitor(config, logger, force=args.force)
        if dashboard.get("status") == "skipped":
            print("当前不在重点交易时段，已跳过行情请求")
        else:
            print(
                f"监测完成：成功 {dashboard['summary']['successful_count']}，"
                f"失败 {len(dashboard['errors'])}"
            )
        return 0 if not dashboard.get("errors") else 2
    except (ConfigError, NotificationError, ValueError) as exc:
        logger.error("命令执行失败：%s", exc)
        print(f"错误：{exc}", file=sys.stderr)
        return 1
    except Exception:
        logger.exception("未处理的错误")
        print("发生未处理错误，请查看 logs/stock-sentinel.log", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
