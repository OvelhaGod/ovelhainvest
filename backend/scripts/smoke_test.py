"""
API smoke test — verifies all key endpoints return 200.
Run: cd backend && uv run python scripts/smoke_test.py
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

BASE = "http://localhost:8000"
USER_ID = os.getenv("DEFAULT_USER_ID", "")
USER_PARAM = f"?user_id={USER_ID}" if USER_ID else ""

tests = [
    ("Health",               f"{BASE}/health",                                    None),
    ("Daily Status",         f"{BASE}/daily_status{USER_PARAM}",                  None),
    ("Valuation Summary",    f"{BASE}/valuation_summary",                          None),
    ("Performance Summary",  f"{BASE}/performance/summary{USER_PARAM}&period=ytd", None),
    ("Tax Estimate",         f"{BASE}/tax/estimate{USER_PARAM}",                   None),
    ("Journal Stats",        f"{BASE}/journal/stats{USER_PARAM}",                  None),
    ("Alert Rules",          f"{BASE}/alerts/rules{USER_PARAM}",                   None),
]

print(f"=== Backend Smoke Test — {BASE} ===\n")
all_pass = True
for name, url, _ in tests:
    try:
        r = requests.get(url, timeout=15)
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, dict):
                keys = list(data.keys())[:5]
                print(f"  OK  {name:<25} fields: {keys}")
            elif isinstance(data, list):
                print(f"  OK  {name:<25} {len(data)} items")
            else:
                print(f"  OK  {name:<25}")
        else:
            print(f"  ERR {name:<25} HTTP {r.status_code}: {r.text[:80]}")
            all_pass = False
    except Exception as e:
        print(f"  EXC {name:<25} {e}")
        all_pass = False

print(f"\n{'All tests PASSED' if all_pass else 'Some tests FAILED'}")
