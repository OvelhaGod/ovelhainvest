"""
Pluggy Open Finance Client — Phase 11+ stub.

Pluggy is the Brazilian Open Finance aggregator used to sync bank and broker data.
Full implementation deferred to Phase 11 (Personal Finance OS).

Docs: https://docs.pluggy.ai
API: https://api.pluggy.ai

Environment variables required:
    PLUGGY_CLIENT_ID     — from pluggy.ai dashboard
    PLUGGY_CLIENT_SECRET — from pluggy.ai dashboard
"""

from __future__ import annotations

import logging

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

PLUGGY_BASE_URL = "https://api.pluggy.ai"


def get_api_key() -> str:
    """
    Authenticate with Pluggy and return an API key (short-lived token).

    Pluggy uses a two-step auth:
    1. POST /auth → exchange client_id + client_secret → api_key (valid 2h)
    2. Use api_key as X-API-KEY header on all subsequent requests

    Returns:
        str: The Pluggy API key

    Raises:
        RuntimeError: If credentials are not configured or auth fails
    """
    settings = get_settings()
    client_id = getattr(settings, "pluggy_client_id", None)
    client_secret = getattr(settings, "pluggy_client_secret", None)

    if not client_id or not client_secret:
        raise RuntimeError(
            "PLUGGY_CLIENT_ID and PLUGGY_CLIENT_SECRET must be set in environment to use Pluggy."
        )

    try:
        with httpx.Client(timeout=15) as client:
            resp = client.post(
                f"{PLUGGY_BASE_URL}/auth",
                json={"clientId": client_id, "clientSecret": client_secret},
            )
            resp.raise_for_status()
            data = resp.json()
            api_key = data.get("apiKey")
            if not api_key:
                raise RuntimeError(f"Pluggy auth response missing apiKey: {data}")
            return api_key
    except httpx.HTTPError as exc:
        logger.error("Pluggy auth HTTP error: %s", exc)
        raise RuntimeError(f"Pluggy authentication failed: {exc}") from exc


def get_connect_token(api_key: str) -> str:
    """
    Create a Pluggy Connect Widget access token for browser-side OAuth flow.

    The Connect Widget is embedded in the frontend to let users authorize
    their bank/broker accounts. The access token is single-use and expires quickly.

    Args:
        api_key: Valid Pluggy API key from get_api_key()

    Returns:
        str: The connect token for the frontend widget

    Raises:
        RuntimeError: If token creation fails
    """
    try:
        with httpx.Client(timeout=15) as client:
            resp = client.post(
                f"{PLUGGY_BASE_URL}/connect_token",
                headers={"X-API-KEY": api_key},
                json={},
            )
            resp.raise_for_status()
            data = resp.json()
            token = data.get("accessToken")
            if not token:
                raise RuntimeError(f"Pluggy connect_token response missing accessToken: {data}")
            return token
    except httpx.HTTPError as exc:
        logger.error("Pluggy connect_token HTTP error: %s", exc)
        raise RuntimeError(f"Pluggy connect token creation failed: {exc}") from exc


def list_items(api_key: str) -> list[dict]:
    """
    List all connected institutions (items) for this account.

    Args:
        api_key: Valid Pluggy API key

    Returns:
        List of item dicts with keys: id, connector, status, createdAt, updatedAt, lastUpdatedAt
    """
    try:
        with httpx.Client(timeout=15) as client:
            resp = client.get(
                f"{PLUGGY_BASE_URL}/items",
                headers={"X-API-KEY": api_key},
            )
            resp.raise_for_status()
            return resp.json().get("results", [])
    except httpx.HTTPError as exc:
        logger.error("Pluggy list_items HTTP error: %s", exc)
        return []


def sync_item(api_key: str, item_id: str) -> dict:
    """
    Trigger a re-sync for a connected institution.

    Args:
        api_key: Valid Pluggy API key
        item_id: The Pluggy item ID to sync

    Returns:
        Updated item dict
    """
    try:
        with httpx.Client(timeout=30) as client:
            resp = client.patch(
                f"{PLUGGY_BASE_URL}/items/{item_id}",
                headers={"X-API-KEY": api_key},
                json={},
            )
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPError as exc:
        logger.error("Pluggy sync_item HTTP error for %s: %s", item_id, exc)
        raise RuntimeError(f"Pluggy sync failed for {item_id}: {exc}") from exc


def get_accounts(api_key: str, item_id: str) -> list[dict]:
    """
    Fetch accounts for a connected item (institution).

    Args:
        api_key: Valid Pluggy API key
        item_id: The Pluggy item ID

    Returns:
        List of account dicts with balance, type, etc.
    """
    try:
        with httpx.Client(timeout=15) as client:
            resp = client.get(
                f"{PLUGGY_BASE_URL}/accounts",
                headers={"X-API-KEY": api_key},
                params={"itemId": item_id},
            )
            resp.raise_for_status()
            return resp.json().get("results", [])
    except httpx.HTTPError as exc:
        logger.error("Pluggy get_accounts HTTP error: %s", exc)
        return []


def get_transactions(
    api_key: str,
    account_id: str,
    from_date: str | None = None,
    to_date: str | None = None,
    page_size: int = 500,
) -> list[dict]:
    """
    Fetch transactions for a specific account.

    Args:
        api_key: Valid Pluggy API key
        account_id: The Pluggy account ID
        from_date: ISO date string (YYYY-MM-DD) for start of range
        to_date: ISO date string (YYYY-MM-DD) for end of range
        page_size: Number of transactions per page (max 500)

    Returns:
        List of transaction dicts
    """
    params: dict = {"accountId": account_id, "pageSize": page_size}
    if from_date:
        params["from"] = from_date
    if to_date:
        params["to"] = to_date

    all_transactions: list[dict] = []
    try:
        with httpx.Client(timeout=30) as client:
            page = 1
            while True:
                params["page"] = page
                resp = client.get(
                    f"{PLUGGY_BASE_URL}/transactions",
                    headers={"X-API-KEY": api_key},
                    params=params,
                )
                resp.raise_for_status()
                data = resp.json()
                results = data.get("results", [])
                all_transactions.extend(results)
                total_pages = data.get("totalPages", 1)
                if page >= total_pages or not results:
                    break
                page += 1
        return all_transactions
    except httpx.HTTPError as exc:
        logger.error("Pluggy get_transactions HTTP error for account %s: %s", account_id, exc)
        return []
