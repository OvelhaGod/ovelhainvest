"""Repository: holdings table."""

from __future__ import annotations

import logging

from app.db.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


def get_holdings(user_id: str) -> list[dict]:
    """
    Fetch all holdings for a user across all accounts.
    Joins with assets and accounts for full context.

    Args:
        user_id: UUID string.

    Returns:
        List of holding dicts with asset and account metadata.
    """
    try:
        client = get_supabase_client()
        resp = (
            client.table("holdings")
            .select(
                "*, "
                "assets(id, symbol, name, asset_class, currency, moat_rating, is_dcf_eligible), "
                "accounts!inner(id, name, broker, account_type, tax_treatment, currency, user_id)"
            )
            .eq("accounts.user_id", user_id)
            .execute()
        )
        # Flatten for convenience
        rows = []
        for h in (resp.data or []):
            asset = h.pop("assets", {}) or {}
            account = h.pop("accounts", {}) or {}
            rows.append({
                **h,
                "symbol": asset.get("symbol", ""),
                "asset_name": asset.get("name", ""),
                "asset_class": asset.get("asset_class", ""),
                "currency": asset.get("currency", account.get("currency", "USD")),
                "moat_rating": asset.get("moat_rating"),
                "is_dcf_eligible": asset.get("is_dcf_eligible", False),
                "account_name": account.get("name", ""),
                "account_type": account.get("account_type", ""),
                "tax_treatment": account.get("tax_treatment", ""),
            })
        return rows
    except Exception as exc:
        logger.error("get_holdings failed for user %s: %s", user_id, exc)
        raise


def get_holdings_by_account(account_id: str) -> list[dict]:
    """
    Fetch all holdings for a specific account.

    Args:
        account_id: UUID string.

    Returns:
        List of holding dicts.
    """
    try:
        client = get_supabase_client()
        resp = (
            client.table("holdings")
            .select("*, assets(symbol, name, asset_class, currency)")
            .eq("account_id", account_id)
            .execute()
        )
        rows = []
        for h in (resp.data or []):
            asset = h.pop("assets", {}) or {}
            rows.append({
                **h,
                "symbol": asset.get("symbol", ""),
                "asset_name": asset.get("name", ""),
                "asset_class": asset.get("asset_class", ""),
                "currency": asset.get("currency", "USD"),
            })
        return rows
    except Exception as exc:
        logger.error("get_holdings_by_account failed for %s: %s", account_id, exc)
        raise


def upsert_holding(holding: dict) -> dict:
    """
    Upsert a holding (insert or update on account_id + asset_id).

    Args:
        holding: Dict with account_id, asset_id, quantity, avg_cost_basis.

    Returns:
        Upserted holding dict.
    """
    try:
        client = get_supabase_client()
        resp = (
            client.table("holdings")
            .upsert(holding, on_conflict="account_id,asset_id")
            .execute()
        )
        data = resp.data
        return data[0] if data else holding
    except Exception as exc:
        logger.error("upsert_holding failed: %s", exc)
        raise
