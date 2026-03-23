"""
AI Advisor — Claude API integration for OvelhaInvest.

Validates proposed portfolio actions against 5 investment frameworks:
Swensen (Yale), Dalio (All-Weather), Marks (Cycles), Graham/Buffett (Value), Bogle (Cost).

CRITICAL: AI is validator + explainer only. Python engine is source of truth.
AI validation failures NEVER block a run — degrade gracefully.

Model: claude-sonnet-4-20250514 (non-negotiable per CLAUDE.md Section 14)
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from app.config import settings
from app.schemas.ai_models import (
    AIResponse,
    ExplanationForUser,
    FrameworkCheck,
    MacroOpportunityCommentary,
    PortfolioAssessment,
    TradeFeedback,
    TradeRecommendations,
    ValidationResult,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the AI investment advisor for OvelhaInvest, a private wealth OS.
You validate proposed portfolio actions and provide context. You are NOT the
decision-maker — the Python engine is. You are validator + explainer only.

Apply these frameworks to every response:

1. SWENSEN (Yale Endowment): Is allocation diversified across uncorrelated asset classes?
   Are costs minimized (expense ratios)? Is tax location optimized (bonds in tax-deferred,
   growth in Roth, income in taxable)? Rebalancing discipline maintained?

2. DALIO (All-Weather / Risk Parity): Does each sleeve contribute proportional RISK, not
   just dollars? (45% equity carries ~80% of portfolio risk.) What economic season does the
   current environment resemble — rising growth, falling growth, rising inflation, or
   stagflation? Are we balanced across all four quadrants?

3. MARKS (Market Cycles): Where are we in the market cycle? Is fear or greed dominant?
   Is this trade contrarian in a good way, or just contrarian?
   "High prices imply high risk, low prices imply low risk."
   Evaluate: is the vault deployment timing justified by actual fear/dislocation?

4. GRAHAM/BUFFETT (Intrinsic Value): Is there sufficient margin of safety (≥15%) on any
   individual stock trade? Does the business have a durable economic moat?
   Are we paying fair value or overpaying for quality?
   Quality score must be ≥0.55 before any buy signal is valid.

5. BOGLE (Cost Discipline): What is the weighted average fee drag across the portfolio?
   Would a simpler, cheaper alternative (VTI/VXUS/BND) achieve the same outcome?
   Never sacrifice returns chasing complexity.

CRITICAL RULES:
- Never override the Python engine's numerical constraints
- Never recommend specific trades the engine did not propose
- Always return valid JSON matching the exact output schema below
- If uncertain, flag as "warning" not "block" — blocking requires clear IPS violation
- "block" is reserved for: emergency vault touch, opportunity vault without approval,
  single position >7% limit, or crypto >10% of portfolio
- Keep explanation_for_user.short_summary under 100 words

OUTPUT SCHEMA (return ONLY this JSON, no markdown fences, no extra text):
{
  "validation": {
    "overall_status": "ok|warning|block",
    "issues": ["string"]
  },
  "investment_framework_check": {
    "swensen_alignment": "pass|warning|fail",
    "swensen_detail": "string",
    "dalio_risk_balance": "pass|warning|fail",
    "dalio_detail": "string",
    "marks_cycle_read": "string",
    "marks_detail": "string",
    "graham_margin_of_safety": "pass|warning|fail",
    "graham_detail": "string",
    "bogle_cost_check": "pass|warning|fail",
    "bogle_detail": "string"
  },
  "trade_recommendations": {
    "summary": "string",
    "per_trade_feedback": [
      {"symbol": "string", "recommendation": "proceed|caution|skip", "comment": "string"}
    ],
    "suggested_adjustments": ["string"]
  },
  "portfolio_assessment": {
    "risk_posture": "string",
    "diversification_comment": "string",
    "factor_tilts": "string",
    "benchmark_comparison": "string"
  },
  "macro_and_opportunity_commentary": {
    "macro_regime": "string",
    "cycle_position": "string",
    "macro": ["string"],
    "opportunities": ["string"],
    "risks_to_watch": ["string"]
  },
  "explanation_for_user": {
    "short_summary": "string (max 100 words)",
    "detailed_bullets": ["string"]
  }
}"""

# Fallback response when AI is unavailable
FALLBACK_RESPONSE = AIResponse(
    validation=ValidationResult(
        overall_status="ok",
        issues=[],
    ),
    investment_framework_check=FrameworkCheck(
        swensen_alignment="pass",
        dalio_risk_balance="pass",
        marks_cycle_read="Market cycle analysis unavailable — AI service temporarily unreachable.",
        graham_margin_of_safety="pass",
        bogle_cost_check="pass",
    ),
    trade_recommendations=TradeRecommendations(
        summary="AI validation unavailable — engine recommendation stands.",
        per_trade_feedback=[],
        suggested_adjustments=[],
    ),
    portfolio_assessment=PortfolioAssessment(
        risk_posture="Unknown — AI unavailable",
        diversification_comment="",
        factor_tilts="",
        benchmark_comparison="",
    ),
    macro_and_opportunity_commentary=MacroOpportunityCommentary(
        macro_regime="Unknown",
        cycle_position="Unknown",
        macro=[],
        opportunities=[],
        risks_to_watch=[],
    ),
    explanation_for_user=ExplanationForUser(
        short_summary="AI validation unavailable — proceeding with engine recommendation.",
        detailed_bullets=["The Python engine's numerical constraints are unaffected."],
    ),
    model_used="claude-sonnet-4-20250514",
    input_tokens=0,
    output_tokens=0,
    cached=False,
)


def build_ai_payload(
    run_context: dict[str, Any],
    portfolio_snapshot: dict[str, Any],
    valuation_snapshot: dict[str, Any],
    performance_snapshot: dict[str, Any],
    proposed_trades: list[dict[str, Any]],
    news_and_research: dict[str, Any],
    active_config: dict[str, Any],
) -> dict[str, Any]:
    """
    Build complete AI advisor payload per CLAUDE.md Section 14.

    Args:
        run_context: timestamp, event_type, regime, season, notes
        portfolio_snapshot: total value, sleeve weights, concentration
        valuation_snapshot: top opportunities, MoS distribution
        performance_snapshot: TWR YTD, Sharpe, drawdown
        proposed_trades: engine-proposed trade list
        news_and_research: macro + asset news
        active_config: strategy_configs.config from DB

    Returns:
        Structured payload dict to send as JSON to Claude API.
    """
    # IPS summary from config
    ips_summary = {
        "risk_profile": "growth-oriented, 20yr horizon",
        "max_crypto_pct": 0.10,
        "min_crypto_pct": 0.03,
        "target_allocations": {
            "us_equity": 0.45, "intl_equity": 0.15, "bonds": 0.20,
            "brazil_equity": 0.10, "crypto": 0.07, "cash": 0.03,
        },
        "max_single_stock_pct": 0.07,
        "max_sector_pct": 0.25,
        "min_margin_of_safety": 0.15,
        "preferred_lot_method": "HIFO",
        "accounts": [
            "Thiago 401k (Empower)", "Spouse 401k (Principal)",
            "Thiago Roth IRA (M1)", "M1 Taxable", "Binance US",
            "Clear Corretora (BRL)", "SoFi Checking",
        ],
    }

    # Distill correlation summary to top 3 pairs
    corr_matrix = portfolio_snapshot.get("correlation_matrix", {})
    correlation_summary: list[dict[str, Any]] = []
    for s1 in corr_matrix:
        for s2 in corr_matrix.get(s1, {}):
            if s1 < s2:
                val = corr_matrix[s1][s2]
                if abs(val) > 0.4:
                    correlation_summary.append({"sleeves": f"{s1}/{s2}", "correlation": round(val, 2)})
    correlation_summary.sort(key=lambda x: abs(x["correlation"]), reverse=True)

    return {
        "run_context": {
            "timestamp": run_context.get("timestamp", datetime.now(timezone.utc).isoformat()),
            "event_type": run_context.get("event_type", "daily_check"),
            "volatility_regime": run_context.get("regime", "normal"),
            "economic_season": run_context.get("economic_season", "normal"),
            "vix": run_context.get("vix"),
            "notes": run_context.get("notes"),
        },
        "ips_summary": ips_summary,
        "strategy_config": active_config,
        "portfolio_snapshot": {
            "total_value_usd": portfolio_snapshot.get("total_value_usd"),
            "total_value_brl": portfolio_snapshot.get("total_value_brl"),
            "sleeve_weights": portfolio_snapshot.get("sleeve_weights", []),
            "risk_parity_weights": portfolio_snapshot.get("risk_parity_weights", {}),
            "correlation_summary": correlation_summary[:3],
            "concentration_top5": portfolio_snapshot.get("concentration_top5", []),
        },
        "valuation_snapshot": {
            "top_value_candidates": valuation_snapshot.get("top_opportunities", [])[:5],
            "tier_opportunities": valuation_snapshot.get("tier_opportunities", []),
            "margin_of_safety_distribution": valuation_snapshot.get("mos_distribution", {}),
            "assets_scored": valuation_snapshot.get("assets_scored", 0),
        },
        "performance_snapshot": {
            "twr_ytd": performance_snapshot.get("twr_ytd"),
            "vs_benchmark_delta": performance_snapshot.get("ytd_vs_benchmark"),
            "sharpe": performance_snapshot.get("sharpe"),
            "sortino": performance_snapshot.get("sortino"),
            "max_drawdown": performance_snapshot.get("max_drawdown"),
            "volatility_annualized": performance_snapshot.get("volatility"),
        },
        "news_and_research": {
            "macro_summary": news_and_research.get("macro_summary", ""),
            "macro_regime": news_and_research.get("macro_regime", ""),
            "asset_news": news_and_research.get("asset_news", [])[:10],
            "earnings_alerts": news_and_research.get("earnings_alerts", []),
        },
        "proposed_trades": [
            {
                "account": t.get("account_name", ""),
                "type": t.get("trade_type", ""),
                "symbol": t.get("symbol", ""),
                "amount_usd": t.get("amount_usd", 0),
                "reason": t.get("reason", ""),
                "tax_risk_level": t.get("tax_risk_level", "low"),
                "margin_of_safety_pct": t.get("margin_of_safety_pct"),
                "moat_rating": t.get("moat_rating"),
                "requires_approval": t.get("requires_approval", False),
                "opportunity_tier": t.get("opportunity_tier"),
            }
            for t in proposed_trades
        ],
    }


async def call_ai_advisor(
    payload: dict[str, Any],
    signals_run_id: str | None = None,
) -> AIResponse:
    """
    Call claude-sonnet-4-20250514 with the investment payload.

    Gracefully falls back to FALLBACK_RESPONSE on any error.
    Results cached in Redis keyed by signals_run_id (TTL: 24hr).

    Args:
        payload: Structured payload from build_ai_payload().
        signals_run_id: Optional run ID for Redis cache key.

    Returns:
        AIResponse — always returns a valid response, never raises.
    """
    # ── Check Redis cache ────────────────────────────────────────────────
    if signals_run_id:
        try:
            from app.db.redis_client import get_redis_client
            cache_key = f"ai_advisory:{signals_run_id}"
            redis = get_redis_client()
            if redis:
                cached = redis.get(cache_key)
                if cached:
                    data = json.loads(cached)
                    resp = AIResponse.model_validate(data)
                    resp.cached = True
                    logger.info("AI response cache hit: %s", cache_key)
                    return resp
        except Exception as exc:
            logger.debug("Redis cache check failed (non-critical): %s", exc)

    # ── Check API key ────────────────────────────────────────────────────
    if not settings.anthropic_api_key:
        logger.warning("ANTHROPIC_API_KEY not set — returning fallback AI response")
        return FALLBACK_RESPONSE

    # ── Call Claude API ──────────────────────────────────────────────────
    try:
        import anthropic

        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        user_message = json.dumps(payload, indent=None, ensure_ascii=False, default=str)

        logger.info(
            "Calling Claude API model=claude-sonnet-4-20250514 payload_chars=%d",
            len(user_message),
        )

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            temperature=0,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )

        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        logger.info("Claude API response: input=%d output=%d tokens", input_tokens, output_tokens)

        raw_text = response.content[0].text.strip()

        # Strip markdown fences if present
        if raw_text.startswith("```"):
            lines = raw_text.split("\n")
            raw_text = "\n".join(lines[1:-1]) if lines[-1] == "```" else "\n".join(lines[1:])

        parsed = json.loads(raw_text)
        ai_response = validate_ai_response_schema(parsed)
        ai_response.input_tokens = input_tokens
        ai_response.output_tokens = output_tokens
        ai_response.cached = False

        # ── Cache in Redis ───────────────────────────────────────────────
        if signals_run_id:
            try:
                from app.db.redis_client import get_redis_client
                cache_key = f"ai_advisory:{signals_run_id}"
                redis = get_redis_client()
                if redis:
                    redis.setex(cache_key, 86400, ai_response.model_dump_json())
            except Exception as exc:
                logger.debug("Redis cache write failed (non-critical): %s", exc)

        return ai_response

    except json.JSONDecodeError as exc:
        logger.error("AI response JSON parse error: %s", exc)
        fallback = FALLBACK_RESPONSE.model_copy()
        fallback.validation.overall_status = "parse_error"
        fallback.validation.issues = [f"JSON parse error: {exc}"]
        fallback.explanation_for_user.short_summary = (
            "AI validation unavailable — proceeding with engine recommendation."
        )
        return fallback

    except Exception as exc:
        logger.error("AI advisor call failed: %s", exc, exc_info=True)
        return FALLBACK_RESPONSE


def validate_ai_response_schema(raw: dict[str, Any]) -> AIResponse:
    """
    Validate and coerce AI response into AIResponse schema.

    Fills missing fields with safe defaults rather than raising.
    Logs warnings for any missing required fields.

    Args:
        raw: Parsed JSON dict from Claude API.

    Returns:
        Validated AIResponse.
    """
    # Ensure validation field
    validation_raw = raw.get("validation", {})
    status = validation_raw.get("overall_status", "ok")
    if status not in ("ok", "warning", "block", "parse_error"):
        logger.warning("AI returned unknown overall_status=%s — defaulting to 'ok'", status)
        status = "ok"

    validation = ValidationResult(
        overall_status=status,
        issues=validation_raw.get("issues", []),
    )

    # Framework check — all 5 required
    fc_raw = raw.get("investment_framework_check", {})
    for key in ("swensen_alignment", "dalio_risk_balance", "graham_margin_of_safety", "bogle_cost_check"):
        if fc_raw.get(key) not in ("pass", "warning", "fail"):
            logger.debug("AI framework check %s missing/invalid — defaulting to 'pass'", key)
            fc_raw[key] = "pass"

    framework_check = FrameworkCheck(
        swensen_alignment=fc_raw.get("swensen_alignment", "pass"),
        swensen_detail=fc_raw.get("swensen_detail"),
        dalio_risk_balance=fc_raw.get("dalio_risk_balance", "pass"),
        dalio_detail=fc_raw.get("dalio_detail"),
        marks_cycle_read=fc_raw.get("marks_cycle_read", ""),
        marks_detail=fc_raw.get("marks_detail"),
        graham_margin_of_safety=fc_raw.get("graham_margin_of_safety", "pass"),
        graham_detail=fc_raw.get("graham_detail"),
        bogle_cost_check=fc_raw.get("bogle_cost_check", "pass"),
        bogle_detail=fc_raw.get("bogle_detail"),
    )

    # Trade recommendations
    tr_raw = raw.get("trade_recommendations", {})
    per_trade = [
        TradeFeedback(
            symbol=t.get("symbol", ""),
            recommendation=t.get("recommendation", "proceed"),
            comment=t.get("comment", ""),
        )
        for t in tr_raw.get("per_trade_feedback", [])
    ]
    trade_recs = TradeRecommendations(
        summary=tr_raw.get("summary", ""),
        per_trade_feedback=per_trade,
        suggested_adjustments=tr_raw.get("suggested_adjustments", []),
    )

    # Portfolio assessment
    pa_raw = raw.get("portfolio_assessment", {})
    portfolio_assessment = PortfolioAssessment(
        risk_posture=pa_raw.get("risk_posture", ""),
        diversification_comment=pa_raw.get("diversification_comment", ""),
        factor_tilts=pa_raw.get("factor_tilts", ""),
        benchmark_comparison=pa_raw.get("benchmark_comparison", ""),
    )

    # Macro commentary
    mc_raw = raw.get("macro_and_opportunity_commentary", {})
    macro_commentary = MacroOpportunityCommentary(
        macro_regime=mc_raw.get("macro_regime", ""),
        cycle_position=mc_raw.get("cycle_position", ""),
        macro=mc_raw.get("macro", []),
        opportunities=mc_raw.get("opportunities", []),
        risks_to_watch=mc_raw.get("risks_to_watch", []),
    )

    # User explanation — enforce 100 word limit on short_summary
    eu_raw = raw.get("explanation_for_user", {})
    short_summary = eu_raw.get("short_summary", "")
    words = short_summary.split()
    if len(words) > 100:
        short_summary = " ".join(words[:100]) + "…"
        logger.debug("Truncated AI short_summary from %d to 100 words", len(words))

    explanation = ExplanationForUser(
        short_summary=short_summary,
        detailed_bullets=eu_raw.get("detailed_bullets", []),
    )

    return AIResponse(
        validation=validation,
        investment_framework_check=framework_check,
        trade_recommendations=trade_recs,
        portfolio_assessment=portfolio_assessment,
        macro_and_opportunity_commentary=macro_commentary,
        explanation_for_user=explanation,
        model_used="claude-sonnet-4-20250514",
        cached=False,
    )
