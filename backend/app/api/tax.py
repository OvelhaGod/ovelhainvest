"""
Tax API endpoints — Phase 8.

GET  /tax/lots               — All open lots with FIFO/HIFO/Spec ID options
GET  /tax/estimate           — Estimated annual US capital gains tax liability
GET  /tax/brazil_darf        — Monthly running total vs R$20k exemption
POST /tax/harvest_candidates — Identify loss harvesting opportunities
POST /tax/preview_sale       — Preview tax impact of a sale (no execution)
POST /tax/lots/sync          — Replay transaction history to build lot state
"""

from __future__ import annotations

import dataclasses
import logging
from datetime import date
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.db.repositories import tax_lots as tax_lots_repo
from app.services.market_data import fetch_current_prices
from app.services.tax_lot_engine import (
    LotMethod,
    find_loss_harvest_candidates,
    get_brazil_darf_status,
    select_lots_to_sell,
    estimate_tax_impact,
    sync_lots_from_transactions,
    BRAZIL_MONTHLY_EXEMPTION_BRL,
    DEFAULT_LT_RATE,
    DEFAULT_ST_RATE,
)

router = APIRouter()
logger = logging.getLogger(__name__)

from app.config import get_default_user_id as _get_default_user_id
_DEFAULT_USER = _get_default_user_id()


# ── Request schemas ───────────────────────────────────────────────────────────

class HarvestCandidatesRequest(BaseModel):
    user_id: str | None = None
    min_loss_pct: float = 0.10


class PreviewSaleRequest(BaseModel):
    user_id: str | None = None
    account_id: str | None = None
    symbol: str
    quantity: float
    lot_method: str = "hifo"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _method(lot_method: str) -> LotMethod:
    try:
        return LotMethod(lot_method.lower())
    except ValueError:
        return LotMethod.HIFO


def _dc(obj: Any) -> Any:
    """Recursively convert dataclasses to dicts."""
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {k: _dc(v) for k, v in dataclasses.asdict(obj).items()}
    if isinstance(obj, (list, tuple)):
        return [_dc(i) for i in obj]
    if isinstance(obj, date):
        return obj.isoformat()
    return obj


def _safe_prices(symbols: list[str]) -> dict[str, float]:
    """Fetch prices, return empty dict on error."""
    if not symbols:
        return {}
    try:
        return fetch_current_prices(symbols)
    except Exception as exc:
        logger.warning("_safe_prices: %s", exc)
        return {}


# ── GET /tax/lots ─────────────────────────────────────────────────────────────

@router.get("/tax/lots")
async def get_tax_lots(
    user_id: str = Query(default=_DEFAULT_USER),
    account_id: str | None = Query(default=None),
    symbol: str | None = Query(default=None),
    lot_method: str = Query(default="hifo"),
) -> dict:
    """
    Return all open tax lots with current unrealized gain/loss, holding period,
    and estimated tax impact if sold now.

    Per-account lot method: HIFO for taxable, FIFO for tax-advantaged.
    """
    method = _method(lot_method)
    lots = tax_lots_repo.get_unrealized_positions(
        user_id=user_id,
    )

    if account_id:
        lots = [l for l in lots if l.get("account_id") == account_id]
    if symbol:
        lots = [l for l in lots if l.get("symbol", "").upper() == symbol.upper()]

    # Fetch prices for any lots missing price data
    missing_symbols = list({l.get("symbol", "") for l in lots if not l.get("current_price") and l.get("symbol")})
    if missing_symbols:
        prices = _safe_prices(missing_symbols)
        for lot in lots:
            sym = lot.get("symbol", "")
            if not lot.get("current_price") and sym in prices:
                p = prices[sym]
                qty = float(lot.get("quantity", 0.0))
                cost_pu = float(lot.get("cost_basis_per_unit", 0.0))
                acq_raw = lot.get("acquisition_date")
                try:
                    acq_date = date.fromisoformat(str(acq_raw)[:10])
                except Exception:
                    acq_date = date.today()
                from app.services.tax_lot_engine import classify_holding_period
                hp = classify_holding_period(acq_date, date.today())
                impact = estimate_tax_impact(lot, qty, p, date.today())
                lot["current_price"] = p
                lot["current_value"] = round(qty * p, 2)
                lot["unrealized_gain"] = round(qty * p - qty * cost_pu, 2)
                lot["unrealized_pct"] = round((p - cost_pu) / cost_pu, 4) if cost_pu else 0.0
                lot["holding_period"] = hp
                lot["estimated_tax_if_sold"] = impact.estimated_tax
                lot["after_tax_proceeds"] = impact.after_tax_proceeds

    # Sort: losses first (harvest candidates), then by symbol
    lots.sort(key=lambda l: (l.get("unrealized_gain", 0) or 0))

    return {
        "lots": lots,
        "total_lots": len(lots),
        "lot_method": method.value,
        "total_unrealized_gain": round(sum(l.get("unrealized_gain", 0) or 0 for l in lots), 2),
        "total_estimated_tax": round(sum(l.get("estimated_tax_if_sold", 0) or 0 for l in lots), 2),
    }


# ── GET /tax/estimate ─────────────────────────────────────────────────────────

@router.get("/tax/estimate")
async def get_tax_estimate(
    user_id: str = Query(default=_DEFAULT_USER),
    year: int | None = Query(default=None),
) -> dict:
    """
    Return estimated annual US tax liability.

    Fields:
    1. realized_ytd — realized gains/losses YTD
    2. unrealized — unrealized gains on all open positions
    3. estimated_tax — computed at ST=32%, LT=15%
    4. worst_case — if all positions closed today
    5. harvest_savings — potential savings from top 3 loss harvest candidates
    """
    current_year = year or date.today().year

    # 1. Realized gains YTD
    realized = tax_lots_repo.get_realized_gains(user_id=user_id, year=current_year)

    # 2. Unrealized positions
    lots = tax_lots_repo.get_all_open_lots(user_id=user_id)
    symbols = list({l.get("symbol", "") for l in lots if l.get("symbol")})
    prices = _safe_prices(symbols)
    positions = tax_lots_repo.get_unrealized_positions(user_id=user_id, current_prices=prices)

    total_unrealized_gain = sum(p.get("unrealized_gain", 0) or 0 for p in positions)
    total_unrealized_lt = sum(
        p.get("unrealized_gain", 0) or 0
        for p in positions if p.get("holding_period") == "long_term"
    )
    total_unrealized_st = total_unrealized_gain - total_unrealized_lt

    # 3. Estimated tax on realized
    estimated_tax_realized = float(realized.get("total_estimated_tax", 0.0))

    # 4. Worst case: close everything today
    worst_case_tax = estimated_tax_realized
    for p in positions:
        ug = p.get("unrealized_gain", 0) or 0
        if ug > 0:
            hp = p.get("holding_period", "short_term")
            rate = DEFAULT_LT_RATE if hp == "long_term" else DEFAULT_ST_RATE
            worst_case_tax += ug * rate
    worst_case_tax = round(worst_case_tax, 2)

    # 5. Harvest savings — top 3 loss candidates
    harvest_candidates = find_loss_harvest_candidates(
        lots=[dict(l) for l in lots],
        current_prices=prices,
        min_loss_pct=0.05,
    )
    top_3 = harvest_candidates[:3]
    harvest_savings = round(sum(c.estimated_tax_savings for c in top_3), 2)

    return {
        # Field 1
        "realized_ytd": {
            "year": current_year,
            **realized,
        },
        # Field 2
        "unrealized": {
            "total_unrealized_gain": round(total_unrealized_gain, 2),
            "unrealized_lt_gain": round(total_unrealized_lt, 2),
            "unrealized_st_gain": round(total_unrealized_st, 2),
            "open_positions": len(positions),
        },
        # Field 3
        "estimated_tax": {
            "on_realized_gains": round(estimated_tax_realized, 2),
            "st_rate": DEFAULT_ST_RATE,
            "lt_rate": DEFAULT_LT_RATE,
        },
        # Field 4
        "worst_case": {
            "if_close_everything_today": worst_case_tax,
            "note": "Assumes all unrealized gains taxed at applicable ST/LT rates",
        },
        # Field 5
        "harvest_savings": {
            "potential_savings_usd": harvest_savings,
            "top_candidates": [_dc(c) for c in top_3],
        },
        "net_estimated_tax": round(estimated_tax_realized - harvest_savings, 2),
    }


# ── GET /tax/brazil_darf ──────────────────────────────────────────────────────

@router.get("/tax/brazil_darf")
async def get_brazil_darf(
    user_id: str = Query(default=_DEFAULT_USER),
    year: int | None = Query(default=None),
    month: int | None = Query(default=None),
) -> dict:
    """
    Return Brazil DARF tracker for current month + last 12 months history.
    Includes optimal sale schedule if near threshold.
    """
    status = get_brazil_darf_status(user_id=user_id, db=None)
    result = _dc(status)

    # Optimal sale schedule hint if close to threshold
    if status.gross_sales_brl > 0.5 * BRAZIL_MONTHLY_EXEMPTION_BRL:
        result["schedule_hint"] = (
            f"You have used {status.exemption_pct_used * 100:.0f}% of the monthly exemption. "
            f"Split any sales > R${status.remaining_before_trigger:,.0f} into next month."
        )

    return result


# ── POST /tax/harvest_candidates ──────────────────────────────────────────────

@router.post("/tax/harvest_candidates")
async def get_harvest_candidates(body: HarvestCandidatesRequest) -> dict:
    """
    Return tax-loss harvesting candidates sorted by tax savings.
    Includes wash sale warnings and suggested replacement ETFs.
    """
    user_id = body.user_id or _DEFAULT_USER

    lots = tax_lots_repo.get_all_open_lots(user_id=user_id)
    symbols = list({l.get("symbol", "") for l in lots if l.get("symbol")})
    prices = _safe_prices(symbols)

    # Fetch recent transactions for wash sale detection
    try:
        from app.db.supabase_client import get_supabase_client
        from app.db.repositories import accounts as accounts_repo
        client = get_supabase_client()
        accts = client.table("accounts").select("id").eq("user_id", user_id).execute()
        account_ids = [a["id"] for a in (accts.data or [])]
        txns_resp = (
            client.table("transactions")
            .select("id, type, asset_id, quantity, price, executed_at")
            .in_("account_id", account_ids)
            .order("executed_at", desc=True)
            .limit(200)
            .execute()
        )
        recent_txns_raw = txns_resp.data or []
        # Enrich with symbol
        asset_ids_txn = {t.get("asset_id") for t in recent_txns_raw if t.get("asset_id")}
        asset_sym_map: dict[str, str] = {}
        if asset_ids_txn:
            a_resp = client.table("assets").select("id, symbol").in_("id", list(asset_ids_txn)).execute()
            asset_sym_map = {r["id"]: r["symbol"] for r in (a_resp.data or [])}
        recent_txns = []
        for t in recent_txns_raw:
            t["symbol"] = asset_sym_map.get(t.get("asset_id", ""), "")
            recent_txns.append(t)
    except Exception as exc:
        logger.warning("harvest_candidates: could not fetch recent txns: %s", exc)
        recent_txns = []

    candidates = find_loss_harvest_candidates(
        lots=[dict(l) for l in lots],
        current_prices=prices,
        min_loss_pct=body.min_loss_pct,
        recent_transactions=recent_txns,
    )

    total_savings = sum(c.estimated_tax_savings for c in candidates)
    return {
        "candidates": [_dc(c) for c in candidates],
        "total_candidates": len(candidates),
        "total_estimated_savings_usd": round(total_savings, 2),
        "methodology": f"HIFO lot selection, min_loss_pct={body.min_loss_pct*100:.0f}%, 30-day wash sale window",
    }


# ── POST /tax/preview_sale ────────────────────────────────────────────────────

@router.post("/tax/preview_sale")
async def preview_sale(body: PreviewSaleRequest) -> dict:
    """
    Preview which lots would be used and total tax impact for a hypothetical sale.
    Does NOT execute any trades.
    """
    user_id = body.user_id or _DEFAULT_USER
    symbol = body.symbol.upper()
    today = date.today()

    # Get open lots for this symbol
    lots = tax_lots_repo.get_open_lots(
        account_id=body.account_id,
        symbol=symbol,
    )
    if not lots:
        # Try all accounts for this user
        all_lots = tax_lots_repo.get_all_open_lots(user_id=user_id)
        lots = [l for l in all_lots if l.get("symbol", "").upper() == symbol]

    if not lots:
        raise HTTPException(status_code=404, detail=f"No open lots found for {symbol}")

    # Fetch current price
    prices = _safe_prices([symbol])
    current_price = prices.get(symbol, 0.0)
    if current_price <= 0:
        raise HTTPException(status_code=503, detail=f"Could not fetch price for {symbol}")

    method = _method(body.lot_method)
    lots_to_sell = select_lots_to_sell(
        lots=[dict(l) for l in lots],
        quantity_to_sell=body.quantity,
        method=method,
    )

    # Compute impact per lot
    lot_impacts = []
    total_proceeds = 0.0
    total_cost = 0.0
    total_gain = 0.0
    total_tax = 0.0
    total_after_tax = 0.0

    for lot, qty in lots_to_sell:
        impact = estimate_tax_impact(lot, qty, current_price, today)
        lot_impacts.append({
            "lot_id": str(lot.get("id", "")),
            "symbol": symbol,
            "account_name": lot.get("account_name", ""),
            "acquisition_date": str(lot.get("acquisition_date", "")),
            "quantity_used": qty,
            "cost_basis_per_unit": float(lot.get("cost_basis_per_unit", 0)),
            "current_price": current_price,
            **_dc(impact),
        })
        total_proceeds   += impact.proceeds
        total_cost       += impact.cost_basis
        total_gain       += impact.gain_loss
        total_tax        += impact.estimated_tax
        total_after_tax  += impact.after_tax_proceeds

    return {
        "symbol": symbol,
        "quantity_requested": body.quantity,
        "lot_method": method.value,
        "current_price": current_price,
        "lot_impacts": lot_impacts,
        "summary": {
            "total_proceeds": round(total_proceeds, 2),
            "total_cost_basis": round(total_cost, 2),
            "total_gain_loss": round(total_gain, 2),
            "total_estimated_tax": round(total_tax, 2),
            "total_after_tax_proceeds": round(total_after_tax, 2),
        },
        "note": "Preview only — no trades executed.",
    }


# ── POST /tax/lots/sync ───────────────────────────────────────────────────────

@router.post("/tax/lots/sync")
async def sync_tax_lots(
    user_id: str = Query(default=_DEFAULT_USER),
) -> dict:
    """
    Replay all transaction history to build/reconcile tax lot state.
    Idempotent — safe to re-run.
    """
    from app.db.supabase_client import get_supabase_client
    client = get_supabase_client()

    try:
        accts = client.table("accounts").select("id, tax_treatment").eq("user_id", user_id).execute()
        accounts = accts.data or []
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Could not fetch accounts: {exc}")

    total = {"lots_opened": 0, "lots_closed": 0, "errors": []}

    for account in accounts:
        account_id = account["id"]
        tax_treatment = account.get("tax_treatment", "taxable")
        # Only track lots for taxable + brazil_taxable accounts
        if tax_treatment in ("tax_deferred", "tax_free", "bank"):
            continue

        try:
            txns_resp = (
                client.table("transactions")
                .select("id, type, asset_id, quantity, price, executed_at")
                .eq("account_id", account_id)
                .order("executed_at", desc=False)
                .execute()
            )
            transactions = txns_resp.data or []

            # Enrich with symbol
            asset_ids = {t.get("asset_id") for t in transactions if t.get("asset_id")}
            asset_sym_map: dict[str, str] = {}
            if asset_ids:
                a_resp = client.table("assets").select("id, symbol").in_("id", list(asset_ids)).execute()
                asset_sym_map = {r["id"]: r["symbol"] for r in (a_resp.data or [])}
            for t in transactions:
                t["symbol"] = asset_sym_map.get(t.get("asset_id", ""), "")

            result = sync_lots_from_transactions(
                account_id=account_id,
                transactions=transactions,
                db=client,
            )
            total["lots_opened"] += result.lots_opened
            total["lots_closed"] += result.lots_closed
            total["errors"].extend(result.errors)

        except Exception as exc:
            logger.error("sync account %s: %s", account_id, exc)
            total["errors"].append(f"account {account_id}: {exc}")

    return {
        "status": "ok" if not total["errors"] else "partial",
        "lots_opened": total["lots_opened"],
        "lots_closed": total["lots_closed"],
        "errors": total["errors"][:20],  # cap error list
    }
