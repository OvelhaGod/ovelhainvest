"""
Valuation API endpoints (Phase 3).

POST /valuation_update         — run weekly valuation pipeline
GET  /valuation_summary        — top opportunities + MoS distribution
GET  /valuation/{symbol}       — full detail for a single asset
POST /admin/seed               — seed SEED_ASSETS + alert rules + benchmarks + strategy config
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

# ── POST /admin/seed ──────────────────────────────────────────────────────────

@router.post("/admin/seed", tags=["admin"])
def seed_dev_data(user_id: str = Query(default=None)) -> dict:
    """
    Full dev seed — idempotent, safe to call multiple times.

    Seeds:
    1. 25 SEED_ASSETS into assets table
    2. 11 BUILT_IN_ALERT_RULES into alert_rules table
    3. 3 benchmark records (SPY, ACWI, AGG) into benchmarks table
    4. Default strategy_config v1.0.0 (is_active=true) into strategy_configs table
    """
    from app.db.repositories.assets import run_seed_data
    from app.db.supabase_client import get_supabase_client
    from app.services.alert_engine import BUILT_IN_ALERT_RULES
    from app.config import get_settings

    if not user_id:
        _s = get_settings()
        user_id = _s.default_user_id or "00000000-0000-0000-0000-000000000001"

    results: dict = {"assets": {}, "alert_rules": {}, "benchmarks": {}, "strategy_config": {}}

    # ── 1. Assets ──
    try:
        results["assets"] = run_seed_data()
    except Exception as exc:
        results["assets"] = {"error": str(exc)}
        logger.error("seed assets failed: %s", exc)

    client = get_supabase_client()

    # ── 2. Alert Rules ──
    try:
        rules_to_insert = []
        for rule in BUILT_IN_ALERT_RULES:
            conditions: dict = {}
            if "threshold" in rule:
                conditions["threshold"] = rule["threshold"]
            if "action" in rule:
                conditions["action"] = rule["action"]
            if "tier" in rule:
                conditions["tier"] = rule["tier"]
            if "days_ahead" in rule:
                conditions["days_ahead"] = rule["days_ahead"]
            if "threshold_pct" in rule:
                conditions["threshold_pct"] = rule["threshold_pct"]
            if "pair" in rule:
                conditions["pair"] = rule["pair"]
            if "priority" in rule:
                conditions["priority"] = rule["priority"]
            rules_to_insert.append({
                "user_id": user_id,
                "rule_name": rule["name"],
                "rule_type": rule["type"],
                "conditions": conditions,
                "channel": rule.get("channel", "telegram"),
                "is_active": True,
            })
        # Upsert: ignore duplicates by rule_name + user_id
        inserted_rules = 0
        skipped_rules = 0
        for rule_rec in rules_to_insert:
            try:
                existing = (
                    client.table("alert_rules")
                    .select("id")
                    .eq("user_id", user_id)
                    .eq("rule_name", rule_rec["rule_name"])
                    .execute()
                )
                if existing.data:
                    skipped_rules += 1
                else:
                    client.table("alert_rules").insert(rule_rec).execute()
                    inserted_rules += 1
            except Exception as exc_r:
                logger.warning("seed alert_rule insert failed: %s", exc_r)
                skipped_rules += 1
        results["alert_rules"] = {
            "total": len(rules_to_insert),
            "inserted": inserted_rules,
            "skipped": skipped_rules,
        }
    except Exception as exc:
        results["alert_rules"] = {"error": str(exc)}
        logger.error("seed alert_rules failed: %s", exc)

    # ── 3. Benchmarks ──
    BENCHMARKS = [
        {"symbol": "SPY",  "description": "S&P 500 — primary US equity benchmark", "blend_weights": {"SPY": 1.0}},
        {"symbol": "ACWI", "description": "MSCI All Country World — global benchmark", "blend_weights": {"ACWI": 1.0}},
        {"symbol": "AGG",  "description": "US Aggregate Bond — bond benchmark",     "blend_weights": {"AGG": 1.0}},
    ]
    try:
        inserted_bench = 0
        skipped_bench = 0
        for bm in BENCHMARKS:
            try:
                existing = (
                    client.table("benchmarks")
                    .select("id")
                    .eq("symbol", bm["symbol"])
                    .execute()
                )
                if existing.data:
                    skipped_bench += 1
                else:
                    client.table("benchmarks").insert(bm).execute()
                    inserted_bench += 1
            except Exception as exc_b:
                logger.warning("seed benchmark insert failed: %s", exc_b)
                skipped_bench += 1
        results["benchmarks"] = {
            "total": len(BENCHMARKS),
            "inserted": inserted_bench,
            "skipped": skipped_bench,
        }
    except Exception as exc:
        results["benchmarks"] = {"error": str(exc)}
        logger.error("seed benchmarks failed: %s", exc)

    # ── 4. Default Strategy Config v1.0.0 ──
    STRATEGY_CONFIG_V1 = {
        "version": "1.0.0",
        "sleeve_targets": {
            "us_equity":     {"target": 0.45, "min": 0.40, "max": 0.50},
            "intl_equity":   {"target": 0.15, "min": 0.10, "max": 0.20},
            "bonds":         {"target": 0.20, "min": 0.10, "max": 0.30},
            "brazil_equity": {"target": 0.10, "min": 0.05, "max": 0.15},
            "crypto":        {"target": 0.07, "min": 0.05, "max": 0.10},
            "cash":          {"target": 0.03, "min": 0.02, "max": 0.10},
        },
        "drift_threshold": 0.05,
        "hard_rebalance_cooldown_days": 30,
        "min_trade_usd": 50,
        "max_single_trade_pct": 0.05,
        "max_daily_trades_pct": 0.10,
        "volatility_regime": {
            "vix_threshold": 30,
            "equity_daily_move_pct": 0.03,
            "crypto_daily_move_pct": 0.10,
            "defer_dca_days": [1, 3],
        },
        "drawdown_thresholds": {
            "alert": 0.25,
            "pause_automation": 0.40,
            "behavioral_max": 0.35,
        },
        "opportunity_rules": {
            "max_events_per_year": 5,
            "required_min_margin_of_safety": 0.15,
            "tier_1": {"drawdown_from_6_12m_high": 0.30, "deploy_fraction_of_vault": 0.20, "max_portfolio_fraction": 0.02},
            "tier_2": {"drawdown_from_6_12m_high": 0.50, "deploy_additional_vault_fraction": 0.30, "max_total_portfolio_fraction": 0.05},
        },
        "concentration_limits": {
            "max_single_stock_pct": 0.07,
            "max_single_sector_pct": 0.25,
            "max_single_country_ex_us_pct": 0.15,
            "max_crypto_pct": 0.10,
            "min_crypto_pct": 0.03,
            "max_individual_stocks_of_equity": 0.30,
        },
    }
    try:
        existing = (
            client.table("strategy_configs")
            .select("id")
            .eq("user_id", user_id)
            .eq("version", "1.0.0")
            .execute()
        )
        if existing.data:
            results["strategy_config"] = {"status": "skipped", "version": "1.0.0"}
        else:
            # Deactivate any existing active config
            client.table("strategy_configs").update({"is_active": False}).eq("user_id", user_id).eq("is_active", True).execute()
            client.table("strategy_configs").insert({
                "user_id": user_id,
                "version": "1.0.0",
                "is_active": True,
                "config": STRATEGY_CONFIG_V1,
            }).execute()
            results["strategy_config"] = {"status": "inserted", "version": "1.0.0"}
    except Exception as exc:
        results["strategy_config"] = {"error": str(exc)}
        logger.error("seed strategy_config failed: %s", exc)

    # ── 5. Sync tax lots from existing transactions (idempotent) ──
    results["tax_lots_sync"] = {}
    try:
        from app.services.tax_lot_engine import sync_lots_from_transactions
        # Fetch all taxable + brazil_taxable accounts for this user
        taxable_accts = (
            client.table("accounts")
            .select("id, tax_treatment")
            .eq("user_id", user_id)
            .in_("tax_treatment", ["taxable", "brazil_taxable"])
            .execute()
        )
        lots_opened = 0
        lots_closed = 0
        sync_errors: list[str] = []
        for acct in (taxable_accts.data or []):
            acct_id = acct["id"]
            txn_resp = (
                client.table("transactions")
                .select("*")
                .eq("account_id", acct_id)
                .order("executed_at")
                .execute()
            )
            txns = txn_resp.data or []
            if not txns:
                continue
            result = sync_lots_from_transactions(
                account_id=acct_id,
                transactions=txns,
                db=client,
            )
            lots_opened += result.lots_opened
            lots_closed += result.lots_closed
            sync_errors.extend(result.errors[:5])  # cap errors per account
        results["tax_lots_sync"] = {
            "accounts_processed": len(taxable_accts.data or []),
            "lots_opened": lots_opened,
            "lots_closed": lots_closed,
            "errors": sync_errors[:10],
        }
    except Exception as exc:
        results["tax_lots_sync"] = {"error": str(exc)}
        logger.error("seed tax_lots_sync failed: %s", exc)

    total_errors = sum(1 for v in results.values() if isinstance(v, dict) and "error" in v)
    return {
        "status": "ok" if total_errors == 0 else "partial",
        "message": f"Seed complete — {total_errors} section(s) with errors",
        "results": results,
    }


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
    Redis-cached for 15 minutes.
    """
    cache_key = f"val_summary:{user_id}"
    try:
        from app.db.redis_client import get_redis_client as _get_rc
        _rc = _get_rc()
        _cached = _rc.get(cache_key)
        if _cached:
            return ValuationSummaryResponse.model_validate_json(_cached)
    except Exception as _ce:
        logger.debug("Redis cache miss (val_summary): %s", _ce)

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

    val_result = ValuationSummaryResponse(
        as_of_date=stats.get("last_updated"),
        assets_scored=stats.get("assets_scored", 0),
        positive_mos_count=stats.get("positive_mos", 0),
        negative_mos_count=stats.get("negative_mos", 0),
        opportunity_count=stats.get("opportunities", 0),
        top_by_composite=[_slim(r) for r in top_composite[:8]],
        top_opportunities=[_slim(r) for r in opps[:5]],
        margin_of_safety_distribution=mos_dist,
    )
    try:
        from app.db.redis_client import get_redis_client as _get_rc2
        _get_rc2().set(cache_key, val_result.model_dump_json(), ex=900)  # 15-minute TTL
    except Exception as _se:
        logger.debug("Redis cache store failed (val_summary): %s", _se)
    return val_result


# ── GET /assets/list ─────────────────────────────────────────────────────────

@router.get("/assets/list", tags=["valuation"])
def assets_list(user_id: str = Query(default=None)) -> dict:
    """
    Return ALL active assets with their latest valuation data.
    Unlike /valuation_summary (which caps at 8), this returns the full universe.
    Includes value_score, momentum_score, quality_score for the assets page table.
    Also includes in_portfolio: bool from current holdings.
    Cached 5 minutes in Redis.
    """
    from app.config import get_default_user_id
    uid = user_id or get_default_user_id()
    cache_key = f"assets:list:{uid}"
    try:
        from app.db.redis_client import get_redis_client as _get_rc
        _rc = _get_rc()
        _cached = _rc.get(cache_key)
        if _cached:
            import json as _json
            return _json.loads(_cached)
    except Exception as _ce:
        logger.debug("Redis cache miss (assets:list): %s", _ce)

    from app.db.repositories.valuations import get_latest_valuations
    from app.db.repositories.holdings import get_holdings

    try:
        rows = get_latest_valuations()
    except Exception as exc:
        logger.error("assets_list failed: %s", exc)
        rows = []

    # Build set of held asset_ids for in_portfolio indicator
    held_asset_ids: set[str] = set()
    try:
        holdings = get_holdings(uid)
        held_asset_ids = {h["asset_id"] for h in holdings if float(h.get("quantity", 0)) > 0}
    except Exception as he:
        logger.debug("Could not load holdings for in_portfolio: %s", he)

    as_of_date = rows[0].get("as_of_date") if rows else None
    scored = sum(1 for r in rows if r.get("composite_score") is not None)

    assets = []
    for row in rows:
        assets.append({
            "symbol":                   row.get("symbol"),
            "name":                     row.get("name"),
            "asset_class":              row.get("asset_class"),
            "moat_rating":              row.get("moat_rating"),
            "currency":                 row.get("currency"),
            "sector":                   row.get("sector"),
            "is_dcf_eligible":          row.get("is_dcf_eligible"),
            "price":                    row.get("price"),
            "value_score":              row.get("value_score"),
            "momentum_score":           row.get("momentum_score"),
            "quality_score":            row.get("quality_score"),
            "composite_score":          row.get("composite_score"),
            "margin_of_safety_pct":     row.get("margin_of_safety_pct"),
            "fair_value_estimate_dcf":  row.get("fair_value_estimate_dcf"),
            "buy_target":               row.get("buy_target"),
            "hold_range_low":           row.get("hold_range_low"),
            "hold_range_high":          row.get("hold_range_high"),
            "sell_target":              row.get("sell_target"),
            "tier":                     row.get("tier"),
            "rank_in_universe":         row.get("rank_in_universe"),
            "as_of_date":               row.get("as_of_date"),
            "vol_30d":                  row.get("vol_30d"),
            "drawdown_from_6_12m_high_pct": row.get("drawdown_from_6_12m_high_pct"),
            "in_portfolio": row.get("id") in held_asset_ids or row.get("asset_id") in held_asset_ids,
        })

    result = {"assets": assets, "total": len(assets), "scored": scored, "as_of_date": as_of_date}
    try:
        import json as _json2
        from app.db.redis_client import get_redis_client as _get_rc2
        _get_rc2().set(cache_key, _json2.dumps(result), ex=300)
    except Exception as _se:
        logger.debug("Redis cache store failed (assets:list): %s", _se)
    return result


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
