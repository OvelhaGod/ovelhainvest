"""
Volatility regime detection and Dalio 4-season economic classifier.

VIX + equity/crypto moves → RegimeState (normal / high_vol / paused).
TIP/IEF + yield curve → EconomicSeason (Dalio's 4 quadrants).
Factor weights shift dynamically based on detected season (Section 26.2).
"""

from __future__ import annotations

import logging

import yfinance as yf

from app.db.redis_client import TTL_MARKET_DATA, get_redis_client
from app.schemas.allocation_models import EconomicSeason, RegimeState

logger = logging.getLogger(__name__)

REDIS_KEY_VIX = "market:vix"

# Regime thresholds (CLAUDE.md Section 7)
VIX_HIGH_VOL = 30
EQUITY_MOVE_HIGH = 0.03
CRYPTO_MOVE_HIGH = 0.10
DRAWDOWN_PAUSE = 0.40

# Dalio 4-quadrant factor weights (CLAUDE.md Section 26.2)
FACTOR_COMPOSITE_WEIGHTS_BY_REGIME: dict[str, dict] = {
    "rising_growth_low_inflation": {
        "value_weight": 0.25,
        "momentum_weight": 0.45,
        "quality_weight": 0.30,
        "rationale": "Momentum dominates in sustained bull runs (2023-2024 Magnificent 7)",
    },
    "falling_growth_low_inflation": {
        "value_weight": 0.40,
        "momentum_weight": 0.15,
        "quality_weight": 0.45,
        "rationale": "Quality resilient in downturns; momentum prone to crash",
    },
    "rising_inflation": {
        "value_weight": 0.50,
        "momentum_weight": 0.20,
        "quality_weight": 0.30,
        "rationale": "Value and real assets hedge inflation; growth gets destroyed",
    },
    "falling_inflation_growth_recovery": {
        "value_weight": 0.35,
        "momentum_weight": 0.35,
        "quality_weight": 0.30,
        "rationale": "Balanced — recovery rewards both value and early momentum",
    },
    "normal": {
        "value_weight": 0.40,
        "momentum_weight": 0.30,
        "quality_weight": 0.30,
        "rationale": "Fama-French baseline weights; no regime conviction",
    },
}


def fetch_vix(use_cache: bool = True) -> float:
    """
    Fetch current VIX index value from yfinance with 15-minute Redis cache.

    Args:
        use_cache: Whether to use Redis cache (default True).

    Returns:
        VIX value (e.g. 18.5). Returns 20.0 (neutral) on failure.
    """
    if use_cache:
        try:
            redis = get_redis_client()
            cached = redis.get(REDIS_KEY_VIX)
            if cached:
                vix = float(cached)
                logger.debug("VIX from cache: %.2f", vix)
                return vix
        except Exception as exc:
            logger.debug("VIX cache miss: %s", exc)

    try:
        hist = yf.Ticker("^VIX").history(period="1d", interval="1m")
        if hist.empty:
            raise ValueError("Empty VIX history")
        vix = float(hist["Close"].iloc[-1])
        logger.info("VIX from yfinance: %.2f", vix)

        if use_cache:
            try:
                redis = get_redis_client()
                redis.setex(REDIS_KEY_VIX, TTL_MARKET_DATA, str(vix))
            except Exception:
                pass

        return vix
    except Exception as exc:
        logger.error("VIX fetch failed: %s — returning neutral 20.0", exc)
        return 20.0


def detect_volatility_regime(
    vix: float,
    equity_move_pct: float,
    crypto_move_pct: float,
    portfolio_drawdown_pct: float = 0.0,
    config: dict | None = None,
) -> RegimeState:
    """
    Classify volatility regime from VIX + daily moves + drawdown.

    Args:
        vix: Current VIX value.
        equity_move_pct: Daily equity market move (SPY or similar). Signed.
        crypto_move_pct: Daily crypto market move (BTC). Signed.
        portfolio_drawdown_pct: Portfolio drawdown from peak (negative = down).
        config: Optional override for thresholds.

    Returns:
        RegimeState.
    """
    vix_thresh = VIX_HIGH_VOL
    eq_thresh = EQUITY_MOVE_HIGH
    crypto_thresh = CRYPTO_MOVE_HIGH

    if config:
        hvt = config.get("high_vol_triggers", {})
        vix_thresh = hvt.get("vix_threshold", vix_thresh)
        eq_thresh = hvt.get("equity_daily_move_pct", eq_thresh)
        crypto_thresh = hvt.get("crypto_daily_move_pct", crypto_thresh)

    dd = abs(portfolio_drawdown_pct)
    if dd >= DRAWDOWN_PAUSE:
        return RegimeState.PAUSED

    is_high = (
        vix >= vix_thresh
        or abs(equity_move_pct) >= eq_thresh
        or abs(crypto_move_pct) >= crypto_thresh
    )

    return RegimeState.HIGH_VOL if is_high else RegimeState.NORMAL


def detect_economic_season(
    vix: float,
    tips_spread: float | None = None,
    yield_curve_slope: float | None = None,
) -> EconomicSeason:
    """
    Classify Dalio 4-quadrant economic season.

    Uses proxies:
    - Inflation signal: TIP/IEF spread (>0 = rising inflation, <0 = falling).
    - Growth signal: yield_curve_slope = ^TNX - ^IRX (steepening = growth, inverting = recession).

    When proxies unavailable, falls back to VIX-based heuristic.

    Args:
        vix: Current VIX value.
        tips_spread: Spread between TIPS yield and nominal yield (proxy: TIP/IEF price ratio change).
        yield_curve_slope: 10y - 3m Treasury spread (positive = normal, negative = inverted).

    Returns:
        EconomicSeason.
    """
    # If we have both proxies, use Dalio quadrant logic
    if tips_spread is not None and yield_curve_slope is not None:
        rising_inflation = tips_spread > 0.5   # TIPS outperforming → inflation expectations rising
        rising_growth = yield_curve_slope > 0.5  # Curve steepening → growth expectations positive

        if rising_growth and not rising_inflation:
            return EconomicSeason.RISING_GROWTH_LOW_INFLATION
        if not rising_growth and not rising_inflation:
            return EconomicSeason.FALLING_GROWTH_LOW_INFLATION
        if rising_inflation and not rising_growth:
            return EconomicSeason.RISING_INFLATION
        if not rising_inflation and yield_curve_slope < -0.5:
            return EconomicSeason.FALLING_INFLATION_GROWTH_RECOVERY

    # VIX-based fallback heuristic
    # Low VIX → likely bull/growth environment
    if vix < 18:
        return EconomicSeason.RISING_GROWTH_LOW_INFLATION
    if vix > 30:
        return EconomicSeason.FALLING_GROWTH_LOW_INFLATION

    return EconomicSeason.NORMAL


def _fetch_yield_proxies() -> tuple[float | None, float | None]:
    """
    Fetch TIP/IEF spread and yield curve slope from yfinance.

    Returns:
        (tips_spread, yield_curve_slope) — either may be None on failure.
    """
    try:
        import pandas as pd

        data = yf.download(["TIP", "IEF", "^TNX", "^IRX"], period="3mo", progress=False)
        if data.empty:
            return None, None

        close = data["Close"]

        # TIP/IEF ratio: rising = real yields falling = inflation expectations rising
        tip_prices = close["TIP"].dropna()
        ief_prices = close["IEF"].dropna()
        if len(tip_prices) > 22 and len(ief_prices) > 22:
            tip_ief_now = float(tip_prices.iloc[-1]) / float(ief_prices.iloc[-1])
            tip_ief_1m = float(tip_prices.iloc[-22]) / float(ief_prices.iloc[-22])
            tips_spread = (tip_ief_now - tip_ief_1m) / tip_ief_1m * 100
        else:
            tips_spread = None

        # Yield curve: 10yr - 3mo
        tnx = close.get("^TNX")
        irx = close.get("^IRX")
        if tnx is not None and irx is not None:
            tnx_s = tnx.dropna()
            irx_s = irx.dropna()
            if len(tnx_s) > 0 and len(irx_s) > 0:
                yield_curve_slope = float(tnx_s.iloc[-1]) - float(irx_s.iloc[-1])
            else:
                yield_curve_slope = None
        else:
            yield_curve_slope = None

        return tips_spread, yield_curve_slope

    except Exception as exc:
        logger.warning("Failed to fetch yield proxies: %s", exc)
        return None, None


def get_economic_season() -> EconomicSeason:
    """
    Fetch market data and classify current economic season.

    Returns:
        EconomicSeason based on live TIP/IEF and yield curve data.
    """
    vix = fetch_vix()
    tips_spread, yield_curve_slope = _fetch_yield_proxies()
    season = detect_economic_season(vix, tips_spread, yield_curve_slope)
    logger.info(
        "Economic season: %s (VIX=%.1f, tips_spread=%s, yield_slope=%s)",
        season, vix, tips_spread, yield_curve_slope,
    )
    return season


def get_factor_weights_for_regime(season: EconomicSeason) -> dict:
    """
    Return factor composite weights for the given economic season.

    Args:
        season: Detected EconomicSeason.

    Returns:
        Dict with value_weight, momentum_weight, quality_weight, rationale.
    """
    return FACTOR_COMPOSITE_WEIGHTS_BY_REGIME.get(
        season.value, FACTOR_COMPOSITE_WEIGHTS_BY_REGIME["normal"]
    )


def should_defer_core_dca(
    regime: RegimeState,
    config: dict | None = None,
) -> tuple[bool, int]:
    """
    Determine if core DCA should be deferred due to high volatility.

    Per CLAUDE.md: high vol → defer 1-3 days. Opportunity still allowed if discounted.

    Args:
        regime: Current regime state.
        config: Optional config override.

    Returns:
        (should_defer: bool, defer_days: int) — defer_days is 0 if no deferral.
    """
    if regime == RegimeState.PAUSED:
        return True, 7  # Long pause on extreme drawdown

    if regime == RegimeState.HIGH_VOL:
        defer_range = (1, 3)
        if config:
            defer_range = config.get("high_vol_triggers", {}).get("defer_dca_days", defer_range)
        return True, defer_range[1]  # Defer by max of range

    return False, 0


def allow_opportunity_mode(
    regime: RegimeState,
    asset_discounted: bool,
    config: dict | None = None,
) -> bool:
    """
    Determine if opportunity vault deployment is allowed in current regime.

    Marks principle: fear is highest in high-vol → opportunity mode is MOST justified.
    But requires explicit asset discount confirmation (Graham margin of safety).

    Args:
        regime: Current regime state.
        asset_discounted: True if asset meets Tier 1/2 opportunity criteria.
        config: Optional config override.

    Returns:
        True if opportunity deployment is allowed.
    """
    if regime == RegimeState.PAUSED:
        return False  # 40%+ drawdown → pause everything

    allow_in_high_vol = True
    if config:
        allow_in_high_vol = config.get("high_vol_triggers", {}).get(
            "allow_opportunity_if_discounted", True
        )

    if regime == RegimeState.HIGH_VOL and allow_in_high_vol and asset_discounted:
        return True

    if regime == RegimeState.NORMAL and asset_discounted:
        return True

    return False
