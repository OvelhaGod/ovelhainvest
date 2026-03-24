"""
Manually trigger n8n workflows and verify execution + Telegram delivery.
Run: cd backend && uv run python scripts/test_n8n_workflows.py
"""
import json
import time
import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

N8N_URL = "http://10.0.0.201:5678"
EMAIL = "thiago@ovelha.us"
PASSWORD = "OvelhaInvest2024!"

# API URL as seen from n8n Docker container (internal homelab network)
# n8n on 10.0.0.201 calls the backend. On Windows devbox: 10.0.0.X:8000
# Check what URL the workflows are using
APP_BASE_URL = os.getenv("APP_BASE_URL", "https://ovelhainvest.ovelha.us")


def login() -> dict:
    r = requests.post(
        f"{N8N_URL}/rest/login",
        json={"emailOrLdapLoginId": EMAIL, "password": PASSWORD},
    )
    cookie = r.cookies.get("n8n-auth")
    if not cookie:
        print(f"Login failed: {r.status_code} {r.text[:200]}")
        sys.exit(1)
    return {"n8n-auth": cookie}


def list_workflows(cookies: dict) -> list:
    r = requests.get(f"{N8N_URL}/rest/workflows", cookies=cookies)
    data = r.json()
    return data.get("data", data) if isinstance(data, dict) else data


def get_workflow_details(cookies: dict, wf_id: str) -> dict:
    r = requests.get(f"{N8N_URL}/rest/workflows/{wf_id}", cookies=cookies)
    data = r.json()
    return data.get("data", data) if isinstance(data, dict) else data


def trigger_workflow(cookies: dict, wf_id: str) -> dict | None:
    """Trigger a workflow manually via the test endpoint."""
    r = requests.post(
        f"{N8N_URL}/rest/workflows/{wf_id}/run",
        json={},
        cookies=cookies,
        headers={"Content-Type": "application/json"},
    )
    if r.status_code in (200, 201):
        return r.json()
    print(f"  Trigger failed: {r.status_code} {r.text[:200]}")
    return None


def get_executions(cookies: dict, wf_id: str, limit: int = 5) -> list:
    r = requests.get(
        f"{N8N_URL}/rest/executions?workflowId={wf_id}&limit={limit}",
        cookies=cookies,
    )
    data = r.json()
    if isinstance(data, dict):
        return data.get("data", [])
    return data or []


def check_http_nodes(wf_data: dict) -> list[dict]:
    """Return all HTTP Request nodes and their URLs."""
    nodes = wf_data.get("nodes", [])
    http_nodes = []
    for node in nodes:
        if "httpRequest" in node.get("type", "").lower() or "http" in node.get("name", "").lower():
            params = node.get("parameters", {})
            url = params.get("url", params.get("url", ""))
            http_nodes.append({"name": node["name"], "url": url})
    return http_nodes


def main():
    print(f"=== n8n Workflow End-to-End Test ===\n")
    cookies = login()
    print("Login OK\n")

    workflows = list_workflows(cookies)
    print(f"Found {len(workflows)} workflows:\n")

    # Show all workflows + HTTP node URLs
    daily_check_id = None
    for wf in workflows:
        wf_id = str(wf.get("id", ""))
        name = wf.get("name", "?")
        active = wf.get("active", False)
        print(f"  {'ACTIVE  ' if active else 'INACTIVE'} [{wf_id}] {name}")

        # Check HTTP Request nodes
        details = get_workflow_details(cookies, wf_id)
        http_nodes = check_http_nodes(details)
        for hn in http_nodes:
            print(f"    HTTP: {hn['name']} -> {hn['url'][:80]}")

        if "Daily Check" in name:
            daily_check_id = wf_id

    print(f"\n--- Testing Daily Check workflow ---")
    if not daily_check_id:
        print("ERROR: Daily Check workflow not found")
        return

    # Check most recent executions first
    print(f"\nRecent executions for Daily Check ({daily_check_id}):")
    execs = get_executions(cookies, daily_check_id, limit=3)
    if execs:
        for ex in execs:
            status = ex.get("status", "?")
            started = ex.get("startedAt", "?")
            finished = ex.get("stoppedAt", "?")
            print(f"  [{status}] started={started} finished={finished}")
    else:
        print("  No executions yet")

    print(f"\nTriggering Daily Check manually...")
    result = trigger_workflow(cookies, daily_check_id)
    if result:
        run_id = result.get("data", {}).get("executionId") if isinstance(result.get("data"), dict) else result.get("executionId")
        print(f"  Triggered OK — executionId={run_id}")

        print("  Waiting 15s for execution to complete...")
        time.sleep(15)

        # Check latest execution
        execs = get_executions(cookies, daily_check_id, limit=1)
        if execs:
            ex = execs[0]
            status = ex.get("status", "?")
            print(f"  Latest execution status: {status}")
            if status == "error":
                # Get error details
                r = requests.get(
                    f"{N8N_URL}/rest/executions/{ex['id']}",
                    cookies=cookies,
                )
                ex_data = r.json()
                if isinstance(ex_data, dict) and "data" in ex_data:
                    ex_data = ex_data["data"]
                data_field = ex_data.get("data", {})
                if isinstance(data_field, dict):
                    result_data = data_field.get("resultData", {})
                    error = result_data.get("error", {})
                    print(f"  Error: {json.dumps(error, indent=2)[:500]}")
        else:
            print("  Could not retrieve execution status")
    else:
        print("  Trigger returned no data")

    print("\n=== Done ===")


if __name__ == "__main__":
    main()
