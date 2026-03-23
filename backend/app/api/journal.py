"""
Decision Journal API endpoints.

GET   /journal           — List decision entries with pagination
POST  /journal           — Create journal entry
GET   /journal/stats     — Override accuracy statistics
PATCH /journal/{id}/outcome — Update 30d/90d outcome (called by n8n)
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.db.repositories.journal import (
    create_journal_entry,
    get_journal_entries,
    get_override_accuracy_stats,
    update_outcome,
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
    user_id: str = Query(default="00000000-0000-0000-0000-000000000001"),
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
    user_id: str = Query(default="00000000-0000-0000-0000-000000000001"),
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
    user_id: str = Query(default="00000000-0000-0000-0000-000000000001"),
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
