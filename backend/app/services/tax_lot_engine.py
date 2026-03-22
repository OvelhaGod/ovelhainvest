"""
Tax lot tracking engine: FIFO, HIFO, Spec ID lot selection.

Handles US capital gains optimization and Brazil DARF tracking.
Wash sale detection (30-day window).

Phase 8 implementation — stub only.
"""

from __future__ import annotations

import logging
from datetime import date
from enum import Enum

logger = logging.getLogger(__name__)

BRAZIL_MONTHLY_EXEMPTION_BRL = 20_000.0  # R$20k/month stock sale exemption


class LotMethod(Enum):
    FIFO = "fifo"       # First in, first out (IRS default)
    HIFO = "hifo"       # Highest cost first (minimizes gains) ← preferred for taxable
    SPEC_ID = "spec_id" # Specific lot identification


def select_lots_to_sell(
    lots: list[dict],
    quantity_to_sell: float,
    method: LotMethod = LotMethod.HIFO,
    account_tax_treatment: str = "taxable",
) -> list[dict]:
    """
    Select which tax lots to use when selling a given quantity.

    For taxable accounts: default to HIFO to minimize realized gains.
    For tax-advantaged (401k, Roth): tax method irrelevant, use FIFO.
    Flags wash sales (buy same security within 30 days of sale at a loss).

    Args:
        lots: List of open tax lot dicts (from tax_lots table).
        quantity_to_sell: Units to sell.
        method: Lot selection method.
        account_tax_treatment: "taxable", "tax_deferred", "tax_free", etc.

    Returns:
        List of selected lot dicts with quantity_used, realized_gain_loss, wash_sale_risk.
    """
    raise NotImplementedError("Phase 8")


def estimate_tax_impact(
    lot: dict,
    current_price: float,
    marginal_rate_lt: float = 0.15,
    marginal_rate_st: float = 0.32,
) -> dict:
    """
    Estimate tax liability for selling a given lot at the current price.

    Args:
        lot: Tax lot dict with acquisition_date, cost_basis_per_unit, quantity.
        current_price: Current market price per unit.
        marginal_rate_lt: Long-term capital gains rate (>1 year holding).
        marginal_rate_st: Short-term rate (ordinary income, <1 year).

    Returns:
        Dict with: unrealized_gain, holding_period ("long"/"short"),
        estimated_tax, after_tax_proceeds, effective_rate.
    """
    raise NotImplementedError("Phase 8")


def find_loss_harvesting_candidates(
    lots: list[dict],
    current_prices: dict[str, float],
    wash_sale_lookback_days: int = 30,
) -> list[dict]:
    """
    Identify lots with unrealized losses > 10% that are eligible for harvesting.

    Filters out lots at wash sale risk (bought within 30 days).

    Args:
        lots: All open tax lots.
        current_prices: Dict of symbol -> current price.
        wash_sale_lookback_days: Window for wash sale check (default 30).

    Returns:
        List of candidate lots with unrealized_loss_pct and suggested_replacement_asset.
    """
    raise NotImplementedError("Phase 8")


def compute_brazil_darf(
    monthly_sales_brl: float,
    realized_gain_brl: float,
    year: int,
    month: int,
    user_id: str,
) -> dict:
    """
    Compute Brazil DARF (Documento de Arrecadação de Receitas Federais) obligation.

    Rules:
    - Sales of stocks below R$20,000/month are EXEMPT from IRPF.
    - Sales above R$20,000 → gains taxed at 15% (variable-income assets).
    - Day trades taxed at 20% regardless of monthly volume.

    Args:
        monthly_sales_brl: Total gross sales in BRL for the month.
        realized_gain_brl: Realized gains in BRL for the month.
        year: Calendar year.
        month: Calendar month (1-12).
        user_id: User UUID.

    Returns:
        Dict with darf_due_brl, exemption_used, effective_rate, warning_if_near_limit.
    """
    raise NotImplementedError("Phase 8")
