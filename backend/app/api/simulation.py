"""
Simulation API endpoints — Phase 7.

POST /simulation/monte_carlo              — Async 5000-sim Monte Carlo (background task)
GET  /simulation/result/{task_id}         — Poll for Monte Carlo result
POST /simulation/stress_test              — Single scenario stress test
POST /simulation/stress_test/all          — All 5 scenarios simultaneously
POST /simulation/contribution_optimizer   — Tax-aware contribution routing
POST /simulation/rebalance_preview        — Before/after rebalance without executing
GET  /simulation/retirement_readiness     — 4% SWR retirement gap analysis
POST /simulation/dashboard_preview        — Lightweight 1000-sim for dashboard card
"""

from __future__ import annotations

import dataclasses
import json
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query

from app.config import settings
from app.services.simulation_engine import (
    STRESS_SCENARIOS,
    MonteCarloResult,
    RetirementReadiness,
    StressTestResult,
    compute_retirement_readiness,
    run_all_stress_tests,
    run_contribution_optimizer,
    run_dashboard_preview,
    run_monte_carlo,
    run_rebalance_preview,
    run_stress_test,
)

router = APIRouter()
logger = logging.getLogger(__name__)

_DEFAULT_USER = "00000000-0000-0000-0000-000000000001"

# Default sleeve weights (IPS targets from CLAUDE.md Section 5)
_DEFAULT_WEIGHTS = {
    "us_equity": 0.45, "intl_equity": 0.15, "bonds": 0.20,
    "brazil_equity": 0.10, "crypto": 0.07, "cash": 0.03,
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _dc_to_dict(obj) -> dict:
    """Recursively convert dataclass to JSON-serializable dict."""
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {k: _dc_to_dict(v) for k, v in dataclasses.asdict(obj).items()}
    return obj


def _redis_set(key: str, value: dict, ttl: int = 3600) -> None:
    """Store value in Redis with TTL. Silently fails if Redis unavailable."""
    try:
        from app.db.redis_client import get_redis_client
        rc = get_redis_client()
        rc.setex(key, ttl, json.dumps(value))
    except Exception as exc:
        logger.debug("Redis set failed: %s", exc)


def _redis_get(key: str) -> dict | None:
    """Retrieve value from Redis. Returns None if not found or Redis unavailable."""
    try:
        from app.db.redis_client import get_redis_client
        rc = get_redis_client()
        raw = rc.get(key)
        if raw:
            return json.loads(raw)
    except Exception as exc:
        logger.debug("Redis get failed: %s", exc)
    return None


def _get_current_portfolio_state(user_id: str) -> dict:
    """Fetch current holdings + prices + config from DB for simulation endpoints."""
    from app.db.supabase_client import get_supabase_client
    from app.services.market_data import fetch_current_prices
    from app.services.fx_engine import fetch_usd_brl_rate

    client = get_supabase_client()

    # Holdings
    holdings_resp = (
        client.table("holdings")
        .select("*, assets(symbol, asset_class, currency), accounts(name, account_type, tax_treatment)")
        .execute()
    )
    raw_holdings = holdings_resp.data or []

    # Prices
    symbols = [h["assets"]["symbol"] for h in raw_holdings if h.get("assets")]
    prices = {}
    if symbols:
        try:
            prices = fetch_current_prices(symbols)
        except Exception:
            pass

    # FX
    usd_brl = 5.5
    try:
        usd_brl = fetch_usd_brl_rate()
    except Exception:
        pass

    # Build holdings list
    holdings: list[dict] = []
    sleeve_portfolio: dict[str, float] = {}

    for h in raw_holdings:
        asset = h.get("assets") or {}
        account = h.get("accounts") or {}
        symbol = asset.get("symbol", "")
        currency = asset.get("currency", "USD")
        asset_class = str(asset.get("asset_class", "cash")).lower()
        qty = float(h.get("quantity", 0))
        price = prices.get(symbol, 0.0)

        if currency == "BRL" and usd_brl > 0:
            price_usd = price / usd_brl
        else:
            price_usd = price

        current_value_usd = qty * price_usd

        holdings.append({
            "symbol": symbol,
            "asset_class": asset_class,
            "quantity": qty,
            "last_price": price_usd,
            "current_value_usd": current_value_usd,
            "account_id": h.get("account_id", ""),
            "account_name": account.get("name", ""),
            "tax_treatment": account.get("tax_treatment", "taxable"),
        })

        sleeve_portfolio[asset_class] = sleeve_portfolio.get(asset_class, 0.0) + current_value_usd

    # Active strategy config
    config_resp = (
        client.table("strategy_configs")
        .select("config")
        .eq("user_id", user_id)
        .eq("is_active", True)
        .limit(1)
        .execute()
    )
    active_config = (config_resp.data[0]["config"] if config_resp.data else {})

    tax_treatments = {h["account_id"]: h["tax_treatment"] for h in holdings}

    return {
        "holdings": holdings,
        "prices": prices,
        "active_config": active_config,
        "tax_treatments": tax_treatments,
        "sleeve_portfolio": sleeve_portfolio,
        "total_value": sum(sleeve_portfolio.values()),
    }


# ── Monte Carlo (async) ───────────────────────────────────────────────────────

def _run_mc_background(
    task_id: str,
    current_value: float,
    monthly_contribution: float,
    years: int,
    sleeve_weights: dict,
    n_simulations: int,
    use_historical_bootstrap: bool,
    target_value: float | None,
) -> None:
    """Background task: run Monte Carlo and store result in Redis."""
    try:
        result = run_monte_carlo(
            current_value=current_value,
            monthly_contribution=monthly_contribution,
            years=years,
            sleeve_weights=sleeve_weights,
            n_simulations=n_simulations,
            use_historical_bootstrap=use_historical_bootstrap,
            target_value=target_value,
        )
        payload = {"status": "complete", "result": _dc_to_dict(result), "task_id": task_id}
    except Exception as exc:
        logger.error("Monte Carlo background task failed: %s", exc)
        payload = {"status": "error", "error": str(exc), "task_id": task_id}

    _redis_set(f"mc_result:{task_id}", payload, ttl=3600)


@router.post("/simulation/monte_carlo", tags=["simulation"])
def start_monte_carlo(
    body: dict,
    background_tasks: BackgroundTasks,
    user_id: str = Query(default=_DEFAULT_USER),
) -> dict:
    """
    Trigger Monte Carlo projection as async background task.

    Body fields:
    - monthly_contribution (required): float
    - years: int (default 20)
    - sleeve_weights: dict (default IPS targets)
    - n_simulations: int (default 5000, max 10000)
    - use_historical_bootstrap: bool (default true)
    - target_value: float (optional, default 2x current)

    Returns immediately: {task_id, status: "running", check_url}
    Poll GET /simulation/result/{task_id} for completion.
    """
    monthly_contribution = float(body.get("monthly_contribution", 0))
    years = int(body.get("years", 20))
    years = max(1, min(years, 50))
    sleeve_weights = body.get("sleeve_weights") or _DEFAULT_WEIGHTS
    n_simulations = min(int(body.get("n_simulations", 5000)), 10000)
    use_bootstrap = bool(body.get("use_historical_bootstrap", True))
    target_value = body.get("target_value")

    # Get current portfolio value for starting point
    current_value = float(body.get("current_value", 0))
    if current_value <= 0:
        try:
            state = _get_current_portfolio_state(user_id)
            current_value = state["total_value"]
        except Exception:
            current_value = 0.0

    task_id = str(uuid.uuid4())

    # Store "running" status immediately
    _redis_set(f"mc_result:{task_id}", {"status": "running", "task_id": task_id}, ttl=3600)

    background_tasks.add_task(
        _run_mc_background,
        task_id=task_id,
        current_value=current_value,
        monthly_contribution=monthly_contribution,
        years=years,
        sleeve_weights=sleeve_weights,
        n_simulations=n_simulations,
        use_historical_bootstrap=use_bootstrap,
        target_value=target_value,
    )

    logger.info("Monte Carlo task started task_id=%s n=%d years=%d", task_id, n_simulations, years)

    return {
        "task_id": task_id,
        "status": "running",
        "check_url": f"/simulation/result/{task_id}",
        "n_simulations": n_simulations,
        "years": years,
        "current_value": current_value,
        "monthly_contribution": monthly_contribution,
    }


@router.get("/simulation/result/{task_id}", tags=["simulation"])
def get_simulation_result(task_id: str) -> dict:
    """
    Poll for Monte Carlo result.

    Returns:
    - {status: "running"} — still computing
    - {status: "complete", result: MonteCarloResult} — done
    - {status: "error", error: str} — failed
    - {status: "not_found"} — task_id unknown or expired (>1hr)
    """
    cached = _redis_get(f"mc_result:{task_id}")
    if cached is None:
        return {"status": "not_found", "task_id": task_id}
    return cached


# ── Stress Test ───────────────────────────────────────────────────────────────

@router.post("/simulation/stress_test", tags=["simulation"])
def stress_test(
    body: dict,
    user_id: str = Query(default=_DEFAULT_USER),
) -> dict:
    """
    Apply a single historical stress scenario to the current portfolio.

    Body: {scenario_name: str}
    Valid scenarios: 2008_gfc, 2020_covid, 2022_rate_shock, stagflation_1970s, brazil_crisis
    """
    scenario_name = body.get("scenario_name", "")
    if not scenario_name:
        raise HTTPException(status_code=422, detail="scenario_name is required")
    if scenario_name not in STRESS_SCENARIOS:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown scenario '{scenario_name}'. Valid: {list(STRESS_SCENARIOS)}",
        )

    # Get current portfolio
    current_portfolio = body.get("current_portfolio")
    if not current_portfolio:
        try:
            state = _get_current_portfolio_state(user_id)
            current_portfolio = state["sleeve_portfolio"]
        except Exception as exc:
            logger.warning("stress_test: could not fetch portfolio: %s", exc)
            current_portfolio = {k: 0.0 for k in _DEFAULT_WEIGHTS}

    try:
        result = run_stress_test(current_portfolio, scenario_name)
        return _dc_to_dict(result)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        logger.error("stress_test failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/simulation/stress_test/all", tags=["simulation"])
def stress_test_all(
    body: dict | None = None,
    user_id: str = Query(default=_DEFAULT_USER),
) -> dict:
    """Run all 5 stress scenarios simultaneously. Returns dict keyed by scenario name."""
    if body is None:
        body = {}

    current_portfolio = body.get("current_portfolio")
    if not current_portfolio:
        try:
            state = _get_current_portfolio_state(user_id)
            current_portfolio = state["sleeve_portfolio"]
        except Exception:
            current_portfolio = {k: 1000.0 for k in _DEFAULT_WEIGHTS}

    results = run_all_stress_tests(current_portfolio)
    return {key: _dc_to_dict(r) for key, r in results.items()}


# ── Contribution Optimizer ────────────────────────────────────────────────────

@router.post("/simulation/contribution_optimizer", tags=["simulation"])
def contribution_optimizer(
    body: dict,
    user_id: str = Query(default=_DEFAULT_USER),
) -> dict:
    """
    Given $X to invest, return optimal account + asset routing.

    Body: {available_amount: float}
    Fetches current holdings, prices, and active strategy config from DB.
    """
    available_amount = float(body.get("available_amount", 0))
    if available_amount <= 0:
        raise HTTPException(status_code=422, detail="available_amount must be > 0")

    try:
        state = _get_current_portfolio_state(user_id)
    except Exception as exc:
        logger.error("contribution_optimizer: portfolio fetch failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Could not fetch portfolio: {exc}")

    try:
        result = run_contribution_optimizer(
            available_amount=available_amount,
            current_holdings=state["holdings"],
            current_prices=state["prices"],
            active_config=state["active_config"],
            tax_treatments=state["tax_treatments"],
        )
        return _dc_to_dict(result)
    except Exception as exc:
        logger.error("contribution_optimizer failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


# ── Rebalance Preview ─────────────────────────────────────────────────────────

@router.post("/simulation/rebalance_preview", tags=["simulation"])
def rebalance_preview(
    body: dict | None = None,
    user_id: str = Query(default=_DEFAULT_USER),
) -> dict:
    """
    Show portfolio before/after a proposed hard rebalance without executing.

    Body: {} — uses current holdings and IPS target weights.
    Returns: before/after weights, trades required, estimated tax impact.
    """
    if body is None:
        body = {}

    try:
        state = _get_current_portfolio_state(user_id)
    except Exception as exc:
        logger.error("rebalance_preview: portfolio fetch failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Could not fetch portfolio: {exc}")

    active_config = state["active_config"]
    target_weights = {
        k: v["target"] if isinstance(v, dict) else v
        for k, v in active_config.get("sleeve_targets", _DEFAULT_WEIGHTS).items()
    }
    if not target_weights:
        target_weights = _DEFAULT_WEIGHTS

    try:
        result = run_rebalance_preview(
            current_holdings=state["holdings"],
            target_weights=target_weights,
            portfolio_value=state["total_value"],
            strategy_config=active_config,
        )
        return result
    except Exception as exc:
        logger.error("rebalance_preview failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


# ── Retirement Readiness ──────────────────────────────────────────────────────

@router.get("/simulation/retirement_readiness", tags=["simulation"])
def retirement_readiness(
    current_age: int = Query(..., description="Current age in years"),
    target_retirement_age: int = Query(65, description="Target retirement age"),
    target_monthly_income: float = Query(..., description="Desired monthly income in retirement (USD)"),
    social_security_monthly: float = Query(0.0, description="Expected monthly SS benefit (USD)"),
    monthly_contribution: float = Query(0.0, description="Current monthly contribution"),
    user_id: str = Query(default=_DEFAULT_USER),
) -> dict:
    """
    Compute retirement readiness using 4% SWR / Trinity Study methodology.

    Required nest egg = (monthly_income - SS) * 12 / 0.04
    on_track = projected_median >= required_nest_egg
    """
    if current_age >= target_retirement_age:
        raise HTTPException(status_code=422, detail="current_age must be less than target_retirement_age")

    # Get current portfolio value
    current_value = 0.0
    sleeve_weights = _DEFAULT_WEIGHTS.copy()
    try:
        state = _get_current_portfolio_state(user_id)
        current_value = state["total_value"]
        total = sum(state["sleeve_portfolio"].values())
        if total > 0:
            sleeve_weights = {k: v / total for k, v in state["sleeve_portfolio"].items()}
    except Exception as exc:
        logger.warning("retirement_readiness: portfolio fetch failed: %s", exc)

    try:
        result = compute_retirement_readiness(
            current_value=current_value,
            monthly_contribution=monthly_contribution,
            current_age=current_age,
            target_retirement_age=target_retirement_age,
            target_monthly_income=target_monthly_income,
            social_security_monthly=social_security_monthly,
            sleeve_weights=sleeve_weights,
        )
        return _dc_to_dict(result)
    except Exception as exc:
        logger.error("retirement_readiness failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


# ── Dashboard Preview ─────────────────────────────────────────────────────────

@router.post("/simulation/dashboard_preview", tags=["simulation"])
def dashboard_preview(
    body: dict | None = None,
    user_id: str = Query(default=_DEFAULT_USER),
) -> dict:
    """
    Lightweight 1000-sim Monte Carlo for dashboard card.
    Returns median_10yr, median_20yr, swr_probability in <2s.
    """
    if body is None:
        body = {}

    monthly_contribution = float(body.get("monthly_contribution", 0))
    current_value = float(body.get("current_value", 0))
    sleeve_weights = body.get("sleeve_weights") or None

    if current_value <= 0 or sleeve_weights is None:
        try:
            state = _get_current_portfolio_state(user_id)
            if current_value <= 0:
                current_value = state["total_value"]
            if sleeve_weights is None:
                total = sum(state["sleeve_portfolio"].values())
                if total > 0:
                    sleeve_weights = {k: v / total for k, v in state["sleeve_portfolio"].items()}
        except Exception:
            pass

    if sleeve_weights is None:
        sleeve_weights = _DEFAULT_WEIGHTS

    try:
        result = run_dashboard_preview(
            current_value=current_value,
            monthly_contribution=monthly_contribution,
            sleeve_weights=sleeve_weights,
        )
        return result
    except Exception as exc:
        logger.error("dashboard_preview failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
