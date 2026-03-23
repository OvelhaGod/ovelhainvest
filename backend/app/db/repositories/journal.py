"""Repository: decision_journal table."""

from __future__ import annotations

import logging
from typing import Any

from app.db.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


def create_journal_entry(
    user_id: str,
    action_type: str,
    reasoning: str | None = None,
    signal_run_id: str | None = None,
    asset_id: str | None = None,
    system_recommendation: dict[str, Any] | None = None,
    actual_action: dict[str, Any] | None = None,
) -> dict:
    """
    Create a decision journal entry.

    Args:
        user_id: UUID string.
        action_type: "followed" | "overrode" | "deferred" | "manual_trade"
        reasoning: Free-text explanation of why you followed/overrode.
        signal_run_id: Linked signals_runs UUID if applicable.
        asset_id: Asset UUID if action is asset-specific.
        system_recommendation: What the engine recommended (JSON).
        actual_action: What you actually did (JSON).

    Returns:
        Created journal entry dict.
    """
    record: dict[str, Any] = {
        "user_id": user_id,
        "action_type": action_type,
        "reasoning": reasoning,
    }
    if signal_run_id:
        record["signal_run_id"] = signal_run_id
    if asset_id:
        record["asset_id"] = asset_id
    if system_recommendation:
        record["system_recommendation"] = system_recommendation
    if actual_action:
        record["actual_action"] = actual_action

    try:
        client = get_supabase_client()
        resp = client.table("decision_journal").insert(record).execute()
        return resp.data[0] if resp.data else record
    except Exception as exc:
        logger.error("create_journal_entry failed: %s", exc)
        raise


def get_journal_entries(
    user_id: str,
    limit: int = 50,
    offset: int = 0,
    action_type: str | None = None,
) -> list[dict]:
    """
    Fetch decision journal entries, newest first.

    Args:
        user_id: UUID string.
        limit: Max entries to return.
        offset: Pagination offset.
        action_type: Optional filter ("followed"|"overrode"|"deferred"|"manual_trade").

    Returns:
        List of journal entry dicts.
    """
    try:
        client = get_supabase_client()
        query = (
            client.table("decision_journal")
            .select("*")
            .eq("user_id", user_id)
            .order("event_date", desc=True)
            .range(offset, offset + limit - 1)
        )
        if action_type:
            query = query.eq("action_type", action_type)
        resp = query.execute()
        return resp.data or []
    except Exception as exc:
        logger.error("get_journal_entries failed for user %s: %s", user_id, exc)
        return []


def update_outcome(
    entry_id: str,
    outcome_30d: float | None = None,
    outcome_90d: float | None = None,
) -> dict:
    """
    Backfill 30-day and/or 90-day outcome for a journal entry.

    Called by n8n journal_outcome_backfill workflow.

    Args:
        entry_id: Journal entry UUID.
        outcome_30d: Return of asset/portfolio 30 days after decision.
        outcome_90d: Return of asset/portfolio 90 days after decision.

    Returns:
        Updated journal entry dict.
    """
    updates: dict[str, Any] = {}
    if outcome_30d is not None:
        updates["outcome_30d"] = outcome_30d
    if outcome_90d is not None:
        updates["outcome_90d"] = outcome_90d
    if not updates:
        raise ValueError("At least one outcome must be provided")

    try:
        client = get_supabase_client()
        resp = (
            client.table("decision_journal")
            .update(updates)
            .eq("id", entry_id)
            .execute()
        )
        return resp.data[0] if resp.data else {"id": entry_id, **updates}
    except Exception as exc:
        logger.error("update_outcome failed for entry %s: %s", entry_id, exc)
        raise


def get_override_accuracy_stats(user_id: str) -> dict[str, Any]:
    """
    Compute override accuracy statistics for the user.

    Returns counts and average outcomes split by action_type.
    Used to power the journal page scorecard.

    Args:
        user_id: UUID string.

    Returns:
        Dict with counts, averages, and system vs override performance comparison.
    """
    try:
        entries = get_journal_entries(user_id, limit=500)
    except Exception as exc:
        logger.error("get_override_accuracy_stats failed: %s", exc)
        return _empty_stats()

    if not entries:
        return _empty_stats()

    counts: dict[str, int] = {"followed": 0, "overrode": 0, "deferred": 0, "manual_trade": 0}
    outcomes_30d: dict[str, list[float]] = {"followed": [], "overrode": [], "deferred": []}
    outcomes_90d: dict[str, list[float]] = {"followed": [], "overrode": [], "deferred": []}

    for e in entries:
        at = e.get("action_type", "")
        if at in counts:
            counts[at] += 1
        if at in outcomes_30d:
            if e.get("outcome_30d") is not None:
                outcomes_30d[at].append(float(e["outcome_30d"]))
            if e.get("outcome_90d") is not None:
                outcomes_90d[at].append(float(e["outcome_90d"]))

    def _avg(lst: list[float]) -> float | None:
        return round(sum(lst) / len(lst), 4) if lst else None

    avg_f30 = _avg(outcomes_30d["followed"])
    avg_o30 = _avg(outcomes_30d["overrode"])
    avg_f90 = _avg(outcomes_90d["followed"])
    avg_o90 = _avg(outcomes_90d["overrode"])

    system_out_30 = (
        round(avg_f30 - avg_o30, 4)
        if avg_f30 is not None and avg_o30 is not None
        else None
    )
    system_out_90 = (
        round(avg_f90 - avg_o90, 4)
        if avg_f90 is not None and avg_o90 is not None
        else None
    )

    return {
        "followed_count": counts["followed"],
        "overrode_count": counts["overrode"],
        "deferred_count": counts["deferred"],
        "manual_count": counts["manual_trade"],
        "total_decisions": sum(counts.values()),
        "avg_outcome_followed_30d": avg_f30,
        "avg_outcome_overrode_30d": avg_o30,
        "avg_outcome_followed_90d": avg_f90,
        "avg_outcome_overrode_90d": avg_o90,
        "system_outperformance_30d": system_out_30,
        "system_outperformance_90d": system_out_90,
    }


def _empty_stats() -> dict[str, Any]:
    return {
        "followed_count": 0,
        "overrode_count": 0,
        "deferred_count": 0,
        "manual_count": 0,
        "total_decisions": 0,
        "avg_outcome_followed_30d": None,
        "avg_outcome_overrode_30d": None,
        "avg_outcome_followed_90d": None,
        "avg_outcome_overrode_90d": None,
        "system_outperformance_30d": None,
        "system_outperformance_90d": None,
    }
