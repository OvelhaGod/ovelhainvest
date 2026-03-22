"""
Simulation API endpoints.

POST /simulation/monte_carlo            — N=5000 Monte Carlo projection
POST /simulation/stress_test            — Historical stress scenario impact
POST /simulation/contribution_optimizer — Optimal account + asset routing for new money
POST /simulation/rebalance_preview      — Before/after rebalance without executing

Heavy simulation runs dispatched as background tasks — never block response.

Phase 7 implementation — stub only.
"""

from fastapi import APIRouter, BackgroundTasks

router = APIRouter()


@router.post("/simulation/monte_carlo")
async def run_monte_carlo(
    body: dict,
    background_tasks: BackgroundTasks,
) -> dict:
    """
    Trigger Monte Carlo projection (async background task).
    Returns run_id; results polled via GET /simulation/monte_carlo/{run_id}.
    """
    raise NotImplementedError("Phase 7")


@router.get("/simulation/monte_carlo/{run_id}")
async def get_monte_carlo_result(run_id: str) -> dict:
    """Return completed Monte Carlo result by run ID."""
    raise NotImplementedError("Phase 7")


@router.post("/simulation/stress_test")
async def run_stress_test(body: dict) -> dict:
    """Apply a historical stress scenario to the current portfolio."""
    raise NotImplementedError("Phase 7")


@router.post("/simulation/contribution_optimizer")
async def contribution_optimizer(body: dict) -> dict:
    """Given $X, return optimal account + asset routing."""
    raise NotImplementedError("Phase 7")


@router.post("/simulation/rebalance_preview")
async def rebalance_preview(body: dict) -> dict:
    """Show before/after portfolio state for a proposed rebalance."""
    raise NotImplementedError("Phase 7")
