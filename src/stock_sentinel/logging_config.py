from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

SENSITIVE_NAMES = (
    "ALPHA_VANTAGE_API_KEY",
    "TWELVE_DATA_API_KEY",
    "RESEND_API_KEY",
    "SMTP_PASSWORD",
)


class SecretFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        for name in SENSITIVE_NAMES:
            secret = os.getenv(name)
            if secret:
                message = message.replace(secret, "***")
        record.msg = message
        record.args = ()
        return True


def configure_logging(log_dir: Path) -> logging.Logger:
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("stock_sentinel")
    logger.setLevel(logging.INFO)
    if logger.handlers:
        return logger
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s", "%Y-%m-%dT%H:%M:%S%z"
    )
    secret_filter = SecretFilter()
    stream = logging.StreamHandler()
    stream.setFormatter(formatter)
    stream.addFilter(secret_filter)
    file_handler = RotatingFileHandler(
        log_dir / "stock-sentinel.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    file_handler.addFilter(secret_filter)
    logger.addHandler(stream)
    logger.addHandler(file_handler)
    return logger
