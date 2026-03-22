"""
Contribution optimizer: optimal account routing and tax-location.

Swensen-inspired: bonds → tax-deferred, growth → Roth IRA,
income payers → avoid taxable.

Phase 7 implementation — delegated to simulation_engine.run_contribution_optimizer().
This module focuses on the tax-location logic.

Phase 7 implementation — stub only.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# Tax-location priority (Swensen model)
# Each asset class maps to preferred account type in order
TAX_LOCATION_PRIORITY: dict[str, list[str]] = {
    "bonds":         ["tax_deferred", "taxable", "tax_free"],   # bonds → 401k first
    "intl_equity":   ["taxable", "tax_free", "tax_deferred"],   # foreign tax credit benefit
    "us_equity":     ["tax_free", "taxable", "tax_deferred"],   # growth → Roth IRA
    "brazil_equity": ["taxable", "tax_free", "tax_deferred"],   # brazil-specific account
    "crypto":        ["tax_free", "taxable", "tax_deferred"],   # max growth → Roth
    "reit":          ["tax_deferred", "tax_free", "taxable"],   # REIT income → sheltered
    "cash":          ["bank", "taxable"],
}


def get_optimal_account_for_asset(
    asset_class: str,
    available_accounts: list[dict],
    account_capacities: dict[str, float],
) -> str | None:
    """
    Return the optimal account_id for a new investment given asset class.

    Follows TAX_LOCATION_PRIORITY. Respects account capacities (contribution limits).

    Args:
        asset_class: Asset class string.
        available_accounts: List of account dicts with id, tax_treatment, type.
        account_capacities: Dict of account_id -> remaining contribution room.

    Returns:
        Optimal account_id, or None if no suitable account found.
    """
    raise NotImplementedError("Phase 7")


def compute_tax_drag(
    holdings: list[dict],
    asset_expense_ratios: dict[str, float],
) -> dict:
    """
    Compute annual fee drag across portfolio (Bogle principle).

    Aggregate weighted average expense ratio.
    Compare against cost-optimized VTI/VXUS/BND equivalent.

    Args:
        holdings: All holdings with symbol, market_value, account.
        asset_expense_ratios: Dict of symbol -> annual expense ratio.

    Returns:
        Dict with weighted_avg_expense_ratio, annual_fee_usd, benchmark_fee_usd,
        excess_drag_bps (basis points above all-index equivalent).
    """
    raise NotImplementedError("Phase 7")
