"""
Opportunity detector: Marks Tier 1/2 triggers with Graham margin-of-safety gate.

Howard Marks principle: opportunity mode is justified when fear is highest.
Benjamin Graham gate: never enter without margin of safety (15% min for stocks).

Tier 1: 30%+ drawdown from 6-12m high + 15% MoS → deploy 20% of opportunity vault
Tier 2: 50%+ drawdown + 25% MoS + existing Tier 1 → deploy 30% more

Maximum 5 opportunity events per year (prevents chasing).
All deployments require explicit approval — NEVER auto-execute.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

from app.schemas.allocation_models import ProposedTrade

logger = logging.getLogger(__name__)

# IPS opportunity rules (CLAUDE.md Section 7)
OPPORTUNITY_RULES: dict[str, Any] = {
    "max_events_per_year": 5,
    "required_min_margin_of_safety": 0.15,  # Graham: never buy without safety buffer
    "tier_1": {
        "drawdown_from_6_12m_high": 0.30,   # 30%+
        "deploy_fraction_of_vault": 0.20,    # 20% of opportunity vault
        "max_portfolio_fraction": 0.02,      # max 2% of total portfolio
    },
    "tier_2": {
        "drawdown_from_6_12m_high": 0.50,   # 50%+
        "deploy_additional_vault_fraction": 0.30,
        "max_total_portfolio_fraction": 0.05,  # 5% per event total
    },
}


def evaluate_tier_1_trigger(
    drawdown_pct: float,
    margin_of_safety_pct: float,
    events_this_year: int,
    config: dict | None = None,
) -> bool:
    """
    Evaluate if Tier 1 opportunity trigger conditions are met.

    Requires BOTH:
    1. Drawdown >= 30% from 6-12 month high (Marks: price has fallen enough)
    2. Margin of safety >= 15% (Graham: price is below intrinsic value)

    Never triggers if max_events_per_year already reached.

    Args:
        drawdown_pct: Current drawdown from 6-12m high (negative, e.g. -0.35 = 35% below).
        margin_of_safety_pct: (fair_value - price) / fair_value. Positive = undervalued.
        events_this_year: Number of opportunity events already triggered this year.
        config: Optional override of OPPORTUNITY_RULES.

    Returns:
        True if Tier 1 trigger conditions are met.
    """
    rules = config or OPPORTUNITY_RULES
    max_events = rules.get("max_events_per_year", 5)
    min_mos = rules.get("required_min_margin_of_safety", 0.15)
    tier1 = rules.get("tier_1", OPPORTUNITY_RULES["tier_1"])
    required_drawdown = tier1["drawdown_from_6_12m_high"]

    if events_this_year >= max_events:
        logger.info("Tier 1 skipped: max events per year (%d) reached", max_events)
        return False

    # drawdown_pct is negative (e.g. -0.35), required_drawdown is positive (0.30)
    actual_drawdown = abs(drawdown_pct)

    passes_drawdown = actual_drawdown >= required_drawdown
    passes_graham = margin_of_safety_pct >= min_mos

    if not passes_drawdown:
        logger.debug(
            "Tier 1 not triggered: drawdown %.1f%% < required %.1f%%",
            actual_drawdown * 100, required_drawdown * 100,
        )
    if not passes_graham:
        logger.debug(
            "Tier 1 Graham gate: MoS %.1f%% < required %.1f%%",
            margin_of_safety_pct * 100, min_mos * 100,
        )

    return passes_drawdown and passes_graham


def evaluate_tier_2_trigger(
    drawdown_pct: float,
    margin_of_safety_pct: float,
    existing_tier_1_event: dict | None,
    config: dict | None = None,
) -> bool:
    """
    Evaluate if Tier 2 escalation is warranted.

    Requires:
    1. Existing Tier 1 event (can't jump to Tier 2 without Tier 1)
    2. Drawdown >= 50% from 6-12m high (further deterioration)
    3. Margin of safety >= 25% (deeper discount = higher conviction)

    Args:
        drawdown_pct: Current drawdown (negative, e.g. -0.55 = 55% below high).
        margin_of_safety_pct: Current MoS. Positive = undervalued.
        existing_tier_1_event: Existing open Tier 1 opportunity event dict (or None).
        config: Optional override.

    Returns:
        True if Tier 2 trigger conditions are met.
    """
    if existing_tier_1_event is None:
        logger.debug("Tier 2 skipped: no existing Tier 1 event")
        return False

    # Tier 2 already triggered?
    if existing_tier_1_event.get("tier_2_trigger_date") is not None:
        logger.debug("Tier 2 already triggered for this event")
        return False

    rules = config or OPPORTUNITY_RULES
    tier2 = rules.get("tier_2", OPPORTUNITY_RULES["tier_2"])
    required_drawdown = tier2["drawdown_from_6_12m_high"]
    min_mos = 0.25  # Tier 2 requires deeper discount

    actual_drawdown = abs(drawdown_pct)

    return actual_drawdown >= required_drawdown and margin_of_safety_pct >= min_mos


def compute_opportunity_vault_deployment(
    vault_balance_usd: float,
    tier: int,
    portfolio_value_usd: float,
    config: dict | None = None,
) -> float:
    """
    Compute how much to deploy from opportunity vault for a given tier.

    Respects both vault fraction limits AND portfolio fraction limits.
    Takes the MIN of the two to be conservative.

    Args:
        vault_balance_usd: Current opportunity vault balance in USD.
        tier: Opportunity tier (1 or 2).
        portfolio_value_usd: Total portfolio value in USD.
        config: Optional override.

    Returns:
        Amount in USD to deploy (always requires approval before executing).
    """
    rules = config or OPPORTUNITY_RULES

    if tier == 1:
        tier_rules = rules.get("tier_1", OPPORTUNITY_RULES["tier_1"])
        vault_fraction = tier_rules["deploy_fraction_of_vault"]
        portfolio_cap = tier_rules["max_portfolio_fraction"] * portfolio_value_usd
    elif tier == 2:
        tier_rules = rules.get("tier_2", OPPORTUNITY_RULES["tier_2"])
        vault_fraction = tier_rules["deploy_additional_vault_fraction"]
        portfolio_cap = tier_rules["max_total_portfolio_fraction"] * portfolio_value_usd
    else:
        raise ValueError(f"Invalid tier: {tier}")

    from_vault = vault_balance_usd * vault_fraction
    deploy_amount = min(from_vault, portfolio_cap)

    logger.info(
        "Tier %d opportunity: vault=%s, portfolio_cap=%s, deploy=%s",
        tier,
        f"${vault_balance_usd:,.0f}",
        f"${portfolio_cap:,.0f}",
        f"${deploy_amount:,.0f}",
    )

    return round(deploy_amount, 2)


def build_opportunity_trade(
    asset: dict,
    deploy_amount_usd: float,
    tier: int,
    margin_of_safety_pct: float,
    account: dict,
) -> ProposedTrade:
    """
    Build a ProposedTrade for an opportunity deployment.

    Always requires_approval=True — hard constraint, never auto-execute.

    Args:
        asset: Asset dict (symbol, asset_class, etc.).
        deploy_amount_usd: Amount to deploy in USD.
        tier: Opportunity tier (1 or 2).
        margin_of_safety_pct: Computed margin of safety.
        account: Account to route trade into.

    Returns:
        ProposedTrade with requires_approval=True.
    """
    symbol = asset.get("symbol", "")
    asset_class = asset.get("asset_class", "")

    tier_label = f"Tier {tier}"
    drawdown_label = "30%+" if tier == 1 else "50%+"

    return ProposedTrade(
        account_name=account.get("name", "Opportunity Account"),
        account_id=account.get("id"),
        trade_type="buy",
        symbol=symbol,
        asset_class=asset_class,
        amount_usd=deploy_amount_usd,
        reason=(
            f"{tier_label} Opportunity: {drawdown_label} drawdown from 6-12m high, "
            f"{margin_of_safety_pct*100:.1f}% margin of safety"
        ),
        sleeve=_asset_class_to_sleeve(asset_class),
        tax_risk_level="low",  # Opportunity = buying, not selling
        requires_approval=True,  # HARD CONSTRAINT: always approval required
        opportunity_tier=tier,
        margin_of_safety_pct=margin_of_safety_pct,
    )


def count_opportunity_events_this_year(events: list[dict]) -> int:
    """
    Count opportunity events triggered in the current calendar year.

    Args:
        events: List of opportunity_events records from DB.

    Returns:
        Count of events where start_date is in current year.
    """
    current_year = date.today().year
    return sum(
        1 for e in events
        if e.get("start_date") and str(e["start_date"])[:4] == str(current_year)
    )


# ── helpers ────────────────────────────────────────────────────────────────────

def _asset_class_to_sleeve(asset_class: str) -> str:
    """Map asset class to sleeve key."""
    mapping = {
        "US_equity": "us_equity",
        "Intl_equity": "intl_equity",
        "Bond": "bonds",
        "Brazil_equity": "brazil_equity",
        "Crypto": "crypto",
    }
    return mapping.get(asset_class, "us_equity")
