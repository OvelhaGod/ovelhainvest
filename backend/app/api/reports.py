"""
Reports API endpoints — Phase 9.

POST /reports/generate              — Trigger PDF generation (async background task)
GET  /reports/list                  — List generated reports
GET  /reports/download/{report_id}  — Download a PDF by ID
GET  /reports/result/{task_id}      — Poll async task status
"""

from __future__ import annotations

import logging
import uuid
from datetime import date, datetime, timezone
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel

from app.db.supabase_client import get_supabase_client
from app.services.report_builder import generate_monthly_report

router = APIRouter()
logger = logging.getLogger(__name__)

# In-memory task tracker (process-local; fine for single-user app)
_TASKS: dict[str, dict[str, Any]] = {}

from app.config import get_default_user_id as _get_default_user_id
DEFAULT_USER = _get_default_user_id()


# ── Request / response models ──────────────────────────────────────────────

class GenerateReportRequest(BaseModel):
    report_type: str = "monthly"      # "monthly" | "annual"
    year: int | None = None           # defaults to current year
    month: int | None = None          # defaults to current month (monthly only)
    user_id: str = DEFAULT_USER


class ReportRecord(BaseModel):
    id: str
    report_type: str
    year: int
    month: int | None
    status: str                        # "pending" | "generating" | "ready" | "error"
    size_bytes: int | None = None
    created_at: str
    download_url: str | None = None


# ── Repository helpers ─────────────────────────────────────────────────────

def _insert_report_record(
    user_id: str,
    report_type: str,
    year: int,
    month: int | None,
    task_id: str,
) -> str:
    """Insert a reports_history row and return its UUID."""
    record: dict[str, Any] = {
        "id": task_id,
        "user_id": user_id,
        "report_type": report_type,
        "year": year,
        "month": month,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        client = get_supabase_client()
        client.table("reports_history").insert(record).execute()
    except Exception as exc:
        logger.warning("Could not insert reports_history row: %s", exc)
    return task_id


def _update_report_record(
    report_id: str,
    status: str,
    pdf_bytes: bytes | None = None,
    error_msg: str | None = None,
) -> None:
    """Update reports_history row with final status + size."""
    updates: dict[str, Any] = {"status": status}
    if pdf_bytes is not None:
        updates["size_bytes"] = len(pdf_bytes)
    if error_msg:
        updates["error_message"] = error_msg[:500]
    try:
        client = get_supabase_client()
        client.table("reports_history").update(updates).eq("id", report_id).execute()
    except Exception as exc:
        logger.warning("Could not update reports_history row %s: %s", report_id, exc)


def _list_report_records(user_id: str, limit: int = 50) -> list[dict]:
    """Fetch reports_history rows for user, newest first."""
    try:
        client = get_supabase_client()
        resp = (
            client.table("reports_history")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return resp.data or []
    except Exception as exc:
        logger.error("_list_report_records failed: %s", exc)
        return []


def _get_report_record(report_id: str) -> dict | None:
    """Fetch a single reports_history row."""
    try:
        client = get_supabase_client()
        resp = (
            client.table("reports_history")
            .select("*")
            .eq("id", report_id)
            .limit(1)
            .execute()
        )
        return resp.data[0] if resp.data else None
    except Exception as exc:
        logger.error("_get_report_record failed %s: %s", report_id, exc)
        return None


# ── Background task ────────────────────────────────────────────────────────

def _gather_report_data(user_id: str, year: int, month: int) -> dict[str, Any]:
    """
    Fetch all data needed to build a monthly report.
    Returns dict with daily_status, signals_runs, performance, journal, tax, ai_summaries.
    Errors are caught per-section and replaced with empty defaults.
    """
    client = get_supabase_client()
    data: dict[str, Any] = {
        "daily_status": {},
        "signals_runs": [],
        "performance": {},
        "journal_entries": [],
        "tax_summary": {},
        "ai_summaries": [],
    }

    # signals_runs for this month
    try:
        from datetime import date as _date

        month_start = _date(year, month, 1).isoformat()
        import calendar as _cal
        last_day = _cal.monthrange(year, month)[1]
        month_end = _date(year, month, last_day).isoformat()
        resp = (
            client.table("signals_runs")
            .select("*")
            .eq("user_id", user_id)
            .gte("run_timestamp", month_start)
            .lte("run_timestamp", month_end + "T23:59:59")
            .order("run_timestamp", desc=True)
            .execute()
        )
        runs = resp.data or []
        data["signals_runs"] = runs
        for run in runs:
            ai_val = run.get("ai_validation_summary") or {}
            summary = ""
            if isinstance(ai_val, dict):
                summary = (
                    ai_val.get("explanation_for_user", {}).get("short_summary", "")
                    or ai_val.get("short_summary", "")
                )
            if summary:
                data["ai_summaries"].append(summary)
    except Exception as exc:
        logger.warning("Could not fetch signals_runs for report: %s", exc)

    # Latest portfolio snapshot → daily_status proxy
    try:
        resp = (
            client.table("portfolio_snapshots")
            .select("*")
            .eq("user_id", user_id)
            .order("snapshot_date", desc=True)
            .limit(1)
            .execute()
        )
        if resp.data:
            snap = resp.data[0]
            data["daily_status"] = {
                "total_value_usd": snap.get("total_value_usd", 0.0),
                "sleeve_weights": snap.get("sleeve_weights", {}),
                "regime_state": "normal",
                "ytd_return_twr": snap.get("portfolio_return_ytd"),
            }
            data["performance"] = {
                "twr_ytd": snap.get("portfolio_return_ytd"),
                "twr_1mo": snap.get("portfolio_return_twr"),
                "benchmark_ytd": snap.get("benchmark_return"),
                "sharpe_ratio": snap.get("sharpe_ratio"),
                "sortino_ratio": snap.get("sortino_ratio"),
                "calmar_ratio": snap.get("calmar_ratio"),
                "max_drawdown_pct": snap.get("drawdown_from_peak_pct"),
            }
    except Exception as exc:
        logger.warning("Could not fetch portfolio_snapshots for report: %s", exc)

    # Journal entries this month
    try:
        resp = (
            client.table("decision_journal")
            .select("*")
            .eq("user_id", user_id)
            .gte("event_date", month_start)
            .lte("event_date", month_end + "T23:59:59")
            .order("event_date", desc=True)
            .execute()
        )
        data["journal_entries"] = resp.data or []
    except Exception as exc:
        logger.warning("Could not fetch journal_entries for report: %s", exc)

    return data


async def _generate_report_task(
    task_id: str,
    user_id: str,
    report_type: str,
    year: int,
    month: int,
) -> None:
    """Background task: build PDF, store bytes in task dict + update DB record."""
    _TASKS[task_id]["status"] = "generating"
    _update_report_record(task_id, "generating")

    try:
        report_data = _gather_report_data(user_id, year, month)
        pdf_bytes = generate_monthly_report(
            year=year,
            month=month,
            daily_status=report_data["daily_status"],
            signals_runs=report_data["signals_runs"],
            performance=report_data["performance"],
            journal_entries=report_data["journal_entries"],
            tax_summary=report_data["tax_summary"],
            ai_summaries=report_data["ai_summaries"],
        )
        _TASKS[task_id]["status"] = "ready"
        _TASKS[task_id]["pdf_bytes"] = pdf_bytes
        _TASKS[task_id]["size_bytes"] = len(pdf_bytes)
        _update_report_record(task_id, "ready", pdf_bytes=pdf_bytes)
        logger.info(
            "Report %s generated: %d bytes (%s/%s)",
            task_id, len(pdf_bytes), month, year,
        )
    except Exception as exc:
        logger.error("Report generation failed for task %s: %s", task_id, exc)
        _TASKS[task_id]["status"] = "error"
        _TASKS[task_id]["error"] = str(exc)
        _update_report_record(task_id, "error", error_msg=str(exc))


# ── Endpoints ──────────────────────────────────────────────────────────────

@router.post("/reports/generate", status_code=202)
async def generate_report(
    body: GenerateReportRequest,
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    """
    Trigger PDF report generation as a background task.

    Returns a task_id immediately. Poll GET /reports/result/{task_id} for status,
    or download directly via GET /reports/download/{task_id} once ready.
    """
    now = datetime.now(timezone.utc)
    year = body.year or now.year
    month = body.month or now.month

    if not 1 <= month <= 12:
        raise HTTPException(status_code=422, detail="month must be 1-12")
    if year < 2020 or year > now.year + 1:
        raise HTTPException(status_code=422, detail=f"year out of range: {year}")

    task_id = str(uuid.uuid4())
    _TASKS[task_id] = {"status": "pending", "year": year, "month": month}

    _insert_report_record(
        user_id=body.user_id,
        report_type=body.report_type,
        year=year,
        month=month if body.report_type == "monthly" else None,
        task_id=task_id,
    )

    background_tasks.add_task(
        _generate_report_task,
        task_id=task_id,
        user_id=body.user_id,
        report_type=body.report_type,
        year=year,
        month=month,
    )

    return {
        "task_id": task_id,
        "status": "pending",
        "report_type": body.report_type,
        "year": year,
        "month": month,
        "download_url": f"/reports/download/{task_id}",
        "poll_url": f"/reports/result/{task_id}",
    }


@router.get("/reports/list")
async def list_reports(
    user_id: str = Query(default=DEFAULT_USER),
    limit: int = Query(default=20, le=100),
) -> list[dict]:
    """
    Return list of generated reports for the user, newest first.

    Each record includes status, size_bytes, and a download_url when ready.
    """
    records = _list_report_records(user_id=user_id, limit=limit)
    # Merge in-memory task status for very recent tasks not yet in DB
    for rec in records:
        tid = rec.get("id")
        if tid and tid in _TASKS:
            rec["status"] = _TASKS[tid].get("status", rec.get("status"))
            rec["size_bytes"] = _TASKS[tid].get("size_bytes", rec.get("size_bytes"))
        rec["download_url"] = (
            f"/reports/download/{rec['id']}" if rec.get("status") == "ready" else None
        )
    return records


@router.get("/reports/result/{task_id}")
async def get_report_result(task_id: str) -> dict[str, Any]:
    """
    Poll the status of a report generation task.

    Returns status: pending | generating | ready | error.
    When ready, includes a download_url.
    """
    # Check in-memory first (fastest path)
    if task_id in _TASKS:
        task = _TASKS[task_id]
        return {
            "task_id": task_id,
            "status": task.get("status", "pending"),
            "size_bytes": task.get("size_bytes"),
            "error": task.get("error"),
            "download_url": f"/reports/download/{task_id}" if task.get("status") == "ready" else None,
        }

    # Fall back to DB
    rec = _get_report_record(task_id)
    if not rec:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    return {
        "task_id": task_id,
        "status": rec.get("status", "unknown"),
        "size_bytes": rec.get("size_bytes"),
        "download_url": f"/reports/download/{task_id}" if rec.get("status") == "ready" else None,
    }


@router.get("/reports/download/{report_id}")
async def download_report(report_id: str) -> Response:
    """
    Download a generated PDF report by its task/report ID.

    Returns PDF bytes with Content-Disposition: attachment.
    Returns 404 if not found or not yet ready.
    """
    task = _TASKS.get(report_id)
    if task and task.get("status") == "ready" and task.get("pdf_bytes"):
        pdf_bytes: bytes = task["pdf_bytes"]
        year = task.get("year", "")
        month = task.get("month", "")
        filename = f"ovelhainvest_report_{year}_{month:02d}.pdf" if month else f"ovelhainvest_report_{year}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    # Task not in memory — check DB for metadata (PDF bytes not persisted in DB by default)
    rec = _get_report_record(report_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Report not found")
    if rec.get("status") != "ready":
        raise HTTPException(
            status_code=404,
            detail=f"Report not ready. Current status: {rec.get('status', 'unknown')}",
        )
    # Bytes lost after restart — re-generate
    raise HTTPException(
        status_code=410,
        detail="Report was generated but PDF bytes are no longer cached. Re-generate via POST /reports/generate.",
    )
