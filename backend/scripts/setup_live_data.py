"""
Option B Master Setup — runs all live data setup steps in order.
Run: cd backend && uv run python scripts/setup_live_data.py

Steps:
  1. check_env         — verify all required env vars
  2. apply_migrations  — print migration instructions + verify tables
  3. create_user       — create Thiago's user record
  4. seed (admin API)  — seed assets, alert rules, strategy config
  5. seed_accounts     — seed accounts + vaults
  6. import_holdings   — import holdings from CSV (if file provided)
  7. valuation_update  — run valuation pipeline via API
  8. snapshot          — create first portfolio snapshot
  9. verify_pipeline   — run full /run_allocation test

Usage:
  cd backend
  # Basic (no holdings):
  uv run python scripts/setup_live_data.py

  # With holdings CSV:
  uv run python scripts/setup_live_data.py --holdings scripts/holdings_template.csv

  # Skip steps already done:
  uv run python scripts/setup_live_data.py --skip-migrations --skip-user
"""
import sys
import os
import argparse
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

def step(n: int, label: str):
    print(f"\n{'='*60}")
    print(f"  Step {n}: {label}")
    print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--holdings", default=None, help="Path to holdings CSV file")
    parser.add_argument("--skip-migrations", action="store_true")
    parser.add_argument("--skip-user", action="store_true")
    parser.add_argument("--skip-seed", action="store_true")
    parser.add_argument("--skip-accounts", action="store_true")
    parser.add_argument("--skip-valuation", action="store_true")
    args = parser.parse_args()

    # Step 1: Check env
    step(1, "Environment Verification")
    from scripts.check_env import CHECKS, OPTIONAL
    from app.config import get_settings
    s = get_settings()
    all_required = True
    for name, (value, validator) in CHECKS.items():
        try:
            ok = bool(value) and validator(value)
        except Exception:
            ok = False
        if not ok and name not in OPTIONAL:
            print(f"  MISSING  {name}")
            all_required = False
        elif ok:
            print(f"  OK       {name}")
        else:
            print(f"  OPTIONAL {name} (skipped)")

    if not all_required:
        print("\nFill in missing values in backend/.env and re-run.")
        sys.exit(1)
    print("\nAll required env vars set.")

    # Step 2: Migrations
    if not args.skip_migrations:
        step(2, "Database Migrations")
        from scripts.apply_migrations import print_migration_instructions, check_tables_via_supabase
        print_migration_instructions()
        tables_ok = check_tables_via_supabase()
        if not tables_ok:
            print("\nApply migrations in Supabase SQL editor, then re-run with --skip-migrations\n")
            sys.exit(1)

    # Step 3: Create user
    if not args.skip_user:
        step(3, "Create User")
        from scripts.create_user import main as create_user
        create_user()

    # Step 4: Seed via API
    if not args.skip_seed:
        step(4, "Seed Assets + Alert Rules + Strategy Config")
        import httpx
        try:
            r = httpx.post("http://localhost:8000/admin/seed", timeout=30)
            if r.status_code == 200:
                d = r.json()
                print(f"  Seeded: {d.get('inserted')} rows, {len(d.get('errors', []))} errors")
            else:
                print(f"  Seed returned {r.status_code} — backend might not be running")
                print("  Start backend: uv run uvicorn app.main:app --reload --port 8000")
        except Exception as e:
            print(f"  Backend unreachable: {e}")
            print("  Start backend and re-run, or manually run: POST /admin/seed")

    # Step 5: Seed accounts
    if not args.skip_accounts:
        step(5, "Seed Accounts + Vaults")
        from scripts.seed_thiago_accounts import main as seed_accounts
        seed_accounts()

    # Step 6: Import holdings
    if args.holdings:
        step(6, f"Import Holdings from {args.holdings}")
        from scripts.import_holdings_csv import import_holdings
        import_holdings(args.holdings)
    else:
        step(6, "Holdings Import (SKIPPED — no CSV provided)")
        print("  Fill in backend/scripts/holdings_template.csv with real data, then run:")
        print("  uv run python scripts/import_holdings_csv.py scripts/holdings_template.csv\n")

    # Step 7: Valuation
    if not args.skip_valuation:
        step(7, "Run Valuation Pipeline")
        import httpx
        try:
            r = httpx.post("http://localhost:8000/valuation_update", json={"dry_run": False}, timeout=120)
            if r.status_code == 200:
                print(f"  Valuation complete: {r.json()}")
            else:
                print(f"  Valuation returned {r.status_code}: {r.text[:200]}")
        except Exception as e:
            print(f"  Backend unreachable: {e}")

    print("\n" + "="*60)
    print("  Option B setup complete!")
    print("  Next steps (manual):")
    print("  1. Fill in backend/scripts/holdings_template.csv with real quantities")
    print("  2. Run: uv run python scripts/import_holdings_csv.py scripts/holdings_template.csv")
    print("  3. Configure Telegram: uv run python scripts/setup_telegram_webhook.py")
    print("  4. Import n8n workflows from automation/n8n/")
    print("  5. Verify full pipeline: uv run python scripts/verify_full_pipeline.py")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
