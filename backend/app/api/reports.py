"""
Reports API endpoints.

POST /reports/generate  — Generate PDF report (daily/monthly/annual)
GET  /reports/list      — List generated reports

Phase 9 implementation — stub only.
"""

from fastapi import APIRouter, BackgroundTasks

router = APIRouter()


@router.post("/reports/generate")
async def generate_report(
    body: dict,
    background_tasks: BackgroundTasks,
) -> dict:
    """
    Trigger PDF report generation (dispatched as background task).
    Returns report_id; download via GET /reports/{report_id}.
    """
    raise NotImplementedError("Phase 9")


@router.get("/reports/list")
async def list_reports() -> list:
    """Return list of generated reports with download URLs."""
    raise NotImplementedError("Phase 9")


@router.get("/reports/{report_id}")
async def get_report(report_id: str):
    """Download a generated PDF report."""
    raise NotImplementedError("Phase 9")
