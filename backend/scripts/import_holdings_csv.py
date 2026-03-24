"""
Item 6 — Import holdings from CSV.
Usage: cd backend && uv run python scripts/import_holdings_csv.py scripts/holdings_template.csv

CSV format (headers required):
  account_name,symbol,quantity,avg_cost_basis

Example:
  account_name,symbol,quantity,avg_cost_basis
  Thiago Roth IRA,VTI,45.234,198.50
  M1 Taxable,VXUS,120.000,52.30
  Binance US,BTC,0.125,38000.00

- quantity: decimal shares (e.g. 0.125 for BTC)
- avg_cost_basis: your average purchase price per unit in account currency
- Leave avg_cost_basis blank if unknown (it will be fetched from yfinance as current price)
"""
import csv
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.db.supabase_client import get_supabase_client
from app.config import get_settings


def import_holdings(csv_path: str):
    settings = get_settings()
    if not settings.supabase_configured:
        print("ERROR: SUPABASE_SERVICE_KEY not set.")
        sys.exit(1)
    if not settings.default_user_id:
        print("ERROR: DEFAULT_USER_ID not set. Run create_user.py first.")
        sys.exit(1)

    client = get_supabase_client()
    USER_ID = settings.default_user_id

    # Build lookup maps
    accounts_resp = client.table("accounts").select("id,name").eq("user_id", USER_ID).execute()
    accounts = {a["name"]: a["id"] for a in accounts_resp.data}

    assets_resp = client.table("assets").select("id,symbol").execute()
    assets = {a["symbol"]: a["id"] for a in assets_resp.data}

    print(f"\nImporting from: {csv_path}")
    print(f"Known accounts: {list(accounts.keys())}")
    print(f"Known assets:   {list(assets.keys())}\n")

    imported, skipped, updated = 0, 0, 0
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            account_name = row.get("account_name", "").strip()
            symbol = row.get("symbol", "").strip().upper()
            quantity_str = row.get("quantity", "0").strip()
            cost_str = row.get("avg_cost_basis", "").strip()

            account_id = accounts.get(account_name)
            asset_id = assets.get(symbol)

            if not account_id:
                print(f"  SKIP  unknown account: '{account_name}'")
                skipped += 1
                continue
            if not asset_id:
                print(f"  SKIP  unknown asset: '{symbol}' (add to assets table or run seed first)")
                skipped += 1
                continue

            try:
                quantity = float(quantity_str) if quantity_str else 0.0
                cost_basis = float(cost_str) if cost_str else None
            except ValueError:
                print(f"  SKIP  invalid number in row: {row}")
                skipped += 1
                continue

            data = {
                "account_id": account_id,
                "asset_id": asset_id,
                "quantity": quantity,
            }
            if cost_basis is not None:
                data["avg_cost_basis"] = cost_basis

            existing = (
                client.table("holdings")
                .select("id")
                .eq("account_id", account_id)
                .eq("asset_id", asset_id)
                .execute()
            )

            if existing.data:
                client.table("holdings").update(data).eq("id", existing.data[0]["id"]).execute()
                print(f"  UPDATED  {account_name} — {symbol} x{quantity} @ {cost_basis or '?'}")
                updated += 1
            else:
                client.table("holdings").insert(data).execute()
                print(f"  INSERTED {account_name} — {symbol} x{quantity} @ {cost_basis or '?'}")
                imported += 1

    print(f"\nDone: {imported} inserted, {updated} updated, {skipped} skipped")
    print("Run the valuation pipeline to compute scores: POST /valuation_update\n")


if __name__ == "__main__":
    csv_path = sys.argv[1] if len(sys.argv) > 1 else "scripts/holdings_template.csv"
    import_holdings(csv_path)
