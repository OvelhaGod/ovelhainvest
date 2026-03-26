"""
Market data service: yfinance + Finnhub wrapper with Redis caching.

Cache TTLs:
  - Current prices:    15 min  (key: "prices:{symbol}")
  - Fundamentals:       6 hrs  (key: "fundamentals:{symbol}")
  - Price history:     60 min  (key: "history:{symbol}:{period}")
  - Finnhub news:      30 min  (key: "news:{symbol}")
"""

from __future__ import annotations

import json
import logging
import math
from datetime import date, datetime
from typing import Any

import httpx
import pandas as pd
import yfinance as yf

from app.config import settings
from app.db.redis_client import TTL_MARKET_DATA, get_redis_client

logger = logging.getLogger(__name__)

TTL_FUNDAMENTALS = 60 * 60 * 6   # 6 hours
TTL_HISTORY = 60 * 60             # 1 hour
TTL_NEWS = 60 * 30                # 30 minutes


def _get_cached(key: str) -> Any | None:
    """Read JSON-encoded value from Redis; return None on any failure."""
    try:
        redis = get_redis_client()
        raw = redis.get(key)
        if raw:
            return json.loads(raw)
    except Exception as exc:
        logger.debug("Cache miss / Redis unavailable (%s): %s", key, exc)
    return None


def _set_cached(key: str, value: Any, ttl: int) -> None:
    """Write JSON-encoded value to Redis; silently swallow errors."""
    try:
        redis = get_redis_client()
        redis.setex(key, ttl, json.dumps(value))
    except Exception as exc:
        logger.debug("Cache write failed (%s): %s", key, exc)


def fetch_current_prices(symbols: list[str]) -> dict[str, float]:
    """
    Fetch current prices for a list of symbols using yfinance batch download.
    Results cached per-symbol at 15-minute TTL.

    Args:
        symbols: List of ticker symbols (e.g. ["VTI", "BTC-USD"]).

    Returns:
        Dict of symbol → latest close price. Missing symbols are omitted.
    """
    result: dict[str, float] = {}
    to_fetch: list[str] = []

    for sym in symbols:
        cached = _get_cached(f"prices:{sym}")
        if cached is not None:
            result[sym] = float(cached)
        else:
            to_fetch.append(sym)

    if not to_fetch:
        return result

    try:
        # yfinance batch: map crypto symbols BTC → BTC-USD for yfinance
        yf_symbols = [_to_yf_symbol(s) for s in to_fetch]
        data = yf.download(yf_symbols, period="1d", interval="1m", progress=False, auto_adjust=True)

        if data.empty:
            logger.warning("yfinance returned empty data for %s", to_fetch)
            return result

        # Handle multi-ticker vs single-ticker structure
        close = data["Close"] if "Close" in data.columns else data

        for orig, yf_sym in zip(to_fetch, yf_symbols):
            try:
                if hasattr(close, "columns"):
                    series = close[yf_sym] if yf_sym in close.columns else close[orig]
                else:
                    series = close
                price = float(series.dropna().iloc[-1])
                result[orig] = price
                _set_cached(f"prices:{orig}", price, TTL_MARKET_DATA)
            except Exception as exc:
                logger.warning("Could not extract price for %s: %s", orig, exc)

    except Exception as exc:
        logger.error("yfinance batch price fetch failed: %s", exc)

    return result


def fetch_fundamentals(symbol: str) -> dict[str, Any]:
    """
    Fetch fundamental data for a symbol: PE, PS, dividend yield, beta.
    Cached at 6-hour TTL.

    Args:
        symbol: Ticker symbol.

    Returns:
        Dict with keys: pe, ps, dividend_yield, beta, market_cap, sector, industry.
    """
    cache_key = f"fundamentals:{symbol}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    try:
        info = yf.Ticker(_to_yf_symbol(symbol)).info
        data = {
            "pe": _safe_float(info.get("trailingPE") or info.get("forwardPE")),
            "ps": _safe_float(info.get("priceToSalesTrailing12Months")),
            "pb": _safe_float(info.get("priceToBook")),
            "dividend_yield": _safe_float(info.get("dividendYield")),
            "beta": _safe_float(info.get("beta")),
            "market_cap": _safe_float(info.get("marketCap")),
            "sector": info.get("sector", ""),
            "industry": info.get("industry", ""),
            "roe": _safe_float(info.get("returnOnEquity")),
            "operating_margin": _safe_float(info.get("operatingMargins")),
            "debt_to_equity": _safe_float(info.get("debtToEquity")),
            "free_cashflow": _safe_float(info.get("freeCashflow")),
            "revenue_growth": _safe_float(info.get("revenueGrowth")),
            "earnings_growth": _safe_float(info.get("earningsGrowth")),
            # DCF inputs
            "shares_outstanding": _safe_float(info.get("sharesOutstanding")),
            "total_debt": _safe_float(info.get("totalDebt")),
            "cash_and_equivalents": _safe_float(info.get("totalCash")),
            "symbol": symbol,
        }
        _set_cached(cache_key, data, TTL_FUNDAMENTALS)
        logger.debug("Fetched fundamentals for %s", symbol)
        return data
    except Exception as exc:
        logger.error("Failed to fetch fundamentals for %s: %s", symbol, exc)
        return {"symbol": symbol}


def fetch_price_history(symbol: str, period: str = "1y") -> pd.Series:
    """
    Fetch Close price history for a symbol.
    Cached at 1-hour TTL (stored as list of [timestamp_ms, price] pairs).

    Args:
        symbol: Ticker symbol.
        period: yfinance period string — "1mo", "3mo", "6mo", "1y", "2y", "5y".

    Returns:
        pd.Series of Close prices indexed by datetime.
    """
    cache_key = f"history:{symbol}:{period}"
    cached = _get_cached(cache_key)
    if cached is not None:
        try:
            idx = pd.to_datetime([c[0] for c in cached], unit="ms")
            vals = [c[1] for c in cached]
            return pd.Series(vals, index=idx, name="Close")
        except Exception:
            pass

    try:
        hist = yf.Ticker(_to_yf_symbol(symbol)).history(period=period, auto_adjust=True)
        if hist.empty:
            return pd.Series(dtype=float)
        series = hist["Close"].dropna()

        # Cache as list of [timestamp_ms, price]
        serializable = [[int(ts.timestamp() * 1000), float(p)] for ts, p in series.items()]
        _set_cached(cache_key, serializable, TTL_HISTORY)
        return series
    except Exception as exc:
        logger.error("Failed to fetch price history for %s: %s", symbol, exc)
        return pd.Series(dtype=float)


def compute_volatility_30d(price_history: pd.Series) -> float:
    """
    Compute annualized 30-day volatility from daily Close prices.

    Args:
        price_history: Series of Close prices.

    Returns:
        Annualized volatility as decimal (e.g. 0.165 = 16.5%).
    """
    if len(price_history) < 5:
        return 0.0
    daily_returns = price_history.pct_change().dropna()
    recent = daily_returns.tail(30)
    annualized_vol = float(recent.std() * math.sqrt(252))
    return annualized_vol


def compute_drawdown_from_high(price_history: pd.Series, window_months: int = 9) -> float:
    """
    Compute drawdown from rolling high over a window.

    Args:
        price_history: Series of Close prices.
        window_months: Approximate months to look back (converted to trading days).

    Returns:
        Drawdown as negative decimal (e.g. -0.30 = 30% below rolling high).
    """
    if len(price_history) < 2:
        return 0.0
    window_days = window_months * 21  # approx trading days per month
    recent = price_history.tail(window_days)
    rolling_max = recent.max()
    current = float(recent.iloc[-1])
    if rolling_max <= 0:
        return 0.0
    drawdown = (current - float(rolling_max)) / float(rolling_max)
    return drawdown


def fetch_news(symbol: str, limit: int = 5) -> list[dict]:
    """
    Fetch recent news for a symbol via Finnhub API.
    Cached at 30-minute TTL.

    Args:
        symbol: Ticker symbol.
        limit: Max number of news items to return.

    Returns:
        List of dicts with keys: headline, summary, url, source, datetime.
    """
    if not settings.finnhub_api_key:
        logger.debug("Finnhub API key not configured — skipping news fetch")
        return []

    cache_key = f"news:{symbol}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached[:limit]

    try:
        today = date.today().isoformat()
        # Fetch 30-day window
        from_date = (date.today().replace(day=1)).isoformat()
        url = (
            f"https://finnhub.io/api/v1/company-news"
            f"?symbol={symbol}&from={from_date}&to={today}&token={settings.finnhub_api_key}"
        )
        with httpx.Client(timeout=10) as client:
            resp = client.get(url)
            resp.raise_for_status()
            items = resp.json()

        HIGH_IMPACT_KEYWORDS = {
            "earnings", "revenue", "profit", "loss", "guidance", "forecast", "acquisition",
            "merger", "ipo", "bankruptcy", "layoff", "ceo", "fed", "rate", "inflation",
            "beat", "miss", "upgrade", "downgrade", "crash", "rally", "surge", "plunge",
        }
        news = []
        for item in items[:20]:
            headline = item.get("headline", "")
            summary = item.get("summary", "")
            # Heuristic importance score 1-10
            text_lower = (headline + " " + summary).lower()
            keyword_hits = sum(1 for kw in HIGH_IMPACT_KEYWORDS if kw in text_lower)
            has_summary = bool(summary and len(summary) > 50)
            importance = min(10, keyword_hits * 2 + (3 if has_summary else 1))
            news.append({
                "headline": headline,
                "summary": summary,
                "url": item.get("url", ""),
                "source": item.get("source", ""),
                "published_at": datetime.fromtimestamp(item["datetime"]).isoformat() if item.get("datetime") else None,
                "category": item.get("category", ""),
                "importance_score": importance,
            })
        _set_cached(cache_key, news, TTL_NEWS)
        return news[:limit]

    except Exception as exc:
        logger.error("Finnhub news fetch failed for %s: %s", symbol, exc)
        return []


def fetch_earnings_calendar(symbols: list[str]) -> list[dict]:
    """
    Fetch upcoming earnings dates for a list of symbols via Finnhub.

    Args:
        symbols: List of ticker symbols.

    Returns:
        List of dicts with keys: symbol, date, eps_estimate, revenue_estimate.
    """
    if not settings.finnhub_api_key:
        return []

    try:
        today = date.today().isoformat()
        # Next 30 days
        from datetime import timedelta
        end_date = (date.today() + timedelta(days=30)).isoformat()
        url = (
            f"https://finnhub.io/api/v1/calendar/earnings"
            f"?from={today}&to={end_date}&token={settings.finnhub_api_key}"
        )
        with httpx.Client(timeout=10) as client:
            resp = client.get(url)
            resp.raise_for_status()
            data = resp.json()

        symbol_set = {s.upper() for s in symbols}
        results = []
        for item in data.get("earningsCalendar", []):
            if item.get("symbol", "").upper() in symbol_set:
                results.append({
                    "symbol": item["symbol"],
                    "date": item.get("date"),
                    "eps_estimate": item.get("epsEstimate"),
                    "revenue_estimate": item.get("revenueEstimate"),
                    "eps_actual": item.get("epsActual"),
                })
        return results

    except Exception as exc:
        logger.error("Finnhub earnings calendar fetch failed: %s", exc)
        return []


# ── helpers ────────────────────────────────────────────────────────────────────

def _to_yf_symbol(symbol: str) -> str:
    """Map internal symbol to yfinance ticker (e.g. BTC → BTC-USD)."""
    crypto_map = {"BTC": "BTC-USD", "ETH": "ETH-USD", "SOL": "SOL-USD", "LINK": "LINK-USD"}
    return crypto_map.get(symbol.upper(), symbol)


def _safe_float(val: Any) -> float | None:
    """Return float or None; swallow NaN and non-numeric."""
    try:
        f = float(val)
        return None if math.isnan(f) else f
    except (TypeError, ValueError):
        return None
