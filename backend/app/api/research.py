"""
Research API endpoints.

GET  /news/feed                  — News feed for held/watched assets
GET  /news/earnings_calendar     — Earnings calendar for next 30 days
GET  /news/{symbol}              — News for a specific symbol
POST /news/summarize             — AI summary of a news item
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

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


@router.get("/news/{symbol}")
def news_by_symbol(symbol: str, limit: int = Query(default=5)) -> list[dict]:
    """Return recent news for a specific symbol."""
    try:
        items = fetch_news(symbol, limit=limit)
        return [{**item, "related_symbol": symbol} for item in items]
    except Exception as exc:
        logger.debug("news_by_symbol failed for %s: %s", symbol, exc)
        return []


class SummarizeRequest(BaseModel):
    headline: str | None = None
    summary: str | None = None
    symbol: str | None = None


@router.post("/news/summarize")
def summarize_news(req: SummarizeRequest) -> dict:
    """
    Generate a concise AI-powered investment-focused summary of a news item.
    Uses Claude API. Returns {summary: str} or raises 503 if AI unavailable.
    """
    text = req.summary or req.headline or ""
    if not text.strip():
        raise HTTPException(status_code=400, detail="No content to summarize")

    try:
        import anthropic
        from app.config import get_settings
        settings = get_settings()
        if not settings.anthropic_api_key:
            raise HTTPException(status_code=503, detail="ANTHROPIC_API_KEY not configured")
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        symbol_ctx = f" The news relates to {req.symbol}." if req.symbol else ""
        prompt = (
            f"Summarize the following news item in 2-3 sentences from an investor's perspective."
            f"{symbol_ctx} Focus on what matters for portfolio decisions (valuation, risk, opportunity).\n\n"
            f"Headline: {req.headline or 'N/A'}\n"
            f"Content: {text[:1500]}"
        )
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}],
        )
        summary_text = message.content[0].text if message.content else "Summary unavailable."
        return {"summary": summary_text}
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("AI summarize failed: %s", exc)
        raise HTTPException(status_code=503, detail=f"AI unavailable: {exc}")
