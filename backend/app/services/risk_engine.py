"""
Risk engine: risk parity weights, correlation matrix, Value at Risk.

Implements Dalio All-Weather risk contribution logic.
scipy.optimize.minimize used for risk parity weight computation.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd
from scipy.optimize import minimize

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
    n = len(sleeve_names)
    if n == 0:
        return {}
    if n == 1:
        return {sleeve_names[0]: 1.0}

    vols = np.array([sleeve_vols.get(s, 0.01) for s in sleeve_names])
    # Build covariance matrix from correlation + vols
    cov_matrix = np.outer(vols, vols) * correlation_matrix

    def portfolio_vol(w: np.ndarray) -> float:
        return float(np.sqrt(w @ cov_matrix @ w))

    def risk_contribution(w: np.ndarray) -> np.ndarray:
        pv = portfolio_vol(w)
        if pv == 0:
            return np.zeros(n)
        marginal_contrib = cov_matrix @ w
        return w * marginal_contrib / pv

    def objective(w: np.ndarray) -> float:
        """Sum of squared differences from equal risk contribution."""
        rc = risk_contribution(w)
        target = np.sum(rc) / n
        return float(np.sum((rc - target) ** 2))

    # Initial guess: equal weights
    w0 = np.ones(n) / n
    constraints = {"type": "eq", "fun": lambda w: np.sum(w) - 1.0}
    bounds = [(0.01, 0.99) for _ in range(n)]

    result = minimize(
        objective,
        w0,
        method="SLSQP",
        bounds=bounds,
        constraints=constraints,
        options={"maxiter": 1000, "ftol": 1e-9},
    )

    if not result.success:
        logger.warning("Risk parity optimizer did not fully converge: %s", result.message)

    weights = np.abs(result.x)
    weights = weights / weights.sum()  # normalize to sum to 1

    return {sleeve_names[i]: round(float(weights[i]), 4) for i in range(n)}


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
    if not returns_by_sleeve:
        return pd.DataFrame()

    df = pd.DataFrame(returns_by_sleeve).dropna(how="all")

    # Use last `window_days` rows
    if len(df) > window_days:
        df = df.tail(window_days)

    corr = df.corr()

    # Log high-correlation pairs
    for i in range(len(corr.columns)):
        for j in range(i + 1, len(corr.columns)):
            val = corr.iloc[i, j]
            if abs(val) >= CORRELATION_ALERT_THRESHOLD:
                logger.warning(
                    "High correlation detected: %s vs %s = %.3f",
                    corr.columns[i],
                    corr.columns[j],
                    val,
                )

    return corr


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
    if portfolio_returns.empty:
        return 0.0

    percentile = (1.0 - confidence) * 100.0
    var = float(np.percentile(portfolio_returns.dropna(), percentile))
    return abs(var)


def compute_cvar(
    portfolio_returns: pd.Series,
    confidence: float = 0.95,
) -> float:
    """
    Conditional Value at Risk (Expected Shortfall).

    Average loss in the worst (1 - confidence)% of days.

    Args:
        portfolio_returns: Daily portfolio returns.
        confidence: Confidence level.

    Returns:
        CVaR as a positive decimal.
    """
    if portfolio_returns.empty:
        return 0.0

    var = compute_var(portfolio_returns, confidence)
    tail = portfolio_returns[portfolio_returns <= -var]
    if tail.empty:
        return var
    return float(abs(tail.mean()))


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
    sleeves = sorted(sleeve_vols.keys())
    n = len(sleeves)
    if n == 0:
        return 1.0

    w = np.array([sleeve_weights.get(s, 0.0) for s in sleeves])
    vols = np.array([sleeve_vols.get(s, 0.0) for s in sleeves])

    # Weighted average of individual vols
    weighted_avg_vol = float(w @ vols)

    # Portfolio volatility via covariance matrix
    cov = np.outer(vols, vols) * correlation_matrix
    port_var = float(w @ cov @ w)
    port_vol = np.sqrt(port_var) if port_var > 0 else 0.0

    if port_vol == 0:
        return 1.0

    return float(weighted_avg_vol / port_vol)
