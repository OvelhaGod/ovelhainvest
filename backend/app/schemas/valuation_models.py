"""Pydantic models for the valuation API (Phase 3)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field


class ValuationUpdateRequest(BaseModel):
    user_id: str = "00000000-0000-0000-0000-000000000001"
    dry_run: bool = Field(False, description="Compute scores but skip DB writes")
    economic_season: str | None = Field(
        None, description="Override detected season (for testing)"
    )


class ValuationUpdateResponse(BaseModel):
    assets_updated: int
    top_opportunities: list[dict[str, Any]]
    notable_changes: list[str]
    errors: list[str]
    economic_season: str
    run_timestamp: datetime


class AssetValuationDetail(BaseModel):
    """Full valuation detail for a single asset (GET /valuation/{symbol})."""
    # Asset metadata
    symbol: str
    name: str | None = None
    asset_class: str | None = None
    currency: str = "USD"
    moat_rating: str | None = None
    is_dcf_eligible: bool = False
    sector: str | None = None
    region: str | None = None

    # Market data
    as_of_date: date | None = None
    price: float | None = None
    pe: float | None = None
    ps: float | None = None
    dividend_yield: float | None = None
    vol_30d: float | None = None
    drawdown_from_6_12m_high_pct: float | None = None

    # Factor scores
    value_score: float | None = None
    momentum_score: float | None = None
    quality_score: float | None = None
    composite_score: float | None = None
    rank_in_universe: int | None = None
    tier: str | None = None

    # Intrinsic value / Graham
    fair_value_estimate_dcf: float | None = None
    margin_of_safety_pct: float | None = None
    buy_target: float | None = None
    hold_range_low: float | None = None
    hold_range_high: float | None = None
    sell_target: float | None = None
    dcf_assumptions: dict[str, Any] | None = None
    passes_buy_gate: bool = False


class ValuationSummaryResponse(BaseModel):
    """High-level summary for the GET /valuation_summary endpoint."""
    as_of_date: str | None = None
    assets_scored: int = 0
    positive_mos_count: int = 0
    negative_mos_count: int = 0
    opportunity_count: int = 0
    top_by_composite: list[dict[str, Any]] = Field(default_factory=list)
    top_opportunities: list[dict[str, Any]] = Field(default_factory=list)
    margin_of_safety_distribution: dict[str, int] = Field(default_factory=dict)
