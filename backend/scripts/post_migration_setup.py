"""
Post-migration setup — run this AFTER applying all_migrations.sql in Supabase.

Usage:
  cd backend
  uv run python scripts/post_migration_setup.py

This runs steps 3-9 of Option B in sequence:
  3. Create Thiago's user record
  4. Seed assets, alert rules, strategy config (via /admin/seed)
  5. Seed accounts + vaults
  6. Run valuation pipeline
  7. Create first portfolio snapshot
  8. Verify full /run_allocation cycle
"""
import sys
import os
import requests
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


API = "http://localhost:8000"


def step(n, label):
    print(f"\n{'='*60}")
    print(f"  Step {n}: {label}")
    print(f"{'='*60}\n")


def check_backend():
    try:
        r = requests.get(f"{API}/health", timeout=5)
        return r.status_code == 200
    except Exception:
        return False


def main():
    from dotenv import load_dotenv
    load_dotenv()

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")
    headers = {"apikey": key, "Authorization": f"Bearer {key}",
               "Content-Type": "application/json", "Prefer": "return=representation"}

    # Verify migrations first
    step(0, "Verify Migrations")
    import scripts.verify_migrations as vm
    # If it exits with 1, tables are missing
    missing = []
    import requests as req
    for table in ["users", "accounts", "assets", "holdings", "signals_runs"]:
        r = req.get(f"{url}/rest/v1/{table}?limit=0",
                    headers={"apikey": key, "Authorization": f"Bearer {key}"}, timeout=10)
        if r.status_code not in [200, 206]:
            missing.append(table)
    if missing:
        print(f"  MISSING tables: {missing}")
        print(f"  Apply migrations first: backend/scripts/all_migrations.sql")
        print(f"  URL: https://supabase.com/dashboard/project/{url.replace('https://','').replace('.supabase.co','')}/sql/new")
        sys.exit(1)
    print("  All required tables present.")

    # Check backend
    step(1, "Check Backend")
    if not check_backend():
        print("  Backend not running. Starting...")
        import subprocess
        subprocess.Popen(
            ["uv", "run", "uvicorn", "app.main:app", "--port", "8000"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        time.sleep(5)
        if not check_backend():
            print("  ERROR: Backend failed to start. Run manually:")
            print("    uv run uvicorn app.main:app --reload --port 8000")
            sys.exit(1)
    print("  Backend running.")

    # Step 3: Create user
    step(3, "Create User")
    r = req.get(f"{url}/rest/v1/users?email=eq.thiago@ovelha.us", headers=headers, timeout=10)
    if r.json():
        uid = r.json()[0]["id"]
        print(f"  User exists: {uid}")
    else:
        r = req.post(f"{url}/rest/v1/users", headers=headers,
                     json={"email": "thiago@ovelha.us", "display_name": "Thiago"}, timeout=10)
        uid = r.json()[0]["id"]
        print(f"  Created user: {uid}")

    # Write DEFAULT_USER_ID to .env
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    with open(env_path, "r") as f:
        content = f.read()
    if f"DEFAULT_USER_ID={uid}" not in content:
        updated = content.replace("DEFAULT_USER_ID=", f"DEFAULT_USER_ID={uid}")
        with open(env_path, "w") as f:
            f.write(updated)
        print(f"  DEFAULT_USER_ID={uid} written to .env")

    # Step 4: Seed via API
    step(4, "Seed Assets + Alert Rules + Strategy Config")
    admin_secret = os.getenv("ADMIN_SECRET", "ovelha-admin-change-in-production")
    r = req.post(f"{API}/admin/seed", timeout=60,
                 headers={"Authorization": f"Bearer {admin_secret}", "Content-Type": "application/json"},
                 json={"user_id": uid})
    if r.status_code == 200:
        d = r.json()
        print(f"  Seeded: {d.get('inserted')} rows, {len(d.get('errors', []))} errors")
        if d.get("errors"):
            for err in d["errors"][:3]:
                print(f"    Error: {err}")
    else:
        print(f"  Seed returned {r.status_code}: {r.text[:200]}")

    # Step 5: Seed accounts
    step(5, "Seed Accounts + Vaults")
    from scripts.seed_thiago_accounts import main as seed_accounts
    seed_accounts()

    # Step 6: Valuation
    step(6, "Run Valuation Pipeline (25 assets)")
    print("  Fetching market data — this may take 60+ seconds...")
    r = req.post(f"{API}/valuation_update",
                 json={"dry_run": False}, timeout=180)
    if r.status_code == 200:
        d = r.json()
        print(f"  Valuation complete: {d.get('updated', 0)} assets scored")
        if d.get("top_assets"):
            print("  Top 3:")
            for a in d["top_assets"][:3]:
                print(f"    {a.get('symbol')}: composite={a.get('composite_score', 0):.3f}")
    else:
        print(f"  Valuation {r.status_code}: {r.text[:200]}")

    # Step 7: Snapshot
    step(7, "Create First Portfolio Snapshot")
    r = req.post(f"{API}/performance/snapshot", timeout=30)
    if r.status_code == 200:
        print(f"  Snapshot: {r.json()}")
    else:
        print(f"  Snapshot {r.status_code}: {r.text[:100]}")

    # Step 8: Full pipeline test
    step(8, "Full Pipeline Test (run_allocation)")
    r = req.post(f"{API}/run_allocation",
                 json={"event_type": "daily_check"}, timeout=90)
    if r.status_code == 200:
        d = r.json()
        print(f"  Status: {d.get('status')}")
        print(f"  Regime: {d.get('regime_state')}")
        print(f"  Trades: {len(d.get('proposed_trades', []))}")
        ai = d.get("ai_validation_summary") or {}
        print(f"  AI status: {ai.get('overall_status', 'n/a')}")
    else:
        print(f"  run_allocation {r.status_code}: {r.text[:200]}")

    print("\n" + "="*60)
    print("  POST-MIGRATION SETUP COMPLETE")
    print("="*60)
    print("\nNext steps:")
    print("  1. Fill real holdings: backend/scripts/holdings_template.csv")
    print("     Then: uv run python scripts/import_holdings_csv.py scripts/holdings_template.csv")
    print("  2. Add Anthropic credits: https://console.anthropic.com/billing")
    print("     (API key valid but credit balance is too low)")
    print("  3. Add n8n workflows once n8n is deployed on homelab")
    print("  4. Verify: uv run python scripts/verify_full_pipeline.py")
    print("="*60)


if __name__ == "__main__":
    main()
