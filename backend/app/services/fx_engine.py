"""
FX engine: USD/BRL normalization and FX attribution.

All portfolio-level math normalized to USD.
BRL positions converted using live rate from yfinance (symbol: "USDBRL=X").
Alerts when USD/BRL moves > FX_ALERT_THRESHOLD in 30 days.

Phase 10 implementation — stub only.
"""

from __future__ import annotations

import logging

import pandas as pd

logger = logging.getLogger(__name__)

FX_ALERT_THRESHOLD = 0.10   # alert when USD/BRL moves >10% in 30 days
FX_SYMBOL = "USDBRL=X"      # yfinance ticker for USD/BRL rate


def normalize_to_usd(brl_value: float, usd_brl_rate: float) -> float:
    """
    Convert BRL value to USD for portfolio-level aggregation.

    Args:
        brl_value: Value in Brazilian Reals.
        usd_brl_rate: Current USD/BRL exchange rate (units of BRL per 1 USD).

    Returns:
        Value in USD.
    """
    raise NotImplementedError("Phase 10")


def normalize_to_brl(usd_value: float, usd_brl_rate: float) -> float:
    """
    Convert USD value to BRL for display to Brazilian-context users.

    Args:
        usd_value: Value in USD.
        usd_brl_rate: Current USD/BRL exchange rate.

    Returns:
        Value in BRL.
    """
    raise NotImplementedError("Phase 10")


def compute_fx_attribution(
    brazil_sleeve_return_brl: float,
    brazil_sleeve_return_usd: float,
) -> float:
    """
    FX contribution to portfolio return.

    FX contribution = brazil_sleeve_return_usd - brazil_sleeve_return_brl
    Positive = BRL strengthened vs USD (helped USD returns).
    Negative = BRL weakened (hurt USD returns).

    Args:
        brazil_sleeve_return_brl: Brazil sleeve return measured in BRL.
        brazil_sleeve_return_usd: Brazil sleeve return measured in USD.

    Returns:
        FX contribution as decimal.
    """
    raise NotImplementedError("Phase 10")


def get_live_usd_brl_rate() -> float:
    """
    Fetch current USD/BRL rate from yfinance.

    Returns:
        Exchange rate (BRL per 1 USD), e.g. 5.30.
    """
    raise NotImplementedError("Phase 2")


def check_fx_alert(
    rate_history: pd.Series,
    window_days: int = 30,
) -> dict | None:
    """
    Check if USD/BRL has moved beyond FX_ALERT_THRESHOLD in the last window_days.

    Args:
        rate_history: Series of daily USD/BRL rates indexed by date.
        window_days: Rolling window to measure move.

    Returns:
        Alert dict if threshold breached, else None.
    """
    raise NotImplementedError("Phase 6")
