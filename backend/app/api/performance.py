"""
Performance API endpoints.

GET /performance/summary      — TWR, MWR, Sharpe, Sortino, Calmar, max drawdown
GET /performance/attribution  — Brinson-Hood-Beebower sleeve + asset attribution
GET /performance/benchmark    — Portfolio vs benchmark comparison
GET /performance/rolling      — Rolling 1mo/3mo/1yr returns

Phase 4 implementation — stub only.
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/performance/summary")
async def performance_summary(period: str = "ytd") -> dict:
    """Return portfolio performance metrics for the given period."""
    raise NotImplementedError("Phase 4")


@router.get("/performance/attribution")
async def performance_attribution(
    period_start: str | None = None,
    period_end: str | None = None,
) -> dict:
    """Return Brinson-Hood-Beebower attribution by sleeve and asset."""
    raise NotImplementedError("Phase 4")


@router.get("/performance/benchmark")
async def performance_vs_benchmark(
    benchmark: str = "SPY",
    period: str = "ytd",
) -> dict:
    """Return portfolio vs benchmark comparison."""
    raise NotImplementedError("Phase 4")


@router.get("/performance/rolling")
async def performance_rolling(windows: str = "1mo,3mo,1yr") -> dict:
    """Return rolling return data for the specified windows."""
    raise NotImplementedError("Phase 4")
