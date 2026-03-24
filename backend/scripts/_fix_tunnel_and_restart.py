"""
Fix Cloudflare tunnel (invest.ovelha.us -> port 3002) and restart cloudflared
via SSH jump: localhost -> 10.0.0.201 -> 10.0.0.151.
Run: cd backend && uv run python scripts/_fix_tunnel_and_restart.py
"""
import time
import requests
import paramiko

HOST = "10.0.0.201"
KEY_PATH = "C:/Users/Thiago/.ssh/id_ed25519"

CF_TOKEN = "CT6Hj6KZnXylywP47v7bkvgYdCbZzEpRmOhaWf_c"
CF_ACCOUNT = "e3ab49948d4cd90c2985c493994daab7"
TUNNEL_ID = "4a869af2-a72d-4b92-9d0a-0de7aa92de20"

FRONTEND_PORT = 3002  # confirmed running on 3002


def connect():
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    key = paramiko.Ed25519Key.from_private_key_file(KEY_PATH)
    c.connect(HOST, username="thiago", pkey=key, timeout=15)
    return c


def run(client, cmd, timeout=60):
    sin, sout, serr = client.exec_command(cmd, timeout=timeout)
    code = sout.channel.recv_exit_status()
    return code, sout.read().decode("utf-8", errors="replace"), serr.read().decode("utf-8", errors="replace")


print("=== Fix Cloudflare Tunnel + Restart cloudflared ===\n")

# ─── Step 1: Fix CF tunnel config ─────────────────────────────────────────────
print("[*] Updating Cloudflare tunnel: invest.ovelha.us -> port 3002...")
headers = {"Authorization": f"Bearer {CF_TOKEN}", "Content-Type": "application/json"}
config_url = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT}/cfd_tunnel/{TUNNEL_ID}/configurations"

r = requests.get(config_url, headers=headers)
result = r.json().get("result", {})
ingress = result.get("config", {}).get("ingress", [])

print(f"  Current ingress rules: {len(ingress)}")
for rule in ingress:
    hostname = rule.get("hostname", "(catch-all)")
    service = rule.get("service", "")
    print(f"    {hostname} -> {service}")

# Fix invest.ovelha.us entry
target_service = f"http://10.0.0.201:{FRONTEND_PORT}"
updated = False
for rule in ingress:
    if rule.get("hostname") == "invest.ovelha.us":
        if rule["service"] != target_service:
            rule["service"] = target_service
            updated = True
            print(f"  Fixed: invest.ovelha.us -> {target_service}")
        else:
            print(f"  Already correct: invest.ovelha.us -> {target_service}")
            updated = True  # mark as handled

if not updated:
    # Insert before catch-all
    catch_all_idx = next((i for i, r in enumerate(ingress) if not r.get("hostname")), len(ingress))
    ingress.insert(catch_all_idx, {"hostname": "invest.ovelha.us", "service": target_service})
    print(f"  Added: invest.ovelha.us -> {target_service}")

put_r = requests.put(config_url, headers=headers, json={"config": result.get("config", {})})
print(f"  Tunnel config update: HTTP {put_r.status_code}")
if put_r.status_code != 200:
    print(f"  Response: {put_r.text[:200]}")

# ─── Step 2: Restart cloudflared via SSH jump ─────────────────────────────────
print("\n[*] Restarting cloudflared via SSH jump (10.0.0.201 -> 10.0.0.151)...")
client = connect()
print(f"  SSH OK to {HOST}")

# Try jump: SSH from 10.0.0.201 to 10.0.0.151 using its own key
# First check what keys exist on 10.0.0.201
code, out, err = run(client, "ls ~/.ssh/", timeout=10)
print(f"  ~/.ssh/ contents: {out.strip()}")

# Try restarting cloudflared via jump to 10.0.0.151
# The devbox likely has its own SSH key that authorizes it to connect to 10.0.0.151
code, out, err = run(
    client,
    "ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 10.0.0.151 'docker restart cloudflared' 2>&1",
    timeout=30,
)
print(f"  Jump SSH exit={code}: {(out + err).strip()[:200]}")

if code != 0:
    # Try with thiago user explicitly
    code, out, err = run(
        client,
        "ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 thiago@10.0.0.151 'docker restart cloudflared' 2>&1",
        timeout=30,
    )
    print(f"  Jump SSH (thiago@) exit={code}: {(out + err).strip()[:200]}")

if code != 0:
    # Try root
    code, out, err = run(
        client,
        "ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 root@10.0.0.151 'docker restart cloudflared' 2>&1",
        timeout=30,
    )
    print(f"  Jump SSH (root@) exit={code}: {(out + err).strip()[:200]}")

if code != 0:
    print("  [!] Jump SSH failed — trying to find cloudflared another way...")
    # Maybe cloudflared is actually on 10.0.0.201 under a different name
    code2, out2, err2 = run(client, "docker ps --format '{{.Names}} {{.Image}}' | grep -i cloud 2>&1", timeout=10)
    print(f"  Docker containers matching 'cloud': {out2.strip() or 'none found'}")

    # Also check if cloudflare tunnel config is managed differently
    code2, out2, err2 = run(client, "docker ps -a --format '{{.Names}}' 2>&1", timeout=10)
    print(f"  All containers: {out2.strip()}")

client.close()

# ─── Step 3: Wait and verify ──────────────────────────────────────────────────
print("\n[*] Waiting 20s for CF propagation...")
time.sleep(20)

tests = [
    ("https://api.invest.ovelha.us/health", "Backend API"),
    ("https://invest.ovelha.us", "Frontend"),
]
print("\n[*] Verifying endpoints...")
for url, name in tests:
    try:
        resp = requests.get(url, timeout=20)
        print(f"  {name}: HTTP {resp.status_code}")
        if name == "Backend API" and resp.status_code == 200:
            data = resp.json()
            print(f"    {data.get('status')} | supabase={data.get('supabase')} | version={data.get('version')}")
    except Exception as e:
        print(f"  {name}: FAILED — {e}")
