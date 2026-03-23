"""
Alerts API endpoints — Phase 6.

GET    /alerts/rules              — List active alert rules
POST   /alerts/rules              — Create alert rule
PATCH  /alerts/rules/{id}         — Toggle active/inactive
GET    /alerts/history            — Triggered alert history (last 50)
POST   /webhooks/telegram         — Receive Telegram callback_query updates
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Header, HTTPException, Query, Request

from app.config import settings
from app.db.supabase_client import get_supabase_client
from app.services.alert_engine import (
    BUILT_IN_ALERT_RULES,
    handle_telegram_callback,
    send_telegram_alert,
)

router = APIRouter()
logger = logging.getLogger(__name__)

_DEFAULT_USER = "00000000-0000-0000-0000-000000000001"


# ── Alert Rules ───────────────────────────────────────────────────────────────

@router.get("/alerts/rules")
async def list_alert_rules(
    user_id: str = Query(default=_DEFAULT_USER),
    include_inactive: bool = Query(default=False),
) -> list[dict]:
    """Return alert rules for the user, newest first."""
    try:
        client = get_supabase_client()
        query = (
            client.table("alert_rules")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=False)
        )
        if not include_inactive:
            query = query.eq("is_active", True)
        resp = query.execute()
        return resp.data or []
    except Exception as exc:
        logger.error("list_alert_rules failed: %s", exc)
        # Fallback: return built-in rules as read-only list
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
    user_id: str = Query(default=_DEFAULT_USER),
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
    body: dict | None = None,
    user_id: str = Query(default=_DEFAULT_USER),
) -> dict:
    """
    Toggle alert rule active/inactive, or update specific fields.
    If body is provided, apply those updates; otherwise toggle is_active.
    """
    try:
        client = get_supabase_client()
        if body:
            # Explicit update (e.g. from frontend test button)
            allowed = {"is_active", "conditions", "channel"}
            updates = {k: v for k, v in body.items() if k in allowed}
            if not updates:
                raise HTTPException(status_code=422, detail="No valid fields to update")
        else:
            # Toggle is_active
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
            updates = {"is_active": not current.data[0]["is_active"]}

        resp = (
            client.table("alert_rules")
            .update(updates)
            .eq("id", rule_id)
            .eq("user_id", user_id)
            .execute()
        )
        return resp.data[0] if resp.data else {"id": rule_id, **updates}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("toggle_alert_rule failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/alerts/history")
async def get_alert_history(
    user_id: str = Query(default=_DEFAULT_USER),
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
        resp = query.execute()
        rows = resp.data or []
        # Filter to this user via joined alert_rules
        filtered = [
            r for r in rows
            if (r.get("alert_rules") or {}).get("user_id") == user_id
        ]
        if rule_type:
            filtered = [
                r for r in filtered
                if (r.get("alert_rules") or {}).get("rule_type") == rule_type
            ]
        return filtered
    except Exception as exc:
        logger.error("get_alert_history failed: %s", exc)
        return []


@router.post("/alerts/test/{rule_id}", status_code=200)
async def test_alert_rule(
    rule_id: str,
    user_id: str = Query(default=_DEFAULT_USER),
) -> dict:
    """Send a test Telegram message for a specific alert rule."""
    if not settings.telegram_enabled:
        raise HTTPException(status_code=503, detail="Telegram not configured")

    # Fetch the rule
    rule = None
    try:
        client = get_supabase_client()
        resp = (
            client.table("alert_rules")
            .select("*")
            .eq("id", rule_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        rule = resp.data[0] if resp.data else None
    except Exception:
        pass

    if not rule:
        # Try built-in rules by builtin-{index}
        if rule_id.startswith("builtin-"):
            try:
                idx = int(rule_id.split("-")[1])
                r = BUILT_IN_ALERT_RULES[idx]
                rule = {"rule_name": r["name"], "rule_type": r["type"]}
            except (IndexError, ValueError):
                raise HTTPException(status_code=404, detail="Rule not found")
        else:
            raise HTTPException(status_code=404, detail="Rule not found")

    rule_type = rule.get("rule_type", "")
    test_message = (
        f"🧪 *TEST ALERT — {rule.get('rule_name', rule_type)}*\n"
        f"Rule type: `{rule_type}`\n"
        f"_This is a test message from OvelhaInvest\\._"
    )
    success = await send_telegram_alert(
        message=test_message,
        chat_id=settings.telegram_chat_id,
        bot_token=settings.telegram_bot_token,
    )
    return {"sent": success, "rule_name": rule.get("rule_name")}


# ── Telegram Webhook ──────────────────────────────────────────────────────────

@router.post("/webhooks/telegram")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> dict:
    """
    Receive Telegram Bot API webhook updates.

    Security: verifies X-Telegram-Bot-Api-Secret-Token header against
    TELEGRAM_WEBHOOK_SECRET env var (or last 32 chars of bot token as fallback).

    Handles:
    - callback_query: approve:{run_id}, reject:{run_id}, snooze:{rule_id}:{days}
    """
    # Security: verify secret token
    webhook_secret = settings.telegram_webhook_secret or settings.telegram_bot_token[-32:]
    if webhook_secret:
        if not x_telegram_bot_api_secret_token:
            logger.warning("Telegram webhook: missing secret token header")
            raise HTTPException(status_code=403, detail="Forbidden — missing secret token")
        if x_telegram_bot_api_secret_token != webhook_secret:
            logger.warning("Telegram webhook: invalid secret token")
            raise HTTPException(status_code=403, detail="Forbidden — invalid secret token")

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # Handle callback_query (inline keyboard presses)
    callback_query = body.get("callback_query")
    if callback_query:
        logger.info("Telegram callback_query: %s", callback_query.get("data", ""))
        result = await handle_telegram_callback(callback_query)
        return {"ok": True, "result": result}

    # Ignore other update types
    logger.debug("Telegram webhook: ignored update type, keys=%s", list(body.keys()))
    return {"ok": True}
