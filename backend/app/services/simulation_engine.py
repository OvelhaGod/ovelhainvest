"""
Simulation engine: Monte Carlo projections, stress testing, contribution optimizer.

Phase 7 — full implementation.

Design:
- Monte Carlo: fully vectorized numpy (N simulations x M months matrix)
- Bootstrap: sample monthly returns from historical portfolio_snapshots (>=24 months)
  Fallback to parametric if insufficient history.
- SWR analysis: decumulation simulation from median ending value
- All heavy paths run as FastAPI BackgroundTasks — never block API
"""

from __future__ import annotations

import logging
import math
import uuid
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

# ── Return assumptions (historical, conservative) — CLAUDE.md Section 10 ─────

RETURN_ASSUMPTIONS: dict[str, dict[str, float]] = {
    "us_equity":     {"mean": 0.095, "std": 0.165},
    "intl_equity":   {"mean": 0.075, "std": 0.175},
    "bonds":         {"mean": 0.035, "std": 0.065},
    "brazil_equity": {"mean": 0.090, "std": 0.280},
    "crypto":        {"mean": 0.150, "std": 0.700},
    "cash":          {"mean": 0.045, "std": 0.010},
}

# ── Stress scenarios (CLAUDE.md Section 10) ───────────────────────────────────

STRESS_SCENARIOS: dict[str, dict] = {
    "2008_gfc": {
        "name": "2008 Global Financial Crisis",
        "us_equity": -0.51, "intl_equity": -0.46, "bonds": +0.12,
        "brazil_equity": -0.58, "crypto": None, "cash": 0.0,
    },
    "2020_covid": {
        "name": "2020 COVID Crash (Feb-Mar)",
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

# Dalio All-Weather risk-parity weights (for stress test comparison)
_RISK_PARITY_WEIGHTS = {
    "us_equity":     0.30,
    "intl_equity":   0.00,
    "bonds":         0.55,
    "brazil_equity": 0.00,
    "crypto":        0.00,
    "cash":          0.15,
}


# ── Dataclasses ───────────────────────────────────────────────────────────────

@dataclass
class MonteCarloResult:
    years: int
    n_simulations: int
    # percentile label -> list of values by year (year 0..years)
    percentile_bands: dict[str, list[float]]
    summary: dict
    metadata: dict


@dataclass
class StressTestResult:
    scenario_key: str
    scenario_name: str
    portfolio_before: float
    portfolio_after: float
    total_loss_usd: float
    total_loss_pct: float
    sleeve_impacts: dict[str, dict]
    estimated_recovery_months: int
    risk_parity_comparison: dict


@dataclass
class ContributionOptimization:
    total_available: float
    proposals: list[dict]
    residual: float
    projected_weights_after: dict
    current_weights_before: dict


@dataclass
class RetirementReadiness:
    years_to_retirement: int
    required_nest_egg: float
    projected_median: float
    gap: float
    on_track: bool
    probability_of_success: float
    required_additional_monthly: float
    swr_survival_probability: float
    current_savings_rate: float | None


# ── Internal helpers ──────────────────────────────────────────────────────────

def _annual_to_monthly(annual_mean: float, annual_std: float) -> tuple[float, float]:
    """Convert annualized mean/std to monthly equivalents."""
    monthly_mean = (1 + annual_mean) ** (1 / 12) - 1
    monthly_std = annual_std / math.sqrt(12)
    return monthly_mean, monthly_std


def _fetch_historical_monthly_returns(months: int = 60) -> dict[str, list[float]] | None:
    """
    Fetch historical monthly portfolio returns from portfolio_snapshots.
    Returns per-portfolio monthly returns if >=24 months available, else None.
    """
    try:
        from app.db.supabase_client import get_supabase_client
        client = get_supabase_client()
        resp = (
            client.table("portfolio_snapshots")
            .select("snapshot_date, portfolio_return_twr")
            .order("snapshot_date", desc=False)
            .limit(months)
            .execute()
        )
        rows = resp.data or []
        returns = [r["portfolio_return_twr"] for r in rows if r.get("portfolio_return_twr") is not None]
        if len(returns) < 24:
            return None
        return {"portfolio": returns}
    except Exception as exc:
        logger.debug("_fetch_historical_monthly_returns failed: %s", exc)
        return None


def _run_swr_survival(
    starting_value: float,
    n_simulations: int,
    sleeve_weights: dict[str, float],
    return_assumptions: dict[str, dict[str, float]],
    withdrawal_years: int = 30,
) -> float:
    """Simulate 4% SWR survival probability from starting_value over withdrawal_years."""
    if starting_value <= 0:
        return 0.0

    monthly_withdrawal = starting_value * 0.04 / 12
    n_months = withdrawal_years * 12

    port_mean, port_std = _compute_weighted_monthly_stats(sleeve_weights, return_assumptions)

    rng = np.random.default_rng(seed=42)
    monthly_returns = rng.normal(port_mean, port_std, size=(n_simulations, n_months))

    portfolios = np.full(n_simulations, starting_value)
    survived = np.ones(n_simulations, dtype=bool)

    for m in range(n_months):
        portfolios = portfolios * (1 + monthly_returns[:, m]) - monthly_withdrawal
        survived &= (portfolios > 0)

    return float(np.mean(survived))


def _compute_weighted_monthly_stats(
    sleeve_weights: dict[str, float],
    return_assumptions: dict[str, dict[str, float]],
) -> tuple[float, float]:
    """Compute weighted portfolio monthly mean and std from sleeve weights."""
    total_w = sum(sleeve_weights.values())
    if total_w <= 0:
        total_w = 1.0

    port_mean = 0.0
    port_var = 0.0
    for sleeve, w in sleeve_weights.items():
        normalized_w = w / total_w
        assumptions = return_assumptions.get(sleeve, RETURN_ASSUMPTIONS.get(sleeve, {"mean": 0.07, "std": 0.15}))
        m_mean, m_std = _annual_to_monthly(assumptions["mean"], assumptions["std"])
        port_mean += normalized_w * m_mean
        port_var += (normalized_w * m_std) ** 2  # assumes sleeve independence

    port_std = math.sqrt(port_var)
    return port_mean, port_std


# ── Item 1: Monte Carlo ───────────────────────────────────────────────────────

def run_monte_carlo(
    current_value: float,
    monthly_contribution: float,
    years: int,
    sleeve_weights: dict[str, float],
    n_simulations: int = 5000,
    return_assumptions: dict[str, dict[str, float]] | None = None,
    use_historical_bootstrap: bool = True,
    target_value: float | None = None,
) -> MonteCarloResult:
    """
    Run N Monte Carlo simulations projecting portfolio value over `years`.

    Method selection:
    - use_historical_bootstrap=True: sample monthly returns from portfolio_snapshots.
      Falls back to parametric if <24 months of history.
    - use_historical_bootstrap=False: parametric using return_assumptions mean/std.

    Vectorized: entire simulation runs as a single numpy loop over months.
    Each month: portfolio = portfolio * (1 + return) + monthly_contribution.

    Returns MonteCarloResult with percentile_bands (by year), summary stats,
    and metadata.
    """
    if return_assumptions is None:
        return_assumptions = RETURN_ASSUMPTIONS.copy()

    n_months = years * 12
    method_used = "parametric"

    # Try bootstrap
    historical_returns: list[float] | None = None
    if use_historical_bootstrap:
        hist = _fetch_historical_monthly_returns(months=120)
        if hist and len(hist.get("portfolio", [])) >= 24:
            historical_returns = hist["portfolio"]
            method_used = "historical_bootstrap"

    rng = np.random.default_rng(seed=None)

    # Build (n_simulations x n_months) return matrix
    if historical_returns is not None:
        hist_arr = np.array(historical_returns, dtype=np.float64)
        idx = rng.integers(0, len(hist_arr), size=(n_simulations, n_months))
        monthly_return_matrix = hist_arr[idx]
    else:
        port_mean, port_std = _compute_weighted_monthly_stats(sleeve_weights, return_assumptions)
        monthly_return_matrix = rng.normal(port_mean, port_std, size=(n_simulations, n_months))

    # Simulate all paths (vectorized across simulations, sequential over months)
    portfolios = np.full(n_simulations, float(current_value))
    # Store yearly snapshots: shape (years+1, n_simulations)
    yearly_values = np.empty((years + 1, n_simulations))
    yearly_values[0] = portfolios

    for m in range(n_months):
        portfolios = portfolios * (1 + monthly_return_matrix[:, m]) + monthly_contribution
        np.maximum(portfolios, 0.0, out=portfolios)  # floor at 0
        if (m + 1) % 12 == 0:
            yr = (m + 1) // 12
            yearly_values[yr] = portfolios

    # Percentile bands by year
    PERCENTILES = [5, 10, 25, 50, 75, 90, 95]
    percentile_bands: dict[str, list[float]] = {str(p): [] for p in PERCENTILES}

    for yr in range(years + 1):
        vals = yearly_values[yr]
        for p in PERCENTILES:
            percentile_bands[str(p)].append(float(np.percentile(vals, p)))

    # Summary stats
    final_values = yearly_values[years]
    median_final = float(np.percentile(final_values, 50))
    p10_final = float(np.percentile(final_values, 10))
    p90_final = float(np.percentile(final_values, 90))

    _target = target_value if target_value is not None else current_value * 2
    prob_reaching_target = float(np.mean(final_values >= _target))
    prob_ruin = float(np.mean(final_values <= 0))

    total_contributed = monthly_contribution * n_months
    median_gain = median_final - current_value - total_contributed

    # SWR survival from median
    swr_survival = _run_swr_survival(
        starting_value=median_final,
        n_simulations=min(1000, n_simulations),
        sleeve_weights=sleeve_weights,
        return_assumptions=return_assumptions,
        withdrawal_years=30,
    )

    summary = {
        "median_final": round(median_final, 2),
        "p10_final": round(p10_final, 2),
        "p90_final": round(p90_final, 2),
        "prob_reaching_target": round(prob_reaching_target, 4),
        "target_value": round(_target, 2),
        "prob_ruin": round(prob_ruin, 4),
        "swr_survival_probability": round(swr_survival, 4),
        "years": years,
        "monthly_contribution": monthly_contribution,
        "total_contributed": round(total_contributed, 2),
        "median_gain": round(median_gain, 2),
        "starting_value": current_value,
    }

    metadata = {
        "n_simulations": n_simulations,
        "method": method_used,
        "return_assumptions_used": {
            k: v for k, v in return_assumptions.items()
            if k in sleeve_weights
        },
    }

    return MonteCarloResult(
        years=years,
        n_simulations=n_simulations,
        percentile_bands=percentile_bands,
        summary=summary,
        metadata=metadata,
    )


# ── Item 2a: Stress Test ──────────────────────────────────────────────────────

def run_stress_test(
    current_portfolio: dict[str, float],
    scenario_name: str,
) -> StressTestResult:
    """
    Apply a historical stress scenario to the current portfolio.

    current_portfolio: {sleeve: value_usd}
    scenario_name: key from STRESS_SCENARIOS
    """
    if scenario_name not in STRESS_SCENARIOS:
        raise ValueError(f"Unknown scenario: {scenario_name}. Valid: {list(STRESS_SCENARIOS)}")

    scenario = STRESS_SCENARIOS[scenario_name]
    total_before = sum(current_portfolio.values())
    if total_before <= 0:
        total_before = 1.0

    # Apply scenario to each sleeve
    sleeve_impacts: dict[str, dict] = {}
    total_after = 0.0

    for sleeve, value in current_portfolio.items():
        shock = scenario.get(sleeve)
        if shock is None:
            shock = 0.0  # N/A in this scenario
        impact_usd = value * shock
        value_after = value + impact_usd
        total_after += value_after
        sleeve_impacts[sleeve] = {
            "value_before": round(value, 2),
            "value_after": round(value_after, 2),
            "shock_pct": round(shock * 100, 1),
            "loss_usd": round(-impact_usd, 2),
        }

    total_loss_usd = total_before - total_after
    total_loss_pct = (total_loss_usd / total_before * 100) if total_before > 0 else 0.0

    # Recovery time at 7% annual: months = log(before/after) / log(1 + 0.07/12)
    if total_after > 0 and total_after < total_before:
        monthly_rate = 0.07 / 12
        try:
            recovery_months = int(math.log(total_before / total_after) / math.log(1 + monthly_rate))
        except (ValueError, ZeroDivisionError):
            recovery_months = 0
    else:
        recovery_months = 0

    # Risk parity comparison
    rp_total_after = 0.0
    for sleeve, rp_w in _RISK_PARITY_WEIGHTS.items():
        rp_value = total_before * rp_w
        shock = scenario.get(sleeve)
        if shock is None:
            shock = 0.0
        rp_total_after += rp_value * (1 + shock)

    rp_loss_pct = ((total_before - rp_total_after) / total_before * 100) if total_before > 0 else 0.0

    risk_parity_comparison = {
        "current_loss_pct": round(total_loss_pct, 2),
        "risk_parity_loss_pct": round(rp_loss_pct, 2),
        "difference_pct": round(rp_loss_pct - total_loss_pct, 2),
        "risk_parity_is_better": rp_loss_pct < total_loss_pct,
    }

    return StressTestResult(
        scenario_key=scenario_name,
        scenario_name=str(scenario["name"]),
        portfolio_before=round(total_before, 2),
        portfolio_after=round(total_after, 2),
        total_loss_usd=round(total_loss_usd, 2),
        total_loss_pct=round(total_loss_pct, 2),
        sleeve_impacts=sleeve_impacts,
        estimated_recovery_months=recovery_months,
        risk_parity_comparison=risk_parity_comparison,
    )


def run_all_stress_tests(current_portfolio: dict[str, float]) -> dict[str, StressTestResult]:
    """Run all 5 scenarios simultaneously."""
    results = {}
    for key in STRESS_SCENARIOS:
        try:
            results[key] = run_stress_test(current_portfolio, key)
        except Exception as exc:
            logger.error("stress_test %s failed: %s", key, exc)
    return results


# ── Item 2b: Contribution Optimizer ──────────────────────────────────────────

def run_contribution_optimizer(
    available_amount: float,
    current_holdings: list[dict],
    current_prices: dict[str, float],
    active_config: dict,
    tax_treatments: dict[str, str],
) -> ContributionOptimization:
    """
    Given $X to invest, find optimal allocation across accounts + assets
    that minimizes sleeve drift AND maximizes tax efficiency.

    Tax-location rules (Swensen / CLAUDE.md Section 7):
    - bonds -> prefer tax_deferred (401k)
    - growth/equity -> prefer tax_free (Roth IRA)
    - crypto -> taxable or crypto account
    - income payers -> avoid taxable
    """
    sleeve_targets = active_config.get("sleeve_targets", {
        k: {"target": 0.1} for k in RETURN_ASSUMPTIONS
    })
    min_trade = float(active_config.get("min_trade_usd", 50.0))

    # Compute current sleeve values
    sleeve_values: dict[str, float] = {}
    total_value = 0.0

    for holding in current_holdings:
        symbol = holding.get("symbol", "")
        price = current_prices.get(symbol, holding.get("last_price", 0.0))
        qty = float(holding.get("quantity", 0))
        value = price * qty
        total_value += value

        sleeve = str(holding.get("asset_class", "cash")).lower()
        sleeve_values[sleeve] = sleeve_values.get(sleeve, 0.0) + value

    if total_value <= 0:
        total_value = available_amount or 1.0

    current_weights = {sleeve: val / total_value for sleeve, val in sleeve_values.items()}

    # Compute drifts (negative = underweight, needs buying)
    drifts: dict[str, float] = {}
    for sleeve, cfg in sleeve_targets.items():
        target = float(cfg.get("target", 0.0))
        current = current_weights.get(sleeve, 0.0)
        drifts[sleeve] = current - target

    # Sort most underweight first
    underweight = sorted(
        [(s, d) for s, d in drifts.items() if d < -0.005],
        key=lambda x: x[1],
    )

    # Tax-location preference by sleeve
    TAX_PREFERENCE: dict[str, list[str]] = {
        "bonds":         ["tax_deferred", "bank", "taxable", "tax_free"],
        "us_equity":     ["tax_free", "taxable", "tax_deferred"],
        "intl_equity":   ["taxable", "tax_free", "tax_deferred"],
        "brazil_equity": ["brazil_taxable", "taxable"],
        "crypto":        ["taxable", "tax_free"],
        "cash":          ["bank", "taxable", "tax_free"],
    }

    # Build account map by tax treatment
    account_by_tax: dict[str, list[dict]] = {}
    seen_accounts: set[str] = set()
    for holding in current_holdings:
        acct_id = str(holding.get("account_id", "default"))
        if acct_id in seen_accounts:
            continue
        seen_accounts.add(acct_id)
        tax = tax_treatments.get(acct_id, "taxable")
        if tax not in account_by_tax:
            account_by_tax[tax] = []
        account_by_tax[tax].append({
            "account_id": acct_id,
            "account_name": holding.get("account_name", acct_id),
            "tax_treatment": tax,
        })

    if not account_by_tax:
        account_by_tax["taxable"] = [{"account_id": "default", "account_name": "Taxable", "tax_treatment": "taxable"}]

    # Representative ETF per sleeve
    SLEEVE_ETF: dict[str, str] = {
        "us_equity": "VTI", "intl_equity": "VXUS", "bonds": "BND",
        "brazil_equity": "ITUB4", "crypto": "BTC", "cash": "CASH",
    }

    remaining = available_amount
    proposals: list[dict] = []
    new_additions: dict[str, float] = {}

    for sleeve, drift in underweight:
        if remaining < min_trade:
            break

        target_w = float(sleeve_targets.get(sleeve, {}).get("target", 0.0))
        needed = (target_w - current_weights.get(sleeve, 0.0)) * total_value
        amount = min(needed, remaining)
        if amount < min_trade:
            continue

        # Find best account for this sleeve
        best_account: dict | None = None
        for tax_pref in TAX_PREFERENCE.get(sleeve, ["taxable"]):
            if tax_pref in account_by_tax:
                best_account = account_by_tax[tax_pref][0]
                break
        if best_account is None:
            for accts in account_by_tax.values():
                if accts:
                    best_account = accts[0]
                    break

        tax_note = _tax_efficiency_note(sleeve, best_account["tax_treatment"] if best_account else "taxable")

        proposals.append({
            "account_name": best_account["account_name"] if best_account else "Taxable",
            "account_id": best_account["account_id"] if best_account else "default",
            "sleeve": sleeve,
            "asset": SLEEVE_ETF.get(sleeve, sleeve.upper()),
            "amount_usd": round(amount, 2),
            "reason": f"{sleeve.replace('_', ' ').title()} underweight by {abs(drift)*100:.1f}%",
            "drift_corrected_pct": round(abs(drift) * 100, 2),
            "tax_efficiency_note": tax_note,
        })
        new_additions[sleeve] = amount
        remaining -= amount

    # Projected weights after
    new_total = total_value + (available_amount - remaining)
    projected_weights: dict[str, float] = {}
    for sleeve in sleeve_targets:
        curr_val = sleeve_values.get(sleeve, 0.0) + new_additions.get(sleeve, 0.0)
        projected_weights[sleeve] = round(curr_val / new_total, 4) if new_total > 0 else 0.0

    return ContributionOptimization(
        total_available=available_amount,
        proposals=proposals,
        residual=round(remaining, 2),
        projected_weights_after=projected_weights,
        current_weights_before={k: round(v, 4) for k, v in current_weights.items()},
    )


def _tax_efficiency_note(sleeve: str, tax_treatment: str) -> str:
    """Swensen-inspired tax efficiency note."""
    if sleeve == "bonds" and tax_treatment == "tax_deferred":
        return "Optimal: bond interest shielded in tax-deferred"
    if sleeve == "us_equity" and tax_treatment == "tax_free":
        return "Optimal: growth compounds tax-free in Roth IRA"
    if sleeve == "crypto" and tax_treatment == "taxable":
        return "Acceptable: crypto gains subject to cap gains tax"
    if sleeve == "bonds" and tax_treatment == "taxable":
        return "Suboptimal: bond interest fully taxable; prefer 401k"
    if tax_treatment == "brazil_taxable":
        return "Brazil account: DARF rules apply above R$20k/month"
    return f"Account type: {tax_treatment.replace('_', ' ')}"


# ── Item 2c: Rebalance Preview ────────────────────────────────────────────────

def run_rebalance_preview(
    current_holdings: list[dict],
    target_weights: dict[str, float],
    portfolio_value: float,
    strategy_config: dict,
) -> dict:
    """Show portfolio before/after proposed hard rebalance without executing."""
    min_trade = float(strategy_config.get("min_trade_usd", 50.0))

    sleeve_values: dict[str, float] = {}
    for holding in current_holdings:
        sleeve = str(holding.get("asset_class", "cash")).lower()
        value = float(holding.get("current_value_usd", 0.0))
        sleeve_values[sleeve] = sleeve_values.get(sleeve, 0.0) + value

    if portfolio_value <= 0:
        portfolio_value = sum(sleeve_values.values()) or 1.0

    current_weights = {sleeve: val / portfolio_value for sleeve, val in sleeve_values.items()}

    trades: list[dict] = []
    total_estimated_tax = 0.0

    for sleeve, target_w in target_weights.items():
        current_w = current_weights.get(sleeve, 0.0)
        current_val = current_w * portfolio_value
        target_val = target_w * portfolio_value
        delta = target_val - current_val

        if abs(delta) < min_trade:
            continue

        action = "buy" if delta > 0 else "sell"
        estimated_tax = 0.0
        if action == "sell":
            estimated_gain = abs(delta) * 0.30  # assume 30% unrealized gain
            estimated_tax = estimated_gain * 0.15  # 15% LT cap gains
            total_estimated_tax += estimated_tax

        trades.append({
            "sleeve": sleeve,
            "action": action,
            "amount_usd": round(abs(delta), 2),
            "current_weight_pct": round(current_w * 100, 1),
            "target_weight_pct": round(target_w * 100, 1),
            "drift_pct": round((current_w - target_w) * 100, 2),
            "estimated_tax_usd": round(estimated_tax, 2),
        })

    tax_warning = total_estimated_tax > 500

    return {
        "before_weights": {k: round(v, 4) for k, v in current_weights.items()},
        "after_weights": {k: round(v, 4) for k, v in target_weights.items()},
        "trades_required": sorted(trades, key=lambda t: abs(t["amount_usd"]), reverse=True),
        "total_estimated_tax_usd": round(total_estimated_tax, 2),
        "tax_warning": tax_warning,
        "tax_warning_message": (
            f"This rebalance would cost ~${total_estimated_tax:,.0f} in estimated taxes. "
            "Soft rebalance with new contributions recommended instead."
        ) if tax_warning else None,
        "portfolio_value": round(portfolio_value, 2),
    }


# ── Item 4: Retirement Readiness ──────────────────────────────────────────────

def compute_retirement_readiness(
    current_value: float,
    monthly_contribution: float,
    current_age: int,
    target_retirement_age: int,
    target_monthly_income: float,
    social_security_monthly: float = 0.0,
    sleeve_weights: dict[str, float] | None = None,
    return_assumptions: dict[str, dict[str, float]] | None = None,
) -> RetirementReadiness:
    """
    Compute retirement readiness using 4% SWR / Trinity Study methodology.

    Required nest egg = (monthly_income - SS) * 12 / 0.04
    on_track = median projection >= required nest egg
    If gap: binary search for required additional monthly contribution.
    """
    if sleeve_weights is None:
        sleeve_weights = {
            "us_equity": 0.45, "intl_equity": 0.15, "bonds": 0.20,
            "brazil_equity": 0.10, "crypto": 0.07, "cash": 0.03,
        }
    if return_assumptions is None:
        return_assumptions = RETURN_ASSUMPTIONS.copy()

    years_to_retirement = max(target_retirement_age - current_age, 1)

    # Required nest egg (4% SWR — Trinity Study)
    net_monthly_needed = target_monthly_income - social_security_monthly
    required_nest_egg = (net_monthly_needed * 12) / 0.04 if net_monthly_needed > 0 else 0.0

    # Base Monte Carlo projection
    mc_result = run_monte_carlo(
        current_value=current_value,
        monthly_contribution=monthly_contribution,
        years=years_to_retirement,
        sleeve_weights=sleeve_weights,
        n_simulations=2000,
        return_assumptions=return_assumptions,
        use_historical_bootstrap=True,
    )

    projected_median = mc_result.summary["median_final"]
    gap = required_nest_egg - projected_median
    on_track = projected_median >= required_nest_egg

    # Probability of success via percentile interpolation
    sorted_pcts = [5, 10, 25, 50, 75, 90, 95]
    final_vals = [mc_result.percentile_bands[str(p)][years_to_retirement] for p in sorted_pcts]
    prob_success = _interpolate_probability(final_vals, sorted_pcts, required_nest_egg)

    # SWR survival at median
    swr_survival = _run_swr_survival(
        starting_value=projected_median,
        n_simulations=500,
        sleeve_weights=sleeve_weights,
        return_assumptions=return_assumptions,
        withdrawal_years=30,
    )

    # Required additional monthly if behind
    required_additional_monthly = 0.0
    if not on_track and gap > 0:
        required_additional_monthly = _find_required_monthly(
            current_value=current_value,
            base_contribution=monthly_contribution,
            years=years_to_retirement,
            sleeve_weights=sleeve_weights,
            return_assumptions=return_assumptions,
            target=required_nest_egg,
        )

    return RetirementReadiness(
        years_to_retirement=years_to_retirement,
        required_nest_egg=round(required_nest_egg, 2),
        projected_median=round(projected_median, 2),
        gap=round(gap, 2),
        on_track=on_track,
        probability_of_success=round(prob_success, 4),
        required_additional_monthly=round(required_additional_monthly, 2),
        swr_survival_probability=round(swr_survival, 4),
        current_savings_rate=None,  # requires income data
    )


def _interpolate_probability(
    percentile_values: list[float],
    percentiles: list[int],
    target: float,
) -> float:
    """Interpolate probability that final value exceeds target from percentile bands."""
    if not percentile_values:
        return 0.5
    if target <= percentile_values[0]:
        return 0.98
    if target >= percentile_values[-1]:
        return 0.02

    for i in range(len(percentile_values) - 1):
        v_lo, v_hi = percentile_values[i], percentile_values[i + 1]
        if v_lo <= target <= v_hi and v_hi > v_lo:
            frac = (target - v_lo) / (v_hi - v_lo)
            p_lo = 1 - percentiles[i] / 100
            p_hi = 1 - percentiles[i + 1] / 100
            return p_lo + frac * (p_hi - p_lo)
    return 0.5


def _find_required_monthly(
    current_value: float,
    base_contribution: float,
    years: int,
    sleeve_weights: dict,
    return_assumptions: dict,
    target: float,
    max_iterations: int = 20,
) -> float:
    """Binary search for additional monthly contribution to close the retirement gap."""
    low, high = 0.0, max(target / max(years * 12, 1), 1000.0)
    best = high

    for _ in range(max_iterations):
        mid = (low + high) / 2
        result = run_monte_carlo(
            current_value=current_value,
            monthly_contribution=base_contribution + mid,
            years=years,
            sleeve_weights=sleeve_weights,
            n_simulations=500,
            return_assumptions=return_assumptions,
            use_historical_bootstrap=False,
        )
        if result.summary["median_final"] >= target:
            best = mid
            high = mid
        else:
            low = mid
        if (high - low) < 10:
            break

    return best


# ── Lightweight dashboard preview ─────────────────────────────────────────────

def run_dashboard_preview(
    current_value: float,
    monthly_contribution: float,
    sleeve_weights: dict[str, float],
    return_assumptions: dict[str, dict[str, float]] | None = None,
) -> dict:
    """
    Lightweight Monte Carlo for dashboard card.
    1000 simulations, years 10+20. Returns median_10yr, median_20yr, swr_probability.
    """
    if return_assumptions is None:
        return_assumptions = RETURN_ASSUMPTIONS.copy()

    result = run_monte_carlo(
        current_value=current_value,
        monthly_contribution=monthly_contribution,
        years=20,
        sleeve_weights=sleeve_weights,
        n_simulations=1000,
        return_assumptions=return_assumptions,
        use_historical_bootstrap=True,
    )

    median_10yr = result.percentile_bands["50"][10] if len(result.percentile_bands["50"]) > 10 else 0.0

    return {
        "median_10yr": round(median_10yr, 2),
        "median_20yr": round(result.summary["median_final"], 2),
        "swr_probability": result.summary["swr_survival_probability"],
        "p10_20yr": round(result.summary["p10_final"], 2),
        "p90_20yr": round(result.summary["p90_final"], 2),
        "starting_value": current_value,
        "monthly_contribution": monthly_contribution,
    }
