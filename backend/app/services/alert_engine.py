"""
Alert engine: rule evaluation and Telegram dispatch.

Evaluates all active alert_rules against current portfolio state.
Dispatches alerts via Telegram Bot API.
Inline keyboard buttons enable approve/reject flows directly from Telegram.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

BUILT_IN_ALERT_RULES = [
    {"name": "Drawdown Alert",         "type": "drawdown",    "conditions": {"threshold": 0.25}, "channel": "telegram"},
    {"name": "Automation Pause",       "type": "drawdown",    "conditions": {"threshold": 0.40, "action": "pause_runs"}, "channel": "telegram"},
    {"name": "Sleeve Drift Breach",    "type": "drift",       "conditions": {"threshold": 0.05}, "channel": "telegram"},
    {"name": "Correlation Spike",      "type": "correlation", "conditions": {"threshold": 0.85}, "channel": "telegram"},
    {"name": "Tier 1 Opportunity",     "type": "opportunity", "conditions": {"tier": 1}, "channel": "telegram", "priority": "HIGH"},
    {"name": "Tier 2 Opportunity",     "type": "opportunity", "conditions": {"tier": 2}, "channel": "telegram", "priority": "HIGH"},
    {"name": "Asset Hits Sell Target", "type": "sell_target", "conditions": {}, "channel": "telegram"},
    {"name": "Earnings Alert",         "type": "earnings",    "conditions": {"days_ahead": 3}, "channel": "telegram"},
    {"name": "DARF Warning",           "type": "brazil_darf", "conditions": {"threshold_pct": 0.80}, "channel": "telegram"},
    {"name": "BRL Weakens >10%",       "type": "fx_move",     "conditions": {"pair": "USDBRL", "threshold": 0.10}, "channel": "telegram"},
    {"name": "Deposit Detected",       "type": "deposit",     "conditions": {}, "channel": "telegram"},
]

# Default cooldown between repeated alerts of the same type (hours)
DEFAULT_COOLDOWN_HOURS = 6
TELEGRAM_API_BASE = "https://api.telegram.org"


def evaluate_all_rules(
    portfolio_state: dict[str, Any],
    alert_rules: list[dict[str, Any]],
    recent_history: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """
    Evaluate all active alert rules against current portfolio state.

    Args:
        portfolio_state: Keys used:
            - max_drawdown: float (negative decimal)
            - sleeve_weights: list of SleeveWeight dicts
            - opportunity_tier_1: bool
            - opportunity_tier_2: bool
            - held_assets_at_sell_target: list of symbol strings
            - darf_progress_pct: float (0-1, monthly DARF usage)
            - usd_brl_30d_change: float (pct change)
            - correlation_pairs: list of {sleeves, correlation} dicts
            - recent_deposits: list of transaction dicts
        alert_rules: Active rules from alert_rules table (or BUILT_IN_ALERT_RULES).
        recent_history: Recent alert_history entries to check cooldowns.

    Returns:
        List of triggered alert dicts: {rule_name, type, payload, priority}.
    """
    recent_history = recent_history or []
    triggered: list[dict[str, Any]] = []

    # Build cooldown index: rule_name -> last_triggered_at
    cooldown_map: dict[str, datetime] = {}
    for h in recent_history:
        rule_name = h.get("rule_name", "")
        ts_str = h.get("triggered_at", "")
        if ts_str and rule_name:
            try:
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                if rule_name not in cooldown_map or ts > cooldown_map[rule_name]:
                    cooldown_map[rule_name] = ts
            except ValueError:
                pass

    now = datetime.now(timezone.utc)

    for rule in alert_rules:
        rule_name = rule.get("name", "")
        rule_type = rule.get("type", "")
        conditions = rule.get("conditions", {})

        # Cooldown check
        last_triggered = cooldown_map.get(rule_name)
        if last_triggered:
            cooldown_h = conditions.get("cooldown_hours", DEFAULT_COOLDOWN_HOURS)
            if (now - last_triggered).total_seconds() < cooldown_h * 3600:
                continue

        alert: dict[str, Any] | None = None

        if rule_type == "drawdown":
            threshold = conditions.get("threshold", 0.25)
            current_dd = abs(portfolio_state.get("max_drawdown", 0.0))
            if current_dd >= threshold:
                action = conditions.get("action", "")
                alert = {
                    "rule_name": rule_name,
                    "type": rule_type,
                    "priority": "CRITICAL" if current_dd >= 0.40 else "HIGH",
                    "payload": {
                        "drawdown_pct": current_dd,
                        "threshold": threshold,
                        "action": action,
                    },
                }

        elif rule_type == "drift":
            threshold = conditions.get("threshold", 0.05)
            sleeve_weights = portfolio_state.get("sleeve_weights", [])
            breached = [
                s for s in sleeve_weights
                if abs(s.get("drift", 0.0)) >= threshold
            ]
            if breached:
                alert = {
                    "rule_name": rule_name,
                    "type": rule_type,
                    "priority": "MEDIUM",
                    "payload": {
                        "breached_sleeves": [
                            {"sleeve": s["sleeve"], "drift": s["drift"]}
                            for s in breached
                        ],
                        "threshold": threshold,
                    },
                }

        elif rule_type == "opportunity":
            tier = conditions.get("tier", 1)
            key = f"opportunity_tier_{tier}"
            if portfolio_state.get(key, False):
                alert = {
                    "rule_name": rule_name,
                    "type": rule_type,
                    "priority": "HIGH",
                    "payload": {
                        "tier": tier,
                        "asset": portfolio_state.get(f"opportunity_tier_{tier}_asset", ""),
                        "drawdown_pct": portfolio_state.get(f"opportunity_tier_{tier}_drawdown", 0.0),
                        "margin_of_safety_pct": portfolio_state.get(f"opportunity_tier_{tier}_mos", 0.0),
                    },
                }

        elif rule_type == "sell_target":
            at_target = portfolio_state.get("held_assets_at_sell_target", [])
            if at_target:
                alert = {
                    "rule_name": rule_name,
                    "type": rule_type,
                    "priority": "MEDIUM",
                    "payload": {"symbols_at_sell_target": at_target},
                }

        elif rule_type == "brazil_darf":
            threshold_pct = conditions.get("threshold_pct", 0.80)
            progress = portfolio_state.get("darf_progress_pct", 0.0)
            if progress >= threshold_pct:
                alert = {
                    "rule_name": rule_name,
                    "type": rule_type,
                    "priority": "HIGH",
                    "payload": {
                        "progress_pct": progress,
                        "threshold_pct": threshold_pct,
                        "gross_sales_brl": portfolio_state.get("darf_gross_sales_brl", 0.0),
                    },
                }

        elif rule_type == "fx_move":
            threshold = conditions.get("threshold", 0.10)
            change = abs(portfolio_state.get("usd_brl_30d_change", 0.0))
            if change >= threshold:
                alert = {
                    "rule_name": rule_name,
                    "type": rule_type,
                    "priority": "MEDIUM",
                    "payload": {
                        "pair": "USDBRL",
                        "change_30d": portfolio_state.get("usd_brl_30d_change", 0.0),
                        "threshold": threshold,
                    },
                }

        elif rule_type == "correlation":
            threshold = conditions.get("threshold", 0.85)
            pairs = portfolio_state.get("correlation_pairs", [])
            high_corr = [p for p in pairs if abs(p.get("correlation", 0.0)) >= threshold]
            if high_corr:
                alert = {
                    "rule_name": rule_name,
                    "type": rule_type,
                    "priority": "MEDIUM",
                    "payload": {"high_correlation_pairs": high_corr[:3]},
                }

        elif rule_type == "deposit":
            deposits = portfolio_state.get("recent_deposits", [])
            if deposits:
                alert = {
                    "rule_name": rule_name,
                    "type": rule_type,
                    "priority": "LOW",
                    "payload": {
                        "deposit_count": len(deposits),
                        "total_amount": sum(d.get("amount", 0) for d in deposits),
                    },
                }

        if alert:
            triggered.append(alert)

    return triggered


def format_alert_message(alert_type: str, payload: dict[str, Any]) -> str:
    """
    Format a Telegram alert message with emoji + title + numbers + action.

    Args:
        alert_type: Rule type string.
        payload: Alert-specific data.

    Returns:
        Plain text formatted message (Telegram MarkdownV2 escaped).
    """
    import re

    def esc(s: str) -> str:
        return re.sub(r"([_*\[\]()~`>#\+\-=|{}.!])", r"\\\1", str(s))

    templates: dict[str, str] = {
        "drawdown": (
            "=📉 *DRAWDOWN ALERT*\n"
            "Portfolio down *{drawdown_pct:.1f}%* from peak \\(threshold: {threshold:.0%}\\)\\.\n"
            "Action: Review allocation and consider pausing automated trades\\."
        ),
        "drift": (
            "⚖️ *SLEEVE DRIFT BREACH*\n"
            "Sleeves out of target band:\n{sleeves}\n"
            "Run /run\\_allocation to rebalance\\."
        ),
        "opportunity": (
            "🟡 *TIER {tier} OPPORTUNITY TRIGGERED*\n"
            "Asset: *{asset}*\n"
            "Drawdown: *{drawdown_pct:.1f}%* \\| MoS: *{mos_pct:.1f}%*\n"
            "Vault deployment ready\\. Approve below\\."
        ),
        "sell_target": (
            "📈 *SELL TARGET REACHED*\n"
            "Assets at or above sell target: {symbols}\n"
            "Review your position sizing\\."
        ),
        "brazil_darf": (
            "🇧🇷 *BRAZIL DARF WARNING*\n"
            "Monthly exemption used: *{pct:.0f}%* of R\\$20,000\n"
            "Gross sales: R\\${gross:,.0f} this month\\. Avoid additional BRL sales\\."
        ),
        "fx_move": (
            "💱 *BRL WEAKENING ALERT*\n"
            "USD/BRL moved *{change:.1f}%* in 30 days \\(threshold: {threshold:.0%}\\)\\.\n"
            "Brazil sleeve returns affected in USD terms\\."
        ),
        "correlation": (
            "📊 *HIGH CORRELATION DETECTED*\n"
            "Diversification may be breaking down:\n{pairs}\n"
            "Consider reducing correlated positions\\."
        ),
        "deposit": (
            "💰 *DEPOSIT DETECTED*\n"
            "{count} deposit\\(s\\) totaling ${total:,.0f}\n"
            "Run /run\\_allocation to optimally route new funds\\."
        ),
    }

    template = templates.get(alert_type, "🔔 *ALERT*\n{details}")

    try:
        if alert_type == "drawdown":
            msg = template.format(
                drawdown_pct=abs(payload.get("drawdown_pct", 0)) * 100,
                threshold=payload.get("threshold", 0.25),
            )
        elif alert_type == "drift":
            sleeves_text = "\n".join(
                f"  • {esc(s['sleeve'])}: {s['drift']*100:+.1f}%"
                for s in payload.get("breached_sleeves", [])
            )
            msg = template.format(sleeves=sleeves_text)
        elif alert_type == "opportunity":
            msg = template.format(
                tier=payload.get("tier", 1),
                asset=esc(payload.get("asset", "Unknown")),
                drawdown_pct=abs(payload.get("drawdown_pct", 0)) * 100,
                mos_pct=payload.get("margin_of_safety_pct", 0) * 100,
            )
        elif alert_type == "sell_target":
            symbols = ", ".join(payload.get("symbols_at_sell_target", []))
            msg = template.format(symbols=esc(symbols))
        elif alert_type == "brazil_darf":
            msg = template.format(
                pct=payload.get("progress_pct", 0) * 100,
                gross=payload.get("gross_sales_brl", 0),
            )
        elif alert_type == "fx_move":
            msg = template.format(
                change=payload.get("change_30d", 0) * 100,
                threshold=payload.get("threshold", 0.10),
            )
        elif alert_type == "correlation":
            pairs_text = "\n".join(
                f"  • {esc(p['sleeves'])}: {p['correlation']:.2f}"
                for p in payload.get("high_correlation_pairs", [])
            )
            msg = template.format(pairs=pairs_text)
        elif alert_type == "deposit":
            msg = template.format(
                count=payload.get("deposit_count", 1),
                total=payload.get("total_amount", 0),
            )
        else:
            msg = f"=🔔 *ALERT \\({esc(alert_type)}\\)*\n{esc(str(payload))}"
    except Exception as exc:
        logger.warning("Alert message format failed for type=%s: %s", alert_type, exc)
        msg = f"=🔔 Alert: {esc(alert_type)}"

    msg += f"\n\n_OvelhaInvest — http://ovelhainvest\\.local_"
    return msg


async def dispatch_alert(
    alert: dict[str, Any],
    channel: str = "telegram",
    inline_keyboard: list[list[dict[str, Any]]] | None = None,
) -> bool:
    """
    Dispatch a triggered alert to the configured channel.

    Stores result in alert_history via supabase on success.

    Args:
        alert: Triggered alert dict from evaluate_all_rules().
        channel: "telegram" (only channel supported in Phase 5).
        inline_keyboard: Optional Telegram inline keyboard markup.

    Returns:
        True if dispatched successfully.
    """
    if channel != "telegram":
        logger.warning("Unsupported alert channel: %s", channel)
        return False

    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        logger.info("Telegram not configured — alert suppressed: %s", alert.get("rule_name"))
        return False

    message = format_alert_message(alert.get("type", ""), alert.get("payload", {}))
    success = await send_telegram_alert(
        message=message,
        chat_id=settings.telegram_chat_id,
        bot_token=settings.telegram_bot_token,
        inline_keyboard=inline_keyboard,
    )

    # Log to alert_history
    try:
        from app.db.supabase_client import get_supabase_client
        client = get_supabase_client()
        client.table("alert_history").insert({
            "alert_rule_id": alert.get("rule_id", "00000000-0000-0000-0000-000000000001"),
            "triggered_at": datetime.now(timezone.utc).isoformat(),
            "payload": alert.get("payload", {}),
            "channel": channel,
            "delivered": success,
        }).execute()
    except Exception as exc:
        logger.debug("alert_history insert failed (non-critical): %s", exc)

    return success


async def send_telegram_alert(
    message: str,
    chat_id: str,
    bot_token: str,
    inline_keyboard: list[list[dict[str, Any]]] | None = None,
) -> bool:
    """
    Send a Telegram message via Bot API.

    Args:
        message: MarkdownV2 formatted text.
        chat_id: Telegram chat ID.
        bot_token: Bot API token.
        inline_keyboard: Optional inline keyboard for approval flows.

    Returns:
        True if delivered successfully.
    """
    url = f"{TELEGRAM_API_BASE}/bot{bot_token}/sendMessage"
    payload: dict[str, Any] = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "MarkdownV2",
        "disable_web_page_preview": True,
    }
    if inline_keyboard:
        payload["reply_markup"] = {"inline_keyboard": inline_keyboard}

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                logger.info("Telegram alert sent to chat_id=%s", chat_id)
                return True
            else:
                logger.error(
                    "Telegram API error %d: %s", resp.status_code, resp.text[:200]
                )
                return False
    except httpx.TimeoutException:
        logger.error("Telegram send timed out")
        return False
    except Exception as exc:
        logger.error("Telegram send failed: %s", exc)
        return False


async def handle_telegram_callback(
    callback_query: dict[str, Any],
    user_id: str = "00000000-0000-0000-0000-000000000001",
) -> dict[str, Any]:
    """
    Process approve/reject callbacks from Telegram inline keyboard.

    Args:
        callback_query: Full Telegram callback_query object.
        user_id: User UUID for authorization.

    Returns:
        Updated signal run dict.
    """
    from app.db.supabase_client import get_supabase_client

    callback_data = callback_query.get("data", "")
    callback_id = callback_query.get("id", "")
    chat_id = callback_query.get("message", {}).get("chat", {}).get("id", "")

    if ":" not in callback_data:
        logger.warning("Invalid callback_data format: %s", callback_data)
        return {"error": "invalid_callback"}

    action, run_id = callback_data.split(":", 1)
    action = action.lower()

    if action not in ("approve", "reject"):
        return {"error": f"unknown_action:{action}"}

    new_status = "approved" if action == "approve" else "rejected"

    try:
        client = get_supabase_client()
        resp = (
            client.table("signals_runs")
            .update({"status": new_status})
            .eq("id", run_id)
            .eq("user_id", user_id)
            .execute()
        )
        updated = resp.data[0] if resp.data else {"id": run_id, "status": new_status}

        # Answer the callback (removes loading state in Telegram)
        if settings.telegram_bot_token and callback_id:
            confirmation = f"Trades {new_status}!" if action == "approve" else "Trades rejected."
            try:
                async with httpx.AsyncClient(timeout=5.0) as http:
                    await http.post(
                        f"{TELEGRAM_API_BASE}/bot{settings.telegram_bot_token}/answerCallbackQuery",
                        json={"callback_query_id": callback_id, "text": confirmation},
                    )
                    if chat_id:
                        await http.post(
                            f"{TELEGRAM_API_BASE}/bot{settings.telegram_bot_token}/sendMessage",
                            json={
                                "chat_id": str(chat_id),
                                "text": f"*{confirmation}*\nRun ID: `{run_id[:8]}...`",
                                "parse_mode": "MarkdownV2",
                            },
                        )
            except Exception as exc:
                logger.debug("Telegram answer callback failed (non-critical): %s", exc)

        logger.info("Telegram callback: action=%s run_id=%s -> status=%s", action, run_id, new_status)
        return updated

    except Exception as exc:
        logger.error("handle_telegram_callback failed: %s", exc)
        return {"error": str(exc)}
