"""
Phase 11 Personal Finance API.

Accounts, spending transactions, budgets, recurring items,
cashflow projection, net worth, and monthly summaries.
"""
from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.db.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)
router = APIRouter()

DEFAULT_USER = "default"


def _db():
    return get_supabase_client()


def _today_month() -> str:
    return date.today().replace(day=1).isoformat()


# ── Pydantic models ──────────────────────────────────────────────────────────

class AccountCreate(BaseModel):
    name: str
    institution: str
    account_type: str  # checking | savings | credit_card | brokerage | crypto | loan
    currency: str = "USD"
    current_balance: float = 0.0
    credit_limit: Optional[float] = None
    is_liability: bool = False

class AccountUpdate(BaseModel):
    current_balance: Optional[float] = None
    credit_limit: Optional[float] = None
    is_liability: Optional[bool] = None
    name: Optional[str] = None
    institution: Optional[str] = None

class TransactionCreate(BaseModel):
    date: str
    description: str
    amount: float
    currency: str = "USD"
    type: str  # income | expense | transfer | investment
    category_id: Optional[str] = None
    account_id: Optional[str] = None
    notes: Optional[str] = None
    is_recurring: bool = False
    tags: Optional[list[str]] = None

class TransactionUpdate(BaseModel):
    category_id: Optional[str] = None
    notes: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[list[str]] = None

class BudgetSet(BaseModel):
    category_id: str
    month: str  # YYYY-MM-DD (first of month)
    amount: float
    currency: str = "USD"

class RecurringCreate(BaseModel):
    name: str
    amount: float
    currency: str = "USD"
    frequency: str  # weekly | biweekly | monthly | annual
    type: str       # income | expense
    day_of_month: Optional[int] = None
    category_id: Optional[str] = None
    is_active: bool = True

class CategoryCreate(BaseModel):
    name: str
    type: str   # income | expense | transfer | investment
    color: str = "#6366f1"
    icon: str = "tag"


# ── Accounts ─────────────────────────────────────────────────────────────────

@router.get("/accounts")
def list_accounts(user_id: str = Query(default=DEFAULT_USER)):
    try:
        rows = _db().table("accounts").select("*").eq("user_id", user_id).eq("is_active", True).execute()
        return rows.data or []
    except Exception as exc:
        logger.error("list_accounts error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/accounts", status_code=201)
def create_account(body: AccountCreate, user_id: str = Query(default=DEFAULT_USER)):
    try:
        row = {
            "user_id": user_id,
            "name": body.name,
            "institution": body.institution,
            "broker": body.institution,   # keep broker in sync for legacy compat
            "account_type": body.account_type,
            "currency": body.currency,
            "current_balance": body.current_balance,
            "credit_limit": body.credit_limit,
            "is_liability": body.is_liability,
            "is_active": True,
            "tax_treatment": "taxable",   # default for Phase 11 accounts
        }
        result = _db().table("accounts").insert(row).execute()
        return result.data[0] if result.data else {}
    except Exception as exc:
        logger.error("create_account error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.put("/accounts/{account_id}")
def update_account(account_id: str, body: AccountUpdate, user_id: str = Query(default=DEFAULT_USER)):
    try:
        updates = {k: v for k, v in body.model_dump().items() if v is not None}
        if not updates:
            raise HTTPException(status_code=400, detail="No fields to update")
        updates["updated_at"] = datetime.utcnow().isoformat()
        result = _db().table("accounts").update(updates).eq("id", account_id).execute()
        return result.data[0] if result.data else {}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete("/accounts/{account_id}")
def delete_account(account_id: str, user_id: str = Query(default=DEFAULT_USER)):
    try:
        _db().table("accounts").update({"is_active": False}).eq("id", account_id).execute()
        return {"deleted": account_id}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ── Categories ───────────────────────────────────────────────────────────────

@router.get("/categories")
def list_categories(user_id: str = Query(default=DEFAULT_USER)):
    try:
        rows = _db().table("categories").select("*").or_(
            f"user_id.eq.{user_id},user_id.eq.default"
        ).order("name").execute()
        return rows.data or []
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/categories", status_code=201)
def create_category(body: CategoryCreate, user_id: str = Query(default=DEFAULT_USER)):
    try:
        result = _db().table("categories").insert({
            "user_id": user_id,
            "name": body.name,
            "type": body.type,
            "color": body.color,
            "icon": body.icon,
            "is_system": False,
        }).execute()
        return result.data[0] if result.data else {}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ── Spending Transactions ─────────────────────────────────────────────────────

@router.get("/transactions")
def list_transactions(
    user_id: str = Query(default=DEFAULT_USER),
    month: Optional[str] = Query(default=None),  # YYYY-MM
    account_id: Optional[str] = Query(default=None),
    category_id: Optional[str] = Query(default=None),
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0),
):
    try:
        q = _db().table("spending_transactions").select(
            "*, categories(id,name,color,icon,type), accounts(id,name,institution)"
        ).eq("user_id", user_id).order("date", desc=True)

        if month:
            year, mon = int(month[:4]), int(month[5:7])
            from calendar import monthrange
            last_day = monthrange(year, mon)[1]
            q = q.gte("date", f"{year}-{mon:02d}-01").lte("date", f"{year}-{mon:02d}-{last_day:02d}")

        if account_id:
            q = q.eq("account_id", account_id)
        if category_id:
            q = q.eq("category_id", category_id)

        rows = q.range(offset, offset + limit - 1).execute()
        return {"transactions": rows.data or [], "offset": offset, "limit": limit}
    except Exception as exc:
        logger.error("list_transactions error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/transactions", status_code=201)
def create_transaction(body: TransactionCreate, user_id: str = Query(default=DEFAULT_USER)):
    try:
        # Normalize amount_usd (if USD already, same; BRL: divide by rate)
        amount_usd = body.amount  # simplified — assumes USD; extend for BRL
        row = {
            "user_id": user_id,
            "date": body.date,
            "description": body.description,
            "amount": body.amount,
            "currency": body.currency,
            "amount_usd": amount_usd,
            "type": body.type,
            "category_id": body.category_id,
            "account_id": body.account_id,
            "notes": body.notes,
            "is_recurring": body.is_recurring,
            "tags": body.tags or [],
            "status": "cleared",
        }
        result = _db().table("spending_transactions").insert(row).execute()
        return result.data[0] if result.data else {}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/transactions/bulk", status_code=201)
def bulk_create_transactions(transactions: list[TransactionCreate], user_id: str = Query(default=DEFAULT_USER)):
    try:
        rows = []
        for body in transactions:
            rows.append({
                "user_id": user_id,
                "date": body.date,
                "description": body.description,
                "amount": body.amount,
                "currency": body.currency,
                "amount_usd": body.amount,
                "type": body.type,
                "category_id": body.category_id,
                "account_id": body.account_id,
                "notes": body.notes,
                "is_recurring": body.is_recurring,
                "tags": body.tags or [],
                "status": "cleared",
            })
        if not rows:
            return {"imported": 0}
        result = _db().table("spending_transactions").insert(rows).execute()
        return {"imported": len(result.data or []), "errors": []}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.put("/transactions/{txn_id}")
def update_transaction(txn_id: str, body: TransactionUpdate, user_id: str = Query(default=DEFAULT_USER)):
    try:
        updates = {k: v for k, v in body.model_dump().items() if v is not None}
        if not updates:
            raise HTTPException(status_code=400, detail="No fields to update")
        updates["updated_at"] = datetime.utcnow().isoformat()
        result = _db().table("spending_transactions").update(updates).eq("id", txn_id).eq("user_id", user_id).execute()
        return result.data[0] if result.data else {}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete("/transactions/{txn_id}")
def delete_transaction(txn_id: str, user_id: str = Query(default=DEFAULT_USER)):
    try:
        _db().table("spending_transactions").delete().eq("id", txn_id).eq("user_id", user_id).execute()
        return {"deleted": txn_id}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/transactions/{txn_id}/categorize")
async def ai_categorize(txn_id: str, user_id: str = Query(default=DEFAULT_USER)):
    try:
        txn_rows = _db().table("spending_transactions").select("*").eq("id", txn_id).execute()
        if not txn_rows.data:
            raise HTTPException(status_code=404, detail="Transaction not found")
        txn = txn_rows.data[0]

        cats = _db().table("categories").select("name").or_(
            f"user_id.eq.{user_id},user_id.eq.default"
        ).execute()

        from app.services.finance_engine import categorize_transaction
        cat_name = await categorize_transaction(txn["description"], txn["amount"], cats.data or [])

        # Look up the category ID
        cat_row = _db().table("categories").select("id,name").eq("name", cat_name).limit(1).execute()
        cat_id = cat_row.data[0]["id"] if cat_row.data else None

        if cat_id:
            _db().table("spending_transactions").update({"category_id": cat_id}).eq("id", txn_id).execute()

        return {"transaction_id": txn_id, "category": cat_name, "category_id": cat_id}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ── Budgets ──────────────────────────────────────────────────────────────────

@router.get("/budgets")
def get_budgets(
    user_id: str = Query(default=DEFAULT_USER),
    month: Optional[str] = Query(default=None),
):
    try:
        month_str = month or _today_month()
        if len(month_str) == 7:
            month_str = month_str + "-01"

        budgets = _db().table("budgets").select(
            "*, categories(id,name,color,icon,type)"
        ).eq("user_id", user_id).eq("month", month_str).execute()

        # Get actuals for this month
        year = int(month_str[:4])
        mon  = int(month_str[5:7])
        from calendar import monthrange
        last_day = monthrange(year, mon)[1]

        txns = _db().table("spending_transactions").select(
            "amount_usd, category_id, type"
        ).eq("user_id", user_id).eq("type", "expense").gte(
            "date", f"{year}-{mon:02d}-01"
        ).lte("date", f"{year}-{mon:02d}-{last_day:02d}").execute()

        # Sum actuals per category
        actuals: dict[str, float] = {}
        for t in (txns.data or []):
            cid = t.get("category_id")
            if cid:
                actuals[cid] = actuals.get(cid, 0.0) + abs(float(t.get("amount_usd") or 0))

        result = []
        for b in (budgets.data or []):
            cid = b.get("category_id")
            spent = actuals.get(cid, 0.0)
            budget_amt = float(b.get("amount", 0))
            result.append({
                **b,
                "spent": round(spent, 2),
                "remaining": round(budget_amt - spent, 2),
                "pct_used": round(spent / budget_amt * 100, 1) if budget_amt > 0 else 0,
            })

        return {"month": month_str, "budgets": result}
    except Exception as exc:
        logger.error("get_budgets error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/budgets", status_code=201)
def set_budget(body: BudgetSet, user_id: str = Query(default=DEFAULT_USER)):
    try:
        month_str = body.month if len(body.month) == 10 else body.month + "-01"
        row = {
            "user_id": user_id,
            "category_id": body.category_id,
            "month": month_str,
            "amount": body.amount,
            "currency": body.currency,
        }
        result = _db().table("budgets").upsert(row, on_conflict="user_id,category_id,month").execute()
        return result.data[0] if result.data else {}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.put("/budgets/{budget_id}")
def update_budget(budget_id: str, body: BudgetSet, user_id: str = Query(default=DEFAULT_USER)):
    try:
        updates = {"amount": body.amount, "currency": body.currency}
        result = _db().table("budgets").update(updates).eq("id", budget_id).eq("user_id", user_id).execute()
        return result.data[0] if result.data else {}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ── Recurring items ───────────────────────────────────────────────────────────

@router.get("/recurring")
def list_recurring(user_id: str = Query(default=DEFAULT_USER)):
    try:
        rows = _db().table("recurring_items").select(
            "*, categories(id,name,color,icon)"
        ).eq("user_id", user_id).eq("is_active", True).order("name").execute()
        return rows.data or []
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/recurring", status_code=201)
def create_recurring(body: RecurringCreate, user_id: str = Query(default=DEFAULT_USER)):
    try:
        result = _db().table("recurring_items").insert({
            "user_id": user_id,
            "name": body.name,
            "amount": body.amount,
            "currency": body.currency,
            "frequency": body.frequency,
            "type": body.type,
            "day_of_month": body.day_of_month,
            "category_id": body.category_id,
            "is_active": body.is_active,
        }).execute()
        return result.data[0] if result.data else {}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.put("/recurring/{item_id}")
def update_recurring(item_id: str, body: RecurringCreate, user_id: str = Query(default=DEFAULT_USER)):
    try:
        updates = {k: v for k, v in body.model_dump().items() if v is not None}
        result = _db().table("recurring_items").update(updates).eq("id", item_id).eq("user_id", user_id).execute()
        return result.data[0] if result.data else {}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete("/recurring/{item_id}")
def deactivate_recurring(item_id: str, user_id: str = Query(default=DEFAULT_USER)):
    try:
        _db().table("recurring_items").update({"is_active": False}).eq("id", item_id).execute()
        return {"deactivated": item_id}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ── Finance summary ───────────────────────────────────────────────────────────

@router.get("/finance/summary")
def finance_summary(
    user_id: str = Query(default=DEFAULT_USER),
    month: Optional[str] = Query(default=None),
):
    """Monthly income/expense/savings summary."""
    try:
        month_str = month or date.today().strftime("%Y-%m")
        year = int(month_str[:4])
        mon  = int(month_str[-2:]) if len(month_str) >= 7 else date.today().month
        from calendar import monthrange
        last_day = monthrange(year, mon)[1]

        txns = _db().table("spending_transactions").select(
            "*, categories(id,name,color,icon,type)"
        ).eq("user_id", user_id).gte(
            "date", f"{year}-{mon:02d}-01"
        ).lte("date", f"{year}-{mon:02d}-{last_day:02d}").execute()

        from app.services.finance_engine import compute_monthly_summary
        month_date = date(year, mon, 1)
        summary = compute_monthly_summary(txns.data or [], month_date)
        return summary
    except Exception as exc:
        logger.error("finance_summary error: %s", exc)
        return {
            "month": month or date.today().strftime("%Y-%m-01"),
            "total_income": 0.0,
            "total_expenses": 0.0,
            "savings": 0.0,
            "savings_rate": 0.0,
            "by_category": {},
        }


@router.get("/finance/cashflow")
def finance_cashflow(
    user_id: str = Query(default=DEFAULT_USER),
    days: int = Query(default=90, le=365),
):
    """90-day projected cash balance using recurring items."""
    try:
        # Current checking + savings balance
        accts = _db().table("accounts").select(
            "current_balance, currency, account_type"
        ).eq("user_id", user_id).eq("is_active", True).in_(
            "account_type", ["checking", "savings"]
        ).execute()

        current_balance = 0.0
        for a in (accts.data or []):
            bal = float(a.get("current_balance") or 0)
            if a.get("currency") == "BRL":
                bal = bal / 5.23  # approximate
            current_balance += bal

        # Recurring items
        recurring = _db().table("recurring_items").select("*").eq(
            "user_id", user_id
        ).eq("is_active", True).execute()

        from app.services.finance_engine import project_cashflow
        projection = project_cashflow(current_balance, recurring.data or [], days)
        return {"current_balance": round(current_balance, 2), "projection": projection}
    except Exception as exc:
        logger.error("finance_cashflow error: %s", exc)
        return {"current_balance": 0.0, "projection": []}


@router.get("/finance/net_worth")
def get_net_worth(user_id: str = Query(default=DEFAULT_USER)):
    """Current net worth = investments + accounts - liabilities."""
    try:
        # Get latest portfolio snapshot for investment value
        snap = _db().table("portfolio_snapshots").select(
            "total_value_usd, usd_brl_rate"
        ).order("snapshot_date", desc=True).limit(1).execute()

        investment_value = 0.0
        usd_brl_rate = 5.23
        if snap.data:
            investment_value = float(snap.data[0].get("total_value_usd") or 0)
            usd_brl_rate = float(snap.data[0].get("usd_brl_rate") or 5.23)

        accts = _db().table("accounts").select(
            "id, name, account_type, currency, current_balance, credit_limit, is_liability, institution"
        ).eq("is_active", True).execute()

        from app.services.finance_engine import compute_net_worth
        nw = compute_net_worth(investment_value, accts.data or [], usd_brl_rate)
        return nw
    except Exception as exc:
        logger.error("get_net_worth error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/finance/net_worth/history")
def net_worth_history(
    user_id: str = Query(default=DEFAULT_USER),
    months: int = Query(default=6, le=24),
):
    """Net worth snapshots over last N months."""
    try:
        from datetime import date
        from dateutil.relativedelta import relativedelta
        cutoff = (date.today() - relativedelta(months=months)).isoformat()

        rows = _db().table("net_worth_snapshots").select("*").eq(
            "user_id", user_id
        ).gte("snapshot_date", cutoff).order("snapshot_date").execute()

        return rows.data or []
    except Exception as exc:
        # dateutil not available — just return recent
        rows = _db().table("net_worth_snapshots").select("*").eq(
            "user_id", user_id
        ).order("snapshot_date", desc=True).limit(months * 30).execute()
        return list(reversed(rows.data or []))
