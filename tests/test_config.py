from __future__ import annotations

import pytest

from stock_sentinel.config import ConfigError, validate_config


def test_config_rejects_unsafe_symbol() -> None:
    with pytest.raises(ConfigError):
        validate_config({"stocks": [{"symbol": "AAPL; DROP", "name": "bad"}]})


def test_config_rejects_duplicate_symbol() -> None:
    with pytest.raises(ConfigError):
        validate_config({"stocks": [{"symbol": "AAPL"}, {"symbol": "AAPL"}]})
