"""
Fix and activate all OvelhaInvest workflows in n8n.
- Repairs keep_alive tags format issue and imports it
- Activates all 6 workflows

Run on the n8n host: python3 n8n_activate.py
"""
import json
import os
import sys
import requests

N8N_URL = "http://localhost:5678"
EMAIL = "thiago@ovelha.us"
PASSWORD = "OvelhaInvest2024!"
WORKFLOW_DIR = "/tmp/n8n_workflows"

TARGET_IDS = {
    "OvelhaInvest \u2014 Daily Check": "ZELR7ROCwjjatA6J",
    "OvelhaInvest \u2014 Journal Outcome Backfill": "pYTlaiyU0ssQRz7a",
    "OvelhaInvest \u2014 Monthly Report Generator": "Q3tkTVTZ1FUesTbH",
    "OvelhaInvest \u2014 Opportunity Scan": "6zEPq2yw3qKyW42Q",
    "OvelhaInvest \u2014 Valuation Pipeline": "D3q8O1HFjgEGhzVB",
}


def login():
    r = requests.post(
        f"{N8N_URL}/rest/login",
        json={"emailOrLdapLoginId": EMAIL, "password": PASSWORD},
    )
    cookie = r.cookies.get("n8n-auth")
    print(f"Login: {r.json().get('data',{}).get('email','?')}")
    return {"n8n-auth": cookie}


def main():
    cookies = login()

    # Step 1: Import keep_alive with tags fixed
    ka_path = os.path.join(WORKFLOW_DIR, "keep_alive_configured.json")
    if os.path.exists(ka_path):
        with open(ka_path, encoding="utf-8") as f:
            wf_data = json.load(f)

        # Fix tags: n8n internal API expects tag name strings, not objects
        tags = wf_data.get("tags", [])
        if tags and isinstance(tags[0], dict):
            wf_data["tags"] = [t.get("name", t) if isinstance(t, dict) else t for t in tags]

        # Strip generated fields
        for key in ("id", "createdAt", "updatedAt", "versionId"):
            wf_data.pop(key, None)

        print("\nImporting: OvelhaInvest — Keep Alive (tags fixed)")
        resp = requests.post(
            f"{N8N_URL}/rest/workflows",
            json=wf_data,
            cookies=cookies,
            headers={"Content-Type": "application/json"},
        )
        if resp.status_code in (200, 201):
            wf = resp.json()
            if isinstance(wf, dict) and "data" in wf:
                wf = wf["data"]
            wf_id = wf.get("id", "?")
            TARGET_IDS["OvelhaInvest \u2014 Keep Alive"] = wf_id
            print(f"  Created: ID={wf_id}")
        else:
            print(f"  Failed: {resp.status_code} {resp.text[:200]}")

    # Step 2: Activate all workflows
    print("\n=== Activating all workflows ===")
    for name, wf_id in TARGET_IDS.items():
        if not wf_id:
            print(f"  SKIP (no ID): {name}")
            continue

        # Try PATCH to activate
        resp = requests.patch(
            f"{N8N_URL}/rest/workflows/{wf_id}",
            json={"active": True},
            cookies=cookies,
            headers={"Content-Type": "application/json"},
        )
        data = resp.json()
        if isinstance(data, dict) and "data" in data:
            data = data["data"]
        is_active = data.get("active", False) if isinstance(data, dict) else False
        print(f"  {'ACTIVE  ' if is_active else 'inactive'} [{wf_id}] {name}")

        # If PATCH didn't activate, try PUT
        if not is_active:
            resp2 = requests.put(
                f"{N8N_URL}/rest/workflows/{wf_id}/activate",
                cookies=cookies,
                headers={"Content-Type": "application/json"},
            )
            if resp2.status_code in (200, 201):
                d2 = resp2.json()
                if isinstance(d2, dict) and "data" in d2:
                    d2 = d2["data"]
                is_active = d2.get("active", False) if isinstance(d2, dict) else False
                print(f"    -> PUT activate: {'ACTIVE' if is_active else 'still inactive: '+resp2.text[:80]}")

    # Step 3: Final status
    print("\n=== Final workflow status ===")
    r = requests.get(f"{N8N_URL}/rest/workflows", cookies=cookies)
    data = r.json()
    wfs = data.get("data", data) if isinstance(data, dict) else data
    if isinstance(wfs, list):
        for w in wfs:
            status = "ACTIVE  " if w.get("active") else "INACTIVE"
            print(f"  [{status}] [{w.get('id','?')}] {w.get('name','?')}")
    else:
        print(f"List response: {str(wfs)[:200]}")


if __name__ == "__main__":
    main()
