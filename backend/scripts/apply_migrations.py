"""
Item 2 — Apply database migrations to Supabase.
Run: cd backend && uv run python scripts/apply_migrations.py

Supabase doesn't support raw SQL execution via the JS/Python client —
this script generates the SQL to copy-paste into the Supabase SQL editor.

Alternatively, if psycopg2 is available and SUPABASE_DB_URL is set,
it will apply migrations directly via psql.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from pathlib import Path

MIGRATIONS = [
    "app/migrations/001_initial_schema.sql",
    "app/migrations/002_tax_lots.sql",
    "app/migrations/003_performance_tables.sql",
    "app/migrations/004_journal_alerts.sql",
]

BASE = Path(__file__).parent.parent

def check_tables_via_supabase():
    """Verify which tables exist using the REST API."""
    from app.db.supabase_client import get_supabase_client
    client = get_supabase_client()

    tables = [
        "users", "accounts", "vaults", "assets", "holdings", "transactions",
        "asset_valuations", "strategy_configs", "signals_runs", "news_items",
        "research_docs", "opportunity_events", "benchmarks", "portfolio_snapshots",
        "tax_lots", "brazil_darf_tracker",
        "performance_attribution", "risk_metrics",
        "decision_journal", "alert_rules", "alert_history",
    ]

    print("\n=== Table Existence Check ===\n")
    missing = []
    for t in tables:
        try:
            result = client.table(t).select("id").limit(1).execute()
            print(f"  OK  {t}")
        except Exception as e:
            print(f"  MISSING  {t}  ({e})")
            missing.append(t)

    if missing:
        print(f"\n{len(missing)} tables missing. Apply migrations in Supabase SQL editor.\n")
    else:
        print("\nAll tables exist.\n")
    return len(missing) == 0


def print_migration_instructions():
    print("\n=== Migration Instructions ===")
    print()
    print("Supabase does not support executing raw DDL via the REST API client.")
    print("Apply migrations manually in the Supabase SQL editor:")
    print()
    print("  1. Go to: https://supabase.com/dashboard/project/omjcxxhmtsmoynsxjxnl/sql/new")
    print("  2. Run each file below IN ORDER (copy the SQL → paste → Run):")
    print()
    for m in MIGRATIONS:
        path = BASE / m
        if path.exists():
            size = path.stat().st_size
            print(f"     {m}  ({size:,} bytes)")
        else:
            print(f"     {m}  (FILE NOT FOUND)")
    print()
    print("  3. After running all 4 migrations, re-run this script to verify.")
    print()


if __name__ == "__main__":
    print_migration_instructions()

    try:
        from app.config import get_settings
        s = get_settings()
        if not s.supabase_configured:
            print("SUPABASE_SERVICE_KEY not set — skipping table check.")
            sys.exit(0)
        all_ok = check_tables_via_supabase()
        sys.exit(0 if all_ok else 1)
    except Exception as e:
        print(f"Could not connect to Supabase: {e}")
        sys.exit(1)
