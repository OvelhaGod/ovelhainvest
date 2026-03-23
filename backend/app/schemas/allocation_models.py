"""Pydantic models for allocation API request/response shapes."""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class RegimeState(str, Enum):
    NORMAL = "normal"
    HIGH_VOL = "high_vol"
    OPPORTUNITY = "opportunity"
    PAUSED = "paused"  # 40%+ drawdown — automation paused


class EconomicSeason(str, Enum):
    RISING_GROWTH_LOW_INFLATION = "rising_growth_low_inflation"
    FALLING_GROWTH_LOW_INFLATION = "falling_growth_low_inflation"
    RISING_INFLATION = "rising_inflation"
    FALLING_INFLATION_GROWTH_RECOVERY = "falling_inflation_growth_recovery"
    NORMAL = "normal"


class SleeveWeight(BaseModel):
    sleeve: str
    current_weight: float
    target_weight: float
    min_weight: float
    max_weight: float
    drift: float = Field(description="current - target")
    drift_pct: float = Field(description="drift as percentage points")
    is_breached: bool = Field(description="abs(drift) > 0.05")
    current_value_usd: float


class ProposedTrade(BaseModel):
    account_name: str
    account_id: str | None = None
    trade_type: str = Field(description="buy | sell | rebalance")
    symbol: str
    asset_class: str
    amount_usd: float
    quantity_estimate: float | None = None
    reason: str
    sleeve: str
    tax_risk_level: str = Field(description="low | medium | high")
    requires_approval: bool = False
    opportunity_tier: int | None = None
    margin_of_safety_pct: float | None = None
    # Phase 8 — tax cost estimate for sell trades in taxable accounts
    tax_cost_usd: float | None = None


class VaultBalance(BaseModel):
    vault_type: str
    balance_usd: float
    min_balance: float | None
    is_investable: bool
    approval_required: bool
    progress_pct: float | None = None


class AllocationRunRequest(BaseModel):
    user_id: str
    event_type: str = "daily_check"
    notes: str | None = None
    force_hard_rebalance: bool = False


class AllocationRunResponse(BaseModel):
    run_id: str
    run_timestamp: datetime
    event_type: str
    regime_state: RegimeState
    economic_season: EconomicSeason
    sleeve_weights: list[SleeveWeight]
    vault_balances: list[VaultBalance]
    proposed_trades: list[ProposedTrade]
    total_value_usd: float
    total_value_brl: float
    usd_brl_rate: float
    approval_required_count: int
    deferred_dca: bool = False
    deferred_reason: str | None = None
    status: str = "pending"
    # Phase 5 — AI advisor fields
    ai_validation_summary: dict[str, Any] | None = None
    ai_framework_check: dict[str, Any] | None = None
    alerts_dispatched: int = 0
    # Phase 8 — tax efficiency fields
    total_estimated_tax_cost: float | None = None
    tax_efficiency_note: str | None = None


class DailyStatusResponse(BaseModel):
    total_value_usd: float
    total_value_brl: float
    usd_brl_rate: float
    sleeve_weights: list[SleeveWeight]
    vault_balances: list[VaultBalance]
    regime_state: RegimeState
    economic_season: EconomicSeason
    pending_approvals: int
    last_run_timestamp: datetime | None
    today_pnl_usd: float | None
    today_pnl_pct: float | None
    ytd_return_twr: float | None
    max_drawdown_pct: float | None
    portfolio_snapshot_date: date | None
    # Phase 4 — performance fields
    ytd_vs_benchmark: float | None = None       # active return vs SPY YTD
    sharpe_trailing_12mo: float | None = None   # trailing 12-month Sharpe
    max_drawdown_current: float | None = None   # current drawdown from peak (live)
