"""Repository: accounts table."""

from __future__ import annotations

import logging
from typing import Any

from app.db.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


def get_accounts(user_id: str) -> list[dict]:
    """
    Fetch all active accounts for a user.

    Args:
        user_id: UUID string of the user.

    Returns:
        List of account dicts.
    """
    try:
        client = get_supabase_client()
        resp = (
            client.table("accounts")
            .select("*")
            .eq("user_id", user_id)
            .eq("is_active", True)
            .execute()
        )
        return resp.data or []
    except Exception as exc:
        logger.error("get_accounts failed for user %s: %s", user_id, exc)
        raise


def get_account_by_id(account_id: str) -> dict | None:
    """
    Fetch a single account by ID.

    Args:
        account_id: UUID string.

    Returns:
        Account dict or None if not found.
    """
    try:
        client = get_supabase_client()
        resp = (
            client.table("accounts")
            .select("*")
            .eq("id", account_id)
            .single()
            .execute()
        )
        return resp.data
    except Exception as exc:
        logger.error("get_account_by_id failed for %s: %s", account_id, exc)
        return None


def upsert_account(account: dict) -> dict:
    """
    Upsert an account record (insert or update on id).

    Args:
        account: Account dict. Must include user_id, name, broker, account_type, tax_treatment.

    Returns:
        Upserted account dict.
    """
    try:
        client = get_supabase_client()
        resp = (
            client.table("accounts")
            .upsert(account, on_conflict="id")
            .execute()
        )
        data = resp.data
        return data[0] if data else account
    except Exception as exc:
        logger.error("upsert_account failed: %s", exc)
        raise


def get_vaults(user_id: str) -> list[dict]:
    """
    Fetch all vaults for a user (joined with account info).

    Args:
        user_id: UUID string.

    Returns:
        List of vault dicts with account metadata.
    """
    try:
        client = get_supabase_client()
        resp = (
            client.table("vaults")
            .select("*, accounts!inner(user_id, name, tax_treatment, currency)")
            .eq("accounts.user_id", user_id)
            .execute()
        )
        return resp.data or []
    except Exception as exc:
        logger.error("get_vaults failed for user %s: %s", user_id, exc)
        raise
