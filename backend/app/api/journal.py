"""
Decision Journal API endpoints.

GET   /journal           — List decision entries with pagination
POST  /journal           — Create journal entry
GET   /journal/stats     — Override accuracy statistics
PATCH /journal/{id}/outcome — Update 30d/90d outcome (called by n8n)
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

import csv
import io

from app.db.repositories.journal import (
    create_journal_entry,
    get_journal_entries,
    get_override_accuracy_stats,
    update_outcome,
)
from app.services.journal_engine import (
    backfill_journal_outcomes,
    compute_journal_insight,
    compute_override_accuracy,
    detect_behavioral_patterns,
)

router = APIRouter()
logger = logging.getLogger(__name__)


class JournalEntryRequest(BaseModel):
    action_type: str                        # "followed" | "overrode" | "deferred" | "manual_trade"
    reasoning: str | None = None
    signal_run_id: str | None = None
    asset_id: str | None = None
    system_recommendation: dict | None = None
    actual_action: dict | None = None


class OutcomeUpdateRequest(BaseModel):
    outcome_30d: float | None = None
    outcome_90d: float | None = None


@router.get("/journal")
async def list_journal(
    user_id: str = Query(default=None),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    action_type: str | None = Query(default=None),
) -> list[dict]:
    """Return decision log entries newest first."""
    return get_journal_entries(
        user_id=user_id,
        limit=limit,
        offset=offset,
        action_type=action_type,
    )


@router.post("/journal", status_code=201)
async def create_entry(
    body: JournalEntryRequest,
    user_id: str = Query(default=None),
) -> dict:
    """Create a new decision journal entry."""
    valid_types = {"followed", "overrode", "deferred", "manual_trade"}
    if body.action_type not in valid_types:
        raise HTTPException(
            status_code=422,
            detail=f"action_type must be one of: {valid_types}",
        )
    try:
        return create_journal_entry(
            user_id=user_id,
            action_type=body.action_type,
            reasoning=body.reasoning,
            signal_run_id=body.signal_run_id,
            asset_id=body.asset_id,
            system_recommendation=body.system_recommendation,
            actual_action=body.actual_action,
        )
    except Exception as exc:
        logger.error("create_entry failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/journal/stats")
async def journal_stats(
    user_id: str = Query(default=None),
) -> dict:
    """
    Return override accuracy statistics.

    Includes: followed vs overrode counts, average 30d/90d outcomes per action type,
    and system outperformance delta.
    """
    return get_override_accuracy_stats(user_id)


@router.patch("/journal/{entry_id}/outcome")
async def patch_outcome(
    entry_id: str,
    body: OutcomeUpdateRequest,
) -> dict:
    """
    Backfill 30d and/or 90d outcome for a journal entry.

    Called by n8n journal_outcome_backfill workflow after 30/90 days.
    """
    if body.outcome_30d is None and body.outcome_90d is None:
        raise HTTPException(
            status_code=422,
            detail="Provide at least one of outcome_30d or outcome_90d.",
        )
    try:
        return update_outcome(
            entry_id=entry_id,
            outcome_30d=body.outcome_30d,
            outcome_90d=body.outcome_90d,
        )
    except Exception as exc:
        logger.error("patch_outcome failed entry=%s: %s", entry_id, exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/journal/patterns")
async def journal_patterns(
    user_id: str = Query(default=None),
) -> list[dict]:
    """
    Detect behavioral patterns in decision history.

    Requires ≥10 journal entries. Returns list of pattern dicts with
    pattern_type, description, severity, and supporting_data.
    """
    entries = get_journal_entries(user_id=user_id, limit=500)
    patterns = detect_behavioral_patterns(entries)
    return [
        {
            "pattern_type": p.pattern_type,
            "description": p.description,
            "severity": p.severity,
            "supporting_data": p.supporting_data,
        }
        for p in patterns
    ]


@router.get("/journal/insight")
async def journal_insight(
    user_id: str = Query(default=None),
) -> dict:
    """
    Generate (or return cached) AI behavioral insight for the user's journal.

    Uses Claude API. Result cached in Redis for 24 hours.
    """
    entries = get_journal_entries(user_id=user_id, limit=500)
    accuracy = compute_override_accuracy(entries)
    insight = compute_journal_insight(accuracy, user_id=user_id)
    return {
        "insight": insight,
        "has_enough_data": accuracy.has_enough_data,
        "followed_count": accuracy.followed_count,
        "overrode_count": accuracy.overrode_count,
        "system_outperformance_30d": accuracy.system_outperformance_delta_30d,
    }


@router.post("/journal/backfill", status_code=202)
async def trigger_backfill(
    background_tasks: BackgroundTasks,
    user_id: str = Query(default=None),
) -> dict:
    """
    Trigger outcome backfill for journal entries missing 30d/90d outcomes.

    Runs as a background task; returns immediately with count of entries queued.
    Backfill uses asset_valuations table for historical price lookups.
    """
    # Fetch entries that need backfill
    all_entries = get_journal_entries(user_id=user_id, limit=500)
    pending = [
        e for e in all_entries
        if e.get("asset_id") and (e.get("outcome_30d") is None or e.get("outcome_90d") is None)
    ]

    async def _run_backfill() -> None:
        try:
            from app.db.supabase_client import get_supabase_client
            client = get_supabase_client()
            updates = backfill_journal_outcomes(
                entries=pending,
                current_prices={},  # uses DB lookups internally
                db=client,
            )
            for upd in updates:
                update_outcome(
                    entry_id=upd.entry_id,
                    outcome_30d=upd.outcome_30d,
                    outcome_90d=upd.outcome_90d,
                )
            logger.info("Backfill complete: %d entries updated for user %s", len(updates), user_id)
        except Exception as exc:
            logger.error("Backfill failed for user %s: %s", user_id, exc)

    background_tasks.add_task(_run_backfill)
    return {
        "queued": len(pending),
        "message": f"{len(pending)} entries queued for outcome backfill",
    }


@router.get("/journal/export")
async def export_journal(
    user_id: str = Query(default=None),
    limit: int = Query(default=500, le=2000),
) -> StreamingResponse:
    """
    Export decision journal as CSV download.

    Returns CSV with columns: date, action_type, asset_id, reasoning,
    outcome_30d, outcome_90d.
    """
    entries = get_journal_entries(user_id=user_id, limit=limit)

    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=["event_date", "action_type", "asset_id", "reasoning", "outcome_30d", "outcome_90d"],
        extrasaction="ignore",
    )
    writer.writeheader()
    for e in entries:
        writer.writerow({
            "event_date": e.get("event_date", ""),
            "action_type": e.get("action_type", ""),
            "asset_id": e.get("asset_id", ""),
            "reasoning": e.get("reasoning", ""),
            "outcome_30d": e.get("outcome_30d", ""),
            "outcome_90d": e.get("outcome_90d", ""),
        })

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="journal_export.csv"'},
    )
