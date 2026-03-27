"""
Seed script for Phase 11 Personal Finance OS.

Seeds:
- Initial accounts (checking, savings, brokerage stubs)
- Spending categories (full taxonomy from CLAUDE.md Section 31.3)
- Sample recurring items (bills + income schedule)

Usage:
    cd backend
    uv run python scripts/seed_finance.py [--dry-run]
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")


SPENDING_CATEGORIES = [
    # Income
    {"name": "Salary",              "type": "income",  "color": "#10b981", "icon": "briefcase"},
    {"name": "Freelance",           "type": "income",  "color": "#06b6d4", "icon": "laptop"},
    {"name": "Investment Income",   "type": "income",  "color": "#10b981", "icon": "trending-up"},
    {"name": "Other Income",        "type": "income",  "color": "#6b7280", "icon": "dollar-sign"},

    # Housing
    {"name": "Rent / Mortgage",     "type": "expense", "color": "#8b5cf6", "icon": "home"},
    {"name": "Insurance",           "type": "expense", "color": "#8b5cf6", "icon": "shield"},
    {"name": "Utilities",           "type": "expense", "color": "#8b5cf6", "icon": "zap"},
    {"name": "Internet / Phone",    "type": "expense", "color": "#8b5cf6", "icon": "wifi"},

    # Food
    {"name": "Groceries",           "type": "expense", "color": "#f59e0b", "icon": "shopping-cart"},
    {"name": "Restaurants",         "type": "expense", "color": "#f97316", "icon": "utensils"},
    {"name": "Coffee",              "type": "expense", "color": "#a78bfa", "icon": "coffee"},
    {"name": "Food Delivery",       "type": "expense", "color": "#fb923c", "icon": "package"},

    # Transport
    {"name": "Gas",                 "type": "expense", "color": "#ef4444", "icon": "fuel"},
    {"name": "Car Payment",         "type": "expense", "color": "#ef4444", "icon": "car"},
    {"name": "Car Insurance",       "type": "expense", "color": "#ef4444", "icon": "car"},
    {"name": "Rideshare",           "type": "expense", "color": "#f59e0b", "icon": "map-pin"},
    {"name": "Parking",             "type": "expense", "color": "#6b7280", "icon": "parking"},

    # Subscriptions
    {"name": "Streaming",           "type": "expense", "color": "#ec4899", "icon": "tv"},
    {"name": "Software / SaaS",     "type": "expense", "color": "#8b5cf6", "icon": "monitor"},
    {"name": "Gym",                 "type": "expense", "color": "#10b981", "icon": "activity"},

    # Health
    {"name": "Doctor / Medical",    "type": "expense", "color": "#06b6d4", "icon": "heart"},
    {"name": "Pharmacy",            "type": "expense", "color": "#06b6d4", "icon": "plus"},

    # Personal
    {"name": "Shopping",            "type": "expense", "color": "#f59e0b", "icon": "shopping-bag"},
    {"name": "Personal Care",       "type": "expense", "color": "#ec4899", "icon": "scissors"},
    {"name": "Clothing",            "type": "expense", "color": "#a78bfa", "icon": "tag"},

    # Lifestyle
    {"name": "Travel",              "type": "expense", "color": "#3b82f6", "icon": "plane"},
    {"name": "Entertainment",       "type": "expense", "color": "#f97316", "icon": "music"},
    {"name": "Gifts",               "type": "expense", "color": "#ec4899", "icon": "gift"},

    # Education
    {"name": "Tuition",             "type": "expense", "color": "#06b6d4", "icon": "graduation-cap"},
    {"name": "Books / Courses",     "type": "expense", "color": "#3b82f6", "icon": "book"},

    # Taxes
    {"name": "Federal Tax",         "type": "expense", "color": "#64748b", "icon": "landmark"},
    {"name": "State Tax",           "type": "expense", "color": "#64748b", "icon": "landmark"},
    {"name": "Brazil Tax / DARF",   "type": "expense", "color": "#22c55e", "icon": "landmark"},

    # Savings / Investment
    {"name": "Investment",          "type": "expense", "color": "#10b981", "icon": "trending-up"},
    {"name": "Emergency Fund",      "type": "expense", "color": "#3b82f6", "icon": "shield"},

    # Catch-all
    {"name": "Other Expense",       "type": "expense", "color": "#6b7280", "icon": "help-circle"},
    {"name": "Uncategorized",       "type": "expense", "color": "#334155", "icon": "help-circle"},
]


SEED_ACCOUNTS = [
    {
        "name": "SoFi Checking",
        "institution": "SoFi",
        "account_type": "checking",
        "currency": "USD",
        "current_balance": 0,
        "is_liability": False,
        "tax_treatment": "bank",
    },
    {
        "name": "SoFi Savings",
        "institution": "SoFi",
        "account_type": "savings",
        "currency": "USD",
        "current_balance": 0,
        "is_liability": False,
        "tax_treatment": "bank",
    },
    {
        "name": "M1 Finance Taxable",
        "institution": "M1 Finance",
        "account_type": "taxable",
        "currency": "USD",
        "current_balance": 0,
        "is_liability": False,
        "tax_treatment": "taxable",
    },
    {
        "name": "Empower 401k",
        "institution": "Empower",
        "account_type": "401k",
        "currency": "USD",
        "current_balance": 0,
        "is_liability": False,
        "tax_treatment": "tax_deferred",
    },
    {
        "name": "Clear Corretora",
        "institution": "Clear",
        "account_type": "brokerage",
        "currency": "BRL",
        "current_balance": 0,
        "is_liability": False,
        "tax_treatment": "brazil_taxable",
    },
]


SEED_RECURRING_ITEMS: list[dict] = [
    # Income
    {
        "name": "Monthly Salary",
        "amount": 8500,
        "direction": "income",
        "frequency": "monthly",
        "anchor_date": "2025-01-01",
        "category": "Salary",
    },
    # Fixed Expenses
    {
        "name": "Rent",
        "amount": 2200,
        "direction": "expense",
        "frequency": "monthly",
        "anchor_date": "2025-01-01",
        "category": "Rent / Mortgage",
    },
    {
        "name": "Internet",
        "amount": 80,
        "direction": "expense",
        "frequency": "monthly",
        "anchor_date": "2025-01-15",
        "category": "Internet / Phone",
    },
    {
        "name": "Netflix",
        "amount": 17,
        "direction": "expense",
        "frequency": "monthly",
        "anchor_date": "2025-01-10",
        "category": "Streaming",
    },
    {
        "name": "Spotify",
        "amount": 11,
        "direction": "expense",
        "frequency": "monthly",
        "anchor_date": "2025-01-10",
        "category": "Streaming",
    },
    {
        "name": "Gym",
        "amount": 45,
        "direction": "expense",
        "frequency": "monthly",
        "anchor_date": "2025-01-05",
        "category": "Gym",
    },
]


def seed(db, dry_run: bool = False) -> None:
    """Seed finance data."""
    user_id = "default"

    # ── Categories ────────────────────────────────────────────────────────────
    print("Seeding categories...")
    existing_cats = db.table("categories").select("name").eq("user_id", user_id).execute()
    existing_names = {c["name"] for c in (existing_cats.data or [])}

    cats_to_insert = [
        {**cat, "user_id": user_id}
        for cat in SPENDING_CATEGORIES
        if cat["name"] not in existing_names
    ]

    if cats_to_insert:
        if not dry_run:
            db.table("categories").insert(cats_to_insert).execute()
        print(f"  Inserted {len(cats_to_insert)} categories")
    else:
        print("  Categories already seeded — skipped")

    # ── Accounts ──────────────────────────────────────────────────────────────
    print("Seeding accounts...")
    existing_accts = db.table("accounts").select("name").eq("user_id", user_id).execute()
    existing_acct_names = {a["name"] for a in (existing_accts.data or [])}

    accts_to_insert = [
        {**acct, "user_id": user_id, "broker": acct["institution"]}
        for acct in SEED_ACCOUNTS
        if acct["name"] not in existing_acct_names
    ]

    if accts_to_insert:
        if not dry_run:
            db.table("accounts").insert(accts_to_insert).execute()
        print(f"  Inserted {len(accts_to_insert)} accounts")
    else:
        print("  Accounts already exist — skipped")

    # ── Recurring items ───────────────────────────────────────────────────────
    print("Seeding recurring items...")
    existing_rec = db.table("recurring_items").select("name").eq("user_id", user_id).execute()
    existing_rec_names = {r["name"] for r in (existing_rec.data or [])}

    from datetime import date, timedelta

    def compute_next_date(anchor: str, frequency: str) -> str:
        anchor_d = date.fromisoformat(anchor)
        today = date.today()
        d = anchor_d
        while d < today:
            if frequency == "monthly":
                m = d.month + 1
                y = d.year + (m - 1) // 12
                m = (m - 1) % 12 + 1
                d = d.replace(year=y, month=m)
            elif frequency == "biweekly":
                d += timedelta(weeks=2)
            elif frequency == "weekly":
                d += timedelta(weeks=1)
            elif frequency in ("annual", "yearly"):
                d = d.replace(year=d.year + 1)
            else:
                break
        return d.isoformat()

    recs_to_insert = []
    for rec in SEED_RECURRING_ITEMS:
        if rec["name"] not in existing_rec_names:
            recs_to_insert.append({
                "user_id": user_id,
                "name": rec["name"],
                "amount": rec["amount"],
                "direction": rec["direction"],
                "frequency": rec["frequency"],
                "anchor_date": rec["anchor_date"],
                "next_date": compute_next_date(rec["anchor_date"], rec["frequency"]),
                "category": rec.get("category"),
                "is_active": True,
            })

    if recs_to_insert:
        if not dry_run:
            db.table("recurring_items").insert(recs_to_insert).execute()
        print(f"  Inserted {len(recs_to_insert)} recurring items")
    else:
        print("  Recurring items already exist — skipped")

    print("Seed complete." if not dry_run else "Dry run complete — no DB changes made.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed Phase 11 finance data")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing to DB")
    args = parser.parse_args()

    from app.db.supabase_client import get_supabase_client
    db = get_supabase_client()
    seed(db, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
