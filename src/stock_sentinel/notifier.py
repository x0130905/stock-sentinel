from __future__ import annotations

import html
import os
import smtplib
import ssl
from collections.abc import Iterable
from email.message import EmailMessage

import httpx

from . import DISCLAIMER
from .models import AlertEvent, AnalysisResult
from .providers.akshare_intraday import IntradayQuote


class NotificationError(RuntimeError):
    pass


class EmailNotifier:
    def __init__(self) -> None:
        self.enabled = os.getenv("EMAIL_ENABLED", "false").lower() == "true"
        self.provider = os.getenv("EMAIL_PROVIDER", "resend").lower()
        self.recipient = os.getenv("EMAIL_TO", "")
        self.sender = os.getenv("EMAIL_FROM", "Stock Sentinel <alerts@example.com>")
        self.site_url = os.getenv("SITE_URL", "http://localhost:5173")

    def validate(self) -> None:
        if not self.recipient or "@" not in self.recipient:
            raise NotificationError("EMAIL_TO 未设置或格式不正确")
        if self.provider == "resend" and not os.getenv("RESEND_API_KEY"):
            raise NotificationError("使用 Resend 时必须设置 RESEND_API_KEY")
        if self.provider == "smtp" and not all(
            os.getenv(name) for name in ("SMTP_HOST", "SMTP_USERNAME", "SMTP_PASSWORD")
        ):
            raise NotificationError("SMTP_HOST、SMTP_USERNAME、SMTP_PASSWORD 必须完整设置")
        if self.provider not in {"resend", "smtp"}:
            raise NotificationError(f"不支持的邮件服务: {self.provider}")

    def send(self, subject: str, html_body: str) -> bool:
        if not self.enabled:
            return False
        self.validate()
        if self.provider == "resend":
            return self._send_resend(subject, html_body)
        return self._send_smtp(subject, html_body)

    def _send_resend(self, subject: str, html_body: str) -> bool:
        response = httpx.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {os.environ['RESEND_API_KEY']}"},
            json={
                "from": self.sender,
                "to": [self.recipient],
                "subject": subject,
                "html": html_body,
            },
            timeout=20,
        )
        if response.status_code >= 400:
            raise NotificationError(f"Resend 发送失败，HTTP {response.status_code}")
        return True

    def _send_smtp(self, subject: str, html_body: str) -> bool:
        host = os.environ["SMTP_HOST"]
        port = int(os.getenv("SMTP_PORT", "465"))
        use_ssl = os.getenv("SMTP_USE_SSL", "true").lower() == "true"
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = self.sender
        message["To"] = self.recipient
        message.set_content("请使用支持 HTML 的邮箱客户端查看此提醒。")
        message.add_alternative(html_body, subtype="html")
        context = ssl.create_default_context()
        connection: smtplib.SMTP
        if use_ssl:
            connection = smtplib.SMTP_SSL(host, port, timeout=20, context=context)
        else:
            connection = smtplib.SMTP(host, port, timeout=20)
            connection.starttls(context=context)
        with connection:
            connection.login(os.environ["SMTP_USERNAME"], os.environ["SMTP_PASSWORD"])
            connection.send_message(message)
        return True

    def send_event(self, event: AlertEvent, result: AnalysisResult) -> bool:
        reason = html.escape(event.reason)
        body = f"""
        <div style="font-family:system-ui;max-width:620px;margin:auto;color:#172033">
          <h2>{html.escape(event.label)} · {html.escape(result.name)} ({result.symbol})</h2>
          <p>当前价格：<b>{result.price:.2f}</b>　更新时间：{html.escape(result.updated_at)}</p>
          <p>买入评分：{result.buy_score}/100　卖出评分：{result.sell_score}/100</p>
          <p>触发原因：{reason}</p>
          <p>风险等级：{result.risk_level}；信号可信度：{result.confidence}；需人工确认。</p>
          <p>{html.escape(result.delay_note)}</p>
          <p><a href="{html.escape(self.site_url)}">打开手机端系统</a></p>
          <hr><p><b>{html.escape(DISCLAIMER)}</b></p>
        </div>
        """
        mode = "[模拟] " if event.simulated else ""
        sent = self.send(f"[Stock Sentinel] {mode}{event.label} - {result.symbol}", body)
        event.sent = sent
        return sent

    def send_summary(self, results: Iterable[AnalysisResult]) -> bool:
        rows = "".join(
            f"<tr><td>{html.escape(item.symbol)}</td><td>{item.price:.2f}</td>"
            f"<td>{item.buy_score}</td><td>{item.sell_score}</td><td>{item.risk_level}</td></tr>"
            for item in results
        )
        body = f"""
        <div style="font-family:system-ui;max-width:700px;margin:auto">
          <h2>Stock Sentinel 每日总结</h2>
          <table cellpadding="8" border="1" style="border-collapse:collapse">
            <tr><th>代码</th><th>价格</th><th>买入评分</th><th>卖出评分</th><th>风险</th></tr>
            {rows}
          </table>
          <p><a href="{html.escape(self.site_url)}">打开手机端系统</a></p>
          <p><b>{html.escape(DISCLAIMER)}</b></p>
        </div>
        """
        return self.send("[Stock Sentinel] 每日收盘总结", body)

    def send_intraday_event(self, event: AlertEvent, quote: IntradayQuote) -> bool:
        body = f"""
        <div style="font-family:system-ui;max-width:620px;margin:auto;color:#172033">
          <h2>{html.escape(event.label)} · {html.escape(event.name)} ({event.symbol})</h2>
          <p>盘中参考价：<b>{quote.price:.3f}</b>　涨跌：{quote.change_percent:+.2f}%</p>
          <p>触发原因：{html.escape(event.reason)}</p>
          <p>{html.escape(quote.delay_note)}</p>
          <p><a href="{html.escape(self.site_url)}">打开手机端系统</a></p>
          <hr><p><b>{html.escape(DISCLAIMER)}</b></p>
        </div>
        """
        sent = self.send(f"[Stock Sentinel] [实验性盘中] {event.label} - {event.symbol}", body)
        event.sent = sent
        return sent

    def send_test(self) -> bool:
        body = (
            "<h2>Stock Sentinel 测试邮件</h2>"
            "<p>如果你看到这封邮件，通知配置已生效。</p>"
            f"<p><b>{html.escape(DISCLAIMER)}</b></p>"
        )
        return self.send("[Stock Sentinel] 测试邮件", body)

    def send_failure(self, symbol: str, count: int, message: str) -> bool:
        body = f"""
        <h2>行情数据连续失败</h2>
        <p>{html.escape(symbol)} 已连续失败 {count} 次。</p>
        <p>错误摘要：{html.escape(message)}</p>
        <p>请打开 GitHub Actions 日志排查。邮件中不会包含任何密钥。</p>
        """
        return self.send(f"[Stock Sentinel] {symbol} 数据源连续失败", body)
