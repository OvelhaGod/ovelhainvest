"""
Insert placeholder holdings so the app shows real data before actual positions are entered.
Mock portfolio ~$50k USD — realistic quantities for demo/dev use.
Run: cd backend && uv run python scripts/insert_placeholder_holdings.py
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

url = os.getenv("SUPABASE_URL", "").rstrip("/")
key = os.getenv("SUPABASE_SERVICE_KEY", "")

if not url or not key:
    print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY required in .env")
    raise SystemExit(1)

headers = {
    "apikey": key,
    "Authorization": f"Bearer {key}",
    "Content-Type": "application/json",
    "Prefer": "return=representation",
}

# Fetch accounts and assets
accounts_r = requests.get(f"{url}/rest/v1/accounts?select=id,name", headers=headers)
accounts = {a["name"]: a["id"] for a in accounts_r.json()}
print(f"Accounts found: {list(accounts.keys())}")

assets_r = requests.get(f"{url}/rest/v1/assets?select=id,symbol", headers=headers)
assets = {a["symbol"]: a["id"] for a in assets_r.json()}
print(f"Assets found: {list(assets.keys())}\n")

# Placeholder holdings — realistic mock portfolio (~$50k total)
HOLDINGS = [
    # Thiago Roth IRA — core ETF portfolio
    ("Thiago Roth IRA", "VTI",   45.0,  198.50),   # ~$9k
    ("Thiago Roth IRA", "VXUS",  80.0,   54.20),   # ~$4.3k
    ("Thiago Roth IRA", "BND",   50.0,   74.50),   # ~$3.7k
    # M1 Taxable
    ("M1 Taxable",      "VTI",   30.0,  185.00),   # ~$5.6k
    ("M1 Taxable",      "VXUS",  60.0,   52.00),   # ~$3.1k
    ("M1 Taxable",      "VNQ",   20.0,   85.00),   # ~$1.7k
    # Thiago 401k
    ("Thiago 401k",     "VTI",   60.0,  175.00),   # ~$10.5k
    ("Thiago 401k",     "BND",   40.0,   72.00),   # ~$2.9k
    # Crypto — Binance US
    ("Binance US",      "BTC",    0.08, 42000.00),  # ~$3.4k BTC
    ("Binance US",      "ETH",    1.20,  2400.00),  # ~$2.9k ETH
    # Brazil — Clear Corretora (BRL values)
    ("Clear Corretora", "PETR4", 200.0,   28.50),   # ~R$5.7k
    ("Clear Corretora", "VALE3", 100.0,   65.00),   # ~R$6.5k
]

inserted = updated = skipped = 0

for account_name, symbol, quantity, cost_basis in HOLDINGS:
    account_id = accounts.get(account_name)
    asset_id = assets.get(symbol)

    if not account_id:
        print(f"  SKIP — account not found: {account_name}")
        skipped += 1
        continue
    if not asset_id:
        print(f"  SKIP — asset not found: {symbol}")
        skipped += 1
        continue

    existing = requests.get(
        f"{url}/rest/v1/holdings?account_id=eq.{account_id}&asset_id=eq.{asset_id}",
        headers=headers,
    ).json()

    payload = {
        "account_id": account_id,
        "asset_id": asset_id,
        "quantity": quantity,
        "avg_cost_basis": cost_basis,
    }

    if existing:
        requests.patch(
            f"{url}/rest/v1/holdings?id=eq.{existing[0]['id']}",
            headers=headers,
            json=payload,
        )
        print(f"  UPDATED:  {account_name} — {symbol} × {quantity}")
        updated += 1
    else:
        requests.post(f"{url}/rest/v1/holdings", headers=headers, json=payload)
        print(f"  INSERTED: {account_name} — {symbol} × {quantity}")
        inserted += 1

print(f"\nDone: {inserted} inserted, {updated} updated, {skipped} skipped")
print("Approximate portfolio: ~$50k USD across 12 positions")
