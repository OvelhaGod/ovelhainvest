"""Repository: assets table."""

from __future__ import annotations

import logging

from app.db.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


def get_active_assets() -> list[dict]:
    """
    Fetch all active assets from the universe.

    Returns:
        List of asset dicts.
    """
    try:
        client = get_supabase_client()
        resp = (
            client.table("assets")
            .select("*")
            .eq("is_active", True)
            .order("symbol")
            .execute()
        )
        return resp.data or []
    except Exception as exc:
        logger.error("get_active_assets failed: %s", exc)
        raise


def get_asset_by_symbol(symbol: str, currency: str = "USD") -> dict | None:
    """
    Fetch a single asset by symbol and currency.

    Args:
        symbol: Ticker symbol (e.g. "VTI").
        currency: Currency code (default "USD").

    Returns:
        Asset dict or None if not found.
    """
    try:
        client = get_supabase_client()
        resp = (
            client.table("assets")
            .select("*")
            .eq("symbol", symbol)
            .eq("currency", currency)
            .limit(1)
            .execute()
        )
        data = resp.data
        return data[0] if data else None
    except Exception as exc:
        logger.error("get_asset_by_symbol failed for %s/%s: %s", symbol, currency, exc)
        return None


def get_assets_by_ids(asset_ids: list[str]) -> list[dict]:
    """
    Fetch assets by a list of UUIDs.

    Args:
        asset_ids: List of asset UUID strings.

    Returns:
        List of asset dicts.
    """
    if not asset_ids:
        return []
    try:
        client = get_supabase_client()
        resp = (
            client.table("assets")
            .select("*")
            .in_("id", asset_ids)
            .execute()
        )
        return resp.data or []
    except Exception as exc:
        logger.error("get_assets_by_ids failed: %s", exc)
        raise


def upsert_asset(asset: dict) -> dict:
    """
    Upsert an asset record (insert or update on symbol+currency unique index).

    Args:
        asset: Asset dict. Must include symbol, name, asset_class, currency.

    Returns:
        Upserted asset dict.
    """
    try:
        client = get_supabase_client()
        resp = (
            client.table("assets")
            .upsert(asset, on_conflict="symbol,currency")
            .execute()
        )
        data = resp.data
        return data[0] if data else asset
    except Exception as exc:
        logger.error("upsert_asset failed for %s: %s", asset.get("symbol"), exc)
        raise
