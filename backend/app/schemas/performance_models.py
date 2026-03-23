"""Pydantic models for performance analytics API."""

from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel


class PeriodReturn(BaseModel):
    period: str
    twr: float | None = None
    mwr: float | None = None
    benchmark_return: float | None = None
    active_return: float | None = None


class RatioInterpretation(BaseModel):
    value: float | None
    label: str  # "Poor" | "Fair" | "Good" | "Excellent"


class DrawdownInfo(BaseModel):
    max_drawdown_pct: float | None
    peak_date: date | None
    trough_date: date | None
    current_drawdown_pct: float | None


class PerformanceSummaryResponse(BaseModel):
    user_id: str | None = None
    as_of_date: date | None = None
    period_returns: list[PeriodReturn]
    sharpe: RatioInterpretation
    sortino: RatioInterpretation
    calmar: RatioInterpretation
    beta: float | None
    information_ratio: float | None
    volatility_annualized: float | None
    drawdown: DrawdownInfo
    data_points: int


class SleeveAttributionDetail(BaseModel):
    sleeve: str
    portfolio_weight: float
    benchmark_weight: float
    portfolio_return: float
    benchmark_return: float
    allocation_effect: float
    selection_effect: float
    interaction_effect: float
    total_effect: float


class AttributionResponse(BaseModel):
    user_id: str | None = None
    period_start: date | None = None
    period_end: date | None = None
    portfolio_return: float | None = None
    benchmark_return: float | None = None
    active_return: float | None = None
    total_allocation_effect: float | None = None
    total_selection_effect: float | None = None
    total_interaction_effect: float | None = None
    fx_contribution: float | None = None
    per_sleeve: list[SleeveAttributionDetail]


class BenchmarkComparisonResponse(BaseModel):
    benchmark_symbol: str
    period: str
    portfolio_return: float | None = None
    benchmark_return: float | None = None
    active_return: float | None = None
    beta: float | None = None
    correlation: float | None = None
    information_ratio: float | None = None


class RollingReturnPoint(BaseModel):
    date: date
    value_1mo: float | None = None
    value_3mo: float | None = None
    value_1yr: float | None = None


class RollingReturnsResponse(BaseModel):
    user_id: str | None = None
    data_points: list[dict[str, Any]]
    windows: list[str]


class RiskSummaryResponse(BaseModel):
    user_id: str | None = None
    as_of_date: date | None = None
    var_95: float | None = None
    var_99: float | None = None
    cvar_95: float | None = None
    diversification_ratio: float | None = None
    risk_parity_weights: dict[str, float]
    actual_weights: dict[str, float]
    correlation_matrix: dict[str, dict[str, float]]
    high_correlation_pairs: list[dict[str, Any]]


class SnapshotTriggerResponse(BaseModel):
    status: str
    snapshot_date: date
    total_value_usd: float | None = None
    message: str
