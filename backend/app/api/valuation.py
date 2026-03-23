"""
Valuation API endpoints (Phase 3).

POST /valuation_update         — run weekly valuation pipeline
GET  /valuation_summary        — top opportunities + MoS distribution
GET  /valuation/{symbol}       — full detail for a single asset
POST /admin/seed               — seed SEED_ASSETS for dev environment
"""

from __future__ import annotations

import logging
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query

from app.schemas.valuation_models import (
    AssetValuationDetail,
    ValuationSummaryResponse,
    ValuationUpdateRequest,
    ValuationUpdateResponse,
)
from app.services.valuation_engine import passes_buy_signal_gate
from app.schemas.allocation_models import EconomicSeason

logger = logging.getLogger(__name__)
router = APIRouter()


# ── POST /valuation_update ────────────────────────────────────────────────────

@router.post("/valuation_update", response_model=ValuationUpdateResponse, tags=["valuation"])
def valuation_update(
    body: ValuationUpdateRequest,
    background_tasks: BackgroundTasks,
) -> ValuationUpdateResponse:
    """
    Trigger the weekly valuation pipeline.

    Scores all active assets using Fama-French factor model,
    runs DCF for eligible stocks, and upserts results to asset_valuations.

    If dry_run=True: computes scores but skips DB writes (safe for testing).
    Heavy computation runs synchronously — for production use, wire to n8n nightly job.
    """
    from app.services.valuation_engine import run_valuation_pipeline
    from app.services.volatility_regime import get_economic_season

    # Resolve economic season
    if body.economic_season:
        try:
            season = EconomicSeason(body.economic_season)
        except ValueError:
            raise HTTPException(400, f"Invalid economic_season: {body.economic_season}")
    else:
        try:
            season = get_economic_season()
        except Exception as exc:
            logger.warning("Season detection failed, using NORMAL: %s", exc)
            season = EconomicSeason.NORMAL

    result = run_valuation_pipeline(season=season, dry_run=body.dry_run)

    return ValuationUpdateResponse(
        assets_updated=result.assets_updated,
        top_opportunities=result.top_opportunities,
        notable_changes=result.notable_changes,
        errors=result.errors,
        economic_season=season.value,
        run_timestamp=datetime.utcnow(),
    )


# ── GET /valuation_summary ────────────────────────────────────────────────────

@router.get("/valuation_summary", response_model=ValuationSummaryResponse, tags=["valuation"])
def valuation_summary(
    user_id: str = Query(
        "00000000-0000-0000-0000-000000000001",
        description="User ID (reserved for future multi-user support)",
    ),
) -> ValuationSummaryResponse:
    """
    Return high-level valuation summary: top opportunities + MoS distribution.

    Used by the dashboard's 'Top Opportunities' and 'Overvalued Positions' cards.
    """
    from app.db.repositories.valuations import (
        get_latest_valuations,
        get_opportunity_candidates,
        get_top_by_composite_score,
        get_valuation_summary_stats,
    )

    try:
        stats = get_valuation_summary_stats()
    except Exception as exc:
        logger.error("Summary stats failed: %s", exc)
        stats = {}

    try:
        top_composite = get_top_by_composite_score(limit=10, min_quality_score=0.40)
    except Exception as exc:
        logger.error("Top composite failed: %s", exc)
        top_composite = []

    try:
        opps = get_opportunity_candidates(min_margin_of_safety=0.15, min_drawdown=0.30)
    except Exception as exc:
        logger.error("Opportunities failed: %s", exc)
        opps = []

    # MoS distribution buckets
    try:
        latest = get_latest_valuations()
        mos_dist: dict[str, int] = {
            "above_20pct": 0, "10_to_20pct": 0,
            "0_to_10pct": 0, "negative": 0, "no_data": 0,
        }
        for v in latest:
            mos = v.get("margin_of_safety_pct")
            if mos is None:
                mos_dist["no_data"] += 1
            elif mos >= 0.20:
                mos_dist["above_20pct"] += 1
            elif mos >= 0.10:
                mos_dist["10_to_20pct"] += 1
            elif mos >= 0:
                mos_dist["0_to_10pct"] += 1
            else:
                mos_dist["negative"] += 1
    except Exception as exc:
        logger.error("MoS distribution failed: %s", exc)
        mos_dist = {}

    # Slim down the response rows for dashboard cards
    def _slim(row: dict) -> dict:
        asset = row.get("assets") or row
        return {
            "symbol":               row.get("symbol") or asset.get("symbol"),
            "name":                 row.get("name")   or asset.get("name"),
            "asset_class":          row.get("asset_class") or asset.get("asset_class"),
            "moat_rating":          row.get("moat_rating") or asset.get("moat_rating"),
            "composite_score":      row.get("composite_score"),
            "margin_of_safety_pct": row.get("margin_of_safety_pct"),
            "tier":                 row.get("tier"),
            "rank_in_universe":     row.get("rank_in_universe"),
            "price":                row.get("price"),
            "buy_target":           row.get("buy_target"),
            "fair_value_estimate_dcf": row.get("fair_value_estimate_dcf"),
        }

    return ValuationSummaryResponse(
        as_of_date=stats.get("last_updated"),
        assets_scored=stats.get("assets_scored", 0),
        positive_mos_count=stats.get("positive_mos", 0),
        negative_mos_count=stats.get("negative_mos", 0),
        opportunity_count=stats.get("opportunities", 0),
        top_by_composite=[_slim(r) for r in top_composite[:8]],
        top_opportunities=[_slim(r) for r in opps[:5]],
        margin_of_safety_distribution=mos_dist,
    )


# ── GET /valuation/{symbol} ───────────────────────────────────────────────────

@router.get("/valuation/{symbol}", response_model=AssetValuationDetail, tags=["valuation"])
def valuation_detail(symbol: str) -> AssetValuationDetail:
    """
    Full valuation detail for a single asset.
    Includes factor scores, DCF assumptions, buy/hold/sell targets, and buy gate status.
    """
    from app.db.repositories.valuations import get_valuation_by_symbol
    from app.services.market_data import fetch_news

    row = get_valuation_by_symbol(symbol.upper())
    if not row:
        raise HTTPException(404, f"No valuation found for {symbol.upper()}")

    v_score = row.get("value_score")    or 0.0
    m_score = row.get("momentum_score") or 0.0
    q_score = row.get("quality_score")  or 0.0
    c_score = row.get("composite_score") or 0.0
    mos     = row.get("margin_of_safety_pct")

    passes = passes_buy_signal_gate(v_score, m_score, q_score, c_score, mos)

    return AssetValuationDetail(
        symbol=row.get("symbol", symbol.upper()),
        name=row.get("name"),
        asset_class=row.get("asset_class"),
        currency=row.get("currency", "USD"),
        moat_rating=row.get("moat_rating"),
        is_dcf_eligible=bool(row.get("is_dcf_eligible")),
        sector=row.get("sector"),
        region=row.get("region"),
        as_of_date=row.get("as_of_date"),
        price=row.get("price"),
        pe=row.get("pe"),
        ps=row.get("ps"),
        dividend_yield=row.get("dividend_yield"),
        vol_30d=row.get("vol_30d"),
        drawdown_from_6_12m_high_pct=row.get("drawdown_from_6_12m_high_pct"),
        value_score=v_score,
        momentum_score=m_score,
        quality_score=q_score,
        composite_score=c_score,
        rank_in_universe=row.get("rank_in_universe"),
        tier=row.get("tier"),
        fair_value_estimate_dcf=row.get("fair_value_estimate_dcf"),
        margin_of_safety_pct=mos,
        buy_target=row.get("buy_target"),
        hold_range_low=row.get("hold_range_low"),
        hold_range_high=row.get("hold_range_high"),
        sell_target=row.get("sell_target"),
        dcf_assumptions=row.get("dcf_assumptions"),
        passes_buy_gate=passes,
    )
