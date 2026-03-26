"""
Markets API endpoints.

GET /markets/overview           — live indices, sectors, FX with sparklines
GET /markets/portfolio_vs_market — portfolio returns vs SPY/QQQ/ACWI
GET /markets/movers             — held assets + market gainers/losers
"""
from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta, timezone

import yfinance as yf
import pandas as pd
from fastapi import APIRouter

from app.config import get_default_user_id as _get_default_user_id

logger = logging.getLogger(__name__)
router = APIRouter()

# ── Constants ─────────────────────────────────────────────────────────────────

INDEX_TICKERS = [
    {"symbol": "SPY",     "name": "S&P 500"},
    {"symbol": "QQQ",     "name": "NASDAQ 100"},
    {"symbol": "IWM",     "name": "Russell 2000"},
    {"symbol": "^VIX",    "name": "VIX", "display": "VIX"},
    {"symbol": "GLD",     "name": "Gold"},
    {"symbol": "TLT",     "name": "20yr Bond"},
    {"symbol": "DX-Y.NYB","name": "USD Index", "display": "DXY"},
    {"symbol": "BTC-USD", "name": "Bitcoin", "display": "BTC"},
]

SECTOR_TICKERS = [
    {"name": "Technology",    "symbol": "XLK"},
    {"name": "Energy",        "symbol": "XLE"},
    {"name": "Healthcare",    "symbol": "XLV"},
    {"name": "Financials",    "symbol": "XLF"},
    {"name": "Real Estate",   "symbol": "XLRE"},
    {"name": "Consumer Disc", "symbol": "XLY"},
    {"name": "Utilities",     "symbol": "XLU"},
    {"name": "Materials",     "symbol": "XLB"},
    {"name": "Industrials",   "symbol": "XLI"},
    {"name": "Comm. Services","symbol": "XLC"},
]

FX_TICKERS = [
    {"pair": "USD/BRL", "symbol": "BRL=X"},
    {"pair": "EUR/USD", "symbol": "EURUSD=X"},
    {"pair": "USD/JPY", "symbol": "JPY=X"},
]


def _try_redis_get(key: str):
    try:
        from app.db.redis_client import get_redis_client
        rc = get_redis_client()
        val = rc.get(key)
        return json.loads(val) if val else None
    except Exception:
        return None


def _try_redis_set(key: str, value, ttl: int = 300):
    try:
        from app.db.redis_client import get_redis_client
        rc = get_redis_client()
        rc.set(key, json.dumps(value), ex=ttl)
    except Exception:
        pass


def _fetch_sparkline(symbol: str, days: int = 30) -> list[float]:
    """Fetch last N days of close prices as a list."""
    try:
        start = (date.today() - timedelta(days=days + 10)).isoformat()
        hist = yf.Ticker(symbol).history(start=start)
        closes = hist["Close"].dropna().tolist()
        return [round(float(v), 4) for v in closes[-days:]]
    except Exception:
        return []


def _pct_change_today(symbol: str) -> tuple[float | None, float | None]:
    """Return (current_price, pct_change_today) for a symbol."""
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="2d")
        if len(hist) < 2:
            if len(hist) == 1:
                price = float(hist["Close"].iloc[-1])
                return price, 0.0
            return None, None
        prev  = float(hist["Close"].iloc[-2])
        curr  = float(hist["Close"].iloc[-1])
        pct   = (curr - prev) / prev if prev else 0.0
        return round(curr, 4), round(pct, 6)
    except Exception:
        return None, None


# ── GET /markets/overview ─────────────────────────────────────────────────────

@router.get("/overview", tags=["markets"])
def markets_overview() -> dict:
    """
    Live market overview: indices, sectors, FX with sparklines.
    Cached 5 minutes in Redis.
    """
    cache_key = "markets:overview"
    cached = _try_redis_get(cache_key)
    if cached:
        return cached

    # ── Indices ──
    indices = []
    for t in INDEX_TICKERS:
        sym = t["symbol"]
        price, chg = _pct_change_today(sym)
        sparkline = _fetch_sparkline(sym, days=30)
        indices.append({
            "symbol": t.get("display", sym),
            "yf_symbol": sym,
            "name": t["name"],
            "price": price,
            "change_pct": round(chg * 100, 2) if chg is not None else None,
            "sparkline": sparkline,
        })

    # ── Sectors ──
    sectors = []
    for s in SECTOR_TICKERS:
        _, chg = _pct_change_today(s["symbol"])
        sectors.append({
            "name": s["name"],
            "symbol": s["symbol"],
            "change_pct": round(chg * 100, 2) if chg is not None else None,
        })

    # ── FX ──
    fx = []
    for f in FX_TICKERS:
        rate, chg = _pct_change_today(f["symbol"])
        fx.append({
            "pair": f["pair"],
            "rate": rate,
            "change_pct": round(chg * 100, 2) if chg is not None else None,
        })

    result = {
        "indices": indices,
        "sectors": sectors,
        "fx": fx,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    _try_redis_set(cache_key, result, ttl=300)
    return result


# ── GET /markets/portfolio_vs_market ─────────────────────────────────────────

@router.get("/portfolio_vs_market", tags=["markets"])
def portfolio_vs_market(user_id: str | None = None) -> dict:
    """
    Compare portfolio returns vs SPY / QQQ / ACWI across multiple periods.
    Uses portfolio_snapshots for portfolio returns, yfinance for benchmarks.
    """
    cache_key = "markets:pvmarket:v2"
    cached = _try_redis_get(cache_key)
    if cached:
        return cached

    uid = user_id or _get_default_user_id()
    today = date.today()
    periods = {
        "1w":  today - timedelta(days=7),
        "1m":  today - timedelta(days=30),
        "3m":  today - timedelta(days=91),
        "ytd": date(today.year, 1, 1),
        "1y":  today - timedelta(days=365),
    }

    # Portfolio returns from snapshots
    from app.db.supabase_client import get_supabase_client
    client = get_supabase_client()
    oldest_start = min(periods.values())
    snaps_resp = (
        client.table("portfolio_snapshots")
        .select("snapshot_date,total_value_usd")
        .eq("user_id", uid)
        .gte("snapshot_date", oldest_start.isoformat())
        .order("snapshot_date")
        .execute()
    )
    snaps = snaps_resp.data or []

    def _portfolio_return_for_period(period_start: date) -> float | None:
        # Find the snapshot closest to period_start (on or after)
        start_snaps = [s for s in snaps if s["snapshot_date"] >= period_start.isoformat()]
        end_snaps   = [s for s in snaps if s["snapshot_date"] <= today.isoformat()]
        if not start_snaps or not end_snaps:
            return None
        v_start = float(start_snaps[0]["total_value_usd"])
        v_end   = float(end_snaps[-1]["total_value_usd"])
        if v_start <= 0:
            return None
        return round((v_end - v_start) / v_start, 6)

    portfolio_returns = {p: _portfolio_return_for_period(d) for p, d in periods.items()}

    # Benchmark returns from yfinance
    bench_syms = {"spy": "SPY", "qqq": "QQQ", "acwi": "ACWI"}
    bench_returns: dict = {k: {} for k in bench_syms}

    start_dl = (oldest_start - timedelta(days=5)).isoformat()
    for key, sym in bench_syms.items():
        # Try up to 2 times with explicit ticker object to avoid silent failures
        for attempt in range(2):
            try:
                ticker = yf.Ticker(sym)
                hist = ticker.history(start=start_dl, auto_adjust=True)
                if hist.empty:
                    logger.warning("Benchmark %s returned empty history (attempt %d)", sym, attempt + 1)
                    if attempt == 0:
                        continue  # retry once
                    break
                hist.index = pd.to_datetime(hist.index).normalize()
                for period, period_start in periods.items():
                    # Closest available date on or after period_start
                    after = hist[hist.index.date >= period_start]
                    if after.empty:
                        continue
                    v_start = float(after["Close"].iloc[0])
                    v_end   = float(hist["Close"].iloc[-1])
                    if v_start <= 0:
                        continue
                    bench_returns[key][period] = round((v_end - v_start) / v_start, 6)
                break  # success — no need to retry
            except Exception as exc:
                logger.warning("Benchmark %s failed (attempt %d): %s", sym, attempt + 1, exc)

    # Alpha vs SPY
    alpha: dict = {}
    for period in periods:
        p_ret = portfolio_returns.get(period)
        s_ret = bench_returns["spy"].get(period)
        if p_ret is not None and s_ret is not None:
            alpha[period] = round(p_ret - s_ret, 6)
        else:
            alpha[period] = None

    result = {
        "periods": list(periods.keys()),
        "portfolio": portfolio_returns,
        "spy":  bench_returns["spy"],
        "qqq":  bench_returns["qqq"],
        "acwi": bench_returns["acwi"],
        "alpha_vs_spy": alpha,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    # Only cache if we got data for at least SPY — don't cache incomplete benchmark results
    if bench_returns["spy"]:
        _try_redis_set(cache_key, result, ttl=300)
    return result


# ── GET /markets/movers ───────────────────────────────────────────────────────

@router.get("/movers", tags=["markets"])
def markets_movers(user_id: str | None = None) -> dict:
    """
    Today's movers: held assets + broader market gainers/losers.
    """
    cache_key = "markets:movers"
    cached = _try_redis_get(cache_key)
    if cached:
        return cached

    uid = user_id or _get_default_user_id()

    # Get held symbols
    from app.db.supabase_client import get_supabase_client
    client = get_supabase_client()
    hold_resp = (
        client.table("holdings")
        .select("quantity,assets(symbol,name,asset_class)")
        .gt("quantity", 0)
        .execute()
    )
    holdings = hold_resp.data or []

    held_assets = []
    for h in holdings:
        asset = h.get("assets") or {}
        sym = asset.get("symbol", "")
        if not sym:
            continue
        yf_sym_map = {"BTC": "BTC-USD", "ETH": "ETH-USD", "SOL": "SOL-USD",
                      "LINK": "LINK-USD", "PETR4": "PETR4.SA",
                      "VALE3": "VALE3.SA", "ITUB4": "ITUB4.SA"}
        yf_sym = yf_sym_map.get(sym, sym)
        price, chg = _pct_change_today(yf_sym)
        held_assets.append({
            "symbol": sym,
            "name": asset.get("name", sym),
            "asset_class": asset.get("asset_class", ""),
            "price": price,
            "change_pct": round(chg * 100, 2) if chg is not None else None,
            "quantity": float(h.get("quantity", 0)),
        })

    # Sort by abs change
    held_assets.sort(key=lambda x: abs(x.get("change_pct") or 0), reverse=True)

    # Broad market watchlist for gainers/losers
    watchlist = ["NVDA", "AAPL", "MSFT", "AMZN", "META", "GOOG", "TSLA",
                 "AMD", "INTC", "JPM", "BAC", "XOM", "CVX", "JNJ"]
    movers = []
    for sym in watchlist:
        price, chg = _pct_change_today(sym)
        if price and chg is not None:
            movers.append({"symbol": sym, "price": price,
                           "change_pct": round(chg * 100, 2)})

    movers.sort(key=lambda x: x["change_pct"], reverse=True)
    gainers = movers[:5]
    losers  = movers[-5:][::-1]

    result = {
        "held_assets": held_assets,
        "market_gainers": gainers,
        "market_losers": losers,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    _try_redis_set(cache_key, result, ttl=120)
    return result
