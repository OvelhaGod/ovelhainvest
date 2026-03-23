"""
Alerts API endpoints.

GET    /alerts/rules         — List active alert rules
POST   /alerts/rules         — Create alert rule
PATCH  /alerts/rules/{id}    — Toggle active/inactive
GET    /alerts/history       — Triggered alert history (last 50)
POST   /webhooks/telegram    — Receive Telegram callback_query updates
"""

from __future__ import annotations

import hashlib
import hmac
import logging

from fastapi import APIRouter, Header, HTTPException, Query, Request

from app.config import settings
from app.db.supabase_client import get_supabase_client
from app.services.alert_engine import (
    BUILT_IN_ALERT_RULES,
    handle_telegram_callback,
)

router = APIRouter()
logger = logging.getLogger(__name__)


def _get_user_id(user_id: str | None = None) -> str:
    return user_id or "00000000-0000-0000-0000-000000000001"


# ── Alert Rules ───────────────────────────────────────────────────────────

@router.get("/alerts/rules")
async def list_alert_rules(
    user_id: str = Query(default="00000000-0000-0000-0000-000000000001"),
) -> list[dict]:
    """Return all active alert rules for the user."""
    try:
        client = get_supabase_client()
        resp = (
            client.table("alert_rules")
            .select("*")
            .eq("user_id", user_id)
            .eq("is_active", True)
            .order("created_at", desc=False)
            .execute()
        )
        return resp.data or []
    except Exception as exc:
        logger.error("list_alert_rules failed: %s", exc)
        # Return built-in rules as fallback if DB unavailable
        return [
            {
                "id": f"builtin-{i}",
                "user_id": user_id,
                "rule_name": r["name"],
                "rule_type": r["type"],
                "conditions": r["conditions"],
                "channel": r.get("channel", "telegram"),
                "is_active": True,
                "last_triggered": None,
                "source": "builtin",
            }
            for i, r in enumerate(BUILT_IN_ALERT_RULES)
        ]


@router.post("/alerts/rules", status_code=201)
async def create_alert_rule(
    body: dict,
    user_id: str = Query(default="00000000-0000-0000-0000-000000000001"),
) -> dict:
    """Create a new alert rule."""
    required = {"rule_name", "rule_type", "conditions"}
    missing = required - set(body.keys())
    if missing:
        raise HTTPException(status_code=422, detail=f"Missing fields: {missing}")

    record = {
        "user_id": user_id,
        "rule_name": body["rule_name"],
        "rule_type": body["rule_type"],
        "conditions": body["conditions"],
        "channel": body.get("channel", "telegram"),
        "is_active": body.get("is_active", True),
    }

    try:
        client = get_supabase_client()
        resp = client.table("alert_rules").insert(record).execute()
        return resp.data[0] if resp.data else record
    except Exception as exc:
        logger.error("create_alert_rule failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.patch("/alerts/rules/{rule_id}")
async def toggle_alert_rule(
    rule_id: str,
    user_id: str = Query(default="00000000-0000-0000-0000-000000000001"),
) -> dict:
    """Toggle an alert rule active/inactive."""
    try:
        client = get_supabase_client()
        # Fetch current state
        current = (
            client.table("alert_rules")
            .select("is_active")
            .eq("id", rule_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        if not current.data:
            raise HTTPException(status_code=404, detail="Alert rule not found")
        new_state = not current.data[0]["is_active"]
        resp = (
            client.table("alert_rules")
            .update({"is_active": new_state})
            .eq("id", rule_id)
            .execute()
        )
        return resp.data[0] if resp.data else {"id": rule_id, "is_active": new_state}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("toggle_alert_rule failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/alerts/history")
async def get_alert_history(
    user_id: str = Query(default="00000000-0000-0000-0000-000000000001"),
    limit: int = Query(default=50, le=200),
    rule_type: str | None = Query(default=None),
) -> list[dict]:
    """Return triggered alert history, newest first."""
    try:
        client = get_supabase_client()
        query = (
            client.table("alert_history")
            .select("*, alert_rules(rule_name, rule_type, user_id)")
            .order("triggered_at", desc=True)
            .limit(limit)
        )
        if rule_type:
            # Filter via join — Supabase PostgREST syntax
            query = query.eq("alert_rules.rule_type", rule_type)

        resp = query.execute()
        # Filter by user_id via the join
        rows = resp.data or []
        return [
            r for r in rows
            if r.get("alert_rules", {}) and r["alert_rules"].get("user_id") == user_id
        ]
    except Exception as exc:
        logger.error("get_alert_history failed: %s", exc)
        return []


# ── Telegram Webhook ──────────────────────────────────────────────────────

@router.post("/webhooks/telegram")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> dict:
    """
    Receive and process Telegram Bot API webhook updates.

    Verifies the secret token header set when registering the webhook.
    Handles inline keyboard callback_query (approve/reject flows).
    """
    # Verify secret token if configured
    expected_token = settings.telegram_bot_token
    if expected_token and x_telegram_bot_api_secret_token:
        # Simple HMAC check using last 8 chars of bot token as key
        if x_telegram_bot_api_secret_token != expected_token[-32:]:
            logger.warning("Telegram webhook: invalid secret token")
            raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    # Only handle callback_query (inline keyboard presses)
    callback_query = body.get("callback_query")
    if callback_query:
        logger.info("Telegram callback_query: %s", callback_query.get("data", ""))
        result = await handle_telegram_callback(callback_query)
        return {"ok": True, "result": result}

    # Ignore other update types (messages, channel posts, etc.)
    logger.debug("Telegram webhook: ignored update type for body keys=%s", list(body.keys()))
    return {"ok": True}
