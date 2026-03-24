"""
Deploy backend + frontend to homelab and configure Cloudflare tunnel.
Run: cd backend && uv run python scripts/_homelab_deploy_all.py
"""
import io
import os
import time
import requests
import paramiko
from dotenv import load_dotenv

load_dotenv()

HOST = "10.0.0.201"
KEY_PATH = "C:/Users/Thiago/.ssh/id_ed25519"
REMOTE_DIR = "/home/thiago/docker/ovelhainvest"
TOKEN = "1a077b690dbdceba3e588bcd8b97d8e2b1e5d88e"

# Cloudflare
CF_TOKEN = "CT6Hj6KZnXylywP47v7bkvgYdCbZzEpRmOhaWf_c"
CF_ACCOUNT = "e3ab49948d4cd90c2985c493994daab7"
TUNNEL_ID = "4a869af2-a72d-4b92-9d0a-0de7aa92de20"

# Env values for frontend build
SUPABASE_URL = "https://ogvonmfwtsfgbpvydlpm.supabase.co"
SUPABASE_ANON_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9n"
    "dm9ubWZ3dHNmZ2JwdnlkbHBtIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NDMxOT"
    "c0MSwiZXhwIjoyMDg5ODk1NzQxfQ.27rJ86b1doN7KMOD5BgRjOmMvU9zTJpBJYNL7u1wPHQ"
)
FRONTEND_API_URL = "https://investapi.ovelha.us"


def connect():
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    key = paramiko.Ed25519Key.from_private_key_file(KEY_PATH)
    c.connect(HOST, username="thiago", pkey=key, timeout=15)
    return c


def run(client, cmd, timeout=180):
    sin, sout, serr = client.exec_command(cmd, timeout=timeout)
    code = sout.channel.recv_exit_status()
    return code, sout.read().decode("utf-8", errors="replace"), serr.read().decode("utf-8", errors="replace")


def step(msg):
    print(f"\n[*] {msg}")


client = connect()
print(f"=== OvelhaInvest Full Homelab Deploy ===\nSSH OK to {HOST}\n")

# ─── Pull latest code ──────────────────────────────────────────────────────────
step("Pulling latest code from Gitea...")
code, out, err = run(client, f"cd {REMOTE_DIR} && git fetch && git checkout dev && git pull 2>&1", timeout=30)
print(f"  {out.strip()[-120:]}")

# ─── Copy .env ────────────────────────────────────────────────────────────────
step("Copying backend .env...")
with open("D:/python/ovelhainvest/backend/.env", "rb") as f:
    env_bytes = f.read()
sftp = client.open_sftp()
sftp.putfo(io.BytesIO(env_bytes), f"{REMOTE_DIR}/backend/.env")
sftp.close()
print("  .env OK")

# ─── Rebuild backend Docker ────────────────────────────────────────────────────
step("Rebuilding backend Docker image (CORS fix)...")
code, out, err = run(
    client,
    f"cd {REMOTE_DIR}/backend && docker build -t ovelhainvest-api . 2>&1 | tail -5",
    timeout=300,
)
print(f"  Build exit={code}: {out.strip()[-100:]}")
if code != 0:
    print("  BUILD FAILED:", err[-200:])

# Restart backend
run(client, "docker stop ovelhainvest-api 2>/dev/null; docker rm -f ovelhainvest-api 2>/dev/null")
code, out, err = run(
    client,
    f"docker run -d --name ovelhainvest-api --restart unless-stopped -p 8090:8000 "
    f"--env-file {REMOTE_DIR}/backend/.env -e APP_ENV=production ovelhainvest-api",
    timeout=20,
)
print(f"  Backend start: exit={code}")

time.sleep(8)
code, out, err = run(client, "wget -qO- http://localhost:8090/health 2>&1 | head -1")
print(f"  Backend health: {out.strip()[:120]}")

# ─── Build frontend Docker ─────────────────────────────────────────────────────
step("Building frontend Docker image (this takes ~3 min)...")
build_cmd = (
    f"cd {REMOTE_DIR} && docker build "
    f"--build-arg NEXT_PUBLIC_API_URL={FRONTEND_API_URL} "
    f"--build-arg NEXT_PUBLIC_SUPABASE_URL={SUPABASE_URL} "
    f"--build-arg NEXT_PUBLIC_SUPABASE_ANON_KEY={SUPABASE_ANON_KEY} "
    f"-t ovelhainvest-frontend ./frontend/ 2>&1 | tail -10"
)
code, out, err = run(client, build_cmd, timeout=600)
print(f"  Build exit={code}")
print(out[-400:])
if code != 0:
    print("  BUILD FAILED:", err[-200:])
    client.close()
    raise SystemExit(1)

# Find a free port for frontend (3000 might be taken by Forgejo exposed differently)
# Forgejo is on 10.0.0.201:3000 externally, but its container port 3000 is mapped
# Let's use port 3001 for frontend to avoid conflict
FRONTEND_PORT = 3001

# Check if port 3001 is taken
code, out, err = run(client, "docker ps --format '{{.Ports}}' | grep 3001 || echo free")
if "free" not in out:
    FRONTEND_PORT = 3002
    print(f"  Port 3001 taken, using 3002")

# Stop/rm old frontend
run(client, f"docker stop ovelhainvest-frontend 2>/dev/null; docker rm -f ovelhainvest-frontend 2>/dev/null")

# Start frontend
code, out, err = run(
    client,
    f"docker run -d --name ovelhainvest-frontend --restart unless-stopped "
    f"-p {FRONTEND_PORT}:3000 ovelhainvest-frontend",
    timeout=20,
)
print(f"\n  Frontend start: exit={code} {(out+err).strip()[-100:]}")

time.sleep(10)
code, out, err = run(client, f"wget -qO- http://localhost:{FRONTEND_PORT}/ 2>&1 | head -1")
print(f"  Frontend health check (HTTP status): {out.strip()[:60] or 'no response'}")

code, out, err = run(client, f"docker ps --filter name=ovelhainvest --format '{{{{.Names}}}} {{{{.Status}}}} {{{{.Ports}}}}'")
print(f"  Containers:\n    {out.strip()}")

# ─── Cloudflare tunnel routes ──────────────────────────────────────────────────
step("Updating Cloudflare tunnel routes...")
headers = {"Authorization": f"Bearer {CF_TOKEN}", "Content-Type": "application/json"}
config_url = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT}/cfd_tunnel/{TUNNEL_ID}/configurations"
zone_url = f"https://api.cloudflare.com/client/v4/zones/887843e7fe5eb42e7fa15ac8feeb908f/dns_records"

r = requests.get(config_url, headers=headers)
config = r.json().get("result", {})
ingress = config.get("config", {}).get("ingress", [])

# Define what we need:
# invest.ovelha.us → frontend (port 3001)
# api.invest.ovelha.us → backend (port 8090)
changes = {
    "invest.ovelha.us": f"http://10.0.0.201:{FRONTEND_PORT}",
    "api.invest.ovelha.us": "http://10.0.0.201:8090",
}

catch_all_idx = next((i for i, rule in enumerate(ingress) if not rule.get("hostname")), len(ingress))

for hostname, service in changes.items():
    existing_idx = next((i for i, rule in enumerate(ingress) if rule.get("hostname") == hostname), None)
    new_rule = {"hostname": hostname, "service": service}
    if existing_idx is not None:
        if ingress[existing_idx]["service"] != service:
            ingress[existing_idx]["service"] = service
            print(f"  Updated: {hostname} -> {service}")
        else:
            print(f"  Unchanged: {hostname} -> {service}")
    else:
        ingress.insert(catch_all_idx, new_rule)
        catch_all_idx += 1
        print(f"  Added: {hostname} -> {service}")

put_r = requests.put(config_url, headers=headers, json={"config": config.get("config", {})})
print(f"  Tunnel config update: {put_r.status_code}")

# Add api.invest.ovelha.us DNS record
dns_r = requests.get(f"{zone_url}?name=api.invest.ovelha.us", headers=headers)
existing_dns = dns_r.json().get("result", [])
if not existing_dns:
    create_r = requests.post(zone_url, headers=headers, json={
        "type": "CNAME",
        "name": "api.invest.ovelha.us",
        "content": f"{TUNNEL_ID}.cfargotunnel.com",
        "proxied": True,
        "ttl": 1,
    })
    if create_r.json().get("success"):
        print(f"  DNS created: api.invest.ovelha.us")
    else:
        print(f"  DNS create failed: {create_r.json()}")
else:
    print(f"  DNS already exists: api.invest.ovelha.us")

# Restart cloudflared to pick up new routes
step("Restarting cloudflared (to pick up new routes)...")
r_cf = run(client, "docker restart cloudflared 2>&1", timeout=30)
print(f"  cloudflared restart: {r_cf[0]}")

client.close()

# ─── Verify ───────────────────────────────────────────────────────────────────
step("Waiting 15s for CF propagation then verifying...")
time.sleep(15)

tests = [
    ("https://api.invest.ovelha.us/health", "Backend API"),
    ("https://invest.ovelha.us", "Frontend"),
]
for url, name in tests:
    try:
        resp = requests.get(url, timeout=20)
        print(f"  {name}: HTTP {resp.status_code}")
    except Exception as e:
        print(f"  {name}: FAILED — {e}")

print("\n=== Deploy Complete ===")
print(f"  Frontend: https://invest.ovelha.us")
print(f"  Backend API: https://api.invest.ovelha.us")
print(f"  Frontend port: {FRONTEND_PORT}")
