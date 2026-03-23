"""
DCF (Discounted Cash Flow) engine — Graham/Buffett intrinsic value framework.

Two-stage DCF model (CLAUDE.md Section 2, Item 2):
  Stage 1: Years 1-5 at high growth rate g1
  Stage 2: Years 6-10 at declining growth rate g2
  Terminal: Gordon Growth Model beyond year 10

Margin of safety (Section 6.4):
  margin_of_safety_pct = (fair_value - current_price) / fair_value
  Buy zone requires minimum 15% MoS for individual stocks.
  Buy target: 20% below fair value (explicit Graham buffer)

Only runs for assets with is_dcf_eligible=True and moat_rating != "none".
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# ── Default assumptions (conservative) ───────────────────────────────────────
_DEFAULTS = {
    "discount_rate": 0.10,   # WACC for US large-cap (10%)
    "g1":            0.12,   # Stage 1 growth (5yr)
    "g2":            0.06,   # Stage 2 growth (5yr)
    "g_terminal":    0.03,   # Terminal growth (≈ long-run nominal GDP)
    "stage1_years":  5,
    "stage2_years":  5,
}

# Per-ticker overrides calibrated to business model (CLAUDE.md SEED_ASSETS)
TICKER_OVERRIDES: dict[str, dict] = {
    "GOOG":  {"g1": 0.14, "g2": 0.08, "r": 0.10},
    "GOOGL": {"g1": 0.14, "g2": 0.08, "r": 0.10},
    "AMZN":  {"g1": 0.16, "g2": 0.10, "r": 0.11},
    "AAPL":  {"g1": 0.10, "g2": 0.06, "r": 0.09},
    "META":  {"g1": 0.18, "g2": 0.10, "r": 0.11},
    "MSFT":  {"g1": 0.13, "g2": 0.08, "r": 0.10},
    "NVDA":  {"g1": 0.22, "g2": 0.12, "r": 0.12},
    "CRM":   {"g1": 0.14, "g2": 0.08, "r": 0.11},
    "PLTR":  {"g1": 0.25, "g2": 0.15, "r": 0.14},
    "ARM":   {"g1": 0.20, "g2": 0.12, "r": 0.13},
}


def run_dcf_for_asset(
    symbol: str,
    fcf_0: float | None,
    current_price: float,
    g1: float | None = None,
    g2: float | None = None,
    r: float | None = None,
    g_terminal: float | None = None,
    net_debt: float | None = None,
    shares_outstanding: float | None = None,
) -> dict[str, Any] | None:
    """
    Two-stage DCF valuation for a single equity.

    Stage 1 (years 1-5): FCF grows at g1 annually.
    Stage 2 (years 6-10): FCF grows at g2 annually.
    Terminal value: Gordon Growth at g_terminal beyond year 10.

    Args:
        symbol:             Ticker — used to look up per-stock growth overrides.
        fcf_0:              Base-year free cash flow (TTM, absolute $). None → skip DCF.
        current_price:      Current market price per share.
        g1:                 Stage 1 annual growth rate. Defaults to TICKER_OVERRIDES or 12%.
        g2:                 Stage 2 annual growth rate. Defaults to 6%.
        r:                  Discount rate / WACC. Defaults to 10%.
        g_terminal:         Terminal growth rate. Defaults to 3%.
        net_debt:           Total debt minus cash ($). None treated as 0.
        shares_outstanding: Shares used for per-share calc. Required to return result.

    Returns:
        Dict with fair_value_per_share, margin_of_safety_pct, dcf_assumptions and
        component PVs (pv_stage1, pv_stage2, pv_terminal). None if DCF cannot run.
    """
    if not fcf_0 or fcf_0 <= 0:
        logger.debug("DCF skipped for %s: no positive FCF (%s)", symbol, fcf_0)
        return None

    if not shares_outstanding or shares_outstanding <= 0:
        logger.debug("DCF skipped for %s: no shares_outstanding", symbol)
        return None

    ovr = TICKER_OVERRIDES.get(symbol.upper(), {})
    _g1    = g1         or ovr.get("g1", _DEFAULTS["g1"])
    _g2    = g2         or ovr.get("g2", _DEFAULTS["g2"])
    _r     = r          or ovr.get("r",  _DEFAULTS["discount_rate"])
    _gt    = g_terminal or _DEFAULTS["g_terminal"]
    _nd    = net_debt   or 0.0
    _s1    = _DEFAULTS["stage1_years"]
    _s2    = _DEFAULTS["stage2_years"]

    # Safety: r must exceed terminal growth
    if _r <= _gt:
        _r = _gt + 0.01

    # Stage 1
    pv1 = 0.0
    fcf = fcf_0
    for t in range(1, _s1 + 1):
        fcf *= (1 + _g1)
        pv1 += fcf / ((1 + _r) ** t)

    # Stage 2
    pv2 = 0.0
    for t in range(1, _s2 + 1):
        fcf *= (1 + _g2)
        pv2 += fcf / ((1 + _r) ** (_s1 + t))

    # Terminal value (Gordon Growth Model)
    tv = fcf * (1 + _gt) / (_r - _gt)
    pv_tv = tv / ((1 + _r) ** (_s1 + _s2))

    ev             = pv1 + pv2 + pv_tv
    equity_value   = ev - _nd
    fv_per_share   = equity_value / shares_outstanding

    if fv_per_share <= 0:
        return None

    mos = compute_margin_of_safety(fv_per_share, current_price)

    assumptions = {
        "fcf_base":           fcf_0,
        "g1":                 _g1,
        "g2":                 _g2,
        "discount_rate":      _r,
        "g_terminal":         _gt,
        "stage1_years":       _s1,
        "stage2_years":       _s2,
        "net_debt":           _nd,
        "shares_outstanding": shares_outstanding,
        "pv_stage1":          round(pv1),
        "pv_stage2":          round(pv2),
        "pv_terminal":        round(pv_tv),
    }

    return {
        "symbol":               symbol,
        "current_price":        current_price,
        "fair_value_per_share": round(fv_per_share, 2),
        "margin_of_safety_pct": round(mos, 4),
        "pv_stage1":            round(pv1),
        "pv_stage2":            round(pv2),
        "pv_terminal":          round(pv_tv),
        "enterprise_value":     round(ev),
        "equity_value":         round(equity_value),
        "dcf_assumptions":      assumptions,
    }


def compute_margin_of_safety(fair_value: float, current_price: float) -> float:
    """
    Graham margin of safety: (fair_value - current_price) / fair_value.

    Positive = price is below intrinsic value (safety buffer).
    Negative = price exceeds intrinsic value (potential overvaluation).

    Buy zone requires >= 0.15 for individual stocks (CLAUDE.md Section 6.4).
    """
    if fair_value <= 0:
        return 0.0
    return (fair_value - current_price) / fair_value


def compute_buy_hold_sell_targets(
    fair_value: float,
    buy_discount: float = 0.20,
    hold_discount: float = 0.10,
    hold_premium: float = 0.15,
    sell_premium: float = 0.25,
) -> dict[str, float]:
    """
    Compute price zones around intrinsic value (CLAUDE.md Section 2, Item 2).

    buy_target:      20% below fair value — explicit Graham margin of safety buffer
    hold_range_low:  10% below fair value — reasonable entry, starting to get full
    hold_range_high: 15% above fair value — approaching full valuation, hold but watch
    sell_target:     25% above fair value — materially overvalued, reduce position

    Args:
        fair_value:   Estimated intrinsic value per share.
        buy_discount: Discount for buy target (default 20%).
        hold_discount: Discount for hold low (default 10%).
        hold_premium:  Premium for hold high (default 15%).
        sell_premium:  Premium for sell target (default 25%).
    """
    return {
        "buy_target":      round(fair_value * (1.0 - buy_discount), 2),
        "hold_range_low":  round(fair_value * (1.0 - hold_discount), 2),
        "hold_range_high": round(fair_value * (1.0 + hold_premium), 2),
        "sell_target":     round(fair_value * (1.0 + sell_premium), 2),
    }


def is_dcf_eligible(asset: dict) -> bool:
    """
    Return True if asset qualifies for DCF valuation.
    Requires: is_dcf_eligible=True AND moat_rating is wide/narrow (not none/unknown/null).
    Circle of competence: only run DCF on businesses with identifiable moats.
    """
    return (
        bool(asset.get("is_dcf_eligible"))
        and asset.get("moat_rating") not in (None, "none", "unknown")
    )
