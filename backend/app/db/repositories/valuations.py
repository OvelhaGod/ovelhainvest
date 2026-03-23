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


def get_top_by_composite_score(
    limit: int = 10,
    min_quality_score: float = 0.0,
    asset_class_filter: str | None = None,
) -> list[dict]:
    """
    Fetch top-ranked assets by composite_score from the latest valuations.

    Args:
        limit:              Max rows to return (default 10).
        min_quality_score:  Minimum quality score filter.
        asset_class_filter: Optional asset class (e.g. "US_equity").

    Returns:
        List of valuation dicts joined with asset metadata, sorted by composite_score desc.
    """
    try:
        client = get_supabase_client()
        query = (
            client.table("asset_valuations")
            .select("*, assets(symbol, name, asset_class, currency, moat_rating, is_dcf_eligible)")
            .gte("quality_score", min_quality_score)
            .order("composite_score", desc=True)
            .limit(limit * 3)   # over-fetch to allow dedup by asset
        )
        resp = query.execute()
        rows = resp.data or []

        # Dedup: keep only most recent per asset, then apply asset_class filter
        seen: set[str] = set()
        results = []
        for row in rows:
            asset_id = row.get("asset_id")
            if asset_id in seen:
                continue
            seen.add(asset_id)
            asset_info = row.get("assets") or {}
            if asset_class_filter and asset_info.get("asset_class") != asset_class_filter:
                continue
            results.append({**asset_info, **row})
            if len(results) >= limit:
                break

        return results
    except Exception as exc:
        logger.error("get_top_by_composite_score failed: %s", exc)
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


def get_valuation_by_symbol(symbol: str) -> dict | None:
    """
    Fetch the latest valuation for a single asset by ticker symbol.

    Args:
        symbol: Ticker (e.g. "NVDA").

    Returns:
        Valuation dict joined with asset metadata, or None if not found.
    """
    try:
        client = get_supabase_client()
        # Join with assets to resolve symbol → asset_id
        asset_resp = (
            client.table("assets")
            .select("id, symbol, name, asset_class, currency, moat_rating, is_dcf_eligible, sector, region")
            .eq("symbol", symbol)
            .eq("is_active", True)
            .limit(1)
            .execute()
        )
        assets = asset_resp.data or []
        if not assets:
            return None
        asset = assets[0]
        asset_id = asset["id"]

        val_resp = (
            client.table("asset_valuations")
            .select("*")
            .eq("asset_id", asset_id)
            .order("as_of_date", desc=True)
            .limit(1)
            .execute()
        )
        vals = val_resp.data or []
        if not vals:
            return None
        return {**asset, **vals[0]}
    except Exception as exc:
        logger.error("get_valuation_by_symbol failed for %s: %s", symbol, exc)
        return None


def get_valuation_summary_stats() -> dict:
    """
    Return high-level stats across the valuation universe for the summary endpoint.

    Returns:
        Dict with counts: assets_scored, positive_mos, negative_mos,
        top_opportunities (tier_1 + tier_2 count), last_updated date.
    """
    try:
        client = get_supabase_client()
        resp = (
            client.table("asset_valuations")
            .select("as_of_date, margin_of_safety_pct, tier, composite_score")
            .order("as_of_date", desc=True)
            .limit(200)
            .execute()
        )
        rows = resp.data or []
        # Dedup by as_of_date — only count most recent run
        if not rows:
            return {"assets_scored": 0, "positive_mos": 0, "negative_mos": 0, "opportunities": 0}

        latest_date = rows[0].get("as_of_date")
        today_rows  = [r for r in rows if r.get("as_of_date") == latest_date]

        positive_mos = sum(1 for r in today_rows if (r.get("margin_of_safety_pct") or 0) > 0)
        negative_mos = sum(1 for r in today_rows if (r.get("margin_of_safety_pct") or 0) < 0)
        opportunities = sum(1 for r in today_rows if r.get("tier") in ("tier_1", "tier_2"))

        return {
            "assets_scored": len(today_rows),
            "positive_mos":  positive_mos,
            "negative_mos":  negative_mos,
            "opportunities": opportunities,
            "last_updated":  latest_date,
        }
    except Exception as exc:
        logger.error("get_valuation_summary_stats failed: %s", exc)
        return {"assets_scored": 0, "positive_mos": 0, "negative_mos": 0, "opportunities": 0}
