"""
Decision journal engine — override accuracy, AI insight, outcome backfill, behavioral patterns.

Phase 9 full implementation.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from enum import Enum
from statistics import mean
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_USER = "00000000-0000-0000-0000-000000000001"
_MODEL = "claude-sonnet-4-20250514"


# ── Enums + dataclasses ────────────────────────────────────────────────────────

class JournalActionType(Enum):
    FOLLOWED     = "followed"
    OVERRODE     = "overrode"
    DEFERRED     = "deferred"
    MANUAL_TRADE = "manual_trade"


@dataclass
class OverrideAccuracy:
    followed_count: int = 0
    overrode_count: int = 0
    deferred_count: int = 0
    manual_count: int = 0
    # 30-day outcomes
    avg_outcome_followed_30d: float | None = None
    avg_outcome_overrode_30d: float | None = None
    avg_outcome_deferred_30d: float | None = None
    # 90-day outcomes
    avg_outcome_followed_90d: float | None = None
    avg_outcome_overrode_90d: float | None = None
    # Win rates (% of outcomes > 0)
    followed_win_rate: float | None = None
    overrode_win_rate: float | None = None
    # Delta: positive = system outperformed user overrides
    system_outperformance_delta_30d: float | None = None
    system_outperformance_delta_90d: float | None = None
    # AI-generated insight
    insight: str = ""
    has_enough_data: bool = False


@dataclass
class BehavioralPattern:
    pattern_id: str
    title: str
    description: str
    severity: str = "info"   # "info" | "warning" | "positive"
    icon: str = "📊"


@dataclass
class DecisionJournalUpdate:
    entry_id: str
    outcome_30d: float | None = None
    outcome_90d: float | None = None


# ── Item 1a: compute_override_accuracy ────────────────────────────────────────

def compute_override_accuracy(
    entries: list[dict],
    min_entries: int = 5,
) -> OverrideAccuracy:
    """
    Compute override accuracy statistics from journal entries.

    Separates entries into followed/overrode/deferred groups.
    For groups with outcome data, computes averages and win rates.
    Returns OverrideAccuracy with system_outperformance_delta.
    """
    acc = OverrideAccuracy()

    followed = [e for e in entries if e.get("action_type") == "followed"]
    overrode  = [e for e in entries if e.get("action_type") == "overrode"]
    deferred  = [e for e in entries if e.get("action_type") == "deferred"]
    manual    = [e for e in entries if e.get("action_type") == "manual_trade"]

    acc.followed_count = len(followed)
    acc.overrode_count = len(overrode)
    acc.deferred_count = len(deferred)
    acc.manual_count   = len(manual)
    acc.has_enough_data = (acc.followed_count + acc.overrode_count) >= min_entries

    # 30-day averages
    followed_30 = [float(e["outcome_30d"]) for e in followed if e.get("outcome_30d") is not None]
    overrode_30  = [float(e["outcome_30d"]) for e in overrode  if e.get("outcome_30d") is not None]
    deferred_30  = [float(e["outcome_30d"]) for e in deferred  if e.get("outcome_30d") is not None]

    if followed_30:
        acc.avg_outcome_followed_30d = round(mean(followed_30), 4)
        acc.followed_win_rate = round(sum(1 for x in followed_30 if x > 0) / len(followed_30), 3)
    if overrode_30:
        acc.avg_outcome_overrode_30d = round(mean(overrode_30), 4)
        acc.overrode_win_rate = round(sum(1 for x in overrode_30 if x > 0) / len(overrode_30), 3)
    if deferred_30:
        acc.avg_outcome_deferred_30d = round(mean(deferred_30), 4)

    # 90-day averages
    followed_90 = [float(e["outcome_90d"]) for e in followed if e.get("outcome_90d") is not None]
    overrode_90  = [float(e["outcome_90d"]) for e in overrode  if e.get("outcome_90d") is not None]

    if followed_90:
        acc.avg_outcome_followed_90d = round(mean(followed_90), 4)
    if overrode_90:
        acc.avg_outcome_overrode_90d = round(mean(overrode_90), 4)

    # System outperformance delta (positive = system was better)
    if acc.avg_outcome_followed_30d is not None and acc.avg_outcome_overrode_30d is not None:
        acc.system_outperformance_delta_30d = round(
            acc.avg_outcome_followed_30d - acc.avg_outcome_overrode_30d, 4
        )
    if acc.avg_outcome_followed_90d is not None and acc.avg_outcome_overrode_90d is not None:
        acc.system_outperformance_delta_90d = round(
            acc.avg_outcome_followed_90d - acc.avg_outcome_overrode_90d, 4
        )

    return acc


# ── Item 1b: compute_journal_insight (Claude API) ─────────────────────────────

def compute_journal_insight(
    stats: OverrideAccuracy,
    user_id: str = _DEFAULT_USER,
) -> str:
    """
    Call Claude API to generate a 3-sentence behavioral insight.

    Caches result in Redis for 24 hours.
    Falls back to a rule-based insight if Claude is unavailable.
    """
    # Try Redis cache first
    try:
        from app.db.redis_client import get_redis_client
        rc = get_redis_client()
        if rc:
            cached = rc.get(f"journal_insight:{user_id}")
            if cached:
                return cached if isinstance(cached, str) else cached.decode()
    except Exception:
        pass

    # Generate insight
    if not stats.has_enough_data:
        insight = (
            f"You have {stats.followed_count + stats.overrode_count} decision(s) logged so far — "
            f"accuracy patterns will emerge after {max(0, 5 - stats.followed_count - stats.overrode_count)} more. "
            "Keep logging every trade decision, including reasoning. "
            "The most valuable insight comes from your first 10 decisions."
        )
        return insight

    # Build prompt with real numbers
    followed_30_str = f"{stats.avg_outcome_followed_30d * 100:+.1f}%" if stats.avg_outcome_followed_30d is not None else "N/A"
    overrode_30_str = f"{stats.avg_outcome_overrode_30d * 100:+.1f}%" if stats.avg_outcome_overrode_30d is not None else "N/A"
    delta_str = f"{stats.system_outperformance_delta_30d * 100:+.1f}%" if stats.system_outperformance_delta_30d is not None else "N/A"
    follow_wr = f"{stats.followed_win_rate * 100:.0f}%" if stats.followed_win_rate is not None else "N/A"
    override_wr = f"{stats.overrode_win_rate * 100:.0f}%" if stats.overrode_win_rate is not None else "N/A"

    prompt = (
        f"You are analyzing an investor's decision journal. Here are their stats:\n"
        f"Followed system: {stats.followed_count} times, avg 30d outcome: {followed_30_str}, win rate: {follow_wr}\n"
        f"Overrode system: {stats.overrode_count} times, avg 30d outcome: {overrode_30_str}, win rate: {override_wr}\n"
        f"System outperformance delta: {delta_str}\n\n"
        f"Write exactly 3 sentences (no more, no less):\n"
        f"1. State what the data shows about their override behavior vs system performance\n"
        f"2. Identify the most significant pattern (when do overrides help vs hurt?)\n"
        f"3. Give one specific, actionable recommendation\n\n"
        f"Be direct and quantitative. Do not hedge. Use the actual numbers."
    )

    insight = _fallback_insight(stats)  # default if Claude fails

    try:
        import anthropic
        from app.config import settings

        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        response = client.messages.create(
            model=_MODEL,
            max_tokens=200,
            temperature=0,
            messages=[{"role": "user", "content": prompt}],
        )
        insight = response.content[0].text.strip()
    except Exception as exc:
        logger.warning("compute_journal_insight Claude call failed: %s", exc)

    # Cache for 24hr
    try:
        from app.db.redis_client import get_redis_client
        rc = get_redis_client()
        if rc:
            rc.setex(f"journal_insight:{user_id}", 86400, insight)
    except Exception:
        pass

    return insight


def _fallback_insight(stats: OverrideAccuracy) -> str:
    """Rule-based fallback insight when Claude is unavailable."""
    delta = stats.system_outperformance_delta_30d
    if delta is None:
        return (
            "Your journal data is accumulating — outcome comparisons are not yet available. "
            "Continue logging decisions to build a meaningful dataset. "
            "Aim for at least 10 followed and 5 overrode entries for reliable patterns."
        )
    if delta > 0.02:
        return (
            f"The system outperformed your overrides by {delta*100:+.1f}% on a 30-day basis "
            f"({stats.followed_count} follows avg {stats.avg_outcome_followed_30d*100:+.1f}% "
            f"vs {stats.overrode_count} overrides avg {stats.avg_outcome_overrode_30d*100:+.1f}%). "
            "This suggests the quantitative signals are capturing information your intuition misses. "
            "Consider reducing override frequency and requiring stronger evidence before deviating from the system."
        )
    if delta < -0.02:
        return (
            f"Your overrides outperformed the system by {abs(delta)*100:.1f}% on a 30-day basis — "
            f"a meaningful edge that warrants investigation into what you're seeing that the signals miss. "
            "Document your reasoning more specifically to identify which override categories add value. "
            "Consider codifying your best override logic into new signal rules."
        )
    return (
        f"Your override outcomes ({stats.avg_outcome_overrode_30d*100:+.1f}% avg) are nearly equal to "
        f"following the system ({stats.avg_outcome_followed_30d*100:+.1f}% avg) — within noise range. "
        "With more data points the pattern will clarify, but currently neither approach dominates. "
        "Focus on logging reasoning quality rather than trying to time overrides better."
    )


# ── Item 1c: backfill_journal_outcomes ────────────────────────────────────────

def backfill_journal_outcomes(
    entries: list[dict],
    current_prices: dict[str, float],
    db: Any = None,
) -> list[DecisionJournalUpdate]:
    """
    Compute 30d/90d outcomes for journal entries that lack them.

    Looks up asset price at entry date from asset_valuations history,
    then computes return vs current price.

    Returns list of updates to apply.
    """
    today = date.today()
    updates: list[DecisionJournalUpdate] = []

    for entry in entries:
        entry_id = entry.get("id", "")
        if not entry_id:
            continue

        created_raw = entry.get("created_at") or entry.get("event_date")
        if not created_raw:
            continue

        try:
            if isinstance(created_raw, str):
                created_at = datetime.fromisoformat(created_raw.replace("Z", "+00:00"))
            else:
                created_at = created_raw
            entry_date = created_at.date() if hasattr(created_at, "date") else created_at
        except (ValueError, AttributeError):
            continue

        days_since = (today - entry_date).days
        has_30d = entry.get("outcome_30d") is not None
        has_90d = entry.get("outcome_90d") is not None

        needs_30d = not has_30d and days_since >= 30
        needs_90d = not has_90d and days_since >= 90

        if not needs_30d and not needs_90d:
            continue

        # Get asset symbol from the entry
        asset_id = entry.get("asset_id")
        symbol = _get_symbol_from_entry(entry, db)
        if not symbol:
            continue

        current_price = current_prices.get(symbol.upper())
        if current_price is None:
            continue

        # Get entry-date price from asset_valuations
        entry_price = _get_historical_price(asset_id, symbol, entry_date, db)
        if not entry_price or entry_price <= 0:
            continue

        update = DecisionJournalUpdate(entry_id=entry_id)

        if needs_30d:
            target_date_30 = entry_date + timedelta(days=30)
            price_30d = _get_historical_price(asset_id, symbol, target_date_30, db) or current_price
            update.outcome_30d = round((price_30d - entry_price) / entry_price, 4)

        if needs_90d:
            target_date_90 = entry_date + timedelta(days=90)
            price_90d = _get_historical_price(asset_id, symbol, target_date_90, db) or current_price
            update.outcome_90d = round((price_90d - entry_price) / entry_price, 4)

        updates.append(update)

    logger.info("backfill_journal_outcomes: %d entries → %d updates", len(entries), len(updates))
    return updates


def _get_symbol_from_entry(entry: dict, db: Any) -> str | None:
    """Resolve symbol from journal entry (via asset_id or system_recommendation)."""
    # Try system_recommendation first
    sys_rec = entry.get("system_recommendation") or {}
    if isinstance(sys_rec, dict):
        symbol = sys_rec.get("symbol")
        if symbol:
            return str(symbol).upper()

    # Try actual_action
    actual = entry.get("actual_action") or {}
    if isinstance(actual, dict):
        symbol = actual.get("symbol")
        if symbol:
            return str(symbol).upper()

    # Resolve from asset_id in DB
    asset_id = entry.get("asset_id")
    if not asset_id or not db:
        return None
    try:
        resp = db.table("assets").select("symbol").eq("id", asset_id).limit(1).execute()
        if resp.data:
            return str(resp.data[0]["symbol"]).upper()
    except Exception:
        pass
    return None


def _get_historical_price(
    asset_id: str | None,
    symbol: str,
    target_date: date,
    db: Any,
) -> float | None:
    """Fetch closest asset_valuation price on or before target_date."""
    if not db:
        return None
    try:
        q = db.table("asset_valuations").select("price, as_of_date")
        if asset_id:
            q = q.eq("asset_id", asset_id)
        resp = (
            q
            .lte("as_of_date", target_date.isoformat())
            .order("as_of_date", desc=True)
            .limit(1)
            .execute()
        )
        if resp.data:
            return float(resp.data[0]["price"])
    except Exception as exc:
        logger.debug("_get_historical_price failed symbol=%s: %s", symbol, exc)
    return None


# ── Item 1d: detect_behavioral_patterns ───────────────────────────────────────

def detect_behavioral_patterns(entries: list[dict]) -> list[BehavioralPattern]:
    """
    Analyze journal entries for behavioral patterns across 4 dimensions.

    Returns up to 3 most significant patterns found.
    Requires >= 10 entries for meaningful analysis.
    """
    if len(entries) < 10:
        return []

    patterns: list[tuple[float, BehavioralPattern]] = []

    overrides = [e for e in entries if e.get("action_type") == "overrode"]
    follows   = [e for e in entries if e.get("action_type") == "followed"]

    # ── Pattern 1: Volatility Override ──
    try:
        overrides_high_vol = [
            e for e in overrides
            if _get_nested(e, "inputs_summary", "regime") in ("high_vol", "opportunity")
        ]
        overrides_normal = [
            e for e in overrides
            if _get_nested(e, "inputs_summary", "regime") == "normal"
        ]
        total_high_vol = sum(
            1 for e in entries
            if _get_nested(e, "inputs_summary", "regime") in ("high_vol", "opportunity")
        )
        total_normal = len(entries) - total_high_vol

        if total_high_vol > 0 and total_normal > 0:
            override_rate_hv = len(overrides_high_vol) / total_high_vol
            override_rate_nm = len(overrides_normal) / total_normal
            if override_rate_hv > override_rate_nm * 1.5 and len(overrides_high_vol) >= 2:
                ratio = override_rate_hv / max(override_rate_nm, 0.001)
                patterns.append((ratio, BehavioralPattern(
                    pattern_id="volatility_override",
                    title="Volatility-Driven Overrides",
                    description=(
                        f"You override the system {ratio:.1f}× more often during high-volatility "
                        f"regimes ({len(overrides_high_vol)} of {total_high_vol} high-vol decisions). "
                        "Fear and urgency may be distorting judgment when markets are stressed."
                    ),
                    severity="warning",
                    icon="⚠️",
                )))
    except Exception as exc:
        logger.debug("Pattern 1 analysis failed: %s", exc)

    # ── Pattern 2: Asset Class Bias ──
    try:
        override_asset_classes: dict[str, int] = {}
        for e in overrides:
            ac = _get_nested(e, "actual_action", "asset_class") or \
                 _get_nested(e, "system_recommendation", "asset_class") or "unknown"
            override_asset_classes[str(ac)] = override_asset_classes.get(str(ac), 0) + 1

        if override_asset_classes and overrides:
            top_class, top_count = max(override_asset_classes.items(), key=lambda x: x[1])
            top_pct = top_count / len(overrides)
            if top_pct >= 0.40 and top_count >= 2:
                class_label = {
                    "crypto": "Crypto", "us_equity": "US Equity",
                    "brazil_equity": "Brazil Equity", "bonds": "Bonds",
                }.get(top_class.lower(), top_class)
                is_high_emotion = top_class.lower() in ("crypto", "brazil_equity")
                patterns.append((top_pct, BehavioralPattern(
                    pattern_id="asset_class_bias",
                    title=f"{class_label} Override Bias",
                    description=(
                        f"{top_pct*100:.0f}% of your overrides are in {class_label} "
                        f"({top_count} of {len(overrides)} override decisions). "
                        + (
                            "This is a high-emotion asset class where sentiment often overrides analysis."
                            if is_high_emotion
                            else "Consider whether familiarity bias is driving these deviations."
                        )
                    ),
                    severity="warning" if is_high_emotion else "info",
                    icon="🎯",
                )))
    except Exception as exc:
        logger.debug("Pattern 2 analysis failed: %s", exc)

    # ── Pattern 3: Override Accuracy (positive pattern when overrides beat system) ──
    try:
        overrides_with_30d = [e for e in overrides if e.get("outcome_30d") is not None]
        follows_with_30d   = [e for e in follows   if e.get("outcome_30d") is not None]

        if len(overrides_with_30d) >= 3 and len(follows_with_30d) >= 3:
            avg_override = mean(float(e["outcome_30d"]) for e in overrides_with_30d)
            avg_follow   = mean(float(e["outcome_30d"]) for e in follows_with_30d)
            delta = avg_override - avg_follow

            if delta > 0.02:  # Overrides beating system by >2%
                patterns.append((delta, BehavioralPattern(
                    pattern_id="override_skill",
                    title="Override Edge Detected",
                    description=(
                        f"Your overrides are averaging {avg_override*100:+.1f}% (30d) vs "
                        f"{avg_follow*100:+.1f}% when following — a {delta*100:+.1f}% edge. "
                        "This is statistically interesting: document what you're seeing "
                        "that the system misses to codify it into permanent signal rules."
                    ),
                    severity="positive",
                    icon="✅",
                )))
            elif delta < -0.03:  # System beating overrides by >3%
                patterns.append((abs(delta), BehavioralPattern(
                    pattern_id="system_edge",
                    title="System Outperforming Overrides",
                    description=(
                        f"Following the system ({avg_follow*100:+.1f}% avg 30d) is outperforming "
                        f"your overrides ({avg_override*100:+.1f}%) by {abs(delta)*100:.1f}%. "
                        "The engine is capturing something your intuition is missing — "
                        "raise the bar for when you deviate from recommendations."
                    ),
                    severity="warning",
                    icon="📊",
                )))
    except Exception as exc:
        logger.debug("Pattern 3 analysis failed: %s", exc)

    # ── Pattern 4: Recency Bias ──
    try:
        # Sort by date, look at last 30-day vs earlier override rate
        sorted_entries = sorted(entries, key=lambda e: e.get("created_at", ""), reverse=True)
        recent_30 = sorted_entries[:max(1, len(sorted_entries) // 3)]
        older     = sorted_entries[max(1, len(sorted_entries) // 3):]

        recent_override_rate = sum(1 for e in recent_30 if e.get("action_type") == "overrode") / max(len(recent_30), 1)
        older_override_rate  = sum(1 for e in older     if e.get("action_type") == "overrode") / max(len(older), 1)

        if recent_override_rate > older_override_rate * 2.0 and len(recent_30) >= 3:
            patterns.append((recent_override_rate, BehavioralPattern(
                pattern_id="recency_bias",
                title="Override Frequency Rising",
                description=(
                    f"Your recent override rate ({recent_override_rate*100:.0f}%) is "
                    f"{recent_override_rate / max(older_override_rate, 0.001):.1f}× your historical rate "
                    f"({older_override_rate*100:.0f}%). "
                    "Rising overrides can indicate loss aversion or recency bias after drawdowns. "
                    "Review whether recent market events are driving emotional decision-making."
                ),
                severity="warning",
                icon="📈",
            )))
    except Exception as exc:
        logger.debug("Pattern 4 analysis failed: %s", exc)

    # Return top 3 by significance score, deduplicated
    patterns.sort(key=lambda x: x[0], reverse=True)
    return [p for _, p in patterns[:3]]


def _get_nested(d: dict, *keys: str) -> Any:
    """Safely get nested dict value."""
    cur = d
    for k in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(k)
    return cur


# ── Item 1e: log_decision (thin wrapper around repository) ────────────────────

def log_decision(
    user_id: str,
    action_type: JournalActionType | str,
    signal_run_id: str | None,
    asset_id: str | None,
    system_recommendation: dict | None,
    actual_action: dict | None,
    reasoning: str,
    db: Any = None,
) -> dict:
    """
    Persist a decision journal entry via the repository layer.

    Args:
        user_id: User UUID.
        action_type: JournalActionType enum or string.
        signal_run_id: signals_run UUID this decision relates to.
        asset_id: Asset UUID if trade-specific.
        system_recommendation: What the system proposed.
        actual_action: What was actually done.
        reasoning: Free-text explanation.
        db: Optional injected Supabase client.

    Returns:
        Created journal entry dict.
    """
    from app.db.repositories.journal import create_journal_entry
    action_str = action_type.value if isinstance(action_type, JournalActionType) else str(action_type)
    return create_journal_entry(
        user_id=user_id,
        action_type=action_str,
        reasoning=reasoning,
        signal_run_id=signal_run_id,
        asset_id=asset_id,
        system_recommendation=system_recommendation,
        actual_action=actual_action,
    )
