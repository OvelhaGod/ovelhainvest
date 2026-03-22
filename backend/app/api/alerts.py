"""
Alerts API endpoints.

GET  /alerts/rules       — Active alert rules
POST /alerts/rules       — Create new alert rule
GET  /alerts/history     — Triggered alert history
POST /alerts/telegram_callback — Telegram inline keyboard callback handler

Phase 6 implementation — stub only.
"""

from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/alerts/rules")
async def list_alert_rules() -> list:
    """Return all active alert rules for the user."""
    raise NotImplementedError("Phase 6")


@router.post("/alerts/rules")
async def create_alert_rule(body: dict) -> dict:
    """Create a new alert rule."""
    raise NotImplementedError("Phase 6")


@router.get("/alerts/history")
async def get_alert_history(
    limit: int = 50,
    rule_type: str | None = None,
) -> list:
    """Return triggered alert history, newest first."""
    raise NotImplementedError("Phase 6")


@router.post("/alerts/telegram_callback")
async def telegram_callback(request: Request) -> dict:
    """
    Handle Telegram Bot API webhook callbacks.
    Used for inline keyboard approve/reject on opportunity vault trades.
    """
    raise NotImplementedError("Phase 6")
