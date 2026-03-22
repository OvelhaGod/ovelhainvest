"""Repository: signals_runs table."""

from __future__ import annotations

import logging
from datetime import datetime

from app.db.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


def create_signals_run(run: dict) -> dict:
    """
    Insert a new signals run record.

    Args:
        run: Dict with user_id, event_type, inputs_summary, proposed_trades,
             ai_validation_summary, status, notes.

    Returns:
        Created signals_run dict with generated id and run_timestamp.
    """
    try:
        client = get_supabase_client()
        resp = client.table("signals_runs").insert(run).execute()
        data = resp.data
        return data[0] if data else run
    except Exception as exc:
        logger.error("create_signals_run failed: %s", exc)
        raise


def update_signals_run_status(
    run_id: str,
    status: str,
    notes: str | None = None,
    ai_validation_summary: dict | None = None,
) -> dict:
    """
    Update the status (and optionally AI summary) of a signals run.

    Args:
        run_id: UUID of the signals run.
        status: New status — "auto_ok", "needs_approval", "executed", "ignored".
        notes: Optional text notes.
        ai_validation_summary: Optional AI validation result to store.

    Returns:
        Updated signals_run dict.
    """
    try:
        client = get_supabase_client()
        update_data: dict = {"status": status}
        if notes is not None:
            update_data["notes"] = notes
        if ai_validation_summary is not None:
            update_data["ai_validation_summary"] = ai_validation_summary

        resp = (
            client.table("signals_runs")
            .update(update_data)
            .eq("id", run_id)
            .execute()
        )
        data = resp.data
        return data[0] if data else {"id": run_id, "status": status}
    except Exception as exc:
        logger.error("update_signals_run_status failed for %s: %s", run_id, exc)
        raise


def get_recent_runs(user_id: str, limit: int = 20) -> list[dict]:
    """
    Fetch recent signals runs for a user, newest first.

    Args:
        user_id: UUID string.
        limit: Max number of records (default 20).

    Returns:
        List of signals_run dicts.
    """
    try:
        client = get_supabase_client()
        resp = (
            client.table("signals_runs")
            .select("*")
            .eq("user_id", user_id)
            .order("run_timestamp", desc=True)
            .limit(limit)
            .execute()
        )
        return resp.data or []
    except Exception as exc:
        logger.error("get_recent_runs failed for user %s: %s", user_id, exc)
        raise


def get_pending_approvals(user_id: str) -> list[dict]:
    """
    Fetch signals runs that need user approval.

    Args:
        user_id: UUID string.

    Returns:
        List of signals_run dicts with status "needs_approval".
    """
    try:
        client = get_supabase_client()
        resp = (
            client.table("signals_runs")
            .select("*")
            .eq("user_id", user_id)
            .eq("status", "needs_approval")
            .order("run_timestamp", desc=True)
            .execute()
        )
        return resp.data or []
    except Exception as exc:
        logger.error("get_pending_approvals failed for user %s: %s", user_id, exc)
        raise


def get_last_run_timestamp(user_id: str) -> datetime | None:
    """
    Get the timestamp of the most recent signals run for a user.

    Args:
        user_id: UUID string.

    Returns:
        Datetime of last run, or None if no runs exist.
    """
    try:
        client = get_supabase_client()
        resp = (
            client.table("signals_runs")
            .select("run_timestamp")
            .eq("user_id", user_id)
            .order("run_timestamp", desc=True)
            .limit(1)
            .execute()
        )
        data = resp.data
        if data:
            ts = data[0].get("run_timestamp")
            if ts:
                return datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return None
    except Exception as exc:
        logger.error("get_last_run_timestamp failed for user %s: %s", user_id, exc)
        return None
