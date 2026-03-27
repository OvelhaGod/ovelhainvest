"""
Pluggy Open Finance Client — Phase 11.

Pluggy is the Brazilian Open Finance aggregator used to sync bank and broker data.
Full implementation: account listing, transaction sync, connect token.

Docs: https://docs.pluggy.ai
API: https://api.pluggy.ai

Environment variables required:
    PLUGGY_CLIENT_ID     — from pluggy.ai dashboard
    PLUGGY_CLIENT_SECRET — from pluggy.ai dashboard
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

PLUGGY_BASE_URL = "https://api.pluggy.ai"

# In-process API key cache (avoids re-auth on every request; token is valid 2h)
_api_key_cache: dict = {"key": None, "expires_at": None}


def _map_account_type(pluggy_type: str) -> str:
    mapping = {
        "BANK": "checking",
        "SAVINGS": "savings",
        "CREDIT": "credit_card",
        "LOAN": "loan",
        "INVESTMENT": "brokerage",
    }
    return mapping.get(pluggy_type.upper(), "checking")


def get_api_key() -> str:
    """
    Authenticate with Pluggy and return a cached API key (TTL ~1h 45min).

    Pluggy uses a two-step auth:
    1. POST /auth → exchange client_id + client_secret → api_key (valid 2h)
    2. Use api_key as X-API-KEY header on all subsequent requests

    Returns:
        str: The Pluggy API key

    Raises:
        RuntimeError: If credentials are not configured or auth fails
    """
    now = datetime.utcnow()
    if _api_key_cache["key"] and _api_key_cache["expires_at"] and _api_key_cache["expires_at"] > now:
        return _api_key_cache["key"]

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
            _api_key_cache["key"] = api_key
            _api_key_cache["expires_at"] = now + timedelta(hours=1, minutes=45)
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


def sync_item_transactions(item_id: str, db, user_id: str = "default") -> dict:
    """
    Full sync: fetch all accounts + transactions for an item, upsert into local DB.
    Returns a summary dict of what was synced.
    """
    api_key = get_api_key()
    accounts = get_accounts(api_key, item_id)
    total_transactions = 0
    synced_account_names: list[str] = []

    for acct in accounts:
        acct_name = acct.get("name", "Unknown")
        acct_type = _map_account_type(acct.get("type", "BANK"))
        currency = acct.get("currencyCode", "BRL")
        is_liability = acct.get("type", "").upper() in ("CREDIT", "LOAN")

        # Upsert account
        try:
            acct_data = {
                "user_id": user_id,
                "name": acct_name,
                "institution": item_id,
                "broker": item_id,
                "account_type": acct_type,
                "currency": currency,
                "current_balance": acct.get("balance", 0),
                "credit_limit": (acct.get("creditData") or {}).get("creditLimit"),
                "is_liability": is_liability,
                "pluggy_item_id": item_id,
                "pluggy_account_id": acct["id"],
                "last_synced_at": "now()",
                "tax_treatment": "taxable",
            }
            existing = db.table("accounts").select("id").eq("pluggy_account_id", acct["id"]).execute()
            if existing.data:
                db.table("accounts").update(acct_data).eq("pluggy_account_id", acct["id"]).execute()
            else:
                db.table("accounts").insert(acct_data).execute()
        except Exception as exc:
            logger.warning("Pluggy sync_item: account upsert failed for %s: %s", acct_name, exc)

        # Fetch transactions
        txns = get_transactions(api_key, acct["id"])
        for t in txns:
            try:
                txn_data = {
                    "user_id": user_id,
                    "date": t["date"][:10],
                    "description": t.get("description", ""),
                    "amount": t["amount"],
                    "currency": currency,
                    "amount_usd": t["amount"] / 5.23 if currency == "BRL" else t["amount"],
                    "type": "income" if t["amount"] > 0 else "expense",
                    "status": "cleared",
                    "pluggy_transaction_id": t["id"],
                }
                db.table("spending_transactions").upsert(
                    txn_data, on_conflict="pluggy_transaction_id"
                ).execute()
                total_transactions += 1
            except Exception:
                pass

        synced_account_names.append(acct_name)

    return {
        "item_id": item_id,
        "accounts_synced": len(synced_account_names),
        "account_names": synced_account_names,
        "transactions_synced": total_transactions,
    }


def get_investments(api_key: str, item_id: str) -> list[dict]:
    """List investment positions for brokerage accounts (Clear, XP, BTG etc.)."""
    try:
        with httpx.Client(timeout=15) as client:
            resp = client.get(
                f"{PLUGGY_BASE_URL}/investments",
                headers={"X-API-KEY": api_key},
                params={"itemId": item_id},
            )
            resp.raise_for_status()
            return resp.json().get("results", [])
    except httpx.HTTPError as exc:
        logger.error("Pluggy get_investments HTTP error: %s", exc)
        return []
