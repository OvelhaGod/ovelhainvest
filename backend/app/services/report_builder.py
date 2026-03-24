"""
Report builder — daily digest + Telegram formatter + PDF generation (Phase 9).

PDF reports use WeasyPrint to render HTML → PDF.
"""

from __future__ import annotations

import calendar
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
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


# ── PDF Report Generation ──────────────────────────────────────────────────

_TEMPLATE_DIR = Path(__file__).parent.parent / "templates"


def _render_template(template_name: str, context: dict[str, Any]) -> str:
    """Render a Jinja2 HTML template to string."""
    try:
        from jinja2 import Environment, FileSystemLoader, select_autoescape

        env = Environment(
            loader=FileSystemLoader(str(_TEMPLATE_DIR)),
            autoescape=select_autoescape(["html"]),
        )
        tmpl = env.get_template(template_name)
        return tmpl.render(**context)
    except Exception as exc:
        logger.warning("Jinja2 render failed (%s): %s", template_name, exc)
        return _minimal_html_report(context)


def _minimal_html_report(context: dict[str, Any]) -> str:
    """Fallback minimal HTML when Jinja2/template unavailable."""
    month = context.get("month_name", "")
    year = context.get("year", "")
    net_worth = context.get("net_worth_usd", 0.0)
    twr_ytd = context.get("twr_ytd", 0.0)
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>OvelhaInvest Report — {month} {year}</title>
<style>body{{font-family:Arial,sans-serif;margin:40px;color:#111}}
h1{{color:#10b981}}table{{border-collapse:collapse;width:100%}}
td,th{{border:1px solid #ddd;padding:8px;text-align:right}}th{{background:#f5f5f5}}</style>
</head><body>
<h1>OvelhaInvest Monthly Report</h1>
<h2>{month} {year}</h2>
<p><strong>Net Worth:</strong> ${net_worth:,.2f}</p>
<p><strong>YTD TWR:</strong> {twr_ytd*100:+.2f}%</p>
<p><em>Full template unavailable — install Jinja2 for formatted reports.</em></p>
</body></html>"""


def _html_to_pdf(html: str) -> bytes:
    """Convert HTML string to PDF bytes via WeasyPrint."""
    try:
        from weasyprint import HTML  # type: ignore[import]

        return HTML(string=html).write_pdf()
    except Exception as exc:
        logger.error("WeasyPrint PDF generation failed: %s", exc)
        raise RuntimeError(f"PDF generation failed: {exc}") from exc


def _build_report_context(
    year: int,
    month: int,
    daily_status: dict[str, Any],
    signals_runs: list[dict[str, Any]],
    performance: dict[str, Any],
    journal_entries: list[dict[str, Any]],
    tax_summary: dict[str, Any],
    ai_summaries: list[str],
) -> dict[str, Any]:
    """
    Assemble template context dict for monthly_report.html.

    Args:
        year: Report year.
        month: Report month (1-12).
        daily_status: Latest /daily_status response.
        signals_runs: All signals_runs for the month.
        performance: /performance/summary response.
        journal_entries: /journal entries for the month.
        tax_summary: /tax/estimate response.
        ai_summaries: List of AI short_summary strings from this month's runs.

    Returns:
        Dict suitable for Jinja2 template rendering.
    """
    month_name = calendar.month_name[month]
    generated_at = datetime.now(timezone.utc).strftime("%B %d, %Y at %H:%M UTC")

    # Portfolio summary
    net_worth_usd = daily_status.get("total_value_usd", 0.0)
    sleeve_weights = daily_status.get("sleeve_weights", {})
    regime = daily_status.get("regime_state", "normal")

    # Performance
    twr_ytd = performance.get("twr_ytd", 0.0) or 0.0
    twr_1mo = performance.get("twr_1mo", 0.0) or 0.0
    benchmark_ytd = performance.get("benchmark_ytd", 0.0) or 0.0
    sharpe = performance.get("sharpe_ratio")
    sortino = performance.get("sortino_ratio")
    calmar = performance.get("calmar_ratio")
    max_dd = performance.get("max_drawdown_pct", 0.0) or 0.0

    # Trade activity
    executed_trades: list[dict[str, Any]] = []
    total_buy_usd = 0.0
    total_sell_usd = 0.0
    for run in signals_runs:
        for t in (run.get("proposed_trades") or []):
            if run.get("status") in ("approved", "executed"):
                executed_trades.append(t)
                amt = float(t.get("amount_usd", 0))
                if t.get("trade_type") == "buy":
                    total_buy_usd += amt
                else:
                    total_sell_usd += amt

    # Journal stats
    followed = sum(1 for e in journal_entries if e.get("action_type") == "followed")
    overrode = sum(1 for e in journal_entries if e.get("action_type") == "overrode")
    deferred = sum(1 for e in journal_entries if e.get("action_type") == "deferred")

    # Tax
    unrealized_gain = 0.0
    estimated_tax = 0.0
    harvest_savings = 0.0
    try:
        unrealized_gain = tax_summary.get("unrealized", {}).get("total_unrealized_gain", 0.0) or 0.0
        estimated_tax = tax_summary.get("estimated_tax", {}).get("on_realized_gains", 0.0) or 0.0
        harvest_savings = tax_summary.get("harvest_savings", {}).get("potential_savings_usd", 0.0) or 0.0
    except Exception:
        pass

    # Sleeve allocation rows
    sleeve_rows = []
    targets = {
        "us_equity": 0.45, "intl_equity": 0.15, "bonds": 0.20,
        "brazil_equity": 0.10, "crypto": 0.07, "cash": 0.03,
    }
    for sleeve, target in targets.items():
        actual = sleeve_weights.get(sleeve, 0.0) or 0.0
        drift = actual - target
        sleeve_rows.append({
            "name": sleeve.replace("_", " ").title(),
            "actual_pct": actual * 100,
            "target_pct": target * 100,
            "drift_pct": drift * 100,
            "drift_class": "positive" if abs(drift) < 0.03 else ("warning" if abs(drift) < 0.05 else "negative"),
        })

    return {
        "year": year,
        "month": month,
        "month_name": month_name,
        "generated_at": generated_at,
        "net_worth_usd": net_worth_usd,
        "net_worth_formatted": f"${net_worth_usd:,.2f}",
        "regime": regime,
        "regime_label": str(regime).replace("_", " ").title(),
        "twr_ytd": twr_ytd,
        "twr_1mo": twr_1mo,
        "benchmark_ytd": benchmark_ytd,
        "alpha_ytd": twr_ytd - benchmark_ytd,
        "sharpe": sharpe,
        "sortino": sortino,
        "calmar": calmar,
        "max_drawdown_pct": max_dd,
        "sleeve_rows": sleeve_rows,
        "executed_trades": executed_trades[:20],
        "total_buy_usd": total_buy_usd,
        "total_sell_usd": total_sell_usd,
        "trade_count": len(executed_trades),
        "followed_count": followed,
        "overrode_count": overrode,
        "deferred_count": deferred,
        "journal_entries": journal_entries[:10],
        "unrealized_gain": unrealized_gain,
        "estimated_tax": estimated_tax,
        "harvest_savings": harvest_savings,
        "ai_summaries": ai_summaries[:3],
        "app_url": APP_URL,
    }


def generate_monthly_report(
    year: int,
    month: int,
    daily_status: dict[str, Any],
    signals_runs: list[dict[str, Any]],
    performance: dict[str, Any],
    journal_entries: list[dict[str, Any]],
    tax_summary: dict[str, Any],
    ai_summaries: list[str],
) -> bytes:
    """
    Generate a monthly PDF report.

    Args:
        year: Report year (e.g. 2025).
        month: Report month (1-12).
        daily_status: Latest portfolio status dict.
        signals_runs: All signals_runs records for the month.
        performance: Performance summary dict.
        journal_entries: Journal entries for the month.
        tax_summary: Tax estimate dict.
        ai_summaries: List of AI short_summary strings.

    Returns:
        PDF bytes.
    """
    context = _build_report_context(
        year=year,
        month=month,
        daily_status=daily_status,
        signals_runs=signals_runs,
        performance=performance,
        journal_entries=journal_entries,
        tax_summary=tax_summary,
        ai_summaries=ai_summaries,
    )
    html = _render_template("monthly_report.html", context)
    logger.info("Generating monthly PDF report for %s/%s", month, year)
    return _html_to_pdf(html)


def generate_annual_report(
    year: int,
    monthly_contexts: list[dict[str, Any]],
    daily_status: dict[str, Any],
    performance: dict[str, Any],
    tax_summary: dict[str, Any],
) -> bytes:
    """
    Generate an annual PDF report by aggregating 12 monthly contexts.

    Args:
        year: Report year.
        monthly_contexts: List of up to 12 monthly context dicts
                          (from _build_report_context) for aggregation.
        daily_status: Year-end portfolio status.
        performance: Full-year performance summary.
        tax_summary: Year-end tax estimate.

    Returns:
        PDF bytes.
    """
    # Aggregate monthly trade counts and journal stats
    total_trades = sum(c.get("trade_count", 0) for c in monthly_contexts)
    total_buy = sum(c.get("total_buy_usd", 0.0) for c in monthly_contexts)
    total_sell = sum(c.get("total_sell_usd", 0.0) for c in monthly_contexts)
    total_followed = sum(c.get("followed_count", 0) for c in monthly_contexts)
    total_overrode = sum(c.get("overrode_count", 0) for c in monthly_contexts)
    total_deferred = sum(c.get("deferred_count", 0) for c in monthly_contexts)
    all_ai_summaries = []
    for c in monthly_contexts:
        all_ai_summaries.extend(c.get("ai_summaries", []))

    # Build annual context reusing monthly structure but with year-level numbers
    context = _build_report_context(
        year=year,
        month=12,  # placeholder — template checks for annual flag
        daily_status=daily_status,
        signals_runs=[],
        performance=performance,
        journal_entries=[],
        tax_summary=tax_summary,
        ai_summaries=all_ai_summaries[:5],
    )
    context.update(
        {
            "is_annual": True,
            "month_name": "Annual Summary",
            "trade_count": total_trades,
            "total_buy_usd": total_buy,
            "total_sell_usd": total_sell,
            "followed_count": total_followed,
            "overrode_count": total_overrode,
            "deferred_count": total_deferred,
            "monthly_summaries": [
                {
                    "month_name": calendar.month_name[c.get("month", 1)],
                    "twr_1mo": c.get("twr_1mo", 0.0),
                    "trade_count": c.get("trade_count", 0),
                }
                for c in monthly_contexts
            ],
        }
    )

    html = _render_template("monthly_report.html", context)
    logger.info("Generating annual PDF report for %s", year)
    return _html_to_pdf(html)
