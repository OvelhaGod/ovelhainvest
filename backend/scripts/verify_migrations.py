"""
Verify all required Supabase tables exist.
Run: cd backend && uv run python scripts/verify_migrations.py
"""
import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_KEY")

if not url or not key:
    print("ERROR: SUPABASE_URL or SUPABASE_SERVICE_KEY missing from .env")
    sys.exit(1)

headers = {"apikey": key, "Authorization": f"Bearer {key}"}

REQUIRED_TABLES = [
    "users", "accounts", "vaults", "assets", "holdings", "transactions",
    "asset_valuations", "strategy_configs", "signals_runs", "news_items",
    "research_docs", "opportunity_events", "benchmarks", "portfolio_snapshots",
    "tax_lots", "brazil_darf_tracker", "performance_attribution", "risk_metrics",
    "decision_journal", "alert_rules", "alert_history",
]

print("\n=== OvelhaInvest Migration Verification ===\n")
missing = []
for table in REQUIRED_TABLES:
    r = requests.get(f"{url}/rest/v1/{table}?limit=0", headers=headers, timeout=10)
    ok = r.status_code in [200, 206]
    print(f"  {'OK  ' if ok else 'MISS'} {table}")
    if not ok:
        missing.append(table)

print()
if missing:
    print(f"RESULT: {len(missing)} tables missing — apply migrations first\n")
    print("  1. Go to: https://supabase.com/dashboard/project/ogvonmfwtsfgbpvydlpm/sql/new")
    print("  2. Open:  backend/scripts/all_migrations.sql")
    print("  3. Paste full contents and click Run")
    print("  4. Re-run this script\n")
    sys.exit(1)
else:
    print(f"RESULT: All {len(REQUIRED_TABLES)} tables present — ready to proceed\n")
    sys.exit(0)
