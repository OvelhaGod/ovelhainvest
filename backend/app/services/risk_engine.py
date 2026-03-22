"""
Risk engine: risk parity weights, correlation matrix, Value at Risk.

Implements Dalio All-Weather risk contribution logic.
scipy.optimize.minimize used for risk parity weight computation.

Phase 4/10 implementation — stub only.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

CORRELATION_ALERT_THRESHOLD = 0.85  # alert when any pair exceeds this


def compute_risk_parity_weights(
    sleeve_vols: dict[str, float],
    correlation_matrix: np.ndarray,
    sleeve_names: list[str],
) -> dict[str, float]:
    """
    Dalio All-Weather: compute weights such that each sleeve contributes equal risk.

    Uses scipy.optimize.minimize to find weights w such that:
        risk_contribution_i = w_i * (Sigma @ w)_i / portfolio_volatility
    is equal for all i.

    Returns risk-parity weights for COMPARISON only — not for forced rebalancing.
    Shows "what your allocation would look like if you balanced risk, not dollars."

    Args:
        sleeve_vols: Dict of sleeve -> annualized volatility.
        correlation_matrix: NxN correlation matrix (same order as sleeve_names).
        sleeve_names: Ordered list of sleeve names.

    Returns:
        Dict of sleeve -> risk-parity weight.
    """
    raise NotImplementedError("Phase 10")


def compute_correlation_matrix(
    returns_by_sleeve: dict[str, pd.Series],
    window_days: int = 90,
) -> pd.DataFrame:
    """
    Rolling 90-day correlation matrix across sleeves.

    Alerts when any pair correlation exceeds CORRELATION_ALERT_THRESHOLD.

    Args:
        returns_by_sleeve: Dict of sleeve -> daily return series.
        window_days: Rolling window (default 90 trading days).

    Returns:
        Correlation DataFrame (sleeves x sleeves).
    """
    raise NotImplementedError("Phase 4")


def compute_var(
    portfolio_returns: pd.Series,
    confidence: float = 0.95,
) -> float:
    """
    Historical Value at Risk.

    "On `confidence`% of days, daily loss will not exceed the returned value."

    Args:
        portfolio_returns: Daily portfolio returns.
        confidence: Confidence level (0.95 or 0.99).

    Returns:
        VaR as a positive decimal (e.g. 0.02 = 2% daily loss threshold).
    """
    raise NotImplementedError("Phase 4")


def compute_effective_diversification_ratio(
    sleeve_vols: dict[str, float],
    sleeve_weights: dict[str, float],
    correlation_matrix: np.ndarray,
) -> float:
    """
    Diversification Ratio: weighted-average volatility / portfolio volatility.

    DR > 1 means portfolio is diversified (correlation < 1).
    DR = 1 means all assets perfectly correlated (no diversification benefit).

    Args:
        sleeve_vols: Dict of sleeve -> annualized volatility.
        sleeve_weights: Dict of sleeve -> portfolio weight.
        correlation_matrix: NxN correlation matrix.

    Returns:
        Diversification ratio (float >= 1).
    """
    raise NotImplementedError("Phase 4")
