"""
Rebalancing engine: soft (new money) and hard (sell/buy) rebalance proposals.

Rules encoded (CLAUDE.md Section 7):
- Soft rebalance preferred over hard rebalance (Bogle: minimize turnover)
- Hard rebalance: max once per 30 days
- Min trade size: $50 USD
- Max single trade: 5% of portfolio
- Max daily trades: 10% of portfolio
- Opportunity vault trades always require approval (Marks: never auto-execute)
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any

from app.schemas.allocation_models import ProposedTrade, SleeveWeight

logger = logging.getLogger(__name__)

# IPS trade size limits (CLAUDE.md Section 7)
MIN_TRADE_USD = 50.0
MAX_SINGLE_TRADE_PCT = 0.05    # 5% of portfolio
MAX_DAILY_TRADES_PCT = 0.10    # 10% of portfolio
HARD_REBALANCE_MIN_DAYS = 30   # max once per 30 days

# Tax treatment priority for sell decisions (Swensen tax-location)
SELL_PRIORITY_ORDER = [
    "tax_deferred",    # 401k — sell here first (no immediate tax)
    "tax_free",        # Roth — sell if needed
    "taxable",         # M1 Taxable — prefer not to sell (HIFO, loss harvest only)
    "brazil_taxable",  # Clear — Brazil rules apply
]


def propose_soft_rebalance_trades(
    drift_weights: list[SleeveWeight],
    available_cash_usd: float,
    assets_by_sleeve: dict[str, list[dict]],
    prices: dict[str, float],
    portfolio_value_usd: float,
    preferred_accounts: list[dict],
    config: dict | None = None,
) -> list[ProposedTrade]:
    """
    Propose soft rebalance: route new money to underweight sleeves only.
    Never sells positions. Respects min/max trade limits.

    Args:
        drift_weights: SleeveWeight list sorted by drift (most underweight first).
        available_cash_usd: Cash available for deployment (vault balance).
        assets_by_sleeve: Dict sleeve → list of asset dicts to buy.
        prices: Dict symbol → price.
        portfolio_value_usd: Total portfolio value for max trade calculation.
        preferred_accounts: List of account dicts to route trades into.
        config: Optional strategy config override.

    Returns:
        List of ProposedTrade.
    """
    max_single = (config or {}).get("max_single_trade_pct", MAX_SINGLE_TRADE_PCT)
    max_trade_usd = portfolio_value_usd * max_single
    min_trade = (config or {}).get("min_trade_usd", MIN_TRADE_USD)

    if available_cash_usd <= 0 or not drift_weights:
        return []

    # Identify underweight sleeves (negative drift = below target)
    underweight = [sw for sw in drift_weights if sw.drift < -0.005]  # >0.5% below target
    if not underweight:
        return []

    # Allocate cash proportionally to how underweight each sleeve is
    total_underweight = sum(abs(sw.drift) for sw in underweight)
    trades: list[ProposedTrade] = []
    remaining_cash = available_cash_usd

    for sw in underweight:
        if remaining_cash < min_trade:
            break

        fraction = abs(sw.drift) / total_underweight if total_underweight > 0 else 0
        amount = min(fraction * available_cash_usd, max_trade_usd, remaining_cash)

        if amount < min_trade:
            continue

        # Pick the primary asset for this sleeve
        sleeve_assets = assets_by_sleeve.get(sw.sleeve, [])
        if not sleeve_assets:
            logger.warning("No assets configured for sleeve %s — skipping", sw.sleeve)
            continue

        primary_asset = sleeve_assets[0]  # first = core ETF or primary position
        symbol = primary_asset.get("symbol", "")
        account = _select_account_for_sleeve(sw.sleeve, preferred_accounts)

        trades.append(ProposedTrade(
            account_name=account.get("name", "Unknown"),
            account_id=account.get("id"),
            trade_type="buy",
            symbol=symbol,
            asset_class=primary_asset.get("asset_class", sw.sleeve),
            amount_usd=round(amount, 2),
            quantity_estimate=_estimate_qty(symbol, amount, prices),
            reason=f"Soft rebalance: {sw.sleeve} underweight by {abs(sw.drift_pct):.1f}%",
            sleeve=sw.sleeve,
            tax_risk_level="low",
            requires_approval=False,
        ))
        remaining_cash -= amount

    return trades


def propose_hard_rebalance_trades(
    drift_weights: list[SleeveWeight],
    holdings: list[dict],
    prices: dict[str, float],
    portfolio_value_usd: float,
    last_hard_rebalance_date: date | None,
    accounts: list[dict],
    config: dict | None = None,
) -> list[ProposedTrade]:
    """
    Propose hard rebalance: sell overweight, buy underweight.
    Only triggers if drift > 5% AND last hard rebalance was > 30 days ago.
    Prefers selling in tax-advantaged accounts first.

    Args:
        drift_weights: SleeveWeight list.
        holdings: All current holdings.
        prices: Dict symbol → price.
        portfolio_value_usd: Total portfolio value.
        last_hard_rebalance_date: Date of last hard rebalance (None if never).
        accounts: List of account dicts with tax_treatment.
        config: Optional strategy config override.

    Returns:
        List of ProposedTrade.
    """
    min_days = (config or {}).get("hard_rebalance_min_days", HARD_REBALANCE_MIN_DAYS)
    max_single = (config or {}).get("max_single_trade_pct", MAX_SINGLE_TRADE_PCT)
    max_trade_usd = portfolio_value_usd * max_single
    min_trade = (config or {}).get("min_trade_usd", MIN_TRADE_USD)

    # Check cadence: no hard rebalance within 30 days
    if last_hard_rebalance_date:
        days_since = (date.today() - last_hard_rebalance_date).days
        if days_since < min_days:
            logger.info(
                "Hard rebalance skipped: only %d days since last (min %d)", days_since, min_days
            )
            return []

    # Only hard rebalance sleeves with abs(drift) > 5%
    breached = [sw for sw in drift_weights if sw.is_breached]
    if not breached:
        return []

    trades: list[ProposedTrade] = []
    overweight = [sw for sw in breached if sw.drift > 0]
    underweight = [sw for sw in breached if sw.drift < 0]

    # Generate sell trades for overweight sleeves (tax-advantaged first)
    account_by_id = {a["id"]: a for a in accounts if "id" in a}
    for sw in overweight:
        excess_usd = sw.drift * portfolio_value_usd
        sell_amount = min(excess_usd * 0.5, max_trade_usd)  # sell half the excess
        if sell_amount < min_trade:
            continue

        # Find best holding to sell in this sleeve (prefer tax-deferred)
        best_holding = _find_best_holding_to_sell(sw.sleeve, holdings, account_by_id, prices)
        if not best_holding:
            continue

        account = account_by_id.get(best_holding.get("account_id", ""), {})
        tax_treatment = account.get("tax_treatment", "taxable")
        symbol = best_holding.get("symbol", "")
        qty_est = _estimate_qty(symbol, sell_amount, prices)
        tax_risk = _assess_tax_risk(tax_treatment, best_holding)
        tax_cost_usd: float | None = None

        # Estimate tax cost for taxable sell trades (Phase 8)
        if tax_treatment in ("taxable", "brazil_taxable"):
            tax_cost_usd = _estimate_sell_tax_cost(
                best_holding, qty_est or 0.0, prices.get(symbol, 0.0), tax_treatment
            )
            if tax_cost_usd is not None and tax_cost_usd > 200:
                tax_risk = "high"

        trades.append(ProposedTrade(
            account_name=account.get("name", "Unknown"),
            account_id=account.get("id"),
            trade_type="sell",
            symbol=symbol,
            asset_class=best_holding.get("asset_class", ""),
            amount_usd=round(sell_amount, 2),
            quantity_estimate=qty_est,
            reason=f"Hard rebalance: {sw.sleeve} overweight by {sw.drift_pct:.1f}%",
            sleeve=sw.sleeve,
            tax_risk_level=tax_risk,
            tax_cost_usd=round(tax_cost_usd, 2) if tax_cost_usd is not None else None,
            requires_approval=True,  # Hard rebalances always need approval
        ))

    return trades


def apply_trade_size_limits(
    trades: list[ProposedTrade],
    portfolio_value_usd: float,
    config: dict | None = None,
) -> list[ProposedTrade]:
    """
    Filter and cap trades to respect IPS size limits.

    Args:
        trades: Raw proposed trades.
        portfolio_value_usd: Total portfolio value.
        config: Optional config override.

    Returns:
        Filtered list respecting min/max size constraints.
    """
    max_single_pct = (config or {}).get("max_single_trade_pct", MAX_SINGLE_TRADE_PCT)
    min_trade = (config or {}).get("min_trade_usd", MIN_TRADE_USD)
    max_trade_usd = portfolio_value_usd * max_single_pct

    result = []
    for t in trades:
        if t.amount_usd < min_trade:
            logger.debug("Trade %s $%.2f below min — skipped", t.symbol, t.amount_usd)
            continue
        if t.amount_usd > max_trade_usd:
            t.amount_usd = round(max_trade_usd, 2)
            t.reason += f" (capped at {max_single_pct*100:.0f}% portfolio limit)"
        result.append(t)

    return result


def enforce_cadence_rules(
    trades: list[ProposedTrade],
    last_execution_date: date | None,
    portfolio_value_usd: float,
    config: dict | None = None,
) -> list[ProposedTrade]:
    """
    Enforce execution frequency limits:
    - Max 1 execution day per week
    - Max 10% of portfolio traded in a single day

    Args:
        trades: Proposed trades.
        last_execution_date: Date of last executed trade (None if never).
        portfolio_value_usd: Total portfolio value.
        config: Optional override.

    Returns:
        Trades list (may be emptied if cadence violated).
    """
    max_daily_pct = (config or {}).get("max_daily_trades_pct", MAX_DAILY_TRADES_PCT)

    # Max once per week
    if last_execution_date:
        days_since = (date.today() - last_execution_date).days
        if days_since < 7:
            logger.info(
                "Cadence: only %d days since last execution (min 7) — deferring", days_since
            )
            return []

    # Cap total trade volume to 10% of portfolio
    total_volume = sum(t.amount_usd for t in trades)
    max_volume = portfolio_value_usd * max_daily_pct

    if total_volume <= max_volume:
        return trades

    # Trim trades proportionally to fit within limit
    scale = max_volume / total_volume
    scaled = []
    for t in trades:
        new_amount = round(t.amount_usd * scale, 2)
        if new_amount >= MIN_TRADE_USD:
            t.amount_usd = new_amount
            scaled.append(t)
    return scaled


def flag_approval_required(
    trades: list[ProposedTrade],
    config: dict | None = None,
) -> list[ProposedTrade]:
    """
    Mark trades that require explicit approval:
    - Any trade from/to opportunity vault
    - Hard rebalance sell trades
    - Crypto trades above threshold

    Args:
        trades: Proposed trades list.
        config: Optional override.

    Returns:
        Same list with requires_approval flags updated.
    """
    for t in trades:
        # Opportunity vault deploys always need approval (hard constraint)
        if t.opportunity_tier is not None:
            t.requires_approval = True
        # Sell trades always need approval
        if t.trade_type == "sell":
            t.requires_approval = True
        # Crypto buys above $1k need approval
        if t.asset_class == "Crypto" and t.amount_usd > 1000:
            t.requires_approval = True

    return trades


# ── helpers ────────────────────────────────────────────────────────────────────

def _select_account_for_sleeve(sleeve: str, accounts: list[dict]) -> dict:
    """Select best account to buy into for a given sleeve (Swensen tax-location)."""
    # Bonds → tax-deferred; equities → Roth/taxable; Brazil → Clear
    preference = {
        "bonds":         ["tax_deferred", "taxable"],
        "us_equity":     ["tax_free", "taxable"],
        "intl_equity":   ["tax_free", "taxable"],
        "brazil_equity": ["brazil_taxable"],
        "crypto":        ["taxable"],
        "cash":          ["bank", "taxable"],
    }
    preferred_treatments = preference.get(sleeve, ["taxable"])

    for treatment in preferred_treatments:
        for acc in accounts:
            if acc.get("tax_treatment") == treatment and acc.get("is_active", True):
                return acc

    return accounts[0] if accounts else {}


def _find_best_holding_to_sell(
    sleeve: str,
    holdings: list[dict],
    account_by_id: dict,
    prices: dict[str, float],
) -> dict | None:
    """Find best holding to sell: prefer tax-deferred, largest position."""
    sleeve_holdings = [
        h for h in holdings
        if h.get("sleeve") == sleeve or h.get("asset_class", "").lower().replace("_", " ") in sleeve
    ]
    if not sleeve_holdings:
        return None

    # Sort: tax_deferred first (no immediate tax), then by value descending
    def sort_key(h: dict) -> tuple:
        acc = account_by_id.get(h.get("account_id", ""), {})
        tax = acc.get("tax_treatment", "taxable")
        priority = SELL_PRIORITY_ORDER.index(tax) if tax in SELL_PRIORITY_ORDER else 99
        price = prices.get(h.get("symbol", ""), 0.0)
        value = float(h.get("quantity", 0)) * price
        return (priority, -value)

    return sorted(sleeve_holdings, key=sort_key)[0]


def _estimate_qty(symbol: str, amount_usd: float, prices: dict[str, float]) -> float | None:
    """Estimate quantity from USD amount and current price."""
    price = prices.get(symbol)
    if price and price > 0:
        return round(amount_usd / price, 6)
    return None


def _assess_tax_risk(tax_treatment: str, holding: dict) -> str:
    """Classify tax risk for a sell trade."""
    if tax_treatment in ("tax_deferred", "tax_free"):
        return "low"
    if tax_treatment == "brazil_taxable":
        return "medium"
    # US taxable: check if it's likely short-term
    acquired = holding.get("acquisition_date")
    if acquired:
        try:
            acq_date = date.fromisoformat(str(acquired))
            if (date.today() - acq_date).days < 365:
                return "high"  # Short-term gains
        except Exception:
            pass
    return "medium"


def _estimate_sell_tax_cost(
    holding: dict,
    quantity: float,
    current_price: float,
    tax_treatment: str,
) -> float | None:
    """
    Estimate tax cost for a sell trade using holding's avg_cost_basis.

    Uses a simplified single-lot approximation. For HIFO precision,
    use tax_lot_engine.estimate_tax_impact() with actual lots.
    Returns None if insufficient data to compute.
    """
    if quantity <= 0 or current_price <= 0:
        return None

    cost_pu = float(holding.get("avg_cost_basis") or 0.0)
    if cost_pu <= 0:
        return None

    gain = (current_price - cost_pu) * quantity
    if gain <= 0:
        return None  # No gain → no tax cost (harvest candidate instead)

    # Determine holding period for rate selection
    acquired = holding.get("acquisition_date")
    is_long_term = True
    if acquired:
        try:
            acq_date = date.fromisoformat(str(acquired[:10]))
            is_long_term = (date.today() - acq_date).days >= 365
        except Exception:
            pass

    if tax_treatment == "brazil_taxable":
        rate = 0.15  # Brazil CGT flat rate
    elif is_long_term:
        rate = 0.15  # US long-term capital gains
    else:
        rate = 0.32  # US short-term (ordinary income)

    return gain * rate
