"""
Price history API endpoints.

GET /price_history/{symbol}?period=1d|1w|1m|3m|6m|1y
  Returns OHLCV-like data for charting with change %, current price.

GET /price_history/batch?symbols=VTI,GOOG,...&period=1m
  Returns sparkline arrays (close prices only) for multiple symbols.

GET /portfolio_history?period=1m|3m|6m|1y
  Returns portfolio value history vs benchmark indices (indexed to 100).
"""

from __future__ import annotations

import json
import logging
from datetime import date, timedelta

import yfinance as yf
from fastapi import APIRouter, Query

from app.services.market_data import _to_yf_symbol
from app.db.redis_client import get_redis_client

logger = logging.getLogger(__name__)
router = APIRouter()

# Cache TTLs by period
_TTL_BY_PERIOD = {
    "1d": 60,
    "1w": 300,
    "1m": 1800,
    "3m": 1800,
    "6m": 3600,
    "1y": 3600,
}

# Map frontend period → yfinance period string
_YF_PERIOD = {
    "1d": "1d",
    "1w": "5d",
    "1m": "1mo",
    "3m": "3mo",
    "6m": "6mo",
    "1y": "1y",
}

# Map frontend period → yfinance interval for intraday granularity
_YF_INTERVAL = {
    "1d": "5m",
    "1w": "1h",
    "1m": "1d",
    "3m": "1d",
    "6m": "1d",
    "1y": "1wk",
}


def _cache_get(key: str):
    try:
        r = get_redis_client()
        if r:
            raw = r.get(key)
            if raw:
                return json.loads(raw)
    except Exception:
        pass
    return None


def _cache_set(key: str, value, ttl: int):
    try:
        r = get_redis_client()
        if r:
            r.setex(key, ttl, json.dumps(value))
    except Exception:
        pass


def _fetch_ohlcv(symbol: str, period: str) -> list[dict]:
    """Fetch OHLCV data for a symbol and period. Returns list of {date, close, open, high, low, volume}."""
    yf_sym = _to_yf_symbol(symbol)
    yf_period = _YF_PERIOD.get(period, "1mo")
    yf_interval = _YF_INTERVAL.get(period, "1d")

    try:
        hist = yf.Ticker(yf_sym).history(period=yf_period, interval=yf_interval, auto_adjust=True)
        if hist.empty:
            return []
        rows = []
        for ts, row in hist.iterrows():
            rows.append({
                "date": ts.strftime("%Y-%m-%d") if period not in ("1d", "1w") else ts.strftime("%Y-%m-%dT%H:%M"),
                "close": round(float(row["Close"]), 4) if not __import__("math").isnan(row["Close"]) else None,
                "open":  round(float(row["Open"]), 4) if not __import__("math").isnan(row["Open"]) else None,
                "high":  round(float(row["High"]), 4) if not __import__("math").isnan(row["High"]) else None,
                "low":   round(float(row["Low"]), 4) if not __import__("math").isnan(row["Low"]) else None,
                "volume": int(row.get("Volume", 0) or 0),
            })
        return [r for r in rows if r["close"] is not None]
    except Exception as exc:
        logger.warning("_fetch_ohlcv %s %s: %s", symbol, period, exc)
        return []


@router.get("/price_history/{symbol}")
def get_price_history(
    symbol: str,
    period: str = Query(default="1m", pattern="^(1d|1w|1m|3m|6m|1y)$"),
):
    """Return OHLCV price history for a single symbol with change metrics."""
    cache_key = f"ph:{symbol}:{period}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    data = _fetch_ohlcv(symbol, period)
    if not data:
        return {"symbol": symbol, "period": period, "data": [], "change_pct": None, "change_abs": None, "current_price": None, "color": "neutral"}

    first_close = data[0]["close"]
    last_close = data[-1]["close"]
    change_abs = round(last_close - first_close, 4) if first_close and last_close else None
    change_pct = round((last_close - first_close) / first_close * 100, 2) if first_close and last_close else None
    color = "green" if (change_pct or 0) >= 0 else "red"

    result = {
        "symbol": symbol,
        "period": period,
        "data": data,
        "change_pct": change_pct,
        "change_abs": change_abs,
        "current_price": last_close,
        "color": color,
    }
    _cache_set(cache_key, result, _TTL_BY_PERIOD.get(period, 1800))
    return result


@router.get("/price_history/batch")
def get_price_history_batch(
    symbols: str = Query(description="Comma-separated symbols e.g. VTI,GOOG,BTC"),
    period: str = Query(default="1m", pattern="^(1d|1w|1m|3m|6m|1y)$"),
):
    """Return sparkline arrays (close prices only) for multiple symbols. Used for inline MiniCharts."""
    symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    if not symbol_list:
        return {}

    result: dict[str, list[float]] = {}
    missing: list[str] = []

    # Check cache first
    for sym in symbol_list:
        cached = _cache_get(f"sparkline:{sym}:{period}")
        if cached is not None:
            result[sym] = cached
        else:
            missing.append(sym)

    # Fetch missing
    for sym in missing:
        data = _fetch_ohlcv(sym, period)
        closes = [r["close"] for r in data if r["close"] is not None]
        result[sym] = closes
        # Only cache if we got actual data — don't cache empty to allow retry on next request
        if len(closes) >= 2:
            _cache_set(f"sparkline:{sym}:{period}", closes, _TTL_BY_PERIOD.get(period, 1800))

    return result


@router.get("/portfolio_history")
def get_portfolio_history(
    period: str = Query(default="3m", pattern="^(1m|3m|6m|1y)$"),
    user_id: str = Query(default=None),
):
    """
    Return portfolio value history vs benchmarks, all indexed to 100 at period start.
    Uses portfolio_snapshots table for portfolio values.
    """
    from app.config import get_default_user_id
    from app.db.repositories.snapshots import get_snapshot_history
    from app.services.fx_engine import fetch_usd_brl_rate

    user_id = user_id or get_default_user_id()

    cache_key = f"port_hist:{user_id}:{period}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    # Determine lookback days
    days_map = {"1m": 35, "3m": 95, "6m": 185, "1y": 370}
    days = days_map.get(period, 95)

    snapshots = get_snapshot_history(user_id, days=days)
    if not snapshots:
        return {"data": [], "portfolio_indexed": [], "benchmarks": {}, "current_value": None, "change_pct": None}

    # Sort ascending
    snapshots = sorted(snapshots, key=lambda s: s["snapshot_date"])
    port_data = [{"date": s["snapshot_date"], "value": float(s["total_value_usd"])} for s in snapshots]

    if len(port_data) < 2:
        return {"data": port_data, "portfolio_indexed": [], "benchmarks": {}, "current_value": port_data[-1]["value"] if port_data else None, "change_pct": None}

    # Index portfolio to 100 at start
    base_val = port_data[0]["value"]
    portfolio_indexed = [{"date": d["date"], "value": round(d["value"] / base_val * 100, 2)} for d in port_data]

    # Fetch benchmark data for same period
    yf_period = _YF_PERIOD.get(period, "3mo")
    benchmarks: dict[str, list[dict]] = {}
    for bench_sym in ["SPY", "QQQ", "ACWI"]:
        try:
            hist = yf.Ticker(bench_sym).history(period=yf_period, interval="1d", auto_adjust=True)
            if not hist.empty:
                closes = hist["Close"].dropna()
                base = float(closes.iloc[0])
                benchmarks[bench_sym] = [
                    {"date": ts.strftime("%Y-%m-%d"), "value": round(float(v) / base * 100, 2)}
                    for ts, v in closes.items()
                ]
        except Exception as exc:
            logger.warning("benchmark fetch %s: %s", bench_sym, exc)

    first_val = port_data[0]["value"]
    last_val = port_data[-1]["value"]
    change_pct = round((last_val - first_val) / first_val * 100, 2) if first_val else None

    result = {
        "data": port_data,
        "portfolio_indexed": portfolio_indexed,
        "benchmarks": benchmarks,
        "current_value": last_val,
        "change_pct": change_pct,
    }
    _cache_set(cache_key, result, 300)  # 5 min cache
    return result
