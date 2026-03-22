"""
FX engine: USD/BRL normalization and FX attribution.

All portfolio-level math normalized to USD.
BRL positions converted using live rate from yfinance (symbol: "USDBRL=X").
Rate cached in Redis for 15 minutes; falls back to last cached value on error.
"""

from __future__ import annotations

import json
import logging
from datetime import date

import pandas as pd
import yfinance as yf

from app.db.redis_client import TTL_MARKET_DATA, get_redis_client

logger = logging.getLogger(__name__)

FX_ALERT_THRESHOLD = 0.10   # alert when USD/BRL moves >10% in 30 days
FX_SYMBOL = "USDBRL=X"      # yfinance ticker for USD/BRL rate
REDIS_KEY_FX = "fx:usd_brl"
FALLBACK_RATE = 5.70        # last-resort default if both live + cache fail


def fetch_usd_brl_rate() -> float:
    """
    Fetch current USD/BRL rate from yfinance with 15-minute Redis cache.

    Returns:
        Exchange rate (BRL per 1 USD), e.g. 5.70.
        Falls back to last cached value if yfinance call fails.
        Falls back to FALLBACK_RATE if both fail.
    """
    try:
        redis = get_redis_client()
        cached = redis.get(REDIS_KEY_FX)
        if cached is not None:
            rate = float(cached)
            logger.debug("FX rate from cache: %.4f", rate)
            return rate
    except Exception as exc:
        logger.warning("Redis unavailable for FX cache read: %s", exc)
        redis = None

    # Fetch from yfinance
    try:
        ticker = yf.Ticker(FX_SYMBOL)
        hist = ticker.history(period="1d", interval="1m")
        if hist.empty:
            raise ValueError("Empty price history from yfinance for USDBRL=X")
        rate = float(hist["Close"].iloc[-1])
        logger.info("FX rate from yfinance: %.4f", rate)

        # Cache it
        if redis is not None:
            try:
                redis.setex(REDIS_KEY_FX, TTL_MARKET_DATA, str(rate))
            except Exception as exc:
                logger.warning("Failed to cache FX rate: %s", exc)

        return rate

    except Exception as exc:
        logger.error("yfinance FX fetch failed (%s), trying stale cache", exc)

    # Last resort: stale cache (no TTL check)
    try:
        if redis is not None:
            raw = redis.get(REDIS_KEY_FX + ":stale")
            if raw:
                rate = float(raw)
                logger.warning("Using stale FX rate: %.4f", rate)
                return rate
    except Exception:
        pass

    logger.error("All FX sources failed — using hardcoded fallback %.4f", FALLBACK_RATE)
    return FALLBACK_RATE


def normalize_to_usd(brl_value: float, usd_brl_rate: float) -> float:
    """
    Convert BRL value to USD for portfolio-level aggregation.

    Args:
        brl_value: Value in Brazilian Reals.
        usd_brl_rate: Current USD/BRL exchange rate (BRL per 1 USD).

    Returns:
        Value in USD.
    """
    if usd_brl_rate <= 0:
        raise ValueError(f"Invalid FX rate: {usd_brl_rate}")
    return brl_value / usd_brl_rate


def normalize_to_brl(usd_value: float, usd_brl_rate: float) -> float:
    """
    Convert USD value to BRL for display.

    Args:
        usd_value: Value in USD.
        usd_brl_rate: Current USD/BRL exchange rate (BRL per 1 USD).

    Returns:
        Value in BRL.
    """
    return usd_value * usd_brl_rate


def normalize_all_positions_to_usd(
    holdings: list[dict],
    prices: dict[str, float],
    fx_rate: float,
) -> dict[str, float]:
    """
    Compute USD market value for every holding, normalizing BRL positions.

    Args:
        holdings: List of holding dicts with keys: symbol, currency, quantity.
        prices: Dict of symbol → price in native currency.
        fx_rate: USD/BRL rate (BRL per 1 USD).

    Returns:
        Dict of symbol → USD market value.
    """
    result: dict[str, float] = {}
    for h in holdings:
        symbol = h["symbol"]
        qty = float(h.get("quantity", 0))
        currency = h.get("currency", "USD")
        price = prices.get(symbol, 0.0)
        native_value = qty * price
        if currency == "BRL":
            result[symbol] = normalize_to_usd(native_value, fx_rate)
        else:
            result[symbol] = native_value
    return result


def compute_fx_attribution(
    brazil_sleeve_return_brl: float,
    brazil_sleeve_return_usd: float,
) -> float:
    """
    FX contribution to portfolio return.

    FX contribution = brazil_sleeve_return_usd - brazil_sleeve_return_brl
    Positive = BRL strengthened vs USD (helped USD returns).
    Negative = BRL weakened (hurt USD returns).

    Args:
        brazil_sleeve_return_brl: Brazil sleeve return measured in BRL (decimal).
        brazil_sleeve_return_usd: Brazil sleeve return measured in USD (decimal).

    Returns:
        FX contribution as decimal.
    """
    return brazil_sleeve_return_usd - brazil_sleeve_return_brl


def get_live_usd_brl_rate() -> float:
    """Alias for fetch_usd_brl_rate — external interface."""
    return fetch_usd_brl_rate()


def check_fx_alert(
    rate_history: pd.Series,
    window_days: int = 30,
) -> dict | None:
    """
    Check if USD/BRL has moved beyond FX_ALERT_THRESHOLD in the last window_days.

    Args:
        rate_history: Series of daily USD/BRL rates indexed by date.
        window_days: Rolling window to measure move.

    Returns:
        Alert dict if threshold breached, else None.
    """
    if len(rate_history) < 2:
        return None

    recent = rate_history.tail(window_days)
    if len(recent) < 2:
        return None

    start_rate = float(recent.iloc[0])
    end_rate = float(recent.iloc[-1])
    move = (end_rate - start_rate) / start_rate

    if abs(move) >= FX_ALERT_THRESHOLD:
        direction = "weakened" if move > 0 else "strengthened"
        return {
            "type": "fx_move",
            "pair": "USDBRL",
            "move_pct": round(move * 100, 2),
            "start_rate": round(start_rate, 4),
            "end_rate": round(end_rate, 4),
            "window_days": window_days,
            "direction": f"BRL {direction} vs USD",
            "severity": "high" if abs(move) >= 0.15 else "medium",
        }
    return None
