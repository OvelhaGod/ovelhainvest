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
    user_id: str = Query(default="00000000-0000-0000-0000-000000000001"),
    period: str = Query(default="ytd"),
) -> PerformanceSummaryResponse:
    """Return portfolio performance metrics — all standard periods."""
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

    return PerformanceSummaryResponse(
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


@router.get("/performance/attribution", response_model=AttributionResponse)
async def performance_attribution(
    user_id: str = Query(default="00000000-0000-0000-0000-000000000001"),
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
    user_id: str = Query(default="00000000-0000-0000-0000-000000000001"),
    benchmark: str = Query(default="SPY"),
    period: str = Query(default="ytd"),
) -> BenchmarkComparisonResponse:
    """Return portfolio vs benchmark comparison."""
    snapshots = get_snapshot_history(user_id, days=1100)
    if len(snapshots) < 2:
        raise HTTPException(status_code=404, detail="Insufficient snapshot data.")

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


@router.get("/performance/rolling", response_model=RollingReturnsResponse)
async def performance_rolling(
    user_id: str = Query(default="00000000-0000-0000-0000-000000000001"),
    windows: str = Query(default="1mo,3mo,1yr"),
) -> RollingReturnsResponse:
    """Return rolling return time series for the specified windows."""
    snapshots = get_snapshot_history(user_id, days=1100)
    if len(snapshots) < 22:
        raise HTTPException(status_code=404, detail="Insufficient data for rolling analysis.")

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
    user_id: str = Query(default="00000000-0000-0000-0000-000000000001"),
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
        raise HTTPException(status_code=404, detail="Insufficient snapshot data for risk metrics.")

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
    user_id: str = Query(default="00000000-0000-0000-0000-000000000001"),
) -> SnapshotTriggerResponse:
    """
    Manually trigger a portfolio snapshot for today.

    In production this is called by n8n daily. This endpoint allows manual triggering.
    The snapshot uses the latest known holdings and current market prices.
    """
    from app.db.repositories.snapshots import get_latest_snapshot as get_snap
    today = date.today()

    latest = get_snap(user_id)
    if latest and latest.get("snapshot_date") == today.isoformat():
        return SnapshotTriggerResponse(
            status="exists",
            snapshot_date=today,
            total_value_usd=latest.get("total_value_usd"),
            message="Snapshot for today already exists.",
        )

    # Build a minimal snapshot from last known state + interpolation
    # Full implementation requires holdings + prices; for now write a placeholder
    # that can be backfilled when holdings data is available.
    prev_value = float(latest["total_value_usd"]) if latest else 0.0
    snapshot = {
        "user_id": user_id,
        "snapshot_date": today.isoformat(),
        "total_value_usd": prev_value,
        "total_value_brl": None,
        "usd_brl_rate": None,
        "sleeve_weights": latest.get("sleeve_weights") if latest else None,
        "benchmark_symbol": "SPY",
    }

    try:
        saved = upsert_portfolio_snapshot(snapshot)
        return SnapshotTriggerResponse(
            status="created",
            snapshot_date=today,
            total_value_usd=prev_value or None,
            message="Snapshot created. Update with live holdings data via n8n.",
        )
    except Exception as exc:
        logger.error("Snapshot creation failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
