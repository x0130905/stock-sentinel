from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class StockConfig:
    symbol: str
    name: str
    market: str = "US"
    cost_basis: float = 0.0
    quantity: float = 0.0
    target_return_percent: float = 10.0
    max_loss_percent: float = 8.0
    take_profit_price: float | None = None
    stop_loss_price: float | None = None
    email_enabled: bool = False
    buy_alert_enabled: bool = True
    sell_alert_enabled: bool = True
    daily_summary_enabled: bool = True


@dataclass(slots=True)
class Criterion:
    key: str
    label: str
    triggered: bool
    score: float
    max_score: float
    detail: str


@dataclass(slots=True)
class ScoreResult:
    score: int
    criteria: list[Criterion]


@dataclass(slots=True)
class MarketData:
    symbol: str
    frame: Any
    provider: str
    updated_at: datetime
    delayed: bool
    delay_minutes: int | None
    delay_note: str
    mode: str = "live"


@dataclass(slots=True)
class AnalysisResult:
    symbol: str
    name: str
    market: str
    price: float
    previous_close: float
    change_percent: float
    updated_at: str
    provider: str
    delayed: bool
    delay_minutes: int | None
    delay_note: str
    mode: str
    buy_score: int
    sell_score: int
    signal_label: str
    risk_level: str
    confidence: str
    human_confirmation_required: bool
    support: float
    resistance: float
    attention_range: list[float]
    stop_loss_reference: float
    metrics: dict[str, float | None]
    buy_criteria: list[Criterion] = field(default_factory=list)
    sell_criteria: list[Criterion] = field(default_factory=list)
    position: dict[str, float] = field(default_factory=dict)
    price_history: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class AlertEvent:
    id: str
    symbol: str
    name: str
    alert_type: str
    label: str
    reason: str
    price: float
    score: int | None
    created_at: str
    sent: bool = False
    simulated: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
