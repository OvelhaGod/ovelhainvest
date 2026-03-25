"""
Research API endpoints.

GET /news/feed                  — News feed for held/watched assets
GET /news/earnings_calendar     — Earnings calendar for next 30 days
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Query

from app.config import get_default_user_id as _get_default_user_id
from app.db.supabase_client import get_supabase_client
from app.services.market_data import fetch_earnings_calendar, fetch_news

router = APIRouter()
logger = logging.getLogger(__name__)

# Core ETFs and default watchlist symbols always included in news
_DEFAULT_SYMBOLS = ["SPY", "QQQ", "BTC-USD", "ETH-USD"]


def _get_held_symbols(user_id: str) -> list[str]:
    """Return symbols currently held by the user."""
    try:
        client = get_supabase_client()
        resp = (
            client.table("holdings")
            .select("assets(symbol)")
            .eq("accounts.user_id", user_id)
            .execute()
        )
        syms: list[str] = []
        for row in resp.data or []:
            asset = row.get("assets") or {}
            sym = asset.get("symbol")
            if sym:
                syms.append(sym)
        return syms
    except Exception as exc:
        logger.debug("Could not fetch held symbols: %s", exc)
        return []


@router.get("/news/feed")
def news_feed(
    user_id: str = Query(default=None),
    limit: int = Query(default=30),
) -> list[dict]:
    """
    Return recent news items for held assets + default watchlist.
    Aggregates per-symbol news, deduplicates, sorts by recency.
    """
    uid = user_id or _get_default_user_id()
    held = _get_held_symbols(uid)

    symbols = list(dict.fromkeys(held + _DEFAULT_SYMBOLS))  # dedupe, preserve order

    all_items: list[dict] = []
    seen_urls: set[str] = set()

    for sym in symbols:
        try:
            items = fetch_news(sym, limit=5)
            for item in items:
                url = item.get("url", "")
                if url and url in seen_urls:
                    continue
                if url:
                    seen_urls.add(url)
                all_items.append({**item, "related_symbol": sym})
        except Exception as exc:
            logger.debug("News fetch failed for %s: %s", sym, exc)

    # Sort by published_at descending
    all_items.sort(
        key=lambda x: x.get("published_at") or "",
        reverse=True,
    )

    return all_items[:limit]


@router.get("/news/earnings_calendar")
def earnings_calendar(
    user_id: str = Query(default=None),
) -> list[dict]:
    """
    Return earnings calendar for the next 30 days for held assets.
    """
    uid = user_id or _get_default_user_id()
    held = _get_held_symbols(uid)
    symbols = held if held else _DEFAULT_SYMBOLS

    try:
        events = fetch_earnings_calendar(symbols)
        events.sort(key=lambda x: x.get("date") or "")
        return events
    except Exception as exc:
        logger.warning("earnings_calendar failed: %s", exc)
        return []
