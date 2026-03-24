"""
Import all OvelhaInvest workflows into n8n via the internal REST API.
Uses email/password auth since the public API key uses JWT in n8n 2.x.

Run on the n8n host: python3 n8n_import.py
"""
import json
import glob
import os
import sys
import requests

N8N_URL = "http://localhost:5678"
EMAIL = "thiago@ovelha.us"
PASSWORD = "OvelhaInvest2024!"
WORKFLOW_DIR = "/tmp/n8n_workflows"

def login():
    """Log in and return session cookie string."""
    r = requests.post(
        f"{N8N_URL}/rest/login",
        json={"emailOrLdapLoginId": EMAIL, "password": PASSWORD},
    )
    if r.status_code != 200:
        print(f"Login failed: {r.status_code} {r.text[:200]}")
        sys.exit(1)
    cookie = r.cookies.get("n8n-auth")
    if not cookie:
        print(f"No auth cookie in response. Cookies: {dict(r.cookies)}")
        sys.exit(1)
    print(f"Login OK — user: {r.json().get('data',{}).get('email','unknown')}")
    return {"n8n-auth": cookie}


def create_workflow(cookies, workflow_data):
    """Create a workflow via the internal REST API."""
    # The internal API uses /rest/workflows
    r = requests.post(
        f"{N8N_URL}/rest/workflows",
        json=workflow_data,
        cookies=cookies,
        headers={"Content-Type": "application/json"},
    )
    return r


def activate_workflow(cookies, workflow_id):
    """Activate a workflow."""
    r = requests.patch(
        f"{N8N_URL}/rest/workflows/{workflow_id}",
        json={"active": True},
        cookies=cookies,
        headers={"Content-Type": "application/json"},
    )
    return r


def list_existing(cookies):
    """List all existing workflows."""
    r = requests.get(f"{N8N_URL}/rest/workflows", cookies=cookies)
    data = r.json()
    if isinstance(data, dict):
        return data.get("data", [])
    return data if isinstance(data, list) else []


def main():
    cookies = login()

    existing = list_existing(cookies)
    existing_names = {w.get("name") for w in existing}
    print(f"Existing workflows: {existing_names or 'none'}\n")

    workflow_files = sorted(glob.glob(os.path.join(WORKFLOW_DIR, "*_configured.json")))
    if not workflow_files:
        print(f"No configured workflow files found in {WORKFLOW_DIR}")
        sys.exit(1)

    results = []
    for filepath in workflow_files:
        with open(filepath, encoding="utf-8") as f:
            wf_data = json.load(f)

        name = wf_data.get("name", "unknown")
        print(f"Importing: {name}")

        if name in existing_names:
            print(f"  SKIP — already exists")
            continue

        # Strip id/createdAt/updatedAt to let n8n assign new ones
        for key in ("id", "createdAt", "updatedAt", "versionId"):
            wf_data.pop(key, None)

        resp = create_workflow(cookies, wf_data)

        if resp.status_code in (200, 201):
            wf = resp.json()
            if isinstance(wf, dict) and "data" in wf:
                wf = wf["data"]
            wf_id = wf.get("id", "?")
            print(f"  Created: ID={wf_id}")

            # Activate
            act_resp = activate_workflow(cookies, wf_id)
            if act_resp.status_code in (200, 201):
                act_data = act_resp.json()
                if isinstance(act_data, dict) and "data" in act_data:
                    act_data = act_data["data"]
                is_active = act_data.get("active", False)
                print(f"  Active: {is_active}")
                results.append({"name": name, "id": wf_id, "active": is_active})
            else:
                print(f"  Activate failed: {act_resp.status_code} {act_resp.text[:100]}")
                results.append({"name": name, "id": wf_id, "active": False})
        else:
            print(f"  Import failed: {resp.status_code} {resp.text[:200]}")
            results.append({"name": name, "id": None, "active": False})

    print("\n=== IMPORT SUMMARY ===")
    # Re-list all workflows
    all_wfs = list_existing(cookies)
    print(f"Total workflows in n8n: {len(all_wfs)}")
    for w in all_wfs:
        status = "ACTIVE  " if w.get("active") else "INACTIVE"
        print(f"  [{status}] [{w.get('id','?')}] {w.get('name','?')}")

    return results


if __name__ == "__main__":
    main()
