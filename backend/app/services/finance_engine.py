"""
Personal Finance Engine — Phase 11.
Handles: AI categorization, cashflow projection, net worth computation, monthly summaries.
"""
from __future__ import annotations

import logging
import os
from collections import defaultdict
from datetime import date, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


# ── AI Categorization ────────────────────────────────────────────────────────

async def categorize_transaction(
    description: str,
    amount: float,
    existing_categories: list[dict],
) -> str:
    """
    Auto-categorize a transaction using Claude Haiku (fast + cheap).
    Returns a category name from existing_categories.
    Falls back to 'Other Expense'/'Other Income' on any failure.
    """
    cat_names = [c["name"] for c in existing_categories if c.get("name")]
    if not cat_names:
        return "Other Expense" if amount < 0 else "Other Income"

    try:
        import anthropic
        api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("CLAUDE_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not set")

        client = anthropic.Anthropic(api_key=api_key)
        txn_type = "income" if amount > 0 else "expense"
        prompt = (
            f"Categorize this financial transaction into exactly one of these categories:\n"
            f"{', '.join(cat_names)}\n\n"
            f'Transaction: "{description}", Amount: ${abs(amount):.2f}, Type: {txn_type}\n\n'
            f"Reply with ONLY the category name, nothing else."
        )
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=50,
            messages=[{"role": "user", "content": prompt}],
        )
        result = msg.content[0].text.strip()
        if result in cat_names:
            return result
    except Exception as exc:
        logger.warning("AI categorization failed: %s", exc)

    return "Other Expense" if amount < 0 else "Other Income"


# ── Monthly summary ──────────────────────────────────────────────────────────

def compute_monthly_summary(transactions: list[dict], month: date) -> dict:
    """
    Aggregate income, expenses, savings for a given calendar month.
    transactions: list of spending_transactions rows (joined with categories).
    """
    month_start = month.replace(day=1)
    if month.month == 12:
        month_end = date(month.year + 1, 1, 1) - timedelta(days=1)
    else:
        month_end = date(month.year, month.month + 1, 1) - timedelta(days=1)

    total_income = 0.0
    total_expenses = 0.0
    by_category: dict[str, float] = defaultdict(float)

    for t in transactions:
        raw_date = t.get("date")
        if isinstance(raw_date, str):
            t_date = date.fromisoformat(raw_date[:10])
        elif isinstance(raw_date, date):
            t_date = raw_date
        else:
            continue

        if not (month_start <= t_date <= month_end):
            continue

        amt_usd = float(t.get("amount_usd") or t.get("amount") or 0)
        txn_type = t.get("type", "expense")

        if txn_type == "income":
            total_income += abs(amt_usd)
        elif txn_type == "expense":
            total_expenses += abs(amt_usd)
            cat = t.get("categories") or {}
            cat_name = cat.get("name", "Uncategorized") if isinstance(cat, dict) else "Uncategorized"
            by_category[cat_name] += abs(amt_usd)

    savings = total_income - total_expenses
    savings_rate = (savings / total_income * 100) if total_income > 0 else 0.0

    return {
        "month": month_start.isoformat(),
        "total_income": round(total_income, 2),
        "total_expenses": round(total_expenses, 2),
        "savings": round(savings, 2),
        "savings_rate": round(savings_rate, 1),
        "by_category": {k: round(v, 2) for k, v in sorted(by_category.items(), key=lambda x: -x[1])},
    }


# ── Cashflow projection ──────────────────────────────────────────────────────

def project_cashflow(
    current_balance: float,
    recurring_items: list[dict],
    days: int = 90,
) -> list[dict]:
    """
    Project bank balance day-by-day for the next N days.
    Uses recurring_items to build the projection.
    Returns list of {date, projected_balance, events, is_today}.
    """
    projection: list[dict] = []
    balance = current_balance
    today = date.today()

    for day_offset in range(days):
        d = today + timedelta(days=day_offset)
        day_events: list[dict] = []

        for item in recurring_items:
            if not item.get("is_active", True):
                continue

            freq = item.get("frequency", "monthly")
            dom = item.get("day_of_month") or 1
            triggers = False

            if freq == "monthly" and d.day == dom:
                triggers = True
            elif freq == "weekly" and d.weekday() == 0:  # every Monday
                triggers = True
            elif freq == "biweekly" and day_offset % 14 == 0:
                triggers = True
            elif freq == "annual" and d.month == 1 and d.day == 1:
                triggers = True

            if triggers:
                amt = float(item.get("amount", 0))
                signed = amt if item.get("type") == "income" else -amt
                balance += signed
                day_events.append({
                    "name": item.get("name", ""),
                    "amount": signed,
                    "type": item.get("type", "expense"),
                })

        projection.append({
            "date": d.isoformat(),
            "projected_balance": round(balance, 2),
            "events": day_events,
            "is_today": day_offset == 0,
        })

    return projection


# ── Net worth ────────────────────────────────────────────────────────────────

def compute_net_worth(
    investment_value_usd: float,
    accounts: list[dict],
    usd_brl_rate: float = 5.23,
) -> dict:
    """
    Compute complete net worth from investment portfolio + all accounts.
    Normalizes BRL-denominated accounts to USD using the provided rate.
    """
    total_assets = investment_value_usd
    total_liabilities = 0.0
    cash_usd = 0.0
    breakdown: dict = {
        "investments": round(investment_value_usd, 2),
        "accounts": {},
    }

    for acct in accounts:
        balance = float(acct.get("current_balance") or 0)
        currency = acct.get("currency", "USD")
        is_liability = bool(acct.get("is_liability", False))
        acct_type = acct.get("account_type", "checking")

        # Normalize to USD
        balance_usd = balance / usd_brl_rate if currency == "BRL" else balance

        breakdown["accounts"][acct.get("name", "Unknown")] = {
            "balance_usd": round(balance_usd, 2),
            "is_liability": is_liability,
            "type": acct_type,
            "currency": currency,
        }

        if is_liability:
            total_liabilities += abs(balance_usd)
        else:
            total_assets += balance_usd
            if acct_type in ("checking", "savings"):
                cash_usd += balance_usd

    return {
        "total_assets_usd": round(total_assets, 2),
        "total_liabilities_usd": round(total_liabilities, 2),
        "net_worth_usd": round(total_assets - total_liabilities, 2),
        "investment_value_usd": round(investment_value_usd, 2),
        "cash_usd": round(cash_usd, 2),
        "breakdown": breakdown,
    }
