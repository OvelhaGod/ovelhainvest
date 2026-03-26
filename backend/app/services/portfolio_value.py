"""
Live portfolio value computation — single source of truth.

Used by:
  - GET  /daily_status          (replaces stale snapshot value)
  - POST /performance/snapshot  (computes correct today value)
"""
from __future__ import annotations

import json
import logging

logger = logging.getLogger(__name__)

# 60-second cache for the full portfolio value result.
# Prevents hammering yfinance on every /daily_status poll.
_CACHE_TTL = 60


def compute_live_portfolio_value(user_id: str) -> tuple[float, float, float]:
    """
    Compute portfolio total value from holdings × current market prices.

    Returns:
        (total_value_usd, total_value_brl, usd_brl_rate)

    Falls back to (0, 0, 5.23) if holdings are missing.
    Raises nothing — caller should handle gracefully.
    """
    from app.db.repositories import holdings as holdings_repo
    from app.services import allocation_engine
    from app.services.fx_engine import fetch_usd_brl_rate, normalize_to_brl
    from app.services.market_data import fetch_current_prices

    # --- Redis cache check (60s TTL to avoid yfinance hammering) ---
    cache_key = f"portfolio_value:{user_id}"
    try:
        from app.db.redis_client import get_redis_client
        r = get_redis_client()
        if r:
            cached = r.get(cache_key)
            if cached:
                data = json.loads(cached)
                logger.debug("compute_live_portfolio_value: cache hit user=%s", user_id)
                return data["usd"], data["brl"], data["fx"]
    except Exception as exc:
        logger.debug("compute_live_portfolio_value: cache miss (%s)", exc)

    holdings = holdings_repo.get_holdings(user_id)
    if not holdings:
        logger.warning("compute_live_portfolio_value: no holdings for user %s", user_id)
        return 0.0, 0.0, 5.23

    symbols = list({h["symbol"] for h in holdings if h.get("symbol") and float(h.get("quantity", 0)) > 0})
    if not symbols:
        return 0.0, 0.0, 5.23

    prices = fetch_current_prices(symbols)
    fx_rate = fetch_usd_brl_rate()

    assets_map = {h["symbol"]: h for h in holdings}
    sleeve_values = allocation_engine.compute_sleeve_values(
        holdings, assets_map, prices, fx_rate
    )
    total_usd = round(sum(sleeve_values.values()), 2)
    total_brl = round(normalize_to_brl(total_usd, fx_rate), 2)
    fx_rounded = round(fx_rate, 4)

    # --- Cache result ---
    try:
        from app.db.redis_client import get_redis_client
        r = get_redis_client()
        if r:
            r.setex(cache_key, _CACHE_TTL, json.dumps({"usd": total_usd, "brl": total_brl, "fx": fx_rounded}))
    except Exception:
        pass

    logger.info(
        "compute_live_portfolio_value user=%s total_usd=%.2f fx=%.4f",
        user_id, total_usd, fx_rate,
    )
    return total_usd, total_brl, fx_rounded
