"""
Performance API endpoints.

GET  /performance/summary      — TWR, MWR, Sharpe, Sortino, Calmar, max drawdown
GET  /performance/attribution  — Brinson-Hood-Beebower sleeve attribution
GET  /performance/benchmark    — Portfolio vs benchmark comparison
GET  /performance/rolling      — Rolling 1mo/3mo/1yr returns
GET  /performance/risk         — Risk parity, correlation matrix, VaR
POST /performance/snapshot     — Manually trigger a portfolio snapshot
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any

import numpy as np
import pandas as pd
import yfinance as yf
from fastapi import APIRouter, HTTPException, Query

from app.db.repositories import performance as perf_repo
from app.db.supabase_client import get_supabase_client
from app.db.redis_client import get_redis_client
from app.db.repositories.snapshots import (
    get_latest_snapshot,
    get_snapshot_history,
    upsert_portfolio_snapshot,
)
from app.schemas.performance_models import (
    AttributionResponse,
    BenchmarkComparisonResponse,
    DrawdownInfo,
    PerformanceSummaryResponse,
    PeriodReturn,
    RatioInterpretation,
    RiskSummaryResponse,
    RollingReturnsResponse,
    SleeveAttributionDetail,
    SnapshotTriggerResponse,
)
from app.services import performance_engine as pe
from app.services import risk_engine as re

logger = logging.getLogger(__name__)
router = APIRouter()

from app.config import get_default_user_id as _get_default_user_id


def _resolve_user(user_id: str | None) -> str:
    return user_id or _get_default_user_id()


RATIO_THRESHOLDS = {
    "sharpe":  [(0.5, "Poor"), (1.0, "Fair"), (1.5, "Good"), (float("inf"), "Excellent")],
    "sortino": [(0.75, "Poor"), (1.5, "Fair"), (2.0, "Good"), (float("inf"), "Excellent")],
    "calmar":  [(0.25, "Poor"), (0.5, "Fair"), (1.0, "Good"), (float("inf"), "Excellent")],
}


def _interpret_ratio(value: float | None, ratio_type: str) -> RatioInterpretation:
    if value is None:
        return RatioInterpretation(value=None, label="—")
    thresholds = RATIO_THRESHOLDS.get(ratio_type, [])
    for threshold, label in thresholds:
        if abs(value) <= threshold:
            return RatioInterpretation(value=round(value, 3), label=label)
    return RatioInterpretation(value=round(value, 3), label="Excellent")


def _snapshots_to_series(snapshots: list[dict]) -> pd.Series:
    """Convert snapshot list to a pandas Series indexed by date."""
    if not snapshots:
        return pd.Series(dtype=float)
    dates = pd.to_datetime([s["snapshot_date"] for s in snapshots])
    values = [float(s["total_value_usd"]) for s in snapshots]
    return pd.Series(values, index=dates).sort_index()


def _series_to_returns(values: pd.Series) -> pd.Series:
    """Convert value series to daily return series."""
    return values.pct_change().dropna()


def _period_start_date(period: str) -> date:
    today = date.today()
    mapping = {
        "1mo": today - timedelta(days=30),
        "3mo": today - timedelta(days=91),
        "6mo": today - timedelta(days=182),
        "ytd": date(today.year, 1, 1),
        "1yr": today - timedelta(days=365),
        "3yr": today - timedelta(days=1095),
        "all": date(2000, 1, 1),
    }
    return mapping.get(period, date(today.year, 1, 1))


def _fetch_benchmark_returns(symbol: str, start_date: date, end_date: date) -> pd.Series:
    """Fetch daily returns for a benchmark ticker via yfinance."""
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(start=start_date.isoformat(), end=end_date.isoformat())
        if hist.empty:
            return pd.Series(dtype=float)
        closes = hist["Close"]
        closes.index = closes.index.tz_localize(None)
        return closes.pct_change().dropna()
    except Exception as exc:
        logger.warning("Failed to fetch benchmark %s: %s", symbol, exc)
        return pd.Series(dtype=float)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/performance/summary", response_model=PerformanceSummaryResponse)
async def performance_summary(
    user_id: str = Query(default=None),
    period: str = Query(default="ytd"),
) -> PerformanceSummaryResponse:
    """Return portfolio performance metrics — all standard periods. Redis-cached 5 min."""
    user_id = _resolve_user(user_id)
    cache_key = f"perf_summary:{user_id}:{period}"
    try:
        rc = get_redis_client()
        cached = rc.get(cache_key)
        if cached:
            import json as _json
            return PerformanceSummaryResponse.model_validate_json(cached)
    except Exception as _cache_exc:
        logger.debug("Redis cache miss (perf_summary): %s", _cache_exc)

    snapshots = get_snapshot_history(user_id, days=1100)  # 3yr
    if len(snapshots) < 2:
        raise HTTPException(
            status_code=404,
            detail="Insufficient snapshot data — run /performance/snapshot first.",
        )

    values = _snapshots_to_series(snapshots)
    returns = _series_to_returns(values)

    # Compute metrics for each standard period
    period_map = {
        "1mo": 30, "3mo": 91, "6mo": 182,
        "ytd": None, "1yr": 365, "3yr": 1095, "all_time": None,
    }
    today = date.today()

    # Build benchmark returns for beta/IR (SPY default, for YTD)
    bench_start = _period_start_date(period)
    bench_returns_raw = _fetch_benchmark_returns("SPY", bench_start, today)

    period_returns_list: list[PeriodReturn] = []
    for label in ["1mo", "3mo", "6mo", "ytd", "1yr", "3yr", "all_time"]:
        if label == "ytd":
            cutoff = pd.Timestamp(today.year, 1, 1)
        elif label == "all_time":
            cutoff = values.index[0]
        else:
            days = period_map[label]
            cutoff = pd.Timestamp(today) - pd.Timedelta(days=days)

        period_vals = values[values.index >= cutoff]
        if len(period_vals) < 2:
            period_returns_list.append(PeriodReturn(period=label))
            continue

        period_returns_series = _series_to_returns(period_vals)
        cf_empty = pd.DataFrame(columns=["date", "amount"])
        twr = pe.compute_twr(period_vals, cf_empty)

        # Benchmark return for period
        bench_label_returns = bench_returns_raw[bench_returns_raw.index >= cutoff] if not bench_returns_raw.empty else pd.Series(dtype=float)
        bench_return = None
        if not bench_label_returns.empty:
            bench_return = float((1 + bench_label_returns).prod() - 1)

        active = (twr - bench_return) if bench_return is not None else None

        period_returns_list.append(PeriodReturn(
            period=label,
            twr=round(twr, 4),
            benchmark_return=round(bench_return, 4) if bench_return is not None else None,
            active_return=round(active, 4) if active is not None else None,
        ))

    # Risk-adjusted metrics on full history
    sharpe_val = pe.compute_sharpe(returns)
    sortino_val = pe.compute_sortino(returns)
    calmar_val = pe.compute_calmar(returns)
    max_dd, peak_dt, trough_dt = pe.compute_max_drawdown(values)
    vol = pe.compute_volatility(returns)

    # Beta and IR using available benchmark data
    beta_val = None
    ir_val = None
    if not bench_returns_raw.empty:
        aligned = returns.align(bench_returns_raw, join="inner")[0]
        bench_aligned = returns.align(bench_returns_raw, join="inner")[1]
        if len(aligned) > 10:
            beta_val = pe.compute_beta(aligned, bench_aligned)
            active_ret = aligned - bench_aligned
            ir_val = pe.compute_information_ratio(active_ret)

    # Current drawdown
    latest_val = float(values.iloc[-1])
    peak_val = float(values.max())
    current_dd = (latest_val - peak_val) / peak_val if peak_val > 0 else 0.0

    result = PerformanceSummaryResponse(
        user_id=user_id,
        as_of_date=today,
        period_returns=period_returns_list,
        sharpe=_interpret_ratio(sharpe_val, "sharpe"),
        sortino=_interpret_ratio(sortino_val, "sortino"),
        calmar=_interpret_ratio(calmar_val, "calmar"),
        beta=round(beta_val, 3) if beta_val is not None else None,
        information_ratio=round(ir_val, 3) if ir_val is not None else None,
        volatility_annualized=round(vol, 4),
        drawdown=DrawdownInfo(
            max_drawdown_pct=round(max_dd, 4),
            peak_date=peak_dt,
            trough_date=trough_dt,
            current_drawdown_pct=round(current_dd, 4),
        ),
        data_points=len(values),
    )
    try:
        rc = get_redis_client()
        rc.set(cache_key, result.model_dump_json(), ex=300)  # 5-minute TTL
    except Exception as _store_exc:
        logger.debug("Redis cache store failed (perf_summary): %s", _store_exc)
    return result


@router.get("/performance/attribution", response_model=AttributionResponse)
async def performance_attribution(
    user_id: str = Query(default=None),
    period_start: str | None = None,
    period_end: str | None = None,
) -> AttributionResponse:
    """Return Brinson-Hood-Beebower attribution by sleeve."""
    today = date.today()
    end_dt = date.fromisoformat(period_end) if period_end else today
    start_dt = date.fromisoformat(period_start) if period_start else date(today.year, 1, 1)

    # Check for cached attribution
    cached = perf_repo.get_attribution_for_period(user_id, start_dt, end_dt)
    if cached and cached.get("attribution_by_sleeve"):
        by_sleeve: dict[str, Any] = cached["attribution_by_sleeve"]
        per_sleeve_list = [
            SleeveAttributionDetail(sleeve=s, **v)
            for s, v in by_sleeve.items()
        ]
        return AttributionResponse(
            user_id=user_id,
            period_start=start_dt,
            period_end=end_dt,
            portfolio_return=cached.get("total_return"),
            benchmark_return=cached.get("benchmark_return"),
            active_return=cached.get("active_return"),
            fx_contribution=cached.get("fx_contribution"),
            per_sleeve=per_sleeve_list,
            total_allocation_effect=sum(s.allocation_effect for s in per_sleeve_list),
            total_selection_effect=sum(s.selection_effect for s in per_sleeve_list),
            total_interaction_effect=sum(s.interaction_effect for s in per_sleeve_list),
        )

    # No cached data — return empty attribution with start/end
    logger.info("No cached attribution for %s – %s; run snapshot pipeline to populate.", start_dt, end_dt)
    return AttributionResponse(
        user_id=user_id,
        period_start=start_dt,
        period_end=end_dt,
        per_sleeve=[],
    )


@router.get("/performance/benchmark", response_model=BenchmarkComparisonResponse)
async def performance_vs_benchmark(
    user_id: str = Query(default=None),
    benchmark: str = Query(default="SPY"),
    period: str = Query(default="ytd"),
) -> BenchmarkComparisonResponse:
    """Return portfolio vs benchmark comparison. Returns empty response (not error) when insufficient data."""
    try:
        snapshots = get_snapshot_history(user_id, days=1100)
        if len(snapshots) < 2:
            return BenchmarkComparisonResponse(
                benchmark_symbol=benchmark.upper(),
                period=period,
                portfolio_return=None,
                benchmark_return=None,
                active_return=None,
            )

        values = _snapshots_to_series(snapshots)
        returns = _series_to_returns(values)

        start_dt = _period_start_date(period)
        today = date.today()

        period_vals = values[values.index >= pd.Timestamp(start_dt)]
        period_returns = _series_to_returns(period_vals) if len(period_vals) > 1 else returns

        bench_returns = _fetch_benchmark_returns(benchmark.upper(), start_dt, today)

        portfolio_return = float((1 + period_returns).prod() - 1) if not period_returns.empty else None
        bench_return = float((1 + bench_returns).prod() - 1) if not bench_returns.empty else None
        active_ret = (portfolio_return - bench_return) if (portfolio_return is not None and bench_return is not None) else None

        beta = None
        corr = None
        ir = None
        if not bench_returns.empty and not period_returns.empty:
            aligned_p, aligned_b = period_returns.align(bench_returns, join="inner")
            if len(aligned_p) > 10:
                beta = pe.compute_beta(aligned_p, aligned_b)
                corr = float(aligned_p.corr(aligned_b))
                active_series = aligned_p - aligned_b
                ir = pe.compute_information_ratio(active_series)

        return BenchmarkComparisonResponse(
            benchmark_symbol=benchmark.upper(),
            period=period,
            portfolio_return=round(portfolio_return, 4) if portfolio_return is not None else None,
            benchmark_return=round(bench_return, 4) if bench_return is not None else None,
            active_return=round(active_ret, 4) if active_ret is not None else None,
            beta=round(beta, 3) if beta is not None else None,
            correlation=round(corr, 3) if corr is not None else None,
            information_ratio=round(ir, 3) if ir is not None else None,
        )
    except Exception as exc:
        logger.warning("performance_vs_benchmark failed gracefully: %s", exc)
        return BenchmarkComparisonResponse(
            benchmark_symbol=benchmark.upper(),
            period=period,
            portfolio_return=None,
            benchmark_return=None,
            active_return=None,
        )


@router.get("/performance/rolling", response_model=RollingReturnsResponse)
async def performance_rolling(
    user_id: str = Query(default=None),
    windows: str = Query(default="1mo,3mo,1yr"),
) -> RollingReturnsResponse:
    """Return rolling return time series for the specified windows."""
    snapshots = get_snapshot_history(user_id, days=1100)
    if len(snapshots) < 22:
        window_labels = [w.strip() for w in windows.split(",")]
        return RollingReturnsResponse(user_id=user_id, data_points=[], windows=window_labels)

    values = _snapshots_to_series(snapshots)
    window_labels = [w.strip() for w in windows.split(",")]
    window_map = {"1mo": 21, "3mo": 63, "6mo": 126, "1yr": 252}
    window_ints = [window_map[w] for w in window_labels if w in window_map]

    rolling_df = pe.compute_rolling_returns(values, window_ints)

    # Convert to list of dicts for response
    data_points: list[dict[str, Any]] = []
    for ts, row in rolling_df.iterrows():
        point: dict[str, Any] = {"date": ts.date().isoformat()}
        for col in rolling_df.columns:
            val = row[col]
            point[col] = round(float(val), 4) if not np.isnan(val) else None
        data_points.append(point)

    return RollingReturnsResponse(
        user_id=user_id,
        data_points=data_points,
        windows=window_labels,
    )


@router.get("/performance/risk", response_model=RiskSummaryResponse)
async def performance_risk(
    user_id: str = Query(default=None),
) -> RiskSummaryResponse:
    """Return risk parity weights, correlation matrix, and VaR."""
    today = date.today()

    # Try cached risk metrics
    cached = perf_repo.get_risk_metrics_latest(user_id)
    if cached:
        return RiskSummaryResponse(
            user_id=user_id,
            as_of_date=cached.get("as_of_date"),
            var_95=cached.get("var_95_1day"),
            var_99=cached.get("var_99_1day"),
            diversification_ratio=cached.get("effective_diversification_ratio"),
            risk_parity_weights=cached.get("risk_parity_weights") or {},
            actual_weights={},
            correlation_matrix=cached.get("correlation_matrix") or {},
            high_correlation_pairs=[],
        )

    # No cached data — compute from snapshots
    snapshots = get_snapshot_history(user_id, days=365)
    if len(snapshots) < 30:
        return RiskSummaryResponse(
            user_id=user_id,
            as_of_date=date.today(),
            var_95=None, var_99=None,
            diversification_ratio=None,
            risk_parity_weights={},
            actual_weights={},
            correlation_matrix={},
            high_correlation_pairs=[],
        )

    values = _snapshots_to_series(snapshots)
    returns = _series_to_returns(values)

    var_95 = re.compute_var(returns, 0.95)
    var_99 = re.compute_var(returns, 0.99)

    # Use sleeve weights from latest snapshot if available
    latest = get_latest_snapshot(user_id)
    sleeve_weights_raw: dict[str, float] = {}
    if latest and latest.get("sleeve_weights"):
        sleeve_weights_raw = {k: float(v) for k, v in latest["sleeve_weights"].items()}

    # Use fixed volatility estimates (Phase 10 will compute from actual sleeve returns)
    vol_estimates = {
        "us_equity": 0.165, "intl_equity": 0.175, "bonds": 0.065,
        "brazil_equity": 0.280, "crypto": 0.700, "cash": 0.010,
    }
    active_sleeves = list(sleeve_weights_raw.keys()) or list(vol_estimates.keys())
    sleeve_vols = {s: vol_estimates.get(s, 0.15) for s in active_sleeves}

    # Simple identity-ish correlation (off-diagonal = 0.2 as placeholder)
    n = len(active_sleeves)
    corr_arr = np.full((n, n), 0.2)
    np.fill_diagonal(corr_arr, 1.0)

    rp_weights = re.compute_risk_parity_weights(sleeve_vols, corr_arr, active_sleeves)

    # Correlation matrix as nested dict for JSON
    corr_dict = {active_sleeves[i]: {active_sleeves[j]: round(float(corr_arr[i, j]), 3) for j in range(n)} for i in range(n)}

    return RiskSummaryResponse(
        user_id=user_id,
        as_of_date=today,
        var_95=round(var_95, 4),
        var_99=round(var_99, 4),
        diversification_ratio=None,
        risk_parity_weights=rp_weights,
        actual_weights=sleeve_weights_raw,
        correlation_matrix=corr_dict,
        high_correlation_pairs=[],
    )


@router.post("/performance/snapshot", response_model=SnapshotTriggerResponse)
async def trigger_snapshot(
    user_id: str = Query(default=None),
    force: bool = Query(default=False),
) -> SnapshotTriggerResponse:
    """
    Trigger a portfolio snapshot for today using live holdings × current prices.

    Called by n8n daily and by SnapshotInit on app startup.
    Always writes today's snapshot with current market prices — never uses
    stale historical values from previous snapshots.

    Set force=true to overwrite an existing today snapshot.
    """
    user_id = _resolve_user(user_id)
    from app.db.repositories.snapshots import get_latest_snapshot as get_snap
    from app.services.portfolio_value import compute_live_portfolio_value
    from app.services import allocation_engine
    from app.db.repositories import holdings as holdings_repo
    today = date.today()

    latest = get_snap(user_id)
    existing_today = latest and latest.get("snapshot_date") == today.isoformat()

    # Skip only if already ran today AND not forced — prevents redundant yfinance calls
    if existing_today and not force:
        # But verify the existing value looks reasonable (> $1k); if not, force refresh
        existing_val = float(latest.get("total_value_usd") or 0)
        if existing_val > 1000:
            return SnapshotTriggerResponse(
                status="exists",
                snapshot_date=today,
                total_value_usd=existing_val,
                message="Snapshot for today already exists with live value.",
            )

    # Compute live portfolio value — holdings × today's market prices
    try:
        total_usd, total_brl, fx_rate = compute_live_portfolio_value(user_id)
    except Exception as exc:
        logger.error("compute_live_portfolio_value failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Live value computation failed: {exc}")

    if total_usd < 100:
        raise HTTPException(
            status_code=422,
            detail="Computed portfolio value < $100 — check holdings and prices.",
        )

    # Build sleeve weights from live computation
    sleeve_weights_dict: dict = {}
    try:
        holdings = holdings_repo.get_holdings(user_id)
        if holdings:
            from app.services.market_data import fetch_current_prices
            symbols = list({h["symbol"] for h in holdings if h.get("symbol")})
            prices = fetch_current_prices(symbols) if symbols else {}
            assets_map = {h["symbol"]: h for h in holdings}
            sleeve_vals = allocation_engine.compute_sleeve_values(
                holdings, assets_map, prices, fx_rate
            )
            sleeve_weights_dict = {
                k: round(v / total_usd, 6)
                for k, v in sleeve_vals.items()
                if total_usd > 0
            }
    except Exception as exc:
        logger.debug("Sleeve weight computation failed (non-critical): %s", exc)

    snapshot = {
        "user_id": user_id,
        "snapshot_date": today.isoformat(),
        "total_value_usd": total_usd,
        "total_value_brl": total_brl,
        "usd_brl_rate": fx_rate,
        "sleeve_weights": sleeve_weights_dict or (latest.get("sleeve_weights") if latest else None),
        "benchmark_symbol": "SPY",
    }

    try:
        upsert_portfolio_snapshot(snapshot)
        logger.info(
            "Snapshot upserted user=%s date=%s value=%.2f",
            user_id, today.isoformat(), total_usd,
        )
        return SnapshotTriggerResponse(
            status="created" if not existing_today else "updated",
            snapshot_date=today,
            total_value_usd=total_usd,
            message=f"Snapshot {'updated' if existing_today else 'created'} with live value ${total_usd:,.0f}.",
        )
    except Exception as exc:
        logger.error("Snapshot upsert failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/performance/fx_attribution")
async def fx_attribution_endpoint(
    period: str = Query(default="ytd"),
    user_id: str = Query(default=None),
) -> dict:
    """
    FX attribution for the Brazil sleeve.

    Returns Brazil sleeve return in BRL vs USD, and pure currency effect.
    Also returns historical USD/BRL rate for the period (for charting).
    """
    from app.services.fx_engine import (
        compute_fx_attribution_over_period,
        get_usd_brl_history,
    )
    from datetime import date as _date, timedelta

    # Determine period dates
    today = _date.today()
    period_map = {
        "1mo":  today - timedelta(days=30),
        "3mo":  today - timedelta(days=90),
        "6mo":  today - timedelta(days=180),
        "ytd":  _date(today.year, 1, 1),
        "1yr":  today - timedelta(days=365),
    }
    period_start = period_map.get(period, _date(today.year, 1, 1))

    # Fetch portfolio snapshots with sleeve data
    try:
        client = get_supabase_client()
        resp = (
            client.table("portfolio_snapshots")
            .select("snapshot_date, sleeve_weights, total_value_usd, usd_brl_rate")
            .eq("user_id", user_id)
            .gte("snapshot_date", period_start.isoformat())
            .lte("snapshot_date", today.isoformat())
            .order("snapshot_date")
            .execute()
        )
        snapshots = resp.data or []
    except Exception as exc:
        logger.error("fx_attribution: snapshot fetch failed: %s", exc)
        snapshots = []

    # Build brazil holdings history from snapshots
    brazil_history = []
    for snap in snapshots:
        weights = snap.get("sleeve_weights") or {}
        total = float(snap.get("total_value_usd", 0))
        fx_rate = float(snap.get("usd_brl_rate") or 5.70)
        brazil_weight_usd = 0.0

        if isinstance(weights, list):
            for w in weights:
                if isinstance(w, dict) and w.get("sleeve") == "brazil_equity":
                    brazil_weight_usd = float(w.get("current_weight", 0)) * total
        elif isinstance(weights, dict):
            brazil_weight_usd = weights.get("brazil_equity", 0) * total

        if brazil_weight_usd > 0:
            brazil_history.append({
                "date": snap["snapshot_date"],
                "value_usd": brazil_weight_usd,
                "value_brl": brazil_weight_usd * fx_rate,
            })

    attribution = compute_fx_attribution_over_period(
        brazil_history, period_start, today
    )

    # Get rate history for chart
    rate_history = get_usd_brl_history(days=(today - period_start).days + 5)
    rate_history = [r for r in rate_history if r["date"] >= period_start.isoformat()]

    if attribution is None:
        return {
            "period": period,
            "has_data": False,
            "message": "Insufficient Brazil sleeve history for this period",
            "rate_history": rate_history,
        }

    return {
        "period": period,
        "has_data": True,
        "brazil_return_brl": attribution.brazil_return_brl,
        "brazil_return_usd": attribution.brazil_return_usd,
        "fx_contribution": attribution.fx_contribution,
        "usd_brl_start": attribution.usd_brl_start,
        "usd_brl_end": attribution.usd_brl_end,
        "usd_brl_change_pct": attribution.usd_brl_change_pct,
        "interpretation": attribution.interpretation,
        "rate_history": rate_history,
    }


@router.get("/performance/correlation_history")
async def correlation_history(
    user_id: str = Query(default=None),
    days: int = Query(default=365, ge=30, le=730),
) -> dict:
    """
    Rolling 90-day correlations for all sleeve pairs over the last N days.

    Returns:
        {
          "pairs": [{"sleeves": [a, b], "history": [{"date": str, "correlation": float}]}],
          "highest_pair": {"sleeves": [a, b], "current_correlation": float},
        }
    """
    from datetime import date as _date, timedelta
    from itertools import combinations

    today = _date.today()
    start = today - timedelta(days=days)

    try:
        client = get_supabase_client()
        resp = (
            client.table("portfolio_snapshots")
            .select("snapshot_date, sleeve_weights")
            .eq("user_id", user_id)
            .gte("snapshot_date", start.isoformat())
            .order("snapshot_date")
            .execute()
        )
        snapshots = resp.data or []
    except Exception as exc:
        logger.error("correlation_history: fetch failed: %s", exc)
        return {"pairs": [], "highest_pair": None}

    if len(snapshots) < 10:
        return {"pairs": [], "highest_pair": None}

    # Build per-sleeve return series
    sleeve_names = ["us_equity", "intl_equity", "bonds", "brazil_equity", "crypto", "cash"]
    sleeve_returns: dict[str, list[float]] = {s: [] for s in sleeve_names}
    dates: list[str] = []

    for i in range(1, len(snapshots)):
        prev_w = snapshots[i - 1].get("sleeve_weights") or {}
        curr_w = snapshots[i].get("sleeve_weights") or {}

        if isinstance(prev_w, list):
            prev_w = {w["sleeve"]: w.get("current_weight", 0) for w in prev_w if isinstance(w, dict)}
        if isinstance(curr_w, list):
            curr_w = {w["sleeve"]: w.get("current_weight", 0) for w in curr_w if isinstance(w, dict)}

        dates.append(snapshots[i]["snapshot_date"])
        for s in sleeve_names:
            prev = float(prev_w.get(s, 0) or 0)
            curr = float(curr_w.get(s, 0) or 0)
            ret = (curr / prev - 1) if prev > 0 else 0.0
            sleeve_returns[s].append(ret)

    # Compute rolling 90-day correlations for all pairs
    window = min(90, len(dates))
    pairs_data = []
    highest_pair: dict | None = None
    highest_corr = -2.0

    for s_a, s_b in combinations(sleeve_names, 2):
        arr_a = sleeve_returns[s_a]
        arr_b = sleeve_returns[s_b]

        if not arr_a or len(arr_a) < 10:
            continue

        history = []
        for i in range(window - 1, len(dates)):
            sub_a = arr_a[max(0, i - window + 1): i + 1]
            sub_b = arr_b[max(0, i - window + 1): i + 1]

            if len(sub_a) < 5:
                continue

            a_arr = np.array(sub_a)
            b_arr = np.array(sub_b)
            std_a = float(np.std(a_arr))
            std_b = float(np.std(b_arr))

            if std_a < 1e-10 or std_b < 1e-10:
                corr = 0.0
            else:
                corr = float(np.corrcoef(a_arr, b_arr)[0, 1])
                corr = max(-1.0, min(1.0, corr))

            history.append({"date": dates[i], "correlation": round(corr, 4)})

        current_corr = history[-1]["correlation"] if history else 0.0

        if current_corr > highest_corr:
            highest_corr = current_corr
            highest_pair = {"sleeves": [s_a, s_b], "current_correlation": current_corr}

        pairs_data.append({
            "sleeves": [s_a, s_b],
            "current_correlation": current_corr,
            "history": history[-52:],  # last 52 data points (~1 year of weekly data)
        })

    return {"pairs": pairs_data, "highest_pair": highest_pair}


@router.get("/performance/sparkline")
def performance_sparkline(
    user_id: str = Query(default=None),
    days: int = Query(default=30, ge=7, le=365),
) -> dict:
    """
    Return the last N daily portfolio values for sparkline display on dashboard.
    Fast — no computation, just raw snapshot values.
    """
    uid = _resolve_user(user_id)
    snapshots = get_snapshot_history(uid, days=days + 10)
    if not snapshots:
        return {"values": [], "dates": []}
    # Trim to requested days
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    filtered = [s for s in snapshots if s["snapshot_date"] >= cutoff]
    values = [float(s["total_value_usd"]) for s in filtered]
    dates  = [s["snapshot_date"] for s in filtered]
    return {"values": values, "dates": dates}
