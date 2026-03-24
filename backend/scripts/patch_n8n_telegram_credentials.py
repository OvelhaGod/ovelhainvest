"""
Create Telegram credential in n8n and patch all workflow Telegram nodes with it.
Run: cd backend && uv run python scripts/patch_n8n_telegram_credentials.py
"""
import json
import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

N8N_URL = "http://10.0.0.201:5678"
EMAIL = "thiago@ovelha.us"
PASSWORD = "OvelhaInvest2024!"
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

if not TELEGRAM_BOT_TOKEN:
    print("ERROR: TELEGRAM_BOT_TOKEN not set in .env")
    sys.exit(1)


def login() -> dict:
    r = requests.post(
        f"{N8N_URL}/rest/login",
        json={"emailOrLdapLoginId": EMAIL, "password": PASSWORD},
    )
    cookie = r.cookies.get("n8n-auth")
    if not cookie:
        print(f"Login failed: {r.status_code} {r.text[:200]}")
        sys.exit(1)
    print(f"Login OK — {r.json().get('data', {}).get('email', '?')}")
    return {"n8n-auth": cookie}


def get_or_create_telegram_credential(cookies: dict) -> str:
    """Return ID of existing or newly created telegramApi credential."""
    # Check existing credentials
    r = requests.get(f"{N8N_URL}/rest/credentials", cookies=cookies)
    creds = r.json()
    if isinstance(creds, dict):
        creds = creds.get("data", [])

    for cred in creds:
        if cred.get("type") == "telegramApi":
            cred_id = cred.get("id")
            print(f"  Found existing telegramApi credential: ID={cred_id} name={cred.get('name')}")
            # Update the token in case it changed
            patch_r = requests.patch(
                f"{N8N_URL}/rest/credentials/{cred_id}",
                json={"data": {"accessToken": TELEGRAM_BOT_TOKEN}},
                cookies=cookies,
                headers={"Content-Type": "application/json"},
            )
            if patch_r.status_code in (200, 201):
                print(f"  Updated token on existing credential")
            return str(cred_id)

    # Create new credential
    payload = {
        "name": "OvelhaInvest Telegram",
        "type": "telegramApi",
        "data": {"accessToken": TELEGRAM_BOT_TOKEN},
    }
    r = requests.post(
        f"{N8N_URL}/rest/credentials",
        json=payload,
        cookies=cookies,
        headers={"Content-Type": "application/json"},
    )
    if r.status_code not in (200, 201):
        print(f"  Failed to create credential: {r.status_code} {r.text[:200]}")
        sys.exit(1)
    resp_data = r.json()
    if isinstance(resp_data, dict) and "data" in resp_data:
        resp_data = resp_data["data"]
    cred_id = str(resp_data.get("id", "?"))
    print(f"  Created telegramApi credential: ID={cred_id}")
    return cred_id


def patch_telegram_nodes_in_workflow(cookies: dict, wf_id: str, wf_name: str, cred_id: str) -> int:
    """Patch all Telegram nodes in a workflow to use the given credential ID."""
    r = requests.get(f"{N8N_URL}/rest/workflows/{wf_id}", cookies=cookies)
    if r.status_code != 200:
        print(f"  Could not fetch workflow {wf_id}: {r.status_code}")
        return 0

    wf_data = r.json()
    if isinstance(wf_data, dict) and "data" in wf_data:
        wf_data = wf_data["data"]

    nodes = wf_data.get("nodes", [])
    patched = 0
    for node in nodes:
        node_type = node.get("type", "")
        if "telegram" in node_type.lower():
            # Set credential on the node
            if "credentials" not in node:
                node["credentials"] = {}
            node["credentials"]["telegramApi"] = {
                "id": cred_id,
                "name": "OvelhaInvest Telegram",
            }
            # Also update chat_id in parameters if it references the env placeholder
            params = node.get("parameters", {})
            if params.get("chatId") in ("", "{TELEGRAM_CHAT_ID}", None):
                params["chatId"] = TELEGRAM_CHAT_ID
                node["parameters"] = params
            patched += 1

    if patched == 0:
        return 0

    # Push updated workflow
    update_r = requests.patch(
        f"{N8N_URL}/rest/workflows/{wf_id}",
        json={"nodes": nodes},
        cookies=cookies,
        headers={"Content-Type": "application/json"},
    )
    if update_r.status_code in (200, 201):
        print(f"  Patched {patched} Telegram node(s) in '{wf_name}'")
    else:
        print(f"  Patch failed for '{wf_name}': {update_r.status_code} {update_r.text[:100]}")
    return patched


def main():
    print(f"=== n8n Telegram Credential Setup ===")
    print(f"Bot token: ...{TELEGRAM_BOT_TOKEN[-8:]}")
    print(f"Chat ID: {TELEGRAM_CHAT_ID}\n")

    cookies = login()

    print("\n1. Creating/updating Telegram credential...")
    cred_id = get_or_create_telegram_credential(cookies)

    print("\n2. Patching all workflows with Telegram nodes...")
    r = requests.get(f"{N8N_URL}/rest/workflows", cookies=cookies)
    wfs_data = r.json()
    if isinstance(wfs_data, dict):
        wfs_data = wfs_data.get("data", [])

    total_patched = 0
    for wf in wfs_data:
        wf_id = str(wf.get("id", ""))
        wf_name = wf.get("name", "?")
        n = patch_telegram_nodes_in_workflow(cookies, wf_id, wf_name, cred_id)
        total_patched += n

    if total_patched == 0:
        print("  No Telegram nodes found to patch (already configured or none present)")
    else:
        print(f"\n  Total nodes patched: {total_patched}")

    print("\n3. Sending test message via Telegram API...")
    test_r = requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
        json={"chat_id": TELEGRAM_CHAT_ID, "text": "OvelhaInvest n8n credentials configured ✓"},
    )
    if test_r.status_code == 200:
        print(f"  Test message sent OK (message_id={test_r.json().get('result', {}).get('message_id')})")
    else:
        print(f"  Test message failed: {test_r.status_code} {test_r.text[:100]}")

    print(f"\nDone. Telegram credential ID: {cred_id}")


if __name__ == "__main__":
    main()
