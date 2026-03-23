"""Pydantic models for AI advisor API (Phase 5)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class FrameworkCheck(BaseModel):
    swensen_alignment: str = "pass"       # "pass" | "warning" | "fail"
    dalio_risk_balance: str = "pass"
    marks_cycle_read: str = ""            # free-text cycle commentary
    graham_margin_of_safety: str = "pass"
    bogle_cost_check: str = "pass"
    # Extra detail per framework (AI may populate)
    swensen_detail: str | None = None
    dalio_detail: str | None = None
    marks_detail: str | None = None
    graham_detail: str | None = None
    bogle_detail: str | None = None


class ValidationResult(BaseModel):
    overall_status: str = "ok"            # "ok" | "warning" | "block" | "parse_error"
    issues: list[str] = Field(default_factory=list)


class TradeFeedback(BaseModel):
    symbol: str
    recommendation: str                   # "proceed" | "caution" | "skip"
    comment: str = ""


class TradeRecommendations(BaseModel):
    summary: str = ""
    per_trade_feedback: list[TradeFeedback] = Field(default_factory=list)
    suggested_adjustments: list[str] = Field(default_factory=list)


class PortfolioAssessment(BaseModel):
    risk_posture: str = ""
    diversification_comment: str = ""
    factor_tilts: str = ""
    benchmark_comparison: str = ""


class MacroOpportunityCommentary(BaseModel):
    macro_regime: str = ""
    cycle_position: str = ""
    macro: list[str] = Field(default_factory=list)
    opportunities: list[str] = Field(default_factory=list)
    risks_to_watch: list[str] = Field(default_factory=list)


class ExplanationForUser(BaseModel):
    short_summary: str = ""              # ≤100 words
    detailed_bullets: list[str] = Field(default_factory=list)


class AIResponse(BaseModel):
    validation: ValidationResult = Field(default_factory=ValidationResult)
    investment_framework_check: FrameworkCheck = Field(default_factory=FrameworkCheck)
    trade_recommendations: TradeRecommendations = Field(default_factory=TradeRecommendations)
    portfolio_assessment: PortfolioAssessment = Field(default_factory=PortfolioAssessment)
    macro_and_opportunity_commentary: MacroOpportunityCommentary = Field(
        default_factory=MacroOpportunityCommentary
    )
    explanation_for_user: ExplanationForUser = Field(default_factory=ExplanationForUser)
    # Metadata
    model_used: str = "claude-sonnet-4-20250514"
    input_tokens: int = 0
    output_tokens: int = 0
    cached: bool = False


# ── Journal models ─────────────────────────────────────────────────────────

class DecisionJournal(BaseModel):
    id: str
    user_id: str
    event_date: str
    signal_run_id: str | None = None
    action_type: str                     # "followed" | "overrode" | "deferred" | "manual_trade"
    asset_id: str | None = None
    system_recommendation: dict[str, Any] | None = None
    actual_action: dict[str, Any] | None = None
    reasoning: str | None = None
    outcome_30d: float | None = None
    outcome_90d: float | None = None
    created_at: str | None = None


class OverrideAccuracyStats(BaseModel):
    followed_count: int
    overrode_count: int
    deferred_count: int
    manual_count: int
    avg_outcome_followed_30d: float | None = None
    avg_outcome_overrode_30d: float | None = None
    avg_outcome_followed_90d: float | None = None
    avg_outcome_overrode_90d: float | None = None
    system_outperformance_30d: float | None = None   # followed - overrode
    system_outperformance_90d: float | None = None
    total_decisions: int
