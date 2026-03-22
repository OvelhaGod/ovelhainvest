"""Repository: asset_valuations table."""

from __future__ import annotations

import logging
from datetime import date

from app.db.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


def upsert_asset_valuation(valuation: dict) -> dict:
    """
    Upsert an asset valuation (insert or update on asset_id + as_of_date).

    Args:
        valuation: Dict matching asset_valuations schema.

    Returns:
        Upserted valuation dict.
    """
    try:
        client = get_supabase_client()
        resp = (
            client.table("asset_valuations")
            .upsert(valuation, on_conflict="asset_id,as_of_date")
            .execute()
        )
        data = resp.data
        return data[0] if data else valuation
    except Exception as exc:
        logger.error("upsert_asset_valuation failed: %s", exc)
        raise


def get_latest_valuations() -> list[dict]:
    """
    Fetch the most recent valuation for each active asset.
    Uses a subquery approach via distinct on asset_id ordered by date.

    Returns:
        List of valuation dicts, one per asset (most recent).
    """
    try:
        client = get_supabase_client()
        # Fetch all active assets first, then latest valuation per asset
        assets_resp = (
            client.table("assets")
            .select("id, symbol, name, asset_class, currency, moat_rating, is_dcf_eligible")
            .eq("is_active", True)
            .execute()
        )
        assets = {a["id"]: a for a in (assets_resp.data or [])}
        asset_ids = list(assets.keys())

        if not asset_ids:
            return []

        # Fetch latest valuation for each asset
        resp = (
            client.table("asset_valuations")
            .select("*")
            .in_("asset_id", asset_ids)
            .order("as_of_date", desc=True)
            .execute()
        )

        # Keep only the most recent per asset
        seen: set[str] = set()
        results = []
        for v in (resp.data or []):
            asset_id = v.get("asset_id")
            if asset_id not in seen:
                seen.add(asset_id)
                asset_info = assets.get(asset_id, {})
                results.append({**asset_info, **v})

        return results
    except Exception as exc:
        logger.error("get_latest_valuations failed: %s", exc)
        raise


def get_valuation_history(asset_id: str, days: int = 90) -> list[dict]:
    """
    Fetch valuation history for a single asset.

    Args:
        asset_id: UUID string.
        days: Number of days of history (default 90).

    Returns:
        List of valuation dicts ordered by date ascending.
    """
    try:
        from datetime import timedelta
        cutoff = (date.today() - timedelta(days=days)).isoformat()
        client = get_supabase_client()
        resp = (
            client.table("asset_valuations")
            .select("*")
            .eq("asset_id", asset_id)
            .gte("as_of_date", cutoff)
            .order("as_of_date")
            .execute()
        )
        return resp.data or []
    except Exception as exc:
        logger.error("get_valuation_history failed for %s: %s", asset_id, exc)
        raise


def get_opportunity_candidates(
    min_margin_of_safety: float = 0.15,
    min_drawdown: float = 0.30,
) -> list[dict]:
    """
    Fetch assets meeting opportunity criteria (Graham + Marks thresholds).

    Args:
        min_margin_of_safety: Minimum margin of safety (default 15%).
        min_drawdown: Minimum drawdown from 6-12m high (default 30%, stored as negative).

    Returns:
        List of valuation dicts for qualifying assets.
    """
    try:
        client = get_supabase_client()
        resp = (
            client.table("asset_valuations")
            .select("*, assets(symbol, name, asset_class, currency, moat_rating)")
            .gte("margin_of_safety_pct", min_margin_of_safety)
            .lte("drawdown_from_6_12m_high_pct", -min_drawdown)  # stored negative
            .order("margin_of_safety_pct", desc=True)
            .execute()
        )
        return resp.data or []
    except Exception as exc:
        logger.error("get_opportunity_candidates failed: %s", exc)
        raise
