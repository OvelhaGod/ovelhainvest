"""
Tax lots repository — database access layer for tax_lots and brazil_darf_tracker tables.

Phase 8 implementation.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

from app.db.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

_DEFAULT_USER = "00000000-0000-0000-0000-000000000001"


# ── Internal helpers ──────────────────────────────────────────────────────────

def _db(db: Any = None):
    """Return supabase client — accept injected db or create one."""
    return db if db is not None else get_supabase_client()


def _enrich_lots_with_symbol(client: Any, lots: list[dict]) -> list[dict]:
    """Join symbol from assets table for lots that only have asset_id."""
    asset_ids = {l.get("asset_id") for l in lots if l.get("asset_id") and not l.get("symbol")}
    if not asset_ids:
        return lots
    try:
        resp = client.table("assets").select("id, symbol").in_("id", list(asset_ids)).execute()
        asset_map = {r["id"]: r["symbol"] for r in (resp.data or [])}
        for lot in lots:
            if not lot.get("symbol") and lot.get("asset_id") in asset_map:
                lot["symbol"] = asset_map[lot["asset_id"]]
    except Exception as exc:
        logger.warning("_enrich_lots_with_symbol: %s", exc)
    return lots


def _enrich_lots_with_account(client: Any, lots: list[dict]) -> list[dict]:
    """Join account_name and tax_treatment from accounts table."""
    account_ids = {l.get("account_id") for l in lots if l.get("account_id") and not l.get("account_name")}
    if not account_ids:
        return lots
    try:
        resp = client.table("accounts").select("id, name, tax_treatment").in_("id", list(account_ids)).execute()
        acct_map = {r["id"]: r for r in (resp.data or [])}
        for lot in lots:
            acct = acct_map.get(lot.get("account_id", ""))
            if acct:
                lot.setdefault("account_name", acct.get("name", ""))
                lot.setdefault("tax_treatment", acct.get("tax_treatment", "taxable"))
    except Exception as exc:
        logger.warning("_enrich_lots_with_account: %s", exc)
    return lots


# ── Open lots ─────────────────────────────────────────────────────────────────

def get_open_lots(
    db: Any = None,
    account_id: str | None = None,
    symbol: str | None = None,
    asset_id: str | None = None,
) -> list[dict]:
    """Return open (not closed) tax lots, optionally filtered."""
    client = _db(db)
    q = client.table("tax_lots").select("*").eq("is_closed", False)
    if account_id:
        q = q.eq("account_id", account_id)
    if asset_id:
        q = q.eq("asset_id", asset_id)
    try:
        resp = q.execute()
        lots = resp.data or []
        lots = _enrich_lots_with_symbol(client, lots)
        lots = _enrich_lots_with_account(client, lots)
        if symbol:
            lots = [l for l in lots if l.get("symbol", "").upper() == symbol.upper()]
        return lots
    except Exception as exc:
        logger.error("get_open_lots: %s", exc)
        return []


def get_all_open_lots(db: Any = None, user_id: str = _DEFAULT_USER) -> list[dict]:
    """Return all open lots across all accounts for a user."""
    client = _db(db)
    try:
        accts = client.table("accounts").select("id").eq("user_id", user_id).execute()
        account_ids = [a["id"] for a in (accts.data or [])]
        if not account_ids:
            return []
        resp = client.table("tax_lots").select("*").eq("is_closed", False).in_("account_id", account_ids).execute()
        lots = resp.data or []
        lots = _enrich_lots_with_symbol(client, lots)
        lots = _enrich_lots_with_account(client, lots)
        return lots
    except Exception as exc:
        logger.error("get_all_open_lots: %s", exc)
        return []


def get_lot_by_id(db: Any = None, lot_id: str = "") -> dict | None:
    """Return a single lot by primary key."""
    try:
        resp = _db(db).table("tax_lots").select("*").eq("id", lot_id).single().execute()
        return resp.data
    except Exception as exc:
        logger.error("get_lot_by_id %s: %s", lot_id, exc)
        return None


def get_lot_by_transaction_id(db: Any = None, transaction_id: str = "") -> dict | None:
    """Return lot tagged with a source_transaction_id (for idempotent sync)."""
    try:
        resp = (
            _db(db).table("tax_lots")
            .select("id")
            .eq("notes", f"txn:{transaction_id}")
            .limit(1)
            .execute()
        )
        data = resp.data or []
        return data[0] if data else None
    except Exception:
        return None


def upsert_lot(db: Any = None, data: dict = {}) -> dict:
    """
    Insert or update a tax lot.
    If data contains 'id', performs an update on that row.
    Otherwise inserts a new row.

    Returns the upserted lot dict.
    """
    client = _db(db)
    try:
        if "id" in data and data["id"]:
            resp = client.table("tax_lots").update(data).eq("id", data["id"]).execute()
        else:
            if "source_transaction_id" in data:
                data["notes"] = f"txn:{data.pop('source_transaction_id')}"
            resp = client.table("tax_lots").insert(data).execute()
        rows = resp.data or []
        return rows[0] if rows else data
    except Exception as exc:
        logger.error("upsert_lot: %s", exc)
        return data


def close_lot(
    db: Any = None,
    lot_id: str = "",
    closed_date: date | None = None,
    proceeds: float = 0.0,
    realized_gain_loss: float = 0.0,
    wash_sale_flag: bool = False,
) -> dict:
    """Mark a lot as closed with realized gain/loss."""
    update = {
        "is_closed": True,
        "closed_date": closed_date.isoformat() if closed_date else None,
        "proceeds": round(proceeds, 2),
        "realized_gain_loss": round(realized_gain_loss, 2),
        "wash_sale_flag": wash_sale_flag,
    }
    return upsert_lot(db, {"id": lot_id, **update})


# ── Realized gains ─────────────────────────────────────────────────────────────

def get_realized_gains(
    db: Any = None,
    user_id: str = _DEFAULT_USER,
    year: int | None = None,
) -> dict:
    """
    Aggregate realized gains/losses for a user and optional year.

    Returns RealizedGainsSummary as a dict.
    """
    from app.services.tax_lot_engine import compute_realized_gains_summary
    client = _db(db)
    current_year = year or date.today().year

    try:
        accts = client.table("accounts").select("id").eq("user_id", user_id).execute()
        account_ids = [a["id"] for a in (accts.data or [])]
        if not account_ids:
            from app.services.tax_lot_engine import RealizedGainsSummary
            return vars(RealizedGainsSummary())

        resp = (
            client.table("tax_lots")
            .select("*")
            .eq("is_closed", True)
            .in_("account_id", account_ids)
            .execute()
        )
        closed_lots = resp.data or []
        summary = compute_realized_gains_summary(closed_lots, current_year)
        return vars(summary)
    except Exception as exc:
        logger.error("get_realized_gains: %s", exc)
        from app.services.tax_lot_engine import RealizedGainsSummary
        return vars(RealizedGainsSummary())


# ── Unrealized positions ───────────────────────────────────────────────────────

def get_unrealized_positions(
    db: Any = None,
    user_id: str = _DEFAULT_USER,
    current_prices: dict[str, float] | None = None,
) -> list[dict]:
    """
    Return all open lots enriched with current unrealized gain/loss.

    If current_prices not provided, returns lots without price-based fields.
    """
    from app.services.tax_lot_engine import classify_holding_period, estimate_tax_impact
    today = date.today()
    lots = get_all_open_lots(db, user_id=user_id)
    prices = current_prices or {}
    result = []

    for lot in lots:
        symbol = str(lot.get("symbol", "")).upper()
        price = prices.get(symbol)
        qty = float(lot.get("quantity", 0.0))
        cost_pu = float(lot.get("cost_basis_per_unit", 0.0))

        acq_raw = lot.get("acquisition_date")
        try:
            acq_date = date.fromisoformat(str(acq_raw)[:10])
        except (TypeError, ValueError):
            acq_date = today

        hp = classify_holding_period(acq_date, today)
        days_held = (today - acq_date).days
        days_to_lt = max(0, 365 - days_held) if hp == "short_term" else 0

        pos = {
            **lot,
            "holding_period": hp,
            "days_held": days_held,
            "days_to_long_term": days_to_lt,
        }

        if price is not None and cost_pu > 0:
            current_value = qty * price
            cost_basis_total = qty * cost_pu
            unrealized_gain = current_value - cost_basis_total
            unrealized_pct = (price - cost_pu) / cost_pu if cost_pu else 0.0
            impact = estimate_tax_impact(lot, qty, price, today)
            wait_savings = None
            if hp == "short_term" and days_to_lt <= 60 and unrealized_gain > 0:
                st_tax = unrealized_gain * 0.32
                lt_tax = unrealized_gain * 0.15
                wait_savings = round(st_tax - lt_tax, 2)
            pos.update({
                "current_price": price,
                "current_value": round(current_value, 2),
                "cost_basis_total_computed": round(cost_basis_total, 2),
                "unrealized_gain": round(unrealized_gain, 2),
                "unrealized_pct": round(unrealized_pct, 4),
                "estimated_tax_if_sold": impact.estimated_tax,
                "after_tax_proceeds": impact.after_tax_proceeds,
                "wait_for_lt_savings": wait_savings,
            })
        result.append(pos)

    return result


# ── Brazil DARF ────────────────────────────────────────────────────────────────

def get_brazil_darf(
    db: Any = None,
    user_id: str = _DEFAULT_USER,
    year: int | None = None,
    month: int | None = None,
) -> dict | None:
    """Return brazil_darf_tracker record for (user_id, year, month)."""
    today = date.today()
    y = year or today.year
    m = month or today.month
    try:
        resp = (
            _db(db).table("brazil_darf_tracker")
            .select("*")
            .eq("user_id", user_id)
            .eq("year", y)
            .eq("month", m)
            .limit(1)
            .execute()
        )
        data = resp.data or []
        return data[0] if data else None
    except Exception as exc:
        logger.error("get_brazil_darf: %s", exc)
        return None


def upsert_brazil_darf(db: Any = None, data: dict = {}) -> dict:
    """Insert or update brazil_darf_tracker record."""
    client = _db(db)
    try:
        resp = client.table("brazil_darf_tracker").upsert(
            data, on_conflict="user_id,year,month"
        ).execute()
        rows = resp.data or []
        return rows[0] if rows else data
    except Exception as exc:
        logger.error("upsert_brazil_darf: %s", exc)
        return data
