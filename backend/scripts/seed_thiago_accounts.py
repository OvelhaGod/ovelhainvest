"""
Item 5 — Seed Thiago's account structure + SoFi vaults.
Run: cd backend && uv run python scripts/seed_thiago_accounts.py

Requires DEFAULT_USER_ID to be set in .env (run create_user.py first).
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.db.supabase_client import get_supabase_client
from app.config import get_settings

ACCOUNTS = [
    {"name": "Thiago 401k",     "broker": "Empower",    "account_type": "401k",    "tax_treatment": "tax_deferred",   "currency": "USD"},
    {"name": "Spouse 401k",     "broker": "Principal",  "account_type": "401k",    "tax_treatment": "tax_deferred",   "currency": "USD"},
    {"name": "Thiago Roth IRA", "broker": "M1 Finance", "account_type": "Roth_IRA","tax_treatment": "tax_free",       "currency": "USD"},
    {"name": "M1 Taxable",      "broker": "M1 Finance", "account_type": "Taxable", "tax_treatment": "taxable",        "currency": "USD"},
    {"name": "Binance US",      "broker": "Binance US", "account_type": "Crypto",  "tax_treatment": "taxable",        "currency": "USD"},
    {"name": "Clear Corretora", "broker": "Clear",      "account_type": "Taxable", "tax_treatment": "brazil_taxable", "currency": "BRL"},
    {"name": "SoFi Checking",   "broker": "SoFi",       "account_type": "Bank",    "tax_treatment": "bank",           "currency": "USD"},
]

VAULTS = [
    {"vault_type": "future_investments", "min_balance": 500,   "max_balance": None},
    {"vault_type": "opportunity",        "min_balance": 1000,  "max_balance": None},
    {"vault_type": "emergency",          "min_balance": None,  "max_balance": None},
]


def main():
    settings = get_settings()
    if not settings.supabase_configured:
        print("ERROR: SUPABASE_SERVICE_KEY not set. Fill in backend/.env first.")
        sys.exit(1)
    if not settings.default_user_id:
        print("ERROR: DEFAULT_USER_ID not set. Run create_user.py first.")
        sys.exit(1)

    client = get_supabase_client()
    USER_ID = settings.default_user_id
    print(f"\nSeeding accounts for user: {USER_ID}\n")

    for account in ACCOUNTS:
        existing = (
            client.table("accounts")
            .select("id")
            .eq("user_id", USER_ID)
            .eq("name", account["name"])
            .execute()
        )
        if existing.data:
            account_id = existing.data[0]["id"]
            print(f"  EXISTS   {account['name']} ({account_id})")
        else:
            result = client.table("accounts").insert({**account, "user_id": USER_ID}).execute()
            account_id = result.data[0]["id"]
            print(f"  CREATED  {account['name']} ({account_id})")

        # Create vaults for SoFi Checking
        if account["name"] == "SoFi Checking":
            for vault in VAULTS:
                v_existing = (
                    client.table("vaults")
                    .select("id")
                    .eq("account_id", account_id)
                    .eq("vault_type", vault["vault_type"])
                    .execute()
                )
                if not v_existing.data:
                    client.table("vaults").insert({**vault, "account_id": account_id}).execute()
                    print(f"    VAULT   {vault['vault_type']}")
                else:
                    print(f"    VAULT   {vault['vault_type']} (exists)")

    print("\nAccounts seeded successfully.")
    print("Next step: fill in holdings_template.csv and run import_holdings_csv.py\n")


if __name__ == "__main__":
    main()
