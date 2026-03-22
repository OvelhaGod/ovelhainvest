"""Repository: portfolio_snapshots table."""

from __future__ import annotations

import logging
from datetime import date, timedelta

from app.db.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


def upsert_portfolio_snapshot(snapshot: dict) -> dict:
    """
    Upsert a portfolio snapshot (insert or update on user_id + snapshot_date).

    Args:
        snapshot: Dict matching portfolio_snapshots schema. Must include user_id, snapshot_date,
                  total_value_usd.

    Returns:
        Upserted snapshot dict.
    """
    try:
        client = get_supabase_client()
        resp = (
            client.table("portfolio_snapshots")
            .upsert(snapshot, on_conflict="user_id,snapshot_date")
            .execute()
        )
        data = resp.data
        return data[0] if data else snapshot
    except Exception as exc:
        logger.error("upsert_portfolio_snapshot failed: %s", exc)
        raise


def get_snapshot_history(user_id: str, days: int = 365) -> list[dict]:
    """
    Fetch portfolio snapshot history for a user.

    Args:
        user_id: UUID string.
        days: Number of days of history (default 365).

    Returns:
        List of snapshot dicts ordered by date ascending.
    """
    try:
        cutoff = (date.today() - timedelta(days=days)).isoformat()
        client = get_supabase_client()
        resp = (
            client.table("portfolio_snapshots")
            .select("*")
            .eq("user_id", user_id)
            .gte("snapshot_date", cutoff)
            .order("snapshot_date")
            .execute()
        )
        return resp.data or []
    except Exception as exc:
        logger.error("get_snapshot_history failed for user %s: %s", user_id, exc)
        raise


def get_latest_snapshot(user_id: str) -> dict | None:
    """
    Fetch the most recent portfolio snapshot for a user.

    Args:
        user_id: UUID string.

    Returns:
        Most recent snapshot dict, or None if no snapshots exist.
    """
    try:
        client = get_supabase_client()
        resp = (
            client.table("portfolio_snapshots")
            .select("*")
            .eq("user_id", user_id)
            .order("snapshot_date", desc=True)
            .limit(1)
            .execute()
        )
        data = resp.data
        return data[0] if data else None
    except Exception as exc:
        logger.error("get_latest_snapshot failed for user %s: %s", user_id, exc)
        return None


def get_snapshot_for_date(user_id: str, snapshot_date: date) -> dict | None:
    """
    Fetch a specific snapshot by date.

    Args:
        user_id: UUID string.
        snapshot_date: Date to look up.

    Returns:
        Snapshot dict or None.
    """
    try:
        client = get_supabase_client()
        resp = (
            client.table("portfolio_snapshots")
            .select("*")
            .eq("user_id", user_id)
            .eq("snapshot_date", snapshot_date.isoformat())
            .limit(1)
            .execute()
        )
        data = resp.data
        return data[0] if data else None
    except Exception as exc:
        logger.error("get_snapshot_for_date failed for user %s, date %s: %s", user_id, snapshot_date, exc)
        return None
