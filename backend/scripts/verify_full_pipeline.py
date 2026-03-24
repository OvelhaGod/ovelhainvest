"""
Item 11 — Verify full run_allocation cycle end-to-end.
Run: cd backend && uv run python scripts/verify_full_pipeline.py

Requires the backend to be running on port 8000.
"""
import sys
import json
import httpx

API = "http://localhost:8000"

REQUIRED_FIELDS = [
    "proposed_trades",
    "ai_validation_summary",
    "alerts_dispatched",
    "regime_state",
    "vault_status",
    "total_value_usd",
]

def check(label: str, ok: bool, detail: str = ""):
    status = "OK   " if ok else "FAIL "
    print(f"  {status} {label}" + (f"  — {detail}" if detail else ""))
    return ok


def main():
    print("\n=== Full Pipeline Verification ===\n")
    all_ok = True

    # Health check
    try:
        r = httpx.get(f"{API}/health", timeout=5)
        all_ok &= check("GET /health", r.status_code == 200, f"status={r.json().get('status')}")
    except Exception as e:
        check("GET /health", False, f"UNREACHABLE: {e}")
        print("\nBackend is not running. Start it first:")
        print("  cd backend && uv run uvicorn app.main:app --reload --port 8000")
        sys.exit(1)

    # Admin status
    try:
        r = httpx.get(f"{API}/admin/status", timeout=5)
        all_ok &= check("GET /admin/status", r.status_code == 200)
    except Exception as e:
        all_ok &= check("GET /admin/status", False, str(e))

    # Daily status
    try:
        r = httpx.get(f"{API}/daily_status", timeout=10)
        all_ok &= check("GET /daily_status", r.status_code == 200,
                        f"etag={'ETag' in r.headers}")
        if r.status_code == 200:
            d = r.json()
            all_ok &= check(
                "  daily_status fields",
                all(k in d for k in ["total_value_usd", "sleeve_weights", "regime"]),
            )
    except Exception as e:
        all_ok &= check("GET /daily_status", False, str(e))

    # Valuation summary
    try:
        r = httpx.get(f"{API}/valuation_summary", timeout=10)
        all_ok &= check("GET /valuation_summary", r.status_code == 200)
    except Exception as e:
        all_ok &= check("GET /valuation_summary", False, str(e))

    # Run allocation
    try:
        r = httpx.post(f"{API}/run_allocation",
                       json={"event_type": "daily_check"},
                       timeout=60)
        ok = r.status_code == 200
        all_ok &= check("POST /run_allocation", ok, f"status={r.status_code}")
        if ok:
            data = r.json()
            for field in REQUIRED_FIELDS:
                all_ok &= check(f"  field: {field}", field in data)
            trades = data.get("proposed_trades", [])
            regime = data.get("regime_state", "unknown")
            ai_status = (data.get("ai_validation_summary") or {}).get("overall_status", "n/a")
            print(f"\n  regime_state:     {regime}")
            print(f"  proposed_trades:  {len(trades)}")
            print(f"  ai_status:        {ai_status}")
            if trades:
                print(f"  first_trade:      {json.dumps(trades[0], indent=4)}")
    except Exception as e:
        all_ok &= check("POST /run_allocation", False, str(e))

    # Reports list
    try:
        r = httpx.get(f"{API}/reports/list", timeout=5)
        all_ok &= check("GET /reports/list", r.status_code == 200 and isinstance(r.json(), list))
    except Exception as e:
        all_ok &= check("GET /reports/list", False, str(e))

    print(f"\n{'All checks passed.' if all_ok else 'Some checks failed — see above.'}\n")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
