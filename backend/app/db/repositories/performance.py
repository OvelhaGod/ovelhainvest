"""Repository: performance_attribution, risk_metrics, portfolio_snapshots (extended)."""

from __future__ import annotations

import logging
from datetime import date, timedelta

from app.db.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


# ── Performance Attribution ──────────────────────────────────────────────────

def upsert_performance_attribution(attribution: dict) -> dict:
    """
    Upsert a performance attribution record.

    Args:
        attribution: Dict matching performance_attribution schema.
                     Must include user_id, period_start, period_end.

    Returns:
        Upserted record dict.
    """
    try:
        client = get_supabase_client()
        resp = (
            client.table("performance_attribution")
            .upsert(attribution, on_conflict="user_id,period_start,period_end")
            .execute()
        )
        data = resp.data
        return data[0] if data else attribution
    except Exception as exc:
        logger.error("upsert_performance_attribution failed: %s", exc)
        raise


def get_attribution_for_period(
    user_id: str,
    period_start: date,
    period_end: date,
) -> dict | None:
    """
    Fetch performance attribution for a specific period.

    Args:
        user_id: UUID string.
        period_start: Start date.
        period_end: End date.

    Returns:
        Attribution dict or None.
    """
    try:
        client = get_supabase_client()
        resp = (
            client.table("performance_attribution")
            .select("*")
            .eq("user_id", user_id)
            .eq("period_start", period_start.isoformat())
            .eq("period_end", period_end.isoformat())
            .limit(1)
            .execute()
        )
        data = resp.data
        return data[0] if data else None
    except Exception as exc:
        logger.error("get_attribution_for_period failed: %s", exc)
        return None


def get_attribution_history(user_id: str, limit: int = 12) -> list[dict]:
    """
    Fetch recent performance attribution records.

    Args:
        user_id: UUID string.
        limit: Max records to return.

    Returns:
        List of attribution dicts ordered by period_end descending.
    """
    try:
        client = get_supabase_client()
        resp = (
            client.table("performance_attribution")
            .select("*")
            .eq("user_id", user_id)
            .order("period_end", desc=True)
            .limit(limit)
            .execute()
        )
        return resp.data or []
    except Exception as exc:
        logger.error("get_attribution_history failed for user %s: %s", user_id, exc)
        return []


# ── Risk Metrics ─────────────────────────────────────────────────────────────

def upsert_risk_metrics(metrics: dict) -> dict:
    """
    Upsert a risk_metrics record for a given date.

    Args:
        metrics: Dict matching risk_metrics schema.
                 Must include user_id, as_of_date.

    Returns:
        Upserted record dict.
    """
    try:
        client = get_supabase_client()
        resp = (
            client.table("risk_metrics")
            .upsert(metrics, on_conflict="user_id,as_of_date")
            .execute()
        )
        data = resp.data
        return data[0] if data else metrics
    except Exception as exc:
        logger.error("upsert_risk_metrics failed: %s", exc)
        raise


def get_risk_metrics_latest(user_id: str) -> dict | None:
    """
    Fetch the most recent risk metrics record for a user.

    Args:
        user_id: UUID string.

    Returns:
        Most recent risk_metrics dict or None.
    """
    try:
        client = get_supabase_client()
        resp = (
            client.table("risk_metrics")
            .select("*")
            .eq("user_id", user_id)
            .order("as_of_date", desc=True)
            .limit(1)
            .execute()
        )
        data = resp.data
        return data[0] if data else None
    except Exception as exc:
        logger.error("get_risk_metrics_latest failed for user %s: %s", user_id, exc)
        return None


def get_risk_metrics_history(user_id: str, days: int = 365) -> list[dict]:
    """
    Fetch risk metrics history.

    Args:
        user_id: UUID string.
        days: Lookback in days.

    Returns:
        List of risk_metrics dicts ordered by as_of_date ascending.
    """
    try:
        cutoff = (date.today() - timedelta(days=days)).isoformat()
        client = get_supabase_client()
        resp = (
            client.table("risk_metrics")
            .select("*")
            .eq("user_id", user_id)
            .gte("as_of_date", cutoff)
            .order("as_of_date")
            .execute()
        )
        return resp.data or []
    except Exception as exc:
        logger.error("get_risk_metrics_history failed for user %s: %s", user_id, exc)
        return []


# ── Snapshots (extended) ─────────────────────────────────────────────────────

def get_snapshots(
    user_id: str,
    start_date: date,
    end_date: date,
) -> list[dict]:
    """
    Fetch portfolio snapshots for a date range.

    Args:
        user_id: UUID string.
        start_date: Inclusive start date.
        end_date: Inclusive end date.

    Returns:
        List of snapshot dicts ordered by snapshot_date ascending.
    """
    try:
        client = get_supabase_client()
        resp = (
            client.table("portfolio_snapshots")
            .select("*")
            .eq("user_id", user_id)
            .gte("snapshot_date", start_date.isoformat())
            .lte("snapshot_date", end_date.isoformat())
            .order("snapshot_date")
            .execute()
        )
        return resp.data or []
    except Exception as exc:
        logger.error("get_snapshots failed for user %s: %s", user_id, exc)
        return []
