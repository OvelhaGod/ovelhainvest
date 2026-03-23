"""
Valuation Engine: Fama-French 5-factor scoring with regime-aware composite weights.

Factor mapping (CLAUDE.md Section 26.1):
  Value score    → Fama-French HML:        PE inverse + PS inverse + PB inverse + dividend yield
  Momentum score → Carhart MOM:            12-1mo return + 3mo return + earnings revision trend
  Quality score  → Fama-French RMW + CMA: ROE + op-margin + debt/equity inverse + earnings stability
  Low-vol        → quality MODIFIER only (+0.05 bonus) — NOT a standalone factor

Composite score uses regime-aware weights from FACTOR_COMPOSITE_WEIGHTS_BY_REGIME (Section 26.2).
BUY_SIGNAL_REQUIREMENTS gate: all factors must exceed minimums (Section 26.3).
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from datetime import date
from typing import Any

import numpy as np
import pandas as pd

from app.services.market_data import (
    compute_drawdown_from_high,
    compute_volatility_30d,
    fetch_current_prices,
    fetch_fundamentals,
    fetch_price_history,
)
from app.services.volatility_regime import get_factor_weights_for_regime
from app.schemas.allocation_models import EconomicSeason

logger = logging.getLogger(__name__)

# ── BUY signal gate (CLAUDE.md Section 26.3) ─────────────────────────────────
BUY_SIGNAL_REQUIREMENTS = {
    "min_value_score":      0.40,
    "min_momentum_score":   0.35,
    "min_quality_score":    0.55,
    "min_composite_score":  0.55,
    "min_margin_of_safety": 0.10,
}

LOW_VOL_QUALITY_BONUS = 0.05  # Section 26.1: low-vol as quality modifier only


# ── Percentile helpers ────────────────────────────────────────────────────────

def _percentile_rank_asc(value: float | None, all_values: list[float | None]) -> float:
    """
    Fraction of valid values strictly below `value` (ascending rank 0-1).
    Returns 0.5 (neutral) when value is None or universe is too small.

    For VALUE metrics: use (1 - rank) since lower P/E = better value.
    For QUALITY metrics: use rank directly since higher ROE = better.
    """
    if value is None:
        return 0.5
    valid = [v for v in all_values if v is not None and not math.isnan(float(v))]
    if len(valid) < 2:
        return 0.5
    return sum(1 for v in valid if v < value) / len(valid)


# ── Factor score functions ────────────────────────────────────────────────────

def compute_value_score(
    fundamentals: dict[str, Any],
    universe_fundamentals: list[dict[str, Any]],
) -> float:
    """
    Fama-French HML value score (0-1, higher = cheaper relative to peers).

    Weights (Section 26.1):
      PE percentile inverse   35%
      PS percentile inverse   25%
      PB percentile inverse   25%
      Dividend yield rank     15%

    Returns 0.5 for assets with no fundamental data (crypto, many ETFs).
    """
    pe  = fundamentals.get("pe")
    ps  = fundamentals.get("ps")
    pb  = fundamentals.get("pb")
    div = fundamentals.get("dividend_yield") or 0.0

    if not any(fundamentals.get(k) for k in ("pe", "ps", "pb", "dividend_yield")):
        return 0.5

    all_pes = [u.get("pe") for u in universe_fundamentals]
    all_ps  = [u.get("ps") for u in universe_fundamentals]
    all_pb  = [u.get("pb") for u in universe_fundamentals]
    all_div = [(u.get("dividend_yield") or 0.0) for u in universe_fundamentals]

    pe_score  = (1.0 - _percentile_rank_asc(pe, all_pes)) if pe else 0.5
    ps_score  = (1.0 - _percentile_rank_asc(ps, all_ps))  if ps else 0.5
    pb_score  = (1.0 - _percentile_rank_asc(pb, all_pb))  if pb else 0.5
    div_score = _percentile_rank_asc(div, all_div)

    return max(0.0, min(1.0,
        0.35 * pe_score + 0.25 * ps_score + 0.25 * pb_score + 0.15 * div_score
    ))


def compute_momentum_score(
    price_history: pd.Series,
    earnings_growth: float | None = None,
) -> float:
    """
    Carhart MOM momentum score (0-1, higher = stronger positive momentum).

    Weights (Section 26.1):
      12-1 month return       60%  (return from -12mo to -1mo, skips recent month)
      3-month return          25%
      Earnings revision proxy 15%  (earnings_growth direction)

    Returns 0.5 with insufficient history (<30 bars).
    """
    if len(price_history) < 30:
        return 0.5

    def _safe_return(bars_start: int, bars_end: int) -> float | None:
        n = len(price_history)
        if n <= bars_start:
            return None
        s = max(0, n - 1 - bars_start)
        e = max(0, n - 1 - bars_end)
        if s >= e:
            return None
        p0 = float(price_history.iloc[s])
        p1 = float(price_history.iloc[e])
        return (p1 / p0 - 1.0) if p0 > 0 else None

    def _sig(ret: float | None, k: float = 4.0) -> float:
        if ret is None:
            return 0.5
        return 1.0 / (1.0 + math.exp(-max(-1.5, min(1.5, ret)) * k))

    return max(0.0, min(1.0,
        0.60 * _sig(_safe_return(252, 21))
        + 0.25 * _sig(_safe_return(63, 0), k=5.0)
        + 0.15 * (_sig(earnings_growth, k=3.0) if earnings_growth is not None else 0.5)
    ))


def compute_quality_score(
    fundamentals: dict[str, Any],
    universe_fundamentals: list[dict[str, Any]],
    vol_30d: float | None = None,
    market_median_vol: float | None = None,
) -> float:
    """
    Fama-French RMW + CMA quality score (0-1, higher = better quality).

    Weights (Section 26.1):
      ROE rank                30%
      Operating margin rank   25%
      Debt/equity inverse     25%
      Earnings growth rank    20%

    Low-vol MODIFIER: +0.05 bonus if vol_30d < market_median_vol (NOT standalone factor).

    Returns 0.5 for assets with no quality fundamental data.
    """
    roe = fundamentals.get("roe")
    om  = fundamentals.get("operating_margin")
    d2e = fundamentals.get("debt_to_equity")
    eg  = fundamentals.get("earnings_growth")

    if not any(fundamentals.get(k) for k in ("roe", "operating_margin", "debt_to_equity")):
        return 0.5

    all_roe = [u.get("roe") for u in universe_fundamentals]
    all_om  = [u.get("operating_margin") for u in universe_fundamentals]
    all_d2e = [u.get("debt_to_equity") for u in universe_fundamentals]
    all_eg  = [u.get("earnings_growth") for u in universe_fundamentals]

    roe_score = _percentile_rank_asc(roe, all_roe) if roe is not None else 0.5
    om_score  = _percentile_rank_asc(om, all_om)   if om  is not None else 0.5
    d2e_score = (1.0 - _percentile_rank_asc(d2e, all_d2e)) if d2e is not None else 0.5
    eg_score  = _percentile_rank_asc(eg, all_eg)   if eg  is not None else 0.5

    score = (
        0.30 * roe_score
        + 0.25 * om_score
        + 0.25 * d2e_score
        + 0.20 * eg_score
    )

    # Low-vol modifier: high-quality + low-vol gets bonus
    if (
        vol_30d is not None
        and market_median_vol is not None
        and market_median_vol > 0
        and vol_30d < market_median_vol
    ):
        score += LOW_VOL_QUALITY_BONUS

    return max(0.0, min(1.0, score))


def compute_composite_score(
    value_score: float,
    momentum_score: float,
    quality_score: float,
    season: EconomicSeason = EconomicSeason.NORMAL,
) -> float:
    """
    Regime-aware composite score using FACTOR_COMPOSITE_WEIGHTS_BY_REGIME (Section 26.2).
    Quality is the anchor — poor quality suppresses composite even with great value/momentum.
    """
    weights = get_factor_weights_for_regime(season)
    return max(0.0, min(1.0,
        weights["value_weight"]    * value_score
        + weights["momentum_weight"] * momentum_score
        + weights["quality_weight"]  * quality_score
    ))


def passes_buy_signal_gate(
    value_score: float,
    momentum_score: float,
    quality_score: float,
    composite_score: float,
    margin_of_safety_pct: float | None = None,
) -> bool:
    """Enforce BUY_SIGNAL_REQUIREMENTS — all factors + composite must meet minimums."""
    req = BUY_SIGNAL_REQUIREMENTS
    return (
        value_score     >= req["min_value_score"]
        and momentum_score  >= req["min_momentum_score"]
        and quality_score   >= req["min_quality_score"]
        and composite_score >= req["min_composite_score"]
        and (margin_of_safety_pct is None or margin_of_safety_pct >= req["min_margin_of_safety"])
    )


def rank_universe(assets_with_scores: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sort by composite_score descending and assign rank_in_universe (1 = best)."""
    sorted_assets = sorted(
        assets_with_scores,
        key=lambda a: a.get("composite_score") or 0.0,
        reverse=True,
    )
    for i, a in enumerate(sorted_assets):
        a["rank_in_universe"] = i + 1
    return sorted_assets


def _assign_tier(
    margin_of_safety_pct: float | None,
    composite_score: float,
    drawdown_pct: float | None,
) -> str | None:
    """
    Marks-inspired opportunity tier assignment (Section 7 OPPORTUNITY_RULES).
    tier_2: 50%+ drawdown + 15%+ MoS
    tier_1: 30%+ drawdown + 15%+ MoS
    watch:  meaningful MoS + strong composite
    """
    mos = margin_of_safety_pct or 0.0
    dd  = abs(drawdown_pct or 0.0)
    if mos >= 0.15 and dd >= 0.50:
        return "tier_2"
    if mos >= 0.15 and dd >= 0.30:
        return "tier_1"
    if mos >= 0.10 and composite_score >= 0.55:
        return "watch"
    return None


# ── Weekly pipeline runner ────────────────────────────────────────────────────

@dataclass
class ValuationRunResult:
    assets_updated: int
    top_opportunities: list[dict]
    notable_changes: list[str]
    errors: list[str]


def run_valuation_pipeline(
    season: EconomicSeason = EconomicSeason.NORMAL,
    dry_run: bool = False,
) -> ValuationRunResult:
    """
    Weekly valuation batch: score all active assets and upsert to asset_valuations.

    1. Fetch all active assets
    2. Batch-fetch current prices (15-min cache)
    3. Fetch fundamentals per asset (6-hr cache)
    4. Fetch 2-year price history per asset (1-hr cache)
    5. Build universe for cross-sectional percentile scoring
    6. Compute value + momentum + quality → composite per asset
    7. Run two-stage DCF for is_dcf_eligible assets
    8. Compute margin of safety and buy/hold/sell targets
    9. Rank universe by composite score
    10. Upsert to asset_valuations (as_of_date = today)

    Args:
        season:  Economic season for regime-aware factor weights.
        dry_run: Compute but skip DB writes (for testing/preview).
    """
    from app.db.repositories.assets import get_active_assets
    from app.db.repositories.valuations import upsert_asset_valuation
    from app.services.dcf import (
        compute_buy_hold_sell_targets,
        compute_margin_of_safety,
        run_dcf_for_asset,
    )

    errors: list[str] = []
    updated = 0
    today = date.today().isoformat()

    try:
        assets = get_active_assets()
    except Exception as exc:
        logger.error("Failed to fetch assets: %s", exc)
        return ValuationRunResult(0, [], [], [str(exc)])

    if not assets:
        return ValuationRunResult(0, [], [], ["No active assets"])

    symbols = [a["symbol"] for a in assets]
    logger.info("Valuation pipeline: scoring %d assets", len(assets))

    prices = fetch_current_prices(symbols)

    # Fundamentals (per-asset, cached 6hr)
    fund_by_sym: dict[str, dict] = {}
    for asset in assets:
        sym = asset["symbol"]
        try:
            fund_by_sym[sym] = fetch_fundamentals(sym)
        except Exception as exc:
            logger.warning("Fundamentals failed for %s: %s", sym, exc)
            fund_by_sym[sym] = {"symbol": sym}

    universe_fundamentals = list(fund_by_sym.values())

    # Price histories + vols
    hist_by_sym: dict[str, pd.Series] = {}
    vol_by_sym:  dict[str, float]     = {}
    for asset in assets:
        sym = asset["symbol"]
        try:
            hist = fetch_price_history(sym, period="2y")
            hist_by_sym[sym] = hist
            vol_by_sym[sym]  = compute_volatility_30d(hist)
        except Exception as exc:
            logger.warning("Price history failed for %s: %s", sym, exc)
            hist_by_sym[sym] = pd.Series(dtype=float)
            vol_by_sym[sym]  = 0.0

    all_vols = [v for v in vol_by_sym.values() if v > 0]
    market_median_vol = float(np.median(all_vols)) if all_vols else 0.20

    # Score each asset
    scored: list[dict] = []
    for asset in assets:
        sym      = asset["symbol"]
        asset_id = asset["id"]
        price    = prices.get(sym)
        fund     = fund_by_sym.get(sym, {})
        hist     = hist_by_sym.get(sym, pd.Series(dtype=float))
        vol      = vol_by_sym.get(sym, 0.0)

        try:
            v_score = compute_value_score(fund, universe_fundamentals)
            m_score = compute_momentum_score(hist, earnings_growth=fund.get("earnings_growth"))
            q_score = compute_quality_score(
                fund, universe_fundamentals,
                vol_30d=vol or None,
                market_median_vol=market_median_vol,
            )
            c_score    = compute_composite_score(v_score, m_score, q_score, season)
            drawdown   = compute_drawdown_from_high(hist, window_months=9)

            # DCF
            fair_value_dcf: float | None   = None
            dcf_assumptions: dict | None   = None
            if price and asset.get("is_dcf_eligible") and asset.get("moat_rating") not in (None, "none"):
                net_debt = (fund.get("total_debt") or 0.0) - (fund.get("cash_and_equivalents") or 0.0)
                try:
                    dcf = run_dcf_for_asset(
                        symbol=sym,
                        fcf_0=fund.get("free_cashflow"),
                        current_price=price,
                        shares_outstanding=fund.get("shares_outstanding"),
                        net_debt=net_debt or None,
                    )
                    if dcf:
                        fair_value_dcf  = dcf.get("fair_value_per_share")
                        dcf_assumptions = dcf.get("dcf_assumptions")
                except Exception as exc:
                    logger.warning("DCF failed for %s: %s", sym, exc)

            mos_pct = buy_t = hold_l = hold_h = sell_t = None
            if fair_value_dcf and price:
                mos_pct = compute_margin_of_safety(fair_value_dcf, price)
                tgt     = compute_buy_hold_sell_targets(fair_value_dcf)
                buy_t, hold_l, hold_h, sell_t = (
                    tgt["buy_target"], tgt["hold_range_low"],
                    tgt["hold_range_high"], tgt["sell_target"],
                )

            tier = _assign_tier(mos_pct, c_score, drawdown)

            row = {
                "asset_id":                     asset_id,
                "as_of_date":                   today,
                "price":                        price,
                "pe":                           fund.get("pe"),
                "ps":                           fund.get("ps"),
                "dividend_yield":               fund.get("dividend_yield"),
                "vol_30d":                      vol or None,
                "drawdown_from_6_12m_high_pct": drawdown or None,
                "value_score":                  round(v_score, 4),
                "momentum_score":               round(m_score, 4),
                "quality_score":                round(q_score, 4),
                "composite_score":              round(c_score, 4),
                "fair_value_estimate":          None,
                "fair_value_estimate_dcf":      fair_value_dcf,
                "margin_of_safety_pct":         round(mos_pct, 4) if mos_pct is not None else None,
                "buy_target":                   buy_t,
                "hold_range_low":               hold_l,
                "hold_range_high":              hold_h,
                "sell_target":                  sell_t,
                "dcf_assumptions":              dcf_assumptions,
                "tier":                         tier,
                "symbol":                       sym,
            }
            scored.append(row)

        except Exception as exc:
            logger.error("Scoring failed for %s: %s", sym, exc)
            errors.append(f"{sym}: {exc}")

    ranked = rank_universe(scored)

    top_opps: list[dict] = []
    for row in ranked:
        db_row = {k: v for k, v in row.items() if k != "symbol"}
        db_row["rank_in_universe"] = row["rank_in_universe"]

        if not dry_run and db_row.get("price"):
            try:
                upsert_asset_valuation(db_row)
                updated += 1
            except Exception as exc:
                logger.error("Upsert failed for %s: %s", row.get("symbol"), exc)
                errors.append(f"DB {row.get('symbol')}: {exc}")

        if row.get("tier") in ("tier_1", "tier_2"):
            top_opps.append({
                "symbol":               row["symbol"],
                "tier":                 row["tier"],
                "composite_score":      row["composite_score"],
                "margin_of_safety_pct": row.get("margin_of_safety_pct"),
                "rank":                 row["rank_in_universe"],
            })

    notable = [
        f"{r['symbol']}: composite={r['composite_score']:.2f}, rank={r['rank_in_universe']}"
        for r in ranked[:5]
    ]
    logger.info("Pipeline done: %d updated, %d opps, %d errors", updated, len(top_opps), len(errors))
    return ValuationRunResult(updated, top_opps, notable, errors)
