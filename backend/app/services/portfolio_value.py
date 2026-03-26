"""
Live portfolio value computation — single source of truth.

Used by:
  - GET  /daily_status          (replaces stale snapshot value)
  - POST /performance/snapshot  (computes correct today value)
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


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
    total_usd = sum(sleeve_values.values())
    total_brl = normalize_to_brl(total_usd, fx_rate)

    logger.info(
        "compute_live_portfolio_value user=%s total_usd=%.2f fx=%.4f",
        user_id, total_usd, fx_rate,
    )
    return round(total_usd, 2), round(total_brl, 2), round(fx_rate, 4)
