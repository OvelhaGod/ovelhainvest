"""
Deletes all portfolio_snapshots for the default user.
Run this before re-generating retroactive snapshots with the fixed generator.
"""
import os
import sys

from dotenv import load_dotenv
import requests

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
DEFAULT_USER_ID = os.getenv("DEFAULT_USER_ID", "df6f002d-c8c0-4d03-9298-1e58e8025a35")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in .env")
    sys.exit(1)

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
}


def clean_snapshots():
    # Count first
    r = requests.get(
        f"{SUPABASE_URL}/rest/v1/portfolio_snapshots"
        f"?user_id=eq.{DEFAULT_USER_ID}&select=count",
        headers={**headers, "Prefer": "count=exact"},
    )
    count_range = r.headers.get("content-range", "0-0/0")
    total = count_range.split("/")[-1]
    print(f"Found {total} snapshots for user {DEFAULT_USER_ID}")

    if total == "0":
        print("Nothing to delete.")
        return

    # Delete all
    r_del = requests.delete(
        f"{SUPABASE_URL}/rest/v1/portfolio_snapshots"
        f"?user_id=eq.{DEFAULT_USER_ID}",
        headers={**headers, "Prefer": "return=minimal"},
    )
    if r_del.status_code in (200, 204):
        print(f"Deleted {total} snapshots successfully.")
    else:
        print(f"Delete failed: HTTP {r_del.status_code} — {r_del.text[:300]}")
        sys.exit(1)

    # Verify
    r_check = requests.get(
        f"{SUPABASE_URL}/rest/v1/portfolio_snapshots"
        f"?user_id=eq.{DEFAULT_USER_ID}&select=count",
        headers={**headers, "Prefer": "count=exact"},
    )
    remaining = r_check.headers.get("content-range", "?").split("/")[-1]
    print(f"Remaining snapshots after delete: {remaining}")


if __name__ == "__main__":
    clean_snapshots()
