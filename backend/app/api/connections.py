"""
Open Finance connections API — Pluggy integration stubs.

Full implementation in Phase 11 (Personal Finance OS).
Current scope: scaffolding for future bank/broker data sync.

POST /connections/token   → get Pluggy Connect widget token
GET  /connections/status  → list connected institutions + last sync
POST /connections/sync/{item_id} → manually re-sync an institution
DELETE /connections/{item_id}    → remove connection
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/status")
def get_connection_status(user_id: str = Query(default=None)):
    """List all connected institutions and their sync status."""
    return {
        "connections": [],
        "message": "No connections configured. Set PLUGGY_CLIENT_ID and PLUGGY_CLIENT_SECRET to enable Open Finance sync.",
        "setup_docs": "/docs/pluggy-setup.md",
    }


@router.post("/token")
def get_connect_token(user_id: str = Query(default=None)):
    """Get a Pluggy Connect widget access token for browser-side OAuth flow."""
    try:
        from app.services.pluggy_client import get_api_key, get_connect_token as _get_token
        api_key = get_api_key()
        token = _get_token(api_key)
        return {"access_token": token}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Pluggy not configured: {exc}") from exc


@router.post("/sync/{item_id}")
def sync_connection(item_id: str, user_id: str = Query(default=None)):
    """Trigger re-sync of a connected institution."""
    return {
        "item_id": item_id,
        "status": "queued",
        "message": "Full sync implementation available in Phase 11.",
        "queued_at": datetime.now(timezone.utc).isoformat(),
    }


@router.delete("/{item_id}")
def delete_connection(item_id: str, user_id: str = Query(default=None)):
    """Remove a connected institution."""
    return {"item_id": item_id, "status": "deleted"}
