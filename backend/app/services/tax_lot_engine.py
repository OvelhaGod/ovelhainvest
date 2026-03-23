"""
Tax lot tracking engine: FIFO, HIFO, Spec ID lot selection.

Handles US capital gains optimization and Brazil DARF tracking.
Wash sale detection (30-day window).

Phase 8 — full implementation.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

BRAZIL_MONTHLY_EXEMPTION_BRL = 20_000.0  # R$20k/month stock sale exemption
BRAZIL_CGT_RATE = 0.15                   # 15% on variable-income gains above limit
DEFAULT_LT_RATE = 0.15                   # US long-term CGT rate
DEFAULT_ST_RATE = 0.32                   # US short-term rate (ordinary income)
LOSS_HARVEST_MIN_PCT = 0.10              # 10% unrealized loss triggers candidate

# ── Replacement ETF map for loss harvesting (avoids wash sales) ───────────────
REPLACEMENT_MAP: dict[str, str] = {
    "VTI":  "ITOT",   "ITOT":  "VTI",
    "VXUS": "IXUS",   "IXUS":  "VXUS",
    "BND":  "AGG",    "AGG":   "BND",
    "BNDX": "IAGG",   "IAGG":  "BNDX",
    "QQQ":  "QQQM",   "QQQM":  "QQQ",
    "SPY":  "IVV",    "IVV":   "VOO",   "VOO": "IVV",
    "VNQ":  "SCHH",   "SCHH":  "VNQ",
    "TIP":  "SCHP",   "SCHP":  "TIP",
}


class LotMethod(Enum):
    FIFO = "fifo"       # First in, first out (IRS default)
    HIFO = "hifo"       # Highest cost first (minimizes gains) ← preferred for taxable
    SPEC_ID = "spec_id" # Specific lot identification


# ── Dataclasses ───────────────────────────────────────────────────────────────

@dataclass
class TaxImpact:
    proceeds: float
    cost_basis: float
    gain_loss: float
    holding_period: str    # "long_term" | "short_term"
    estimated_tax: float
    after_tax_proceeds: float
    effective_rate: float
    quantity: float


@dataclass
class LossHarvestCandidate:
    symbol: str
    lot_id: str
    account_name: str
    acquisition_date: date
    quantity: float
    cost_basis_per_unit: float
    current_price: float
    unrealized_loss_usd: float
    unrealized_loss_pct: float
    estimated_tax_savings: float
    wash_sale_warning: bool
    suggested_replacement: str | None
    holding_period: str


@dataclass
class SyncResult:
    lots_opened: int = 0
    lots_closed: int = 0
    errors: list[str] = field(default_factory=list)


@dataclass
class BrazilDARFStatus:
    year: int
    month: int
    gross_sales_brl: float
    exemption_limit: float
    remaining_before_trigger: float
    exemption_pct_used: float
    darf_due: float
    is_triggered: bool
    realized_gain_brl: float
    projected_month_end: float | None
    recommendation: str
    history: list[dict] = field(default_factory=list)


@dataclass
class RealizedGainsSummary:
    total_st_gains: float = 0.0
    total_lt_gains: float = 0.0
    total_st_losses: float = 0.0
    total_lt_losses: float = 0.0
    net_st: float = 0.0
    net_lt: float = 0.0
    estimated_tax_st: float = 0.0
    estimated_tax_lt: float = 0.0
    total_estimated_tax: float = 0.0


# ── Core functions ─────────────────────────────────────────────────────────────

def classify_holding_period(acquisition_date: date, sale_date: date) -> str:
    """Return 'long_term' if held >= 365 days, else 'short_term'."""
    days_held = (sale_date - acquisition_date).days
    return "long_term" if days_held >= 365 else "short_term"


def check_wash_sale(
    symbol: str,
    sale_date: date,
    recent_transactions: list[dict],
    window_days: int = 30,
) -> bool:
    """
    Detect wash sale: same symbol purchased within 30 days before OR after sale.

    Args:
        symbol: Ticker symbol being sold.
        sale_date: Date of sale.
        recent_transactions: List of transaction dicts with 'type', 'symbol', 'executed_at'.
        window_days: Wash sale window (default 30).

    Returns:
        True if wash sale would be triggered.
    """
    start = sale_date - timedelta(days=window_days)
    end   = sale_date + timedelta(days=window_days)
    for txn in recent_transactions:
        if txn.get("type", "").lower() not in ("buy", "purchase", "reinvest"):
            continue
        txn_symbol = txn.get("symbol", "")
        if txn_symbol.upper() != symbol.upper():
            continue
        # Parse transaction date
        raw_date = txn.get("executed_at") or txn.get("date")
        if not raw_date:
            continue
        if isinstance(raw_date, str):
            try:
                txn_date = date.fromisoformat(raw_date[:10])
            except ValueError:
                continue
        elif isinstance(raw_date, date):
            txn_date = raw_date
        else:
            continue
        if start <= txn_date <= end:
            logger.debug("Wash sale detected for %s: buy on %s near sale %s", symbol, txn_date, sale_date)
            return True
    return False


def select_lots_to_sell(
    lots: list[dict],
    quantity_to_sell: float,
    method: LotMethod = LotMethod.HIFO,
    account_tax_treatment: str = "taxable",
) -> list[tuple[dict, float]]:
    """
    Select which tax lots to use when selling a given quantity.

    For taxable accounts: default to HIFO to minimize realized gains.
    For tax-advantaged (401k, Roth): tax method irrelevant, use FIFO.

    Args:
        lots: List of open tax lot dicts (from tax_lots table).
        quantity_to_sell: Units to sell.
        method: Lot selection method (ignored for tax-advantaged — always FIFO).
        account_tax_treatment: "taxable", "tax_deferred", "tax_free", etc.

    Returns:
        List of (lot_dict, quantity_from_this_lot) pairs.
    """
    open_lots = [l for l in lots if not l.get("is_closed", False)]
    if not open_lots:
        logger.warning("select_lots_to_sell: no open lots")
        return []

    # Tax-advantaged accounts: always FIFO (tax method irrelevant)
    effective_method = method
    if account_tax_treatment in ("tax_deferred", "tax_free"):
        effective_method = LotMethod.FIFO

    # Sort lots per method
    if effective_method == LotMethod.FIFO:
        sorted_lots = sorted(open_lots, key=lambda l: l.get("acquisition_date", ""))
    elif effective_method == LotMethod.HIFO:
        sorted_lots = sorted(open_lots, key=lambda l: l.get("cost_basis_per_unit", 0.0), reverse=True)
    else:
        # SPEC_ID: return lots as-is (caller must pass pre-selected lots)
        sorted_lots = open_lots

    result: list[tuple[dict, float]] = []
    remaining = quantity_to_sell

    for lot in sorted_lots:
        if remaining <= 0:
            break
        available = float(lot.get("quantity", 0.0))
        if available <= 0:
            continue
        use_qty = min(available, remaining)
        result.append((lot, use_qty))
        remaining -= use_qty

    if remaining > 1e-8:
        logger.warning(
            "select_lots_to_sell: insufficient lots — needed %.4f more units", remaining
        )

    return result


def estimate_tax_impact(
    lot: dict,
    quantity: float,
    current_price: float,
    sale_date: date,
    marginal_rate_lt: float = DEFAULT_LT_RATE,
    marginal_rate_st: float = DEFAULT_ST_RATE,
) -> TaxImpact:
    """
    Estimate tax liability for selling `quantity` units from `lot` at `current_price`.

    Returns:
        TaxImpact with proceeds, cost_basis, gain_loss, holding_period,
        estimated_tax, after_tax_proceeds, effective_rate.
    """
    raw_acq = lot.get("acquisition_date")
    if isinstance(raw_acq, str):
        acq_date = date.fromisoformat(raw_acq[:10])
    elif isinstance(raw_acq, date):
        acq_date = raw_acq
    else:
        acq_date = sale_date  # fallback — worst case short-term

    proceeds      = quantity * current_price
    cost_per_unit = float(lot.get("cost_basis_per_unit", 0.0))
    cost_basis    = quantity * cost_per_unit
    gain_loss     = proceeds - cost_basis
    holding_period = classify_holding_period(acq_date, sale_date)

    rate = marginal_rate_lt if holding_period == "long_term" else marginal_rate_st
    estimated_tax = max(0.0, gain_loss * rate)
    after_tax_proceeds = proceeds - estimated_tax
    effective_rate = estimated_tax / proceeds if proceeds > 0 else 0.0

    return TaxImpact(
        proceeds=round(proceeds, 2),
        cost_basis=round(cost_basis, 2),
        gain_loss=round(gain_loss, 2),
        holding_period=holding_period,
        estimated_tax=round(estimated_tax, 2),
        after_tax_proceeds=round(after_tax_proceeds, 2),
        effective_rate=round(effective_rate, 4),
        quantity=quantity,
    )


def find_loss_harvest_candidates(
    lots: list[dict],
    current_prices: dict[str, float],
    min_loss_pct: float = LOSS_HARVEST_MIN_PCT,
    wash_sale_safe_symbols: set[str] | None = None,
    recent_transactions: list[dict] | None = None,
) -> list[LossHarvestCandidate]:
    """
    Identify lots with unrealized losses >= min_loss_pct eligible for harvesting.

    Args:
        lots: All open tax lot dicts (include 'symbol', 'account_name' fields).
        current_prices: Dict symbol → current price.
        min_loss_pct: Minimum loss percentage to qualify (default 10%).
        wash_sale_safe_symbols: Symbols already confirmed wash-sale-safe.
        recent_transactions: Transactions for wash sale detection.

    Returns:
        List of LossHarvestCandidate sorted by estimated_tax_savings DESC.
    """
    today = date.today()
    candidates: list[LossHarvestCandidate] = []
    recent_txns = recent_transactions or []

    for lot in lots:
        if lot.get("is_closed", False):
            continue
        symbol = lot.get("symbol", "").upper()
        if not symbol:
            continue
        price = current_prices.get(symbol)
        if price is None:
            continue

        cost_per_unit = float(lot.get("cost_basis_per_unit", 0.0))
        if cost_per_unit <= 0:
            continue
        quantity = float(lot.get("quantity", 0.0))
        if quantity <= 0:
            continue

        loss_pct = (price - cost_per_unit) / cost_per_unit
        if loss_pct > -min_loss_pct:
            continue  # Not enough loss

        unrealized_loss = quantity * (price - cost_per_unit)  # negative
        impact = estimate_tax_impact(lot, quantity, price, today)

        # Tax savings = tax we would avoid by realizing the loss as a deduction
        # Short-term loss offsets short-term gains (32%) or LT gains (15%)
        holding = classify_holding_period(
            date.fromisoformat(str(lot.get("acquisition_date", today))[:10]), today
        )
        rate = DEFAULT_ST_RATE if holding == "short_term" else DEFAULT_LT_RATE
        # Loss is negative gain_loss → tax_savings = abs(gain_loss) * rate
        estimated_tax_savings = max(0.0, abs(impact.gain_loss) * rate)

        # Wash sale check
        wash_sale_warning = False
        if wash_sale_safe_symbols and symbol in wash_sale_safe_symbols:
            wash_sale_warning = False
        else:
            wash_sale_warning = check_wash_sale(symbol, today, recent_txns)

        replacement = REPLACEMENT_MAP.get(symbol)

        candidates.append(LossHarvestCandidate(
            symbol=symbol,
            lot_id=str(lot.get("id", "")),
            account_name=lot.get("account_name", lot.get("account_id", "Unknown")),
            acquisition_date=date.fromisoformat(str(lot.get("acquisition_date", today))[:10]),
            quantity=quantity,
            cost_basis_per_unit=cost_per_unit,
            current_price=price,
            unrealized_loss_usd=round(unrealized_loss, 2),
            unrealized_loss_pct=round(loss_pct * 100, 2),
            estimated_tax_savings=round(estimated_tax_savings, 2),
            wash_sale_warning=wash_sale_warning,
            suggested_replacement=replacement,
            holding_period=holding,
        ))

    candidates.sort(key=lambda c: c.estimated_tax_savings, reverse=True)
    return candidates


# ── Lot management ─────────────────────────────────────────────────────────────

def open_lot(
    account_id: str,
    asset_id: str,
    symbol: str,
    quantity: float,
    price: float,
    acquisition_date: date,
    db: Any,
) -> dict:
    """
    Insert a new open tax lot record.

    Returns the created lot as a dict.
    """
    from app.db.repositories import tax_lots as tax_lots_repo
    cost_total = round(quantity * price, 2)
    lot_data = {
        "account_id": account_id,
        "asset_id": asset_id,
        "symbol": symbol,
        "acquisition_date": acquisition_date.isoformat(),
        "quantity": quantity,
        "cost_basis_per_unit": round(price, 6),
        "cost_basis_total": cost_total,
        "lot_type": "long",  # reclassified on sale
        "is_closed": False,
        "wash_sale_flag": False,
    }
    lot = tax_lots_repo.upsert_lot(db, lot_data)
    logger.info("Opened lot: %s %.4f @ $%.2f = $%.2f", symbol, quantity, price, cost_total)
    return lot


def close_lots(
    lots_to_close: list[tuple[dict, float]],
    current_price: float,
    sale_date: date,
    db: Any,
    recent_transactions: list[dict] | None = None,
) -> list[dict]:
    """
    Close or partially close lots after a sale.

    For each (lot, quantity):
      - Full close: set is_closed=True, compute realized gain.
      - Partial close: reduce lot.quantity, create closed child lot.

    Returns list of closed lot records.
    """
    from app.db.repositories import tax_lots as tax_lots_repo
    closed = []
    for lot, qty in lots_to_close:
        lot_id = str(lot.get("id", ""))
        lot_qty = float(lot.get("quantity", 0.0))
        symbol = lot.get("symbol", "")
        proceeds = round(qty * current_price, 2)
        cost_basis_pu = float(lot.get("cost_basis_per_unit", 0.0))
        realized = round(proceeds - qty * cost_basis_pu, 2)

        # Wash sale detection
        wash = check_wash_sale(symbol, sale_date, recent_transactions or [])

        if abs(qty - lot_qty) < 1e-8:
            # Full close
            closed_lot = tax_lots_repo.close_lot(
                db=db,
                lot_id=lot_id,
                closed_date=sale_date,
                proceeds=proceeds,
                realized_gain_loss=realized,
                wash_sale_flag=wash,
            )
            closed.append(closed_lot)
            logger.info("Closed lot %s: %.4f @ $%.2f → gain $%.2f", symbol, qty, current_price, realized)
        else:
            # Partial close — split into closed child + remaining open parent
            # Create closed child lot
            child_data = {
                "account_id": lot.get("account_id"),
                "asset_id": lot.get("asset_id"),
                "symbol": symbol,
                "acquisition_date": lot.get("acquisition_date"),
                "quantity": qty,
                "cost_basis_per_unit": cost_basis_pu,
                "cost_basis_total": round(qty * cost_basis_pu, 2),
                "lot_type": lot.get("lot_type", "long"),
                "is_closed": True,
                "closed_date": sale_date.isoformat(),
                "proceeds": proceeds,
                "realized_gain_loss": realized,
                "wash_sale_flag": wash,
            }
            child = tax_lots_repo.upsert_lot(db, child_data)
            closed.append(child)

            # Reduce parent lot quantity
            new_qty = round(lot_qty - qty, 8)
            tax_lots_repo.upsert_lot(db, {
                "id": lot_id,
                "quantity": new_qty,
                "cost_basis_total": round(new_qty * cost_basis_pu, 2),
            })
            logger.info(
                "Partial close lot %s: sold %.4f, remaining %.4f → gain $%.2f",
                symbol, qty, new_qty, realized,
            )
    return closed


def sync_lots_from_transactions(
    account_id: str,
    transactions: list[dict],
    db: Any,
) -> SyncResult:
    """
    Replay transaction history to build/reconcile lot state.
    Idempotent — uses transaction.id as dedup key.

    Returns SyncResult with counts.
    """
    from app.db.repositories import tax_lots as tax_lots_repo
    result = SyncResult()

    # Sort by date ascending for correct chronological replay
    sorted_txns = sorted(transactions, key=lambda t: t.get("executed_at", ""))

    for txn in sorted_txns:
        txn_type = str(txn.get("type", "")).lower()
        symbol = str(txn.get("symbol", "")).upper()
        qty = float(txn.get("quantity") or 0)
        price = float(txn.get("price") or 0)
        asset_id = str(txn.get("asset_id") or "")
        txn_id = str(txn.get("id", ""))

        if qty <= 0 or price <= 0:
            continue

        raw_date = txn.get("executed_at") or txn.get("date")
        try:
            txn_date = date.fromisoformat(str(raw_date)[:10])
        except (ValueError, TypeError):
            result.errors.append(f"Bad date on txn {txn_id}")
            continue

        try:
            if txn_type in ("buy", "purchase", "reinvest"):
                # Check if already synced (idempotent)
                existing = tax_lots_repo.get_lot_by_transaction_id(db, txn_id)
                if existing:
                    continue
                lot = open_lot(account_id, asset_id, symbol, qty, price, txn_date, db)
                # Tag with source transaction id
                tax_lots_repo.upsert_lot(db, {"id": str(lot.get("id")), "source_transaction_id": txn_id})
                result.lots_opened += 1

            elif txn_type in ("sell", "withdrawal"):
                open_lots = tax_lots_repo.get_open_lots(db, account_id=account_id, symbol=symbol)
                lots_to_close = select_lots_to_sell(
                    lots=[dict(l) for l in open_lots],
                    quantity_to_sell=qty,
                    method=LotMethod.HIFO,
                )
                closed = close_lots(lots_to_close, price, txn_date, db)
                result.lots_closed += len(closed)

        except Exception as exc:
            logger.warning("sync_lots error on txn %s: %s", txn_id, exc)
            result.errors.append(f"txn {txn_id}: {exc}")

    return result


# ── Brazil DARF ────────────────────────────────────────────────────────────────

def update_brazil_darf(
    user_id: str,
    sale_amount_brl: float,
    realized_gain_brl: float,
    sale_date: date,
    db: Any,
) -> dict:
    """
    Upsert brazil_darf_tracker for (user_id, year, month).
    Accumulates sales + gains; computes DARF if threshold exceeded.

    Returns updated DARF record dict.
    """
    from app.db.repositories import tax_lots as tax_lots_repo
    year, month = sale_date.year, sale_date.month
    existing = tax_lots_repo.get_brazil_darf(db, user_id=user_id, year=year, month=month) or {}

    new_gross = float(existing.get("gross_sales_brl", 0.0)) + sale_amount_brl
    new_gain  = float(existing.get("realized_gain_brl", 0.0)) + realized_gain_brl

    exemption_used = new_gross >= BRAZIL_MONTHLY_EXEMPTION_BRL
    darf_due = round(new_gain * BRAZIL_CGT_RATE, 2) if exemption_used else 0.0

    record = {
        "user_id": user_id,
        "year": year,
        "month": month,
        "gross_sales_brl": round(new_gross, 2),
        "realized_gain_brl": round(new_gain, 2),
        "exemption_used": exemption_used,
        "darf_due": darf_due,
    }
    return tax_lots_repo.upsert_brazil_darf(db, record)


def get_brazil_darf_status(user_id: str, db: Any) -> BrazilDARFStatus:
    """
    Get current month's Brazil DARF status with recommendation and history.
    """
    from app.db.repositories import tax_lots as tax_lots_repo
    today = date.today()
    year, month = today.year, today.month

    record = tax_lots_repo.get_brazil_darf(db, user_id=user_id, year=year, month=month) or {}
    gross  = float(record.get("gross_sales_brl", 0.0))
    gain   = float(record.get("realized_gain_brl", 0.0))
    limit  = BRAZIL_MONTHLY_EXEMPTION_BRL

    remaining  = max(0.0, limit - gross)
    pct_used   = min(gross / limit, 1.0) if limit > 0 else 0.0
    triggered  = gross >= limit
    darf_due   = round(gain * BRAZIL_CGT_RATE, 2) if triggered else 0.0

    # Project month-end based on elapsed days
    import calendar
    days_in_month = calendar.monthrange(year, month)[1]
    elapsed_days  = today.day
    projected: float | None = None
    if elapsed_days > 0:
        daily_rate = gross / elapsed_days
        projected = round(daily_rate * days_in_month, 2)

    # Build recommendation
    if triggered:
        month_name = today.strftime("%B")
        rec = (
            f"DARF triggered. R${darf_due:,.0f} due by last business day of {month_name}. "
            "Consider deferring additional Brazil sales to next month."
        )
    elif remaining < 2_000:
        rec = (
            f"⚠ Only R${remaining:,.0f} of exempt sales remaining. "
            "Split additional sales into next month to avoid DARF."
        )
    else:
        rec = f"R${remaining:,.0f} of exempt sales remaining this month."

    # Last 12 months history
    history = []
    for i in range(12):
        m = month - i
        y = year
        while m <= 0:
            m += 12
            y -= 1
        rec_h = tax_lots_repo.get_brazil_darf(db, user_id=user_id, year=y, month=m) or {}
        history.append({
            "year": y, "month": m,
            "gross_sales_brl": float(rec_h.get("gross_sales_brl", 0.0)),
            "darf_due": float(rec_h.get("darf_due", 0.0)),
            "exemption_used": bool(rec_h.get("exemption_used", False)),
        })

    return BrazilDARFStatus(
        year=year,
        month=month,
        gross_sales_brl=gross,
        exemption_limit=limit,
        remaining_before_trigger=remaining,
        exemption_pct_used=round(pct_used, 4),
        darf_due=darf_due,
        is_triggered=triggered,
        realized_gain_brl=gain,
        projected_month_end=projected,
        recommendation=rec,
        history=history,
    )


def compute_brazil_optimal_sale_schedule(
    lots_to_sell: list[dict],
    current_prices: dict[str, float],
    usd_brl_rate: float,
    already_sold_brl: float = 0.0,
) -> list[dict]:
    """
    If total planned sales > R$20,000: suggest splitting across months.
    Returns monthly sale schedule keeping each month under R$20,000.
    """
    today = date.today()
    year, month = today.year, today.month

    plans: list[dict] = []
    running_brl = already_sold_brl

    for lot in lots_to_sell:
        symbol = str(lot.get("symbol", "")).upper()
        price_usd = current_prices.get(symbol, 0.0)
        price_brl = price_usd * usd_brl_rate
        qty = float(lot.get("quantity", 0.0))
        sale_brl = qty * price_brl

        if running_brl + sale_brl <= BRAZIL_MONTHLY_EXEMPTION_BRL:
            plans.append({"symbol": symbol, "quantity": qty, "month": month, "year": year, "sale_brl": round(sale_brl, 2)})
            running_brl += sale_brl
        else:
            # Split: sell as much as fits this month, rest next month
            fits_brl = max(0.0, BRAZIL_MONTHLY_EXEMPTION_BRL - running_brl)
            fits_qty = fits_brl / price_brl if price_brl > 0 else 0.0
            if fits_qty > 0.01:
                plans.append({"symbol": symbol, "quantity": round(fits_qty, 4), "month": month, "year": year, "sale_brl": round(fits_qty * price_brl, 2)})
            # Remainder → next month
            next_month = month + 1 if month < 12 else 1
            next_year  = year if month < 12 else year + 1
            remaining_qty = qty - fits_qty
            plans.append({"symbol": symbol, "quantity": round(remaining_qty, 4), "month": next_month, "year": next_year, "sale_brl": round(remaining_qty * price_brl, 2), "deferred": True})
            running_brl = 0.0  # reset for next month

    return plans


def compute_realized_gains_summary(
    closed_lots: list[dict],
    year: int,
    lt_rate: float = DEFAULT_LT_RATE,
    st_rate: float = DEFAULT_ST_RATE,
) -> RealizedGainsSummary:
    """Aggregate realized gains/losses for a tax year."""
    s = RealizedGainsSummary()
    for lot in closed_lots:
        closed_date_raw = lot.get("closed_date")
        if not closed_date_raw:
            continue
        closed_date = date.fromisoformat(str(closed_date_raw)[:10])
        if closed_date.year != year:
            continue
        gain = float(lot.get("realized_gain_loss", 0.0))
        acq_raw = lot.get("acquisition_date")
        if acq_raw:
            acq_date = date.fromisoformat(str(acq_raw)[:10])
            hp = classify_holding_period(acq_date, closed_date)
        else:
            hp = "short_term"

        if hp == "long_term":
            if gain >= 0:
                s.total_lt_gains += gain
            else:
                s.total_lt_losses += abs(gain)
        else:
            if gain >= 0:
                s.total_st_gains += gain
            else:
                s.total_st_losses += abs(gain)

    s.net_st = s.total_st_gains - s.total_st_losses
    s.net_lt = s.total_lt_gains - s.total_lt_losses
    s.estimated_tax_st = max(0.0, s.net_st * st_rate)
    s.estimated_tax_lt = max(0.0, s.net_lt * lt_rate)
    s.total_estimated_tax = s.estimated_tax_st + s.estimated_tax_lt
    return s
