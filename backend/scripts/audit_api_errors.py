"""Audit all API endpoints for errors against the live backend."""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

BASE = os.getenv("APP_BASE_URL", "https://investapi.ovelha.us")
USER_ID = os.getenv("DEFAULT_USER_ID", "")
U = f"?user_id={USER_ID}" if USER_ID else ""

ENDPOINTS = [
    ("GET",  "/health",                                None, "Health check"),
    ("GET",  f"/daily_status{U}",                      None, "Daily status"),
    ("GET",  "/valuation_summary",                     None, "Valuation summary"),
    ("GET",  f"/performance/summary{U}&period=ytd",    None, "Performance summary"),
    ("GET",  f"/performance/attribution{U}&period_start=2025-01-01&period_end=2026-03-24", None, "Performance attribution"),
    ("GET",  f"/performance/benchmark{U}&period=ytd",  None, "Benchmark comparison"),
    ("GET",  f"/performance/risk{U}",                  None, "Risk metrics"),
    ("GET",  f"/performance/rolling{U}",               None, "Rolling returns"),
    ("GET",  f"/tax/lots{U}",                          None, "Tax lots"),
    ("GET",  f"/tax/estimate{U}",                      None, "Tax estimate"),
    ("GET",  f"/tax/brazil_darf{U}",                   None, "Brazil DARF"),
    ("POST", f"/tax/harvest_candidates{U}",            {}, "Harvest candidates"),
    ("GET",  f"/alerts/rules{U}",                      None, "Alert rules"),
    ("GET",  f"/alerts/history{U}",                    None, "Alert history"),
    ("GET",  f"/journal{U}",                           None, "Journal entries"),
    ("GET",  f"/journal/stats{U}",                     None, "Journal stats"),
    ("GET",  f"/reports/list{U}",                      None, "Reports list"),
    ("GET",  f"/simulation/retirement_readiness{U}&current_age=35&target_retirement_age=60&target_monthly_income=5000", None, "Retirement readiness"),
    ("POST", f"/simulation/stress_test{U}",            {"scenario_name": "2020_covid"}, "Stress test"),
]

print(f"=== API Audit — {BASE} ===\n")
errors = []
passed = 0

for method, path, body, desc in ENDPOINTS:
    try:
        url = f"{BASE}{path}"
        if method == "GET":
            r = requests.get(url, timeout=20)
        else:
            r = requests.post(url, json=body or {}, timeout=20)

        if r.status_code == 200:
            data = r.json()
            if isinstance(data, dict) and "detail" in data and len(data) == 1:
                print(f"  WARN  {desc:<35} — returned only detail: {data['detail'][:60]}")
                errors.append((path, f"detail-only: {data['detail'][:60]}"))
            else:
                keys = list(data.keys())[:3] if isinstance(data, dict) else f"{len(data)} items"
                print(f"  OK    {desc:<35} {keys}")
                passed += 1
        else:
            try:
                detail = r.json().get("detail", r.text[:80])
            except Exception:
                detail = r.text[:80]
            print(f"  ERR   {desc:<35} — HTTP {r.status_code}: {str(detail)[:80]}")
            errors.append((path, f"HTTP {r.status_code}: {str(detail)[:80]}"))
    except Exception as exc:
        print(f"  EXC   {desc:<35} — {exc}")
        errors.append((path, str(exc)[:80]))

print(f"\n{'='*60}")
print(f"Results: {passed}/{len(ENDPOINTS)} passing")
if errors:
    print(f"\nErrors ({len(errors)}):")
    for path, err in errors:
        print(f"  {path}")
        print(f"    {err}")
