"""
Alert engine — rule evaluation + Telegram dispatch.

Phase 6: fully implemented evaluators for all 11 rule types.
Each evaluator reads conditions from the rule dict, checks cooldowns via
alert_history, and returns a rich payload for Telegram formatting.
"""

from __future__ import annotations

import logging
import re
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

DEFAULT_COOLDOWN_HOURS = 6
TELEGRAM_API_BASE = "https://api.telegram.org"
DARF_MONTHLY_EXEMPTION_BRL = 20_000.0


# ── Redis helpers (graceful fallback if Redis unavailable) ────────────────────

def _redis_get(key: str) -> str | None:
    try:
        from app.db.redis_client import get_redis_client
        return get_redis_client().get(key)
    except Exception:
        return None


def _redis_set(key: str, value: str, ex: int | None = None) -> None:
    try:
        from app.db.redis_client import get_redis_client
        get_redis_client().set(key, value, ex=ex)
    except Exception as exc:
        logger.debug("Redis set failed (non-critical): %s", exc)


def _redis_delete(key: str) -> None:
    try:
        from app.db.redis_client import get_redis_client
        get_redis_client().delete(key)
    except Exception as exc:
        logger.debug("Redis delete failed (non-critical): %s", exc)


def is_automation_paused() -> bool:
    """Return True if automation is paused (drawdown >= 40% or manual pause)."""
    return _redis_get("automation_paused") is not None


def set_automation_paused(reason: str = "drawdown") -> None:
    """Pause automation; sets Redis key indefinitely (cleared by /admin/resume)."""
    _redis_set("automation_paused", reason)
    logger.warning("AUTOMATION PAUSED — reason=%s", reason)


def clear_automation_paused() -> None:
    """Resume automation by clearing the Redis key."""
    _redis_delete("automation_paused")
    logger.info("Automation resumed — Redis key cleared")


# ── MarkdownV2 escaper ────────────────────────────────────────────────────────

def _esc(s: str | int | float) -> str:
    """Escape a string for Telegram MarkdownV2."""
    return re.sub(r"([_*\[\]()~`>#\+\-=|{}.!])", r"\\\1", str(s))


# ── Rule evaluators ───────────────────────────────────────────────────────────

def _eval_drawdown(conditions: dict, portfolio_state: dict) -> dict | None:
    threshold = conditions.get("threshold", 0.25)
    current_dd = abs(portfolio_state.get("max_drawdown", 0.0))
    if current_dd < threshold:
        return None

    current_value = portfolio_state.get("total_value_usd", 0.0)
    peak_value = portfolio_state.get("portfolio_value_at_peak", current_value)
    is_pause_trigger = conditions.get("action") == "pause_runs" or current_dd >= 0.40

    if is_pause_trigger:
        set_automation_paused("drawdown")

    return {
        "drawdown_pct": current_dd,
        "threshold": threshold,
        "current_value_usd": current_value,
        "portfolio_value_at_peak": peak_value,
        "automation_paused": is_pause_trigger,
        "recovery_needed_pct": round(current_dd / (1 - current_dd), 4) if current_dd < 1 else 0,
    }


def _eval_drift(conditions: dict, portfolio_state: dict) -> dict | None:
    threshold = conditions.get("threshold", 0.05)
    sleeve_weights = portfolio_state.get("sleeve_weights", [])
    breached = [
        {
            "sleeve": s.get("sleeve", ""),
            "current_weight": s.get("current_weight", 0.0),
            "target_weight": s.get("target_weight", 0.0),
            "drift": s.get("drift", 0.0),
            "drift_pct": s.get("drift_pct", 0.0),
            "proposed_action": "buy" if s.get("drift", 0.0) < 0 else "trim",
        }
        for s in sleeve_weights
        if abs(s.get("drift", 0.0)) >= threshold
    ]
    if not breached:
        return None
    return {"breached_sleeves": breached, "threshold": threshold, "count": len(breached)}


def _eval_opportunity(conditions: dict, portfolio_state: dict) -> dict | None:
    tier = conditions.get("tier", 1)
    key = f"opportunity_tier_{tier}"
    if not portfolio_state.get(key, False):
        return None
    asset = portfolio_state.get(f"opportunity_tier_{tier}_asset", "")
    drawdown = portfolio_state.get(f"opportunity_tier_{tier}_drawdown", 0.0)
    mos = portfolio_state.get(f"opportunity_tier_{tier}_mos", 0.0)
    opp_vault = portfolio_state.get("opportunity_vault_balance_usd", 0.0)
    deploy_frac = 0.20 if tier == 1 else 0.30
    deploy_usd = opp_vault * deploy_frac

    return {
        "tier": tier,
        "asset_symbol": asset,
        "drawdown_pct": drawdown,
        "margin_of_safety_pct": mos,
        "vault_balance_usd": opp_vault,
        "vault_recommended_deployment": deploy_frac,
        "vault_deployment_usd": round(deploy_usd, 2),
        "ai_commentary": portfolio_state.get(f"opportunity_tier_{tier}_ai_commentary", ""),
    }


def _eval_sell_target(conditions: dict, portfolio_state: dict) -> dict | None:  # noqa: ARG001
    targets_hit = portfolio_state.get("held_assets_at_sell_target", [])
    if not targets_hit:
        return None
    # targets_hit: list of dicts with symbol, current_price, sell_target, etc.
    if isinstance(targets_hit, list) and targets_hit and isinstance(targets_hit[0], str):
        # legacy: list of symbols only
        targets_hit = [{"symbol": s} for s in targets_hit]
    return {"assets": targets_hit[:5], "count": len(targets_hit)}


def _eval_earnings(conditions: dict, portfolio_state: dict) -> dict | None:
    days_ahead = conditions.get("days_ahead", 3)
    # portfolio_state["upcoming_earnings"] is populated by run_allocation or n8n
    upcoming = portfolio_state.get("upcoming_earnings", [])
    # Also try Finnhub if configured
    if not upcoming and settings.finnhub_api_key:
        upcoming = _fetch_finnhub_earnings(
            portfolio_state.get("held_symbols", []), days_ahead
        )
    alerts = [e for e in upcoming if e.get("days_until", 999) <= days_ahead]
    if not alerts:
        return None
    return {"upcoming": alerts[:5], "days_ahead": days_ahead}


def _fetch_finnhub_earnings(symbols: list[str], days_ahead: int) -> list[dict]:
    """Fetch earnings calendar from Finnhub for held symbols. Returns [] on failure."""
    if not symbols or not settings.finnhub_api_key:
        return []
    try:
        from datetime import date
        today = date.today()
        end = today + timedelta(days=days_ahead)
        import httpx as _httpx
        resp = _httpx.get(
            "https://finnhub.io/api/v1/calendar/earnings",
            params={"from": today.isoformat(), "to": end.isoformat(),
                    "token": settings.finnhub_api_key},
            timeout=8.0,
        )
        if resp.status_code != 200:
            return []
        data = resp.json().get("earningsCalendar", [])
        held_upper = {s.upper() for s in symbols}
        results = []
        for item in data:
            if item.get("symbol", "").upper() not in held_upper:
                continue
            try:
                ed = date.fromisoformat(item["date"])
                days = (ed - today).days
            except Exception:
                days = 999
            results.append({
                "symbol": item.get("symbol"),
                "earnings_date": item.get("date"),
                "days_until": days,
                "expected_eps": item.get("epsEstimate"),
                "prior_eps": item.get("epsPrior"),
            })
        return results
    except Exception as exc:
        logger.debug("Finnhub earnings fetch failed (non-critical): %s", exc)
        return []


def _eval_brazil_darf(conditions: dict, portfolio_state: dict) -> dict | None:
    threshold_pct = conditions.get("threshold_pct", 0.80)
    # Try DB first; fall back to portfolio_state
    gross_sales = portfolio_state.get("darf_gross_sales_brl", 0.0)
    if not gross_sales:
        gross_sales = _fetch_darf_month_sales()
    progress = gross_sales / DARF_MONTHLY_EXEMPTION_BRL
    if progress < threshold_pct:
        return None
    remaining = max(DARF_MONTHLY_EXEMPTION_BRL - gross_sales, 0.0)
    return {
        "gross_sales_brl": round(gross_sales, 2),
        "threshold_brl": DARF_MONTHLY_EXEMPTION_BRL,
        "progress_pct": round(progress, 4),
        "threshold_pct": threshold_pct,
        "remaining_before_darf": round(remaining, 2),
        "month": datetime.now(timezone.utc).strftime("%Y-%m"),
    }


def _fetch_darf_month_sales() -> float:
    """Query brazil_darf_tracker for current month's gross sales."""
    try:
        from app.db.supabase_client import get_supabase_client
        now = datetime.now(timezone.utc)
        resp = (
            get_supabase_client()
            .table("brazil_darf_tracker")
            .select("gross_sales_brl")
            .eq("year", now.year)
            .eq("month", now.month)
            .limit(1)
            .execute()
        )
        if resp.data:
            return float(resp.data[0].get("gross_sales_brl", 0.0))
    except Exception as exc:
        logger.debug("DARF DB fetch failed (non-critical): %s", exc)
    return 0.0


def _eval_fx_move(conditions: dict, portfolio_state: dict) -> dict | None:
    threshold = conditions.get("threshold", 0.10)
    change = portfolio_state.get("usd_brl_30d_change", 0.0)
    if abs(change) < threshold:
        return None
    current_rate = portfolio_state.get("usd_brl_rate", 0.0)
    prior_rate = current_rate / (1 + change) if change != -1 else current_rate
    brazil_sleeve_usd = portfolio_state.get("brazil_sleeve_value_usd", 0.0)
    impact_usd = brazil_sleeve_usd * change if brazil_sleeve_usd else 0.0
    return {
        "pair": "USDBRL",
        "current_rate": round(current_rate, 4),
        "rate_30d_ago": round(prior_rate, 4),
        "change_pct": round(change, 4),
        "threshold": threshold,
        "brazil_sleeve_impact_usd": round(impact_usd, 2),
    }


def _eval_correlation(conditions: dict, portfolio_state: dict) -> dict | None:
    threshold = conditions.get("threshold", 0.85)
    pairs = portfolio_state.get("correlation_pairs", [])
    high = []
    for p in pairs:
        corr = abs(p.get("correlation", 0.0))
        if corr >= threshold:
            # Normalise to sleeve_a / sleeve_b format
            sleeves = p.get("sleeves", "")
            if isinstance(sleeves, str) and "/" in sleeves:
                a, b = sleeves.split("/", 1)
            elif isinstance(p.get("sleeve_a"), str):
                a, b = p["sleeve_a"], p.get("sleeve_b", "")
            else:
                a, b = str(sleeves), ""
            high.append({"sleeve_a": a.strip(), "sleeve_b": b.strip(),
                          "correlation": round(corr, 3),
                          "diversification_concern": corr >= 0.90})
    if not high:
        return None
    return {"high_correlation_pairs": high[:3], "threshold": threshold}


def _eval_deposit(conditions: dict, portfolio_state: dict) -> dict | None:  # noqa: ARG001
    deposits = portfolio_state.get("recent_deposits", [])
    # Also check if SoFi vault balance increased since last snapshot
    sofi_delta = portfolio_state.get("sofi_balance_delta_usd", 0.0)
    if not deposits and sofi_delta <= 0:
        return None
    total = sum(d.get("amount", 0) for d in deposits) + max(sofi_delta, 0)
    return {
        "deposit_count": len(deposits) + (1 if sofi_delta > 0 and not deposits else 0),
        "total_amount_usd": round(total, 2),
        "detected_at": datetime.now(timezone.utc).isoformat(),
        "suggested_vault_allocation": {
            "future_investments": round(total * 0.80, 2),
            "opportunity": round(total * 0.15, 2),
            "cash_buffer": round(total * 0.05, 2),
        },
    }


# ── Master evaluator ──────────────────────────────────────────────────────────

_EVALUATORS = {
    "drawdown":    _eval_drawdown,
    "drift":       _eval_drift,
    "opportunity": _eval_opportunity,
    "sell_target": _eval_sell_target,
    "earnings":    _eval_earnings,
    "brazil_darf": _eval_brazil_darf,
    "fx_move":     _eval_fx_move,
    "correlation": _eval_correlation,
    "deposit":     _eval_deposit,
}


def evaluate_all_rules(
    portfolio_state: dict[str, Any],
    alert_rules: list[dict[str, Any]],
    recent_history: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """
    Evaluate all active alert rules against current portfolio state.

    Each rule reads conditions from the rule dict and checks cooldowns via
    recent_history (alert_history rows). Returns triggered alert dicts.
    """
    recent_history = recent_history or []

    # Cooldown index: rule_name -> last_triggered_at (UTC)
    cooldown_map: dict[str, datetime] = {}
    for h in recent_history:
        rule_name = h.get("rule_name") or (h.get("alert_rules") or {}).get("rule_name", "")
        ts_str = h.get("triggered_at", "")
        if ts_str and rule_name:
            try:
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                if rule_name not in cooldown_map or ts > cooldown_map[rule_name]:
                    cooldown_map[rule_name] = ts
            except ValueError:
                pass

    now = datetime.now(timezone.utc)
    triggered: list[dict[str, Any]] = []

    for rule in alert_rules:
        rule_name = rule.get("name", "")
        rule_type = rule.get("type", rule.get("rule_type", ""))
        conditions = rule.get("conditions", {})
        is_active = rule.get("is_active", True)

        if not is_active:
            continue

        # Cooldown check
        last_triggered = cooldown_map.get(rule_name)
        if last_triggered:
            cooldown_h = conditions.get("cooldown_hours", DEFAULT_COOLDOWN_HOURS)
            if (now - last_triggered).total_seconds() < cooldown_h * 3600:
                continue

        evaluator = _EVALUATORS.get(rule_type)
        if evaluator is None:
            continue

        try:
            payload = evaluator(conditions, portfolio_state)
        except Exception as exc:
            logger.error("Alert evaluator %s failed: %s", rule_type, exc)
            continue

        if payload is None:
            continue

        priority = rule.get("priority", "MEDIUM")
        if rule_type == "drawdown" and payload.get("drawdown_pct", 0) >= 0.40:
            priority = "CRITICAL"

        triggered.append({
            "rule_id": rule.get("id", f"builtin-{rule_type}"),
            "rule_name": rule_name,
            "type": rule_type,
            "priority": priority,
            "channel": rule.get("channel", "telegram"),
            "payload": payload,
        })

    return triggered


# ── Rich Telegram message formatters ─────────────────────────────────────────

def _fmt_drawdown(payload: dict) -> str:
    pct = payload.get("drawdown_pct", 0) * 100
    threshold = payload.get("threshold", 0.25) * 100
    current = payload.get("current_value_usd", 0)
    peak = payload.get("portfolio_value_at_peak", current)
    paused = payload.get("automation_paused", False)

    lines = [
        f"🔴 *DRAWDOWN ALERT — {_esc(f'{pct:.1f}')}%*",
        f"Portfolio has dropped *{_esc(f'{pct:.1f}')}%* from peak\\.",
        f"Peak value: {_esc(f'${peak:,.0f}')} → Current: {_esc(f'${current:,.0f}')}",
    ]
    if paused:
        lines.append("⛔ *AUTOMATION PAUSED* — manual override required\\.")
        lines.append("Use /admin/resume to re\\-enable scheduled runs\\.")
    lines.append(f"_Threshold: {_esc(f'{threshold:.0f}')}%_")
    return "\n".join(lines)


def _fmt_drift(payload: dict) -> str:
    sleeves = payload.get("breached_sleeves", [])
    parts = []
    for s in sleeves:
        cur = _esc(f"{s.get('current_weight', 0)*100:.1f}")
        tgt = _esc(f"{s.get('target_weight', 0)*100:.1f}")
        dft = _esc(f"{s.get('drift', 0)*100:+.1f}")
        slv = _esc(s.get("sleeve", ""))
        parts.append(f"  • {slv}: {cur}% vs target {tgt}% \\({dft}%\\)")
    sleeve_lines = "\n".join(parts)
    count = _esc(payload.get("count", len(sleeves)))
    threshold = _esc(f"{payload.get('threshold', 0.05)*100:.0f}")
    return (
        f"⚖️ *SLEEVE DRIFT BREACH*\n"
        f"{count} sleeve\\(s\\) outside ±{threshold}% band:\n"
        f"{sleeve_lines}\n"
        f"Run /run\\_allocation to rebalance\\."
    )


def _fmt_opportunity(payload: dict) -> str:
    tier = payload.get("tier", 1)
    symbol = payload.get("asset_symbol", "Unknown")
    drawdown = payload.get("drawdown_pct", 0) * 100
    mos = payload.get("margin_of_safety_pct", 0) * 100
    deploy_pct = payload.get("vault_recommended_deployment", 0) * 100
    deploy_usd = payload.get("vault_deployment_usd", 0)
    commentary = payload.get("ai_commentary", "")

    lines = [
        f"🎯 *TIER {_esc(tier)} OPPORTUNITY — {_esc(symbol)}*",
        f"Drawdown from 6\\-12mo high: *{_esc(f'{drawdown:.1f}')}%*",
        f"Margin of safety: *{_esc(f'{mos:.1f}')}%*",
        f"Recommended deployment: {_esc(f'{deploy_pct:.0f}')}% of Opportunity Vault \\(~{_esc(f'${deploy_usd:,.0f}')}\\)",
    ]
    if commentary:
        lines.append(f"_{_esc(commentary[:120])}_")
    return "\n".join(lines)


def _fmt_sell_target(payload: dict) -> str:
    assets = payload.get("assets", [])
    lines = ["💰 *SELL TARGET REACHED*"]
    for a in assets[:3]:
        sym = a.get("symbol", "?")
        price = a.get("current_price", 0)
        target = a.get("sell_target", 0)
        gain = a.get("unrealized_gain_pct", 0) * 100
        tax = a.get("estimated_tax_impact", 0)
        lines.append(
            f"• *{_esc(sym)}*: {_esc(f'${price:.2f}')} → target {_esc(f'${target:.2f}')} "
            f"\\| gain: {_esc(f'+{gain:.1f}')}% \\| est\\. tax: {_esc(f'${tax:,.0f}')}"
        )
    return "\n".join(lines)


def _fmt_earnings(payload: dict) -> str:
    upcoming = payload.get("upcoming", [])
    if not upcoming:
        return "📅 *EARNINGS ALERT*\nUpcoming earnings for held positions\\."
    item = upcoming[0]
    days = item.get("days_until", "?")
    sym = item.get("symbol", "?")
    edate = item.get("earnings_date", "?")
    eps_est = item.get("expected_eps")
    prior = item.get("prior_eps")
    lines = [
        f"📅 *EARNINGS IN {_esc(days)} DAYS — {_esc(sym)}*",
        f"Date: {_esc(edate)}",
    ]
    if eps_est is not None:
        lines.append(f"Expected EPS: {_esc(f'${eps_est}')}")
    if prior is not None:
        lines.append(f"Prior quarter: {_esc(f'${prior}')}")
    if len(upcoming) > 1:
        others = ", ".join(_esc(u["symbol"]) for u in upcoming[1:3])
        lines.append(f"Also upcoming: {others}")
    return "\n".join(lines)


def _fmt_darf(payload: dict) -> str:
    pct = payload.get("progress_pct", 0) * 100
    gross = payload.get("gross_sales_brl", 0)
    remaining = payload.get("remaining_before_darf", 0)
    month = payload.get("month", "")
    return (
        f"🇧🇷 *DARF WARNING — {_esc(f'{pct:.0f}')}% of exemption used*\n"
        f"Gross sales this month: R\\${_esc(f'{gross:,.0f}')} / R\\$20,000\n"
        f"Remaining before tax trigger: R\\${_esc(f'{remaining:,.0f}')}\n"
        f"Month: {_esc(month)} — avoid additional BRL stock sales\\."
    )


def _fmt_fx(payload: dict) -> str:
    change = payload.get("change_pct", 0) * 100
    current = payload.get("current_rate", 0)
    prior = payload.get("rate_30d_ago", 0)
    impact = payload.get("brazil_sleeve_impact_usd", 0)
    direction = "weakened" if change > 0 else "strengthened"
    sign = "+" if change >= 0 else ""
    return (
        f"💱 *BRL/USD MOVED {_esc(f'{sign}{change:.1f}')}% in 30 days*\n"
        f"BRL has {_esc(direction)} vs USD\\.\n"
        f"Rate: {_esc(f'{current:.4f}')} \\(was {_esc(f'{prior:.4f}')}\\)\n"
        f"Brazil sleeve impact: {_esc(f'{impact:+.0f}')} USD"
    )


def _fmt_correlation(payload: dict) -> str:
    pairs = payload.get("high_correlation_pairs", [])
    threshold = payload.get("threshold", 0.85)
    lines = [f"⚠️ *CORRELATION SPIKE — Diversification Risk*"]
    for p in pairs[:2]:
        a, b = p.get("sleeve_a", "?"), p.get("sleeve_b", "?")
        corr = p.get("correlation", 0)
        lines.append(
            f"• {_esc(a)} ↔ {_esc(b)}: {_esc(f'{corr:.2f}')} \\(threshold: {_esc(f'{threshold:.2f}')}\\)"
        )
    lines.append("Diversification benefit reduced — consider reviewing allocation\\.")
    return "\n".join(lines)


def _fmt_deposit(payload: dict) -> str:
    count = payload.get("deposit_count", 1)
    total = payload.get("total_amount_usd", 0)
    alloc = payload.get("suggested_vault_allocation", {})
    lines = [
        f"💰 *DEPOSIT DETECTED*",
        f"{_esc(count)} deposit\\(s\\) totaling {_esc(f'${total:,.0f}')}",
    ]
    if alloc:
        fi = alloc.get("future_investments", 0)
        opp = alloc.get("opportunity", 0)
        lines.append(f"Suggested routing: {_esc(f'${fi:,.0f}')} → Future Investments, {_esc(f'${opp:,.0f}')} → Opportunity Vault")
    lines.append("Run /run\\_allocation to optimally route new funds\\.")
    return "\n".join(lines)


_FORMATTERS = {
    "drawdown":    _fmt_drawdown,
    "drift":       _fmt_drift,
    "opportunity": _fmt_opportunity,
    "sell_target": _fmt_sell_target,
    "earnings":    _fmt_earnings,
    "brazil_darf": _fmt_darf,
    "fx_move":     _fmt_fx,
    "correlation": _fmt_correlation,
    "deposit":     _fmt_deposit,
}


def format_alert_message(alert_type: str, payload: dict[str, Any]) -> str:
    """Format a Telegram alert message in MarkdownV2 from alert type + payload."""
    formatter = _FORMATTERS.get(alert_type)
    try:
        if formatter:
            msg = formatter(payload)
        else:
            msg = f"🔔 *ALERT \\({_esc(alert_type)}\\)*\n{_esc(str(payload))}"
    except Exception as exc:
        logger.warning("Alert format failed type=%s: %s", alert_type, exc)
        msg = f"🔔 Alert: {_esc(alert_type)}"

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    msg += f"\n\n_{_esc(now_str)} — OvelhaInvest_"
    return msg


# ── Dispatch ──────────────────────────────────────────────────────────────────

async def dispatch_alert(
    alert: dict[str, Any],
    channel: str = "telegram",
    inline_keyboard: list[list[dict[str, Any]]] | None = None,
) -> bool:
    """
    Format and dispatch a triggered alert to the configured channel.
    Logs result to alert_history. Never raises — returns False on failure.
    """
    if channel != "telegram":
        logger.warning("Unsupported alert channel: %s", channel)
        return False

    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        logger.info("Telegram not configured — alert suppressed: %s", alert.get("rule_name"))
        return False

    alert_type = alert.get("type", "")
    payload = alert.get("payload", {})

    # Auto-attach approval keyboard for opportunity alerts
    if inline_keyboard is None and alert_type == "opportunity":
        run_id = payload.get("run_id", "")
        if run_id:
            inline_keyboard = [[
                {"text": "✅ Approve", "callback_data": f"approve:{run_id}"},
                {"text": "❌ Reject",  "callback_data": f"reject:{run_id}"},
            ]]

    message = format_alert_message(alert_type, payload)
    success = await send_telegram_alert(
        message=message,
        chat_id=settings.telegram_chat_id,
        bot_token=settings.telegram_bot_token,
        inline_keyboard=inline_keyboard,
    )

    # Write to alert_history
    try:
        from app.db.supabase_client import get_supabase_client
        get_supabase_client().table("alert_history").insert({
            "alert_rule_id": alert.get("rule_id", "00000000-0000-0000-0000-000000000001"),
            "triggered_at": datetime.now(timezone.utc).isoformat(),
            "payload": payload,
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
    """Send a MarkdownV2 Telegram message. Returns True on success."""
    url = f"{TELEGRAM_API_BASE}/bot{bot_token}/sendMessage"
    body: dict[str, Any] = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "MarkdownV2",
        "disable_web_page_preview": True,
    }
    if inline_keyboard:
        body["reply_markup"] = {"inline_keyboard": inline_keyboard}

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, json=body)
            if resp.status_code == 200:
                logger.info("Telegram alert sent to chat_id=%s", chat_id)
                return True
            logger.error("Telegram API error %d: %s", resp.status_code, resp.text[:200])
            return False
    except httpx.TimeoutException:
        logger.error("Telegram send timed out")
        return False
    except Exception as exc:
        logger.error("Telegram send failed: %s", exc)
        return False


# ── Telegram callback handler ─────────────────────────────────────────────────

def _wire_lot_tracking_for_run(client: Any, run_id: str, user_id: str) -> None:
    """
    After a signals_run is approved via Telegram, record tax lots for executed trades.

    - BUY trades in taxable/brazil_taxable accounts → open_lot()
    - SELL trades in taxable/brazil_taxable accounts → close_lots()
    - SELL trades in brazil_taxable accounts → update_brazil_darf()

    Tax-advantaged accounts (tax_deferred, tax_free) are skipped — lot tracking
    is irrelevant there. All errors are swallowed; lot tracking must never block approval.
    """
    from datetime import date, datetime as _dt
    from app.services.tax_lot_engine import open_lot, update_brazil_darf
    from app.services.market_data import fetch_current_prices

    # Fetch signals_run record
    run_resp = client.table("signals_runs").select("proposed_trades").eq("id", run_id).limit(1).execute()
    run_data = (run_resp.data or [{}])[0]
    proposed_trades: list[dict] = run_data.get("proposed_trades") or []
    if not proposed_trades:
        return

    # Build account tax_treatment map
    accts_resp = client.table("accounts").select("id, name, tax_treatment, currency").eq("user_id", user_id).execute()
    acct_map: dict[str, dict] = {}
    acct_name_map: dict[str, dict] = {}
    for a in (accts_resp.data or []):
        acct_map[a["id"]] = a
        acct_name_map[a["name"]] = a

    # Build asset_id map by symbol
    symbols = list({t.get("symbol", "") for t in proposed_trades if t.get("symbol")})
    assets_resp = client.table("assets").select("id, symbol").in_("symbol", symbols).execute()
    asset_id_map: dict[str, str] = {a["symbol"]: a["id"] for a in (assets_resp.data or [])}

    # Fetch current prices for quantity estimation
    prices = {}
    try:
        prices = fetch_current_prices(symbols)
    except Exception:
        pass

    today = date.today()

    for trade in proposed_trades:
        trade_type = str(trade.get("trade_type", "")).lower()
        symbol = str(trade.get("symbol", "")).upper()
        account_id = trade.get("account_id") or ""
        account_name = str(trade.get("account_name", ""))
        amount_usd = float(trade.get("amount_usd", 0.0))
        qty_est = float(trade.get("quantity_estimate") or 0.0)

        # Resolve account
        acct = acct_map.get(account_id) or acct_name_map.get(account_name) or {}
        tax_treatment = acct.get("tax_treatment", "")
        resolved_account_id = acct.get("id", account_id)

        # Only track lots for taxable accounts
        if tax_treatment not in ("taxable", "brazil_taxable"):
            continue

        asset_id = asset_id_map.get(symbol, "")
        if not resolved_account_id or not asset_id:
            continue

        current_price = prices.get(symbol) or (amount_usd / qty_est if qty_est > 0 else 0.0)
        if current_price <= 0:
            continue

        if trade_type == "buy":
            quantity = qty_est if qty_est > 0 else (amount_usd / current_price)
            try:
                open_lot(
                    account_id=resolved_account_id,
                    asset_id=asset_id,
                    symbol=symbol,
                    quantity=quantity,
                    price=current_price,
                    acquisition_date=today,
                    db=client,
                )
                logger.info("Lot opened: %s qty=%.4f acct=%s", symbol, quantity, resolved_account_id)
            except Exception as exc:
                logger.warning("open_lot failed symbol=%s: %s", symbol, exc)

        elif trade_type in ("sell", "rebalance") and trade.get("trade_type", "").lower() == "sell" or trade_type == "rebalance":
            # For rebalance sells, only close lots when trade_type is explicitly sell
            if trade_type != "sell":
                continue

            quantity = qty_est if qty_est > 0 else (amount_usd / current_price)
            try:
                from app.db.repositories.tax_lots import get_open_lots
                open_lots = get_open_lots(db=client, account_id=resolved_account_id, symbol=symbol)
                from app.services.tax_lot_engine import close_lots, LotMethod
                closed = close_lots(
                    lots_to_close=open_lots,
                    current_price=current_price,
                    sale_date=today,
                    db=client,
                    quantity_override=quantity,
                )
                logger.info("Lots closed: %s qty=%.4f count=%d", symbol, quantity, len(closed))

                # Brazil DARF update
                if tax_treatment == "brazil_taxable":
                    try:
                        usd_brl = 5.70
                        try:
                            from app.services.fx_engine import fetch_usd_brl_rate
                            usd_brl = fetch_usd_brl_rate()
                        except Exception:
                            pass
                        sale_brl = amount_usd * usd_brl
                        gain_brl = sum(
                            float(c.get("realized_gain_loss", 0.0)) * usd_brl
                            for c in closed
                        )
                        update_brazil_darf(
                            user_id=user_id,
                            sale_amount_brl=sale_brl,
                            realized_gain_brl=gain_brl,
                            sale_date=today,
                            db=client,
                        )
                        logger.info("Brazil DARF updated: symbol=%s sale_brl=%.2f", symbol, sale_brl)
                    except Exception as exc:
                        logger.warning("Brazil DARF update failed: %s", exc)
            except Exception as exc:
                logger.warning("close_lots failed symbol=%s: %s", symbol, exc)


async def handle_telegram_callback(
    callback_query: dict[str, Any],
    user_id: str = "00000000-0000-0000-0000-000000000001",
) -> dict[str, Any]:
    """
    Process inline keyboard callbacks from Telegram.

    Supported callback_data formats:
      approve:{run_id}            — approve signal run
      reject:{run_id}             — reject signal run
      snooze:{alert_rule_id}:{days} — snooze an alert rule
    """
    from app.db.supabase_client import get_supabase_client

    callback_data = callback_query.get("data", "")
    callback_id = callback_query.get("id", "")
    chat_id = str(callback_query.get("message", {}).get("chat", {}).get("id", ""))

    parts = callback_data.split(":", 2)
    if len(parts) < 2:
        return {"error": "invalid_callback_format"}

    action = parts[0].lower()
    resource_id = parts[1]

    try:
        client = get_supabase_client()

        if action in ("approve", "reject"):
            new_status = "approved" if action == "approve" else "rejected"
            resp = (
                client.table("signals_runs")
                .update({"status": new_status})
                .eq("id", resource_id)
                .eq("user_id", user_id)
                .execute()
            )
            updated = resp.data[0] if resp.data else {"id": resource_id, "status": new_status}

            # Create journal entry
            action_type = "followed" if action == "approve" else "overrode"
            try:
                client.table("decision_journal").insert({
                    "user_id": user_id,
                    "signal_run_id": resource_id,
                    "action_type": action_type,
                    "reasoning": f"Telegram {action} callback",
                }).execute()
            except Exception as exc:
                logger.debug("Journal entry from callback failed: %s", exc)

            # ── Tax lot tracking on approve ──────────────────────────────────
            if action == "approve":
                try:
                    _wire_lot_tracking_for_run(client, resource_id, user_id)
                except Exception as exc_lot:
                    logger.warning("Lot tracking post-approve failed (non-critical): %s", exc_lot)

            confirmation = f"✅ Trades approved\\!" if action == "approve" else "❌ Trades rejected\\."
            result = updated

        elif action == "snooze":
            days = int(parts[2]) if len(parts) > 2 else 7
            # Insert snooze as delivered alert_history entry
            client.table("alert_history").insert({
                "alert_rule_id": resource_id,
                "triggered_at": datetime.now(timezone.utc).isoformat(),
                "payload": {"snoozed_days": days},
                "channel": "telegram",
                "delivered": True,
            }).execute()
            # Optionally update last_triggered on the rule
            client.table("alert_rules").update({
                "last_triggered": datetime.now(timezone.utc).isoformat()
            }).eq("id", resource_id).execute()
            confirmation = f"🔕 Alert snoozed for {days} days\\."
            result = {"snoozed": True, "days": days}
        else:
            return {"error": f"unknown_action:{action}"}

        # Answer callback to remove Telegram loading state
        if settings.telegram_bot_token and callback_id:
            plain_confirmation = confirmation.replace("\\", "").replace("*", "")
            try:
                async with httpx.AsyncClient(timeout=5.0) as http:
                    await http.post(
                        f"{TELEGRAM_API_BASE}/bot{settings.telegram_bot_token}/answerCallbackQuery",
                        json={"callback_query_id": callback_id, "text": plain_confirmation},
                    )
                    if chat_id:
                        await http.post(
                            f"{TELEGRAM_API_BASE}/bot{settings.telegram_bot_token}/sendMessage",
                            json={"chat_id": chat_id, "text": confirmation,
                                  "parse_mode": "MarkdownV2"},
                        )
            except Exception as exc:
                logger.debug("Telegram answer callback failed: %s", exc)

        logger.info("Telegram callback: action=%s id=%s", action, resource_id)
        return result

    except Exception as exc:
        logger.error("handle_telegram_callback failed: %s", exc)
        return {"error": str(exc)}


def _esc_md(text: str) -> str:
    """Escape MarkdownV2 special characters for Telegram."""
    return re.sub(r"([_*\[\]()~`>#+=|{}.!\\-])", r"\\\1", str(text))


async def send_journal_daily_line(
    journal_stats: dict[str, Any],
    chat_id: str,
    bot_token: str,
) -> bool:
    """
    Append a journal accuracy line to the daily digest message.

    Sends a standalone mini-message summarising decision tracking.
    Called from run_allocation flow after the main digest.

    Args:
        journal_stats: Output of GET /journal/stats (followed/overrode counts + outcomes).
        chat_id: Telegram chat ID.
        bot_token: Telegram bot token.

    Returns:
        True if sent successfully.
    """
    followed = journal_stats.get("followed_count", 0)
    overrode = journal_stats.get("overrode_count", 0)
    total    = followed + overrode

    if total == 0:
        return True  # nothing to report yet

    delta30 = journal_stats.get("system_outperformance_30d")
    f30     = journal_stats.get("avg_outcome_followed_30d")
    o30     = journal_stats.get("avg_outcome_overrode_30d")

    def _pct(v: float | None) -> str:
        if v is None:
            return "n/a"
        return f"{'+' if v >= 0 else ''}{v*100:.1f}%"

    lines = [
        "📓 *Decision Journal*",
        "",
        f"Decisions tracked: *{_esc_md(str(total))}*  \\({followed} followed / {overrode} overrode\\)",
    ]
    if f30 is not None or o30 is not None:
        lines.append(f"30d avg: followed *{_esc_md(_pct(f30))}* / overrode *{_esc_md(_pct(o30))}*")
    if delta30 is not None:
        edge_sign = "+" if delta30 >= 0 else ""
        lines.append(
            f"System edge: *{_esc_md(edge_sign + f'{delta30*100:.1f}%')}* vs overrides"
        )

    message = "\n".join(lines)
    return await send_telegram_alert(message=message, chat_id=chat_id, bot_token=bot_token)


async def send_journal_milestone_alert(
    milestone: str,
    detail: str,
    chat_id: str,
    bot_token: str,
) -> bool:
    """
    Send a one-off Telegram alert when a journal milestone is reached.

    Milestones: first_decision, 10_decisions, 25_decisions, 50_decisions,
                system_beating_user, user_beating_system.

    Args:
        milestone: Milestone key string.
        detail: Human-readable detail line (already escaped by caller if needed).
        chat_id: Telegram chat ID.
        bot_token: Telegram bot token.

    Returns:
        True if sent successfully.
    """
    milestone_emojis = {
        "first_decision": "🎉",
        "10_decisions":   "🔟",
        "25_decisions":   "📊",
        "50_decisions":   "🏆",
        "system_beating_user": "🤖",
        "user_beating_system": "🧠",
    }
    emoji = milestone_emojis.get(milestone, "📓")
    message = (
        f"{emoji} *Journal Milestone*\n\n"
        f"{_esc_md(detail)}\n\n"
        f"_View full analysis at /journal_"
    )
    return await send_telegram_alert(message=message, chat_id=chat_id, bot_token=bot_token)


async def check_and_send_journal_milestones(
    user_id: str,
    chat_id: str,
    bot_token: str,
) -> None:
    """
    Check for unannounced journal milestones and send Telegram alerts.

    Uses Redis to track which milestones have been announced.
    Silently skips if Redis or Supabase unavailable.
    """
    from app.db.repositories.journal import get_override_accuracy_stats

    try:
        stats = get_override_accuracy_stats(user_id)
        total = stats.get("total_decisions", 0)
        f30   = stats.get("avg_outcome_followed_30d")
        o30   = stats.get("avg_outcome_overrode_30d")
    except Exception as exc:
        logger.debug("check_and_send_journal_milestones: stats failed: %s", exc)
        return

    milestone_checks = [
        ("first_decision",   total >= 1,   "You've logged your first investment decision\\!"),
        ("10_decisions",     total >= 10,  f"You've tracked 10 investment decisions\\. Patterns are starting to emerge\\."),
        ("25_decisions",     total >= 25,  f"25 decisions tracked\\. You now have statistically meaningful behavioral data\\."),
        ("50_decisions",     total >= 50,  f"50 decisions tracked\\. Your journal is now a powerful self\\-improvement tool\\."),
        ("system_beating_user",
            f30 is not None and o30 is not None and (f30 - o30) > 0.05,
            f"The system is outperforming your overrides by {f30 - o30 if f30 and o30 else 0:.1%} on 30\\-day returns\\. Trust the process\\."),
        ("user_beating_system",
            f30 is not None and o30 is not None and (o30 - f30) > 0.05,
            f"Your overrides are outperforming the system by {o30 - f30 if f30 and o30 else 0:.1%}\\. Impressive instincts\\."),
    ]

    for milestone_key, condition, detail in milestone_checks:
        if not condition:
            continue
        cache_key = f"milestone_sent:{user_id}:{milestone_key}"
        already_sent = _redis_get(cache_key)
        if already_sent:
            continue
        try:
            sent = await send_journal_milestone_alert(
                milestone=milestone_key,
                detail=detail,
                chat_id=chat_id,
                bot_token=bot_token,
            )
            if sent:
                _redis_set(cache_key, "1", ex=365 * 24 * 3600)  # 1-year TTL
        except Exception as exc:
            logger.debug("Milestone send failed for %s: %s", milestone_key, exc)


async def register_telegram_webhook(base_url: str) -> bool:
    """Register the Telegram webhook URL with Bot API. Called on app startup in production."""
    if not settings.telegram_bot_token:
        return False
    webhook_url = f"{base_url.rstrip('/')}/webhooks/telegram"
    secret = settings.telegram_webhook_secret or settings.telegram_bot_token[-32:]
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{TELEGRAM_API_BASE}/bot{settings.telegram_bot_token}/setWebhook",
                json={"url": webhook_url, "secret_token": secret,
                      "allowed_updates": ["callback_query", "message"]},
            )
            if resp.status_code == 200 and resp.json().get("ok"):
                logger.info("Telegram webhook registered: %s", webhook_url)
                return True
            logger.error("Telegram setWebhook failed: %s", resp.text[:200])
            return False
    except Exception as exc:
        logger.error("Telegram setWebhook error: %s", exc)
        return False


# ── Keep-Alive ─────────────────────────────────────────────────────────────────

def write_keep_alive_ping(db, source: str = "run_allocation") -> None:
    """
    Write a keep-alive record after every successful /run_allocation.
    Prevents Supabase free tier from pausing due to inactivity.
    Fails silently — never blocks the main pipeline.
    """
    try:
        db.table("keep_alive_log").insert({
            "source": source,
            "pinged_at": datetime.now(timezone.utc).isoformat(),
        }).execute()
        logger.debug("keep_alive_log written (source=%s)", source)
    except Exception as exc:
        logger.debug("keep_alive_ping skipped (table may not exist yet): %s", exc)
