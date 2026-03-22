"""
Simulation engine: Monte Carlo projections, stress testing, contribution optimizer.

Uses numpy for vectorized simulations (N=5000 default).
Monte Carlo fan chart output consumed by /projections page.
Heavy runs are dispatched as FastAPI BackgroundTasks — never block the API response.

Phase 7 implementation — stub only.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ── Return assumptions per sleeve (historical, conservative) ─────────────────

RETURN_ASSUMPTIONS: dict[str, dict[str, float]] = {
    "us_equity":     {"mean": 0.095, "std": 0.165},
    "intl_equity":   {"mean": 0.075, "std": 0.175},
    "bonds":         {"mean": 0.035, "std": 0.065},
    "brazil_equity": {"mean": 0.090, "std": 0.280},
    "crypto":        {"mean": 0.150, "std": 0.700},
    "cash":          {"mean": 0.045, "std": 0.010},
}

# ── Stress scenarios ──────────────────────────────────────────────────────────

STRESS_SCENARIOS: dict[str, dict] = {
    "2008_gfc": {
        "name": "2008 Global Financial Crisis",
        "us_equity": -0.51, "intl_equity": -0.46, "bonds": +0.12,
        "brazil_equity": -0.58, "crypto": None, "cash": 0.0,
    },
    "2020_covid": {
        "name": "2020 COVID Crash (Feb–Mar)",
        "us_equity": -0.34, "intl_equity": -0.33, "bonds": +0.04,
        "brazil_equity": -0.46, "crypto": -0.40, "cash": 0.0,
    },
    "2022_rate_shock": {
        "name": "2022 Rate Shock",
        "us_equity": -0.19, "intl_equity": -0.16, "bonds": -0.15,
        "brazil_equity": +0.08, "crypto": -0.65, "cash": +0.02,
    },
    "stagflation_1970s": {
        "name": "1970s Stagflation Analog",
        "us_equity": -0.45, "intl_equity": -0.40, "bonds": -0.25,
        "brazil_equity": -0.30, "crypto": -0.50, "cash": +0.06,
    },
    "brazil_crisis": {
        "name": "Brazil Currency/Political Crisis",
        "us_equity": -0.05, "intl_equity": -0.08, "bonds": 0.0,
        "brazil_equity": -0.50, "crypto": -0.20, "cash": 0.0,
    },
}


@dataclass
class MonteCarloResult:
    """Percentile bands and probability estimates from a Monte Carlo run."""

    years: int
    n_simulations: int
    percentiles: dict[int, list[float]]  # {5: [...], 25: [...], 50: [...], 75: [...], 95: [...]}
    prob_reach_target: float | None
    prob_survive_30yr_swr: float | None   # 4% safe withdrawal rate
    median_ending_value: float


def run_monte_carlo(
    current_value: float,
    monthly_contribution: float,
    years: int,
    sleeve_weights: dict[str, float],
    n_simulations: int = 5000,
    return_assumptions: dict[str, dict[str, float]] | None = None,
    target_value: float | None = None,
) -> MonteCarloResult:
    """
    Run N Monte Carlo simulations projecting portfolio value over `years`.

    Method: parametric — each sleeve sampled independently using annual mean/std,
    then combined by weight. Monthly compounding with regular contributions.

    Args:
        current_value: Starting portfolio value (USD).
        monthly_contribution: Monthly cash contribution (USD).
        years: Projection horizon.
        sleeve_weights: Dict of sleeve -> weight (must sum to 1).
        n_simulations: Number of simulation paths (default 5000).
        return_assumptions: Per-sleeve mean + std overrides. Defaults to RETURN_ASSUMPTIONS.
        target_value: Optional USD target for probability calculation.

    Returns:
        MonteCarloResult with percentile bands and probability estimates.
    """
    raise NotImplementedError("Phase 7")


def run_stress_test(
    current_value: float,
    sleeve_weights: dict[str, float],
    scenario_key: str,
) -> dict:
    """
    Apply a historical stress scenario to the current portfolio.

    Args:
        current_value: Current portfolio value (USD).
        sleeve_weights: Current sleeve allocation.
        scenario_key: Key from STRESS_SCENARIOS.

    Returns:
        Dict with portfolio_value_after, dollar_loss, pct_loss, scenario_name,
        and per-sleeve impact.
    """
    raise NotImplementedError("Phase 7")


def run_contribution_optimizer(
    additional_amount_usd: float,
    current_sleeve_weights: dict[str, float],
    current_portfolio_value: float,
    accounts: list[dict],
    strategy_config: dict,
) -> dict:
    """
    Given $X to invest, determine optimal account + asset routing.

    Optimizes for:
    1. Minimizing sleeve drift (primary)
    2. Tax-location efficiency (secondary — Swensen logic)
    3. Opportunity vault rules compliance

    Args:
        additional_amount_usd: New money to invest.
        current_sleeve_weights: Current vs target drift.
        current_portfolio_value: Total portfolio value before new money.
        accounts: List of available account dicts.
        strategy_config: Active strategy config from DB.

    Returns:
        Dict with recommended_trades list and before/after allocation comparison.
    """
    raise NotImplementedError("Phase 7")


def run_rebalance_preview(
    current_holdings: dict,
    target_weights: dict[str, float],
    portfolio_value: float,
    strategy_config: dict,
) -> dict:
    """
    Show portfolio before/after a proposed rebalance without executing.

    Args:
        current_holdings: Current holdings by sleeve.
        target_weights: Target sleeve weights.
        portfolio_value: Total portfolio value.
        strategy_config: Active strategy config.

    Returns:
        Dict with before/after weights, proposed trades, estimated tax impact.
    """
    raise NotImplementedError("Phase 7")
