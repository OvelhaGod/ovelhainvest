"""
Performance analytics engine.

Implements TWR, MWR/IRR, Sharpe, Sortino, Calmar, max drawdown, beta,
information ratio, and Brinson-Hood-Beebower attribution.

All heavy computation uses pandas + numpy. scipy used for MWR (brentq solver).
Results are cached in Redis and persisted to performance_attribution / risk_metrics.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

import numpy as np
import pandas as pd
from scipy.optimize import brentq

logger = logging.getLogger(__name__)

RISK_FREE_RATE = 0.045  # Update quarterly to current 10yr Treasury yield
TRADING_DAYS_PER_YEAR = 252


def compute_twr(daily_values: pd.Series, cash_flows: pd.DataFrame) -> float:
    """
    Time-Weighted Return using Modified Dietz / sub-period linking.

    For each sub-period between cash flows:
        r = (V_end - V_start - CF) / (V_start + weighted_CF)
    where weighted_CF = CF * (days_remaining / days_in_period)
    TWR = product of (1 + r_i) for all sub-periods - 1
    Annualized if period > 1 year.

    Args:
        daily_values: Series indexed by date with portfolio total value.
        cash_flows: DataFrame with columns [date, amount] — positive=contribution.

    Returns:
        TWR as a decimal (e.g. 0.12 = 12%). Annualized if > 1 year.
    """
    if daily_values.empty or len(daily_values) < 2:
        return 0.0

    daily_values = daily_values.sort_index()

    # Build breakpoints: start + each cash flow date + end
    start_date = daily_values.index[0]
    end_date = daily_values.index[-1]

    if cash_flows is None or cash_flows.empty:
        # Single sub-period
        v_start = daily_values.iloc[0]
        v_end = daily_values.iloc[-1]
        if v_start <= 0:
            return 0.0
        twr = (v_end / v_start) - 1.0
    else:
        # Sort cash flows and build sub-period breakpoints
        cf = cash_flows.copy()
        cf["date"] = pd.to_datetime(cf["date"])
        cf = cf.sort_values("date")

        # All unique dates with cash flows
        cf_dates = cf["date"].tolist()
        breakpoints = sorted(set([start_date] + cf_dates + [end_date]))

        sub_period_returns = []
        for i in range(len(breakpoints) - 1):
            p_start = breakpoints[i]
            p_end = breakpoints[i + 1]
            if p_start == p_end:
                continue

            # Get values at start and end of sub-period
            period_values = daily_values[
                (daily_values.index >= p_start) & (daily_values.index <= p_end)
            ]
            if len(period_values) < 2:
                continue

            v_start = period_values.iloc[0]
            v_end = period_values.iloc[-1]
            if v_start <= 0:
                continue

            # Cash flows within this sub-period (excluding the start date)
            period_cfs = cf[
                (cf["date"] > p_start) & (cf["date"] <= p_end)
            ]

            days_in_period = max((p_end - p_start).days, 1)
            weighted_cf = 0.0
            total_cf = 0.0
            for _, row in period_cfs.iterrows():
                cf_date = row["date"]
                days_remaining = max((p_end - cf_date).days, 0)
                weight = days_remaining / days_in_period
                weighted_cf += row["amount"] * weight
                total_cf += row["amount"]

            denominator = v_start + weighted_cf
            if denominator <= 0:
                continue

            r_i = (v_end - v_start - total_cf) / denominator
            sub_period_returns.append(1.0 + r_i)

        if not sub_period_returns:
            return 0.0

        twr = 1.0
        for r in sub_period_returns:
            twr *= r
        twr -= 1.0

    # Annualize if period > 1 year
    total_days = (end_date - start_date).days
    if total_days > 365:
        twr = (1.0 + twr) ** (365.0 / total_days) - 1.0

    return float(twr)


def compute_mwr(
    cash_flows: list[tuple[date, float]],
    current_value: float,
) -> float:
    """
    Money-Weighted Return (IRR) — reflects the actual return given timing of contributions.

    Solves NPV = 0 using scipy.optimize.brentq.
    Positive cash flows = contributions (money in), negative = withdrawals.

    Args:
        cash_flows: List of (date, amount) tuples. Contributions positive.
        current_value: Current portfolio value (treated as final cash inflow).

    Returns:
        Annualized MWR as a decimal.
    """
    if not cash_flows:
        return 0.0

    sorted_cfs = sorted(cash_flows, key=lambda x: x[0])
    first_date = sorted_cfs[0][0]
    last_date = sorted_cfs[-1][0]

    # Build (t_years, amount) pairs — outflows are negative (money out to buy)
    # Convention: contributions are negative (you pay them out), final value is positive
    dated_cfs: list[tuple[float, float]] = []
    for dt, amount in sorted_cfs:
        t_years = (dt - first_date).days / 365.25
        dated_cfs.append((t_years, -amount))  # contribution = cash outflow

    # Add current value as final inflow
    t_final = (last_date - first_date).days / 365.25
    if t_final == 0:
        t_final = 1.0
    dated_cfs.append((t_final, current_value))

    def npv(rate: float) -> float:
        return sum(cf / (1.0 + rate) ** t for t, cf in dated_cfs)

    try:
        mwr = brentq(npv, -0.999, 100.0, xtol=1e-6, maxiter=1000)
        return float(mwr)
    except (ValueError, RuntimeError):
        logger.warning("MWR brentq solver failed to converge")
        return 0.0


def compute_sharpe(returns: pd.Series, rf: float = RISK_FREE_RATE) -> float:
    """
    Sharpe Ratio: (annualized_return - rf) / annualized_std.

    Args:
        returns: Daily return series.
        rf: Annualized risk-free rate.

    Returns:
        Sharpe ratio (annualized).
    """
    if returns.empty or len(returns) < 2:
        return 0.0

    daily_rf = rf / TRADING_DAYS_PER_YEAR
    excess_returns = returns - daily_rf
    mean_excess = excess_returns.mean()
    std = returns.std(ddof=1)

    if std == 0:
        return 0.0

    return float((mean_excess * TRADING_DAYS_PER_YEAR) / (std * np.sqrt(TRADING_DAYS_PER_YEAR)))


def compute_sortino(returns: pd.Series, rf: float = RISK_FREE_RATE) -> float:
    """
    Sortino Ratio: (annualized_return - rf) / annualized_downside_std.

    Superior to Sharpe for long-only investors — does not penalise upside volatility.
    Downside std computed using only negative daily returns.

    Args:
        returns: Daily return series.
        rf: Annualized risk-free rate.

    Returns:
        Sortino ratio (annualized).
    """
    if returns.empty or len(returns) < 2:
        return 0.0

    daily_rf = rf / TRADING_DAYS_PER_YEAR
    excess_return_annualized = (returns.mean() - daily_rf) * TRADING_DAYS_PER_YEAR

    downside_returns = returns[returns < daily_rf] - daily_rf
    if downside_returns.empty:
        return float("inf") if excess_return_annualized > 0 else 0.0

    downside_std = np.sqrt((downside_returns ** 2).mean()) * np.sqrt(TRADING_DAYS_PER_YEAR)
    if downside_std == 0:
        return 0.0

    return float(excess_return_annualized / downside_std)


def compute_calmar(returns: pd.Series) -> float:
    """
    Calmar Ratio: annualized_return / |max_drawdown|.

    Best for evaluating drawdown resilience.

    Args:
        returns: Daily return series.

    Returns:
        Calmar ratio.
    """
    if returns.empty or len(returns) < 2:
        return 0.0

    annualized_return = returns.mean() * TRADING_DAYS_PER_YEAR
    values = (1 + returns).cumprod()
    max_dd, _, _ = compute_max_drawdown(values)

    if max_dd == 0:
        return float("inf") if annualized_return > 0 else 0.0

    return float(annualized_return / abs(max_dd))


def compute_max_drawdown(values: pd.Series) -> tuple[float, date, date]:
    """
    Maximum peak-to-trough drawdown.

    Args:
        values: Portfolio value series indexed by date.

    Returns:
        Tuple of (max_drawdown_pct, peak_date, trough_date).
        max_drawdown_pct is negative (e.g. -0.25 = 25% drawdown).
    """
    if values.empty or len(values) < 2:
        return 0.0, values.index[0] if not values.empty else date.today(), date.today()

    values = values.sort_index()
    rolling_max = values.cummax()
    drawdown = (values - rolling_max) / rolling_max

    max_dd = float(drawdown.min())
    trough_idx = drawdown.idxmin()

    # Peak is the last rolling max before trough
    peak_values = values[:trough_idx]
    peak_idx = peak_values.idxmax() if not peak_values.empty else values.index[0]

    # Convert to date
    peak_date = peak_idx.date() if hasattr(peak_idx, "date") else peak_idx
    trough_date = trough_idx.date() if hasattr(trough_idx, "date") else trough_idx

    return max_dd, peak_date, trough_date


def compute_beta(
    portfolio_returns: pd.Series,
    benchmark_returns: pd.Series,
) -> float:
    """
    Beta = Cov(portfolio, benchmark) / Var(benchmark).

    Args:
        portfolio_returns: Daily portfolio returns.
        benchmark_returns: Daily benchmark returns.

    Returns:
        Beta coefficient.
    """
    if portfolio_returns.empty or benchmark_returns.empty:
        return 1.0

    # Align on common dates
    aligned = pd.DataFrame({"portfolio": portfolio_returns, "benchmark": benchmark_returns}).dropna()
    if len(aligned) < 2:
        return 1.0

    var_bench = aligned["benchmark"].var(ddof=1)
    if var_bench == 0:
        return 1.0

    cov = aligned["portfolio"].cov(aligned["benchmark"])
    return float(cov / var_bench)


def compute_information_ratio(active_returns: pd.Series) -> float:
    """
    Information Ratio: mean(active_returns) / std(active_returns).

    Measures consistency of alpha generation.

    Args:
        active_returns: Series of (portfolio_return - benchmark_return) per period.

    Returns:
        Information ratio (annualized).
    """
    if active_returns.empty or len(active_returns) < 2:
        return 0.0

    mean_active = active_returns.mean()
    std_active = active_returns.std(ddof=1)

    if std_active == 0:
        return float("inf") if mean_active > 0 else 0.0

    return float((mean_active / std_active) * np.sqrt(TRADING_DAYS_PER_YEAR))


def compute_attribution(
    portfolio_weights: dict[str, float],
    portfolio_returns: dict[str, float],
    benchmark_weights: dict[str, float],
    benchmark_returns: dict[str, float],
) -> dict[str, Any]:
    """
    Brinson-Hood-Beebower attribution decomposition.

    For each sleeve:
      - Allocation effect: (w_p - w_b) * (r_b - r_total_b)
      - Selection effect:  w_b * (r_p - r_b)
      - Interaction effect: (w_p - w_b) * (r_p - r_b)

    Total active return = sum of all effects.

    Args:
        portfolio_weights: Dict of sleeve -> portfolio weight.
        portfolio_returns: Dict of sleeve -> portfolio return for period.
        benchmark_weights: Dict of sleeve -> benchmark weight.
        benchmark_returns: Dict of sleeve -> benchmark return for period.

    Returns:
        Dict with per-sleeve effects and totals.
    """
    all_sleeves = set(portfolio_weights) | set(benchmark_weights)

    # Total benchmark return
    r_total_b = sum(
        benchmark_weights.get(s, 0.0) * benchmark_returns.get(s, 0.0)
        for s in all_sleeves
    )

    per_sleeve: dict[str, dict[str, float]] = {}
    total_allocation = 0.0
    total_selection = 0.0
    total_interaction = 0.0

    for sleeve in sorted(all_sleeves):
        w_p = portfolio_weights.get(sleeve, 0.0)
        w_b = benchmark_weights.get(sleeve, 0.0)
        r_p = portfolio_returns.get(sleeve, 0.0)
        r_b = benchmark_returns.get(sleeve, 0.0)

        allocation_effect = (w_p - w_b) * (r_b - r_total_b)
        selection_effect = w_b * (r_p - r_b)
        interaction_effect = (w_p - w_b) * (r_p - r_b)
        total_effect = allocation_effect + selection_effect + interaction_effect

        per_sleeve[sleeve] = {
            "portfolio_weight": round(w_p, 4),
            "benchmark_weight": round(w_b, 4),
            "portfolio_return": round(r_p, 4),
            "benchmark_return": round(r_b, 4),
            "allocation_effect": round(allocation_effect, 4),
            "selection_effect": round(selection_effect, 4),
            "interaction_effect": round(interaction_effect, 4),
            "total_effect": round(total_effect, 4),
        }

        total_allocation += allocation_effect
        total_selection += selection_effect
        total_interaction += interaction_effect

    # Portfolio total return
    r_total_p = sum(
        portfolio_weights.get(s, 0.0) * portfolio_returns.get(s, 0.0)
        for s in all_sleeves
    )
    active_return = r_total_p - r_total_b

    return {
        "per_sleeve": per_sleeve,
        "total_allocation_effect": round(total_allocation, 4),
        "total_selection_effect": round(total_selection, 4),
        "total_interaction_effect": round(total_interaction, 4),
        "total_active_return": round(active_return, 4),
        "portfolio_return": round(r_total_p, 4),
        "benchmark_return": round(r_total_b, 4),
    }


def compute_rolling_returns(
    values: pd.Series,
    windows: list[int] = [21, 63, 252],
) -> pd.DataFrame:
    """
    Rolling returns for given windows (in trading days).

    Args:
        values: Portfolio value series indexed by date.
        windows: List of window sizes (21=1mo, 63=3mo, 252=1yr).

    Returns:
        DataFrame with one column per window.
    """
    if values.empty:
        return pd.DataFrame()

    values = values.sort_index()
    result = pd.DataFrame(index=values.index)

    window_names = {21: "1mo", 63: "3mo", 126: "6mo", 252: "1yr"}
    for w in windows:
        col_name = window_names.get(w, f"{w}d")
        shifted = values.shift(w)
        result[col_name] = (values / shifted) - 1.0

    return result


def compute_period_returns(values: pd.Series) -> dict[str, float | None]:
    """
    Compute standard period returns: 1mo, 3mo, 6mo, YTD, 1yr, 3yr, all-time.

    Args:
        values: Portfolio value series indexed by date.

    Returns:
        Dict of period label -> return as decimal.
    """
    if values.empty or len(values) < 2:
        return {}

    values = values.sort_index()
    today = values.index[-1]
    current_val = values.iloc[-1]

    def _ret(lookback_days: int | None = None, start_of_year: bool = False) -> float | None:
        if start_of_year:
            ytd_start = pd.Timestamp(today.year, 1, 1)
            past = values[values.index <= ytd_start]
        elif lookback_days is not None:
            cutoff = today - pd.Timedelta(days=lookback_days)
            past = values[values.index <= cutoff]
        else:
            past = values.iloc[[0]]

        if past.empty:
            return None
        past_val = past.iloc[-1]
        if past_val <= 0:
            return None
        return float((current_val / past_val) - 1.0)

    return {
        "1mo": _ret(30),
        "3mo": _ret(91),
        "6mo": _ret(182),
        "ytd": _ret(start_of_year=True),
        "1yr": _ret(365),
        "3yr": _ret(1095),
        "all_time": _ret(),
    }


def compute_volatility(returns: pd.Series) -> float:
    """
    Annualized volatility (standard deviation of daily returns * sqrt(252)).

    Args:
        returns: Daily return series.

    Returns:
        Annualized volatility as decimal.
    """
    if returns.empty or len(returns) < 2:
        return 0.0
    return float(returns.std(ddof=1) * np.sqrt(TRADING_DAYS_PER_YEAR))
