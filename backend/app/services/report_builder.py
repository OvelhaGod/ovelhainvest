"""
Report builder — daily digest + Telegram message formatter + opportunity alerts.

Formats structured data into human-readable Telegram messages.
PDF generation is Phase 9 (WeasyPrint).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from app.schemas.ai_models import AIResponse

logger = logging.getLogger(__name__)

APP_URL = "http://ovelhainvest.local"


# ── Data structures ────────────────────────────────────────────────────────

@dataclass
class DailyDigest:
    header: str
    net_worth: str
    regime: str
    proposed_trades: list[str]
    ai_summary: str
    framework_flags: list[str]
    alerts: list[str]
    footer: str
    needs_approval: bool = False
    approval_run_id: str | None = None


# ── Telegram MarkdownV2 helpers ────────────────────────────────────────────

_ESCAPE_CHARS = r"\_*[]()~`>#+-=|{}.!"

def _esc(text: str) -> str:
    """Escape special characters for Telegram MarkdownV2."""
    return re.sub(r"([" + re.escape(_ESCAPE_CHARS) + r"])", r"\\\1", str(text))


def _sign(val: float | None) -> str:
    if val is None:
        return "—"
    return f"+{val:.1f}%" if val >= 0 else f"{val:.1f}%"


def _sign_usd(val: float | None) -> str:
    if val is None:
        return "—"
    return f"+${val:,.0f}" if val >= 0 else f"-${abs(val):,.0f}"


# ── Framework emoji map ────────────────────────────────────────────────────

_STATUS_EMOJI = {"pass": "✅", "warning": "⚠️", "fail": "🚫", "ok": "✅", "block": "🚫"}

_FRAMEWORK_SHORT = {
    "swensen_alignment": "Swensen",
    "dalio_risk_balance": "Dalio",
    "graham_margin_of_safety": "Graham",
    "bogle_cost_check": "Bogle",
}


def _framework_flag_line(ai_response: AIResponse) -> str:
    """Produce a single line: '✅ Swensen | ⚠️ Marks | ✅ Graham | ✅ Dalio | ✅ Bogle'"""
    fc = ai_response.investment_framework_check
    parts = []
    for key, label in _FRAMEWORK_SHORT.items():
        status = getattr(fc, key, "pass")
        emoji = _STATUS_EMOJI.get(status, "❓")
        parts.append(f"{emoji} {label}")
    # Marks is free-text, derive pass/warning from marks_cycle_read content
    marks_read = fc.marks_cycle_read or ""
    marks_emoji = "⚠️" if any(w in marks_read.lower() for w in ("caution", "late", "overvalued", "bubble", "peak")) else "✅"
    parts.insert(2, f"{marks_emoji} Marks")
    return " | ".join(parts)


# ── Main builders ──────────────────────────────────────────────────────────

def build_daily_digest(
    daily_status: dict[str, Any],
    signals_run: dict[str, Any],
    ai_response: AIResponse,
) -> DailyDigest:
    """
    Build structured daily digest from portfolio status + AI response.

    Args:
        daily_status: Response from GET /daily_status.
        signals_run: Latest signals_run record from DB.
        ai_response: Validated AIResponse from call_ai_advisor().

    Returns:
        DailyDigest dataclass ready for Telegram formatting.
    """
    today_str = date.today().strftime("%b %d, %Y")
    total_usd = daily_status.get("total_value_usd", 0.0)
    ytd = daily_status.get("ytd_return_twr")
    today_pnl = daily_status.get("today_pnl_usd")

    net_worth_line = f"${total_usd:,.0f} USD"
    if today_pnl is not None:
        sign = "↑" if today_pnl >= 0 else "↓"
        net_worth_line += f" ({sign} {_sign_usd(today_pnl)} today"
        if ytd is not None:
            net_worth_line += f", {_sign(ytd * 100)} YTD)"
        else:
            net_worth_line += ")"

    regime_val = daily_status.get("regime_state", "normal")
    regime_emoji = {"normal": "🟢", "high_vol": "🟡", "opportunity": "🟣", "paused": "🔴"}.get(str(regime_val), "⚪")
    regime_label = str(regime_val).replace("_", " ").title()
    cycle_pos = ai_response.macro_and_opportunity_commentary.cycle_position or ""
    regime_line = f"{regime_emoji} {regime_label}"
    if cycle_pos:
        regime_line += f" — {cycle_pos}"

    # Proposed trades
    trades_raw = signals_run.get("proposed_trades") or []
    trade_lines: list[str] = []
    for t in trades_raw[:8]:
        direction = t.get("trade_type", "buy").upper()
        sym = t.get("symbol", "")
        amt = t.get("amount_usd", 0)
        acct = t.get("account_name", "")
        approval = " ⚠️ APPROVAL NEEDED" if t.get("requires_approval") else ""
        trade_lines.append(f"{direction} {sym} ${amt:,.0f} — {acct}{approval}")

    # Framework flags
    framework_line = _framework_flag_line(ai_response)
    framework_flags = [framework_line]

    # Alerts
    alerts: list[str] = []
    pending = daily_status.get("pending_approvals", 0)
    if pending:
        alerts.append(f"🔔 {pending} trade(s) awaiting approval")
    max_dd = daily_status.get("max_drawdown_pct")
    if max_dd and abs(max_dd) >= 0.20:
        alerts.append(f"⚠️ Drawdown: {_sign(max_dd * 100)} from peak")
    for w in ai_response.investment_framework_check.model_dump().values():
        if w == "warning":
            alerts.append("⚠️ AI flagged framework warning — check signals page")
            break
    risks = ai_response.macro_and_opportunity_commentary.risks_to_watch
    for r in risks[:2]:
        alerts.append(f"👀 {r}")

    needs_approval = signals_run.get("status") == "needs_approval"
    run_id = signals_run.get("id")

    return DailyDigest(
        header=f"OvelhaInvest Daily — {today_str}",
        net_worth=net_worth_line,
        regime=regime_line,
        proposed_trades=trade_lines,
        ai_summary=ai_response.explanation_for_user.short_summary,
        framework_flags=framework_flags,
        alerts=alerts,
        footer=f"View full analysis: {APP_URL}",
        needs_approval=needs_approval,
        approval_run_id=run_id,
    )


def build_telegram_message(digest: DailyDigest) -> str:
    """
    Format DailyDigest as Telegram MarkdownV2 message.

    Keeps under 4096 chars. Includes inline keyboard markup hint if approval needed.

    Args:
        digest: DailyDigest from build_daily_digest().

    Returns:
        MarkdownV2 formatted string ready for Telegram sendMessage.
    """
    lines: list[str] = []

    # Header
    lines.append(f"*{_esc(digest.header)}*")
    lines.append("")

    # Net worth
    lines.append(f"💼 *Net Worth:* {_esc(digest.net_worth)}")
    lines.append(f"📡 *Regime:* {_esc(digest.regime)}")
    lines.append("")

    # Proposed trades
    if digest.proposed_trades:
        lines.append("📋 *Proposed Trades:*")
        for t in digest.proposed_trades:
            lines.append(f"  • {_esc(t)}")
        lines.append("")

    # AI summary
    if digest.ai_summary:
        lines.append(f"🤖 *AI Advisory:*")
        lines.append(_esc(digest.ai_summary))
        lines.append("")

    # Framework flags
    for flag in digest.framework_flags:
        lines.append(_esc(flag))
    lines.append("")

    # Alerts
    if digest.alerts:
        lines.append("🔔 *Alerts:*")
        for a in digest.alerts:
            lines.append(f"  {_esc(a)}")
        lines.append("")

    # Approval CTA
    if digest.needs_approval:
        lines.append("⚠️ *Action Required:* Trades need your approval\\.")
        lines.append(f"Tap below or visit: {_esc(APP_URL + '/signals')}")
        lines.append("")

    # Footer
    lines.append(f"_{_esc(digest.footer)}_")

    message = "\n".join(lines)

    # Telegram max is 4096 chars
    if len(message) > 4000:
        message = message[:3990] + "\n_\\.\\.\\. truncated_"

    return message


def build_telegram_inline_keyboard(run_id: str) -> dict[str, Any]:
    """
    Build Telegram inline keyboard markup for approval flows.

    Args:
        run_id: signals_run UUID.

    Returns:
        reply_markup dict for Telegram sendMessage payload.
    """
    return {
        "inline_keyboard": [
            [
                {"text": "✅ Approve All", "callback_data": f"approve:{run_id}"},
                {"text": "❌ Reject", "callback_data": f"reject:{run_id}"},
            ],
            [
                {"text": "🔍 View Details", "url": f"{APP_URL}/signals"},
            ],
        ]
    }


def build_opportunity_alert(
    opportunity: dict[str, Any],
    ai_commentary: str,
    tier: int,
) -> str:
    """
    Format urgent Telegram alert for a Tier 1 or 2 opportunity trigger.

    Args:
        opportunity: Asset + trigger data dict.
        ai_commentary: One-line AI commentary.
        tier: 1 or 2.

    Returns:
        MarkdownV2 formatted Telegram message.
    """
    symbol = opportunity.get("symbol", "UNKNOWN")
    drawdown = opportunity.get("drawdown_pct", 0.0)
    mos = opportunity.get("margin_of_safety_pct", 0.0)
    vault_deploy_pct = 0.20 if tier == 1 else 0.30
    run_id = opportunity.get("run_id", "")

    tier_emoji = "🟡" if tier == 1 else "🔴"
    lines: list[str] = [
        f"{tier_emoji} *TIER {tier} OPPORTUNITY: {_esc(symbol)}*",
        "",
        f"📉 Drawdown from 6\\-12m high: *{_esc(f'{drawdown*100:.1f}%')}*",
        f"🎯 Margin of Safety: *{_esc(f'{mos*100:.1f}%')}*",
        f"💰 Vault deployment: *{_esc(f'{vault_deploy_pct*100:.0f}%')} of Opportunity Vault*",
        "",
        f"🤖 AI: {_esc(ai_commentary)}",
        "",
        f"_{_esc(f'Approve deployment via the buttons below or at {APP_URL}/signals')}_",
    ]
    message = "\n".join(lines)

    if len(message) > 4000:
        message = message[:3990] + "\n_\\.\\.\\. truncated_"

    return message
