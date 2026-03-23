"""Repository: assets table."""

from __future__ import annotations

import logging

from app.db.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


def get_active_assets() -> list[dict]:
    """
    Fetch all active assets from the universe.

    Returns:
        List of asset dicts.
    """
    try:
        client = get_supabase_client()
        resp = (
            client.table("assets")
            .select("*")
            .eq("is_active", True)
            .order("symbol")
            .execute()
        )
        return resp.data or []
    except Exception as exc:
        logger.error("get_active_assets failed: %s", exc)
        raise


def get_asset_by_symbol(symbol: str, currency: str = "USD") -> dict | None:
    """
    Fetch a single asset by symbol and currency.

    Args:
        symbol: Ticker symbol (e.g. "VTI").
        currency: Currency code (default "USD").

    Returns:
        Asset dict or None if not found.
    """
    try:
        client = get_supabase_client()
        resp = (
            client.table("assets")
            .select("*")
            .eq("symbol", symbol)
            .eq("currency", currency)
            .limit(1)
            .execute()
        )
        data = resp.data
        return data[0] if data else None
    except Exception as exc:
        logger.error("get_asset_by_symbol failed for %s/%s: %s", symbol, currency, exc)
        return None


def get_assets_by_ids(asset_ids: list[str]) -> list[dict]:
    """
    Fetch assets by a list of UUIDs.

    Args:
        asset_ids: List of asset UUID strings.

    Returns:
        List of asset dicts.
    """
    if not asset_ids:
        return []
    try:
        client = get_supabase_client()
        resp = (
            client.table("assets")
            .select("*")
            .in_("id", asset_ids)
            .execute()
        )
        return resp.data or []
    except Exception as exc:
        logger.error("get_assets_by_ids failed: %s", exc)
        raise


def get_dcf_eligible_assets() -> list[dict]:
    """
    Fetch assets that qualify for DCF valuation.
    Requires is_dcf_eligible=True and a meaningful moat rating.

    Returns:
        List of asset dicts ready for DCF analysis.
    """
    try:
        client = get_supabase_client()
        resp = (
            client.table("assets")
            .select("*")
            .eq("is_active", True)
            .eq("is_dcf_eligible", True)
            .not_.in_("moat_rating", ["none", "unknown"])
            .execute()
        )
        return resp.data or []
    except Exception as exc:
        logger.error("get_dcf_eligible_assets failed: %s", exc)
        raise


def upsert_asset(asset: dict) -> dict:
    """
    Upsert an asset record (insert or update on symbol+currency unique index).

    Args:
        asset: Asset dict. Must include symbol, name, asset_class, currency.

    Returns:
        Upserted asset dict.
    """
    try:
        client = get_supabase_client()
        resp = (
            client.table("assets")
            .upsert(asset, on_conflict="symbol,currency")
            .execute()
        )
        data = resp.data
        return data[0] if data else asset
    except Exception as exc:
        logger.error("upsert_asset failed for %s: %s", asset.get("symbol"), exc)
        raise


# ── Seed data ────────────────────────────────────────────────────────────────

SEED_ASSETS = [
    # Core ETFs (Swensen/Bogle model — low cost, broad exposure)
    {"symbol": "VTI",   "name": "Vanguard Total Stock Market ETF",   "asset_class": "US_equity",    "currency": "USD", "is_dcf_eligible": False, "moat_rating": None,      "sector": "Diversified"},
    {"symbol": "VXUS",  "name": "Vanguard Total Intl Stock ETF",     "asset_class": "Intl_equity",  "currency": "USD", "is_dcf_eligible": False, "moat_rating": None,      "sector": "Diversified"},
    {"symbol": "BND",   "name": "Vanguard Total Bond Market ETF",    "asset_class": "Bond",         "currency": "USD", "is_dcf_eligible": False, "moat_rating": None,      "sector": "Fixed Income"},
    {"symbol": "BNDX",  "name": "Vanguard Total Intl Bond ETF",      "asset_class": "Bond",         "currency": "USD", "is_dcf_eligible": False, "moat_rating": None,      "sector": "Fixed Income"},
    {"symbol": "VNQ",   "name": "Vanguard Real Estate ETF",          "asset_class": "US_equity",    "currency": "USD", "is_dcf_eligible": False, "moat_rating": None,      "sector": "REIT"},
    {"symbol": "TIP",   "name": "iShares TIPS Bond ETF",             "asset_class": "Bond",         "currency": "USD", "is_dcf_eligible": False, "moat_rating": None,      "sector": "Inflation Protected"},
    # US Large-Cap Tech (Buffett moat screen)
    {"symbol": "GOOG",  "name": "Alphabet Inc",                      "asset_class": "US_equity",    "currency": "USD", "is_dcf_eligible": True,  "moat_rating": "wide",    "sector": "Communication Services"},
    {"symbol": "AMZN",  "name": "Amazon.com Inc",                    "asset_class": "US_equity",    "currency": "USD", "is_dcf_eligible": True,  "moat_rating": "wide",    "sector": "Consumer Discretionary"},
    {"symbol": "AAPL",  "name": "Apple Inc",                         "asset_class": "US_equity",    "currency": "USD", "is_dcf_eligible": True,  "moat_rating": "wide",    "sector": "Technology"},
    {"symbol": "META",  "name": "Meta Platforms Inc",                "asset_class": "US_equity",    "currency": "USD", "is_dcf_eligible": True,  "moat_rating": "wide",    "sector": "Communication Services"},
    {"symbol": "MSFT",  "name": "Microsoft Corp",                    "asset_class": "US_equity",    "currency": "USD", "is_dcf_eligible": True,  "moat_rating": "wide",    "sector": "Technology"},
    {"symbol": "NVDA",  "name": "NVIDIA Corp",                       "asset_class": "US_equity",    "currency": "USD", "is_dcf_eligible": True,  "moat_rating": "narrow",  "sector": "Technology"},
    {"symbol": "CRM",   "name": "Salesforce Inc",                    "asset_class": "US_equity",    "currency": "USD", "is_dcf_eligible": True,  "moat_rating": "narrow",  "sector": "Technology"},
    {"symbol": "PLTR",  "name": "Palantir Technologies",             "asset_class": "US_equity",    "currency": "USD", "is_dcf_eligible": False, "moat_rating": "narrow",  "sector": "Technology"},
    {"symbol": "ARM",   "name": "Arm Holdings",                      "asset_class": "US_equity",    "currency": "USD", "is_dcf_eligible": False, "moat_rating": "narrow",  "sector": "Technology"},
    # Crypto
    {"symbol": "BTC",   "name": "Bitcoin",                           "asset_class": "Crypto",       "currency": "USD", "is_dcf_eligible": False, "moat_rating": None},
    {"symbol": "ETH",   "name": "Ethereum",                         "asset_class": "Crypto",       "currency": "USD", "is_dcf_eligible": False, "moat_rating": None},
    {"symbol": "SOL",   "name": "Solana",                            "asset_class": "Crypto",       "currency": "USD", "is_dcf_eligible": False, "moat_rating": None},
    {"symbol": "LINK",  "name": "Chainlink",                         "asset_class": "Crypto",       "currency": "USD", "is_dcf_eligible": False, "moat_rating": None},
    # Brazil (Clear Corretora sleeve)
    {"symbol": "PETR4", "name": "Petrobras PN",                      "asset_class": "Brazil_equity","currency": "BRL", "is_dcf_eligible": False, "moat_rating": "narrow",  "sector": "Energy"},
    {"symbol": "VALE3", "name": "Vale ON",                           "asset_class": "Brazil_equity","currency": "BRL", "is_dcf_eligible": False, "moat_rating": "narrow",  "sector": "Materials"},
    {"symbol": "ITUB4", "name": "Itaú Unibanco PN",                  "asset_class": "Brazil_equity","currency": "BRL", "is_dcf_eligible": False, "moat_rating": "wide",    "sector": "Financials"},
    # Benchmarks (used for performance attribution, not scored)
    {"symbol": "SPY",   "name": "SPDR S&P 500 ETF",                  "asset_class": "US_equity",    "currency": "USD", "is_dcf_eligible": False, "moat_rating": None,      "sector": "Benchmark"},
    {"symbol": "ACWI",  "name": "iShares MSCI ACWI ETF",             "asset_class": "Intl_equity",  "currency": "USD", "is_dcf_eligible": False, "moat_rating": None,      "sector": "Benchmark"},
    {"symbol": "AGG",   "name": "iShares Core US Aggregate Bond ETF","asset_class": "Bond",         "currency": "USD", "is_dcf_eligible": False, "moat_rating": None,      "sector": "Benchmark"},
]


def run_seed_data() -> dict:
    """
    Insert all SEED_ASSETS into the assets table (upsert — idempotent).
    Safe to call multiple times; existing records are updated, not duplicated.

    Returns:
        Summary dict with inserted/updated count and any errors.
    """
    inserted = 0
    errors: list[str] = []

    for asset_def in SEED_ASSETS:
        row = {
            "symbol":         asset_def["symbol"],
            "name":           asset_def.get("name", asset_def["symbol"]),
            "asset_class":    asset_def["asset_class"],
            "currency":       asset_def.get("currency", "USD"),
            "is_dcf_eligible": asset_def.get("is_dcf_eligible", False),
            "moat_rating":    asset_def.get("moat_rating"),
            "sector":         asset_def.get("sector"),
            "region":         asset_def.get("region"),
            "is_active":      True,
        }
        try:
            upsert_asset(row)
            inserted += 1
        except Exception as exc:
            msg = f"{asset_def['symbol']}: {exc}"
            logger.error("Seed upsert failed — %s", msg)
            errors.append(msg)

    logger.info("Seed complete: %d upserted, %d errors", inserted, len(errors))
    return {"inserted": inserted, "total": len(SEED_ASSETS), "errors": errors}
