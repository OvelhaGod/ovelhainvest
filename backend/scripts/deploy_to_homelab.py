"""
Deploy OvelhaInvest FastAPI backend to homelab devbox (10.0.0.201).

What this does:
1. Rsync backend code to devbox at /opt/docker/ovelhainvest/
2. Copy .env file (if not already present)
3. Build Docker image on devbox
4. Start/restart the container
5. Add Cloudflare tunnel route: invest.ovelha.us -> http://10.0.0.201:8000
6. Verify /health endpoint responds

Prerequisites:
- SSH key at ~/.ssh/id_ed25519 authorized on 10.0.0.201
- Docker running on 10.0.0.201
- .env file at backend/.env

Run: cd backend && uv run python scripts/deploy_to_homelab.py
"""
import os
import sys
import subprocess
import time
import requests
import paramiko

HOST = "10.0.0.201"
USER = "thiago"
KEY_PATH = os.path.expanduser("~/.ssh/id_ed25519")
REMOTE_DIR = "/opt/docker/ovelhainvest"
LOCAL_BACKEND = os.path.join(os.path.dirname(__file__), "..")
LOCAL_ROOT = os.path.join(LOCAL_BACKEND, "..")

CLOUDFLARE_TUNNEL_ID = "4a869af2-a72d-4b92-9d0a-0de7aa92de20"
NEW_HOSTNAME = "invest.ovelha.us"
BACKEND_PORT = 8000


def ssh_connect() -> paramiko.SSHClient:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    key = paramiko.Ed25519Key.from_private_key_file(KEY_PATH)
    client.connect(HOST, username=USER, pkey=key, timeout=15)
    return client


def run_remote(client: paramiko.SSHClient, cmd: str, timeout: int = 120) -> tuple[int, str, str]:
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    exit_code = stdout.channel.recv_exit_status()
    return exit_code, stdout.read().decode(errors="replace"), stderr.read().decode(errors="replace")


def step(msg: str) -> None:
    print(f"\n[*] {msg}")


def ok(msg: str) -> None:
    print(f"    OK: {msg}")


def fail(msg: str) -> None:
    print(f"    FAIL: {msg}")
    sys.exit(1)


def main():
    print("=== OvelhaInvest Homelab Deployment ===\n")
    print(f"Target: {USER}@{HOST}:{REMOTE_DIR}")
    print(f"New URL: https://{NEW_HOSTNAME}\n")

    client = ssh_connect()
    ok(f"SSH connected to {HOST}")

    # Step 1 — Create remote directory
    step("Creating remote directory...")
    code, out, err = run_remote(client, f"mkdir -p {REMOTE_DIR}/backend/app {REMOTE_DIR}/backend/scripts")
    ok(f"Directory ready: {REMOTE_DIR}")

    # Step 2 — Rsync backend code using SSH
    step("Syncing backend code to devbox...")
    rsync_cmd = [
        "rsync", "-az", "--delete",
        "--exclude", "__pycache__",
        "--exclude", "*.pyc",
        "--exclude", ".venv",
        "--exclude", "*.egg-info",
        "-e", f"ssh -i {KEY_PATH} -o StrictHostKeyChecking=no",
        f"{LOCAL_BACKEND}/app/",
        f"{USER}@{HOST}:{REMOTE_DIR}/backend/app/",
    ]
    result = subprocess.run(rsync_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        fail(f"rsync failed: {result.stderr[:200]}")
    ok("App code synced")

    # Sync pyproject.toml, uv.lock, Dockerfile
    for fname in ["pyproject.toml", "uv.lock", "Dockerfile"]:
        rsync_cmd = [
            "rsync", "-az",
            "-e", f"ssh -i {KEY_PATH} -o StrictHostKeyChecking=no",
            f"{LOCAL_BACKEND}/{fname}",
            f"{USER}@{HOST}:{REMOTE_DIR}/backend/{fname}",
        ]
        result = subprocess.run(rsync_cmd, capture_output=True, text=True)
        if result.returncode == 0:
            ok(f"Synced {fname}")
        else:
            fail(f"rsync {fname} failed: {result.stderr[:100]}")

    # Sync docker-compose
    rsync_cmd = [
        "rsync", "-az",
        "-e", f"ssh -i {KEY_PATH} -o StrictHostKeyChecking=no",
        f"{LOCAL_ROOT}/docker-compose.homelab.yml",
        f"{USER}@{HOST}:{REMOTE_DIR}/docker-compose.yml",
    ]
    result = subprocess.run(rsync_cmd, capture_output=True, text=True)
    if result.returncode == 0:
        ok("Synced docker-compose.yml")
    else:
        fail(f"rsync docker-compose failed: {result.stderr[:100]}")

    # Step 3 — Copy .env if not present
    step("Checking .env on devbox...")
    code, out, err = run_remote(client, f"test -f {REMOTE_DIR}/backend/.env && echo exists || echo missing")
    if "missing" in out:
        print("  .env not found on devbox — copying from local...")
        env_path = os.path.join(LOCAL_BACKEND, ".env")
        if not os.path.exists(env_path):
            fail("backend/.env not found locally")
        sftp = client.open_sftp()
        sftp.put(env_path, f"{REMOTE_DIR}/backend/.env")
        sftp.close()
        ok(".env copied to devbox")
    else:
        ok(".env already present on devbox")

    # Step 4 — Build Docker image
    step("Building Docker image on devbox...")
    code, out, err = run_remote(
        client,
        f"cd {REMOTE_DIR} && docker build -t ovelhainvest-api ./backend/ 2>&1 | tail -5",
        timeout=300,
    )
    if code != 0:
        fail(f"Docker build failed:\n{out}\n{err}")
    ok("Docker image built")

    # Step 5 — Start/restart container
    step("Starting ovelhainvest-api container...")
    run_remote(client, "docker stop ovelhainvest-api 2>/dev/null; docker rm ovelhainvest-api 2>/dev/null")
    code, out, err = run_remote(
        client,
        f"cd {REMOTE_DIR} && docker compose up -d",
        timeout=60,
    )
    if code != 0:
        fail(f"docker compose up failed:\n{out}\n{err}")
    ok("Container started")

    time.sleep(5)
    code, out, err = run_remote(client, 'docker ps --filter name=ovelhainvest-api --format "{{.Names}} {{.Status}}"')
    ok(f"Container status: {out.strip()}")

    # Step 6 — Verify /health locally on devbox
    step("Verifying /health on devbox (localhost:8000)...")
    code, out, err = run_remote(client, f"wget -qO- http://localhost:{BACKEND_PORT}/health 2>&1 | head -2")
    if '"status"' in out:
        ok(f"Health check: {out.strip()[:100]}")
    else:
        fail(f"Health check failed: {out}{err}")

    # Step 7 — Configure Cloudflare tunnel route
    step(f"Adding Cloudflare tunnel route: {NEW_HOSTNAME} -> http://localhost:{BACKEND_PORT}...")
    print(f"\n  MANUAL STEP REQUIRED:")
    print(f"  Go to: https://one.dash.cloudflare.com/")
    print(f"  Navigate: Zero Trust -> Networks -> Tunnels -> homelab-tunnel -> Edit")
    print(f"  Add public hostname:")
    print(f"    Subdomain: invest")
    print(f"    Domain: ovelha.us")
    print(f"    Service: HTTP -> 10.0.0.201:{BACKEND_PORT}")
    print(f"\n  OR use Cloudflare API (requires CF_API_TOKEN env var).")

    cf_token = os.getenv("CF_API_TOKEN")
    cf_account = os.getenv("CF_ACCOUNT_ID")
    if cf_token and cf_account:
        print("\n  CF_API_TOKEN found — attempting API route creation...")
        # Add ingress rule via Cloudflare Tunnel Config API
        config_url = f"https://api.cloudflare.com/client/v4/accounts/{cf_account}/cfd_tunnel/{CLOUDFLARE_TUNNEL_ID}/configurations"
        r = requests.get(config_url, headers={"Authorization": f"Bearer {cf_token}"})
        if r.status_code == 200:
            config = r.json().get("result", {})
            ingress = config.get("config", {}).get("ingress", [])
            # Check if already present
            existing = [i for i in ingress if i.get("hostname") == NEW_HOSTNAME]
            if not existing:
                # Insert before the catch-all rule
                new_rule = {
                    "hostname": NEW_HOSTNAME,
                    "service": f"http://10.0.0.201:{BACKEND_PORT}",
                }
                # Find catch-all (no hostname) and insert before it
                catch_all_idx = next((i for i, r in enumerate(ingress) if not r.get("hostname")), len(ingress))
                ingress.insert(catch_all_idx, new_rule)
                config.setdefault("config", {})["ingress"] = ingress
                put_r = requests.put(
                    config_url,
                    headers={"Authorization": f"Bearer {cf_token}", "Content-Type": "application/json"},
                    json=config,
                )
                if put_r.status_code == 200:
                    ok(f"Route added: {NEW_HOSTNAME} -> http://10.0.0.201:{BACKEND_PORT}")
                else:
                    print(f"  Route add failed: {put_r.status_code} {put_r.text[:200]}")
            else:
                ok(f"Route {NEW_HOSTNAME} already exists in tunnel config")
        else:
            print(f"  Could not fetch tunnel config: {r.status_code}")

    print(f"\n=== Deployment Complete ===")
    print(f"  Backend API: http://{HOST}:{BACKEND_PORT}")
    print(f"  Public URL (after CF route): https://{NEW_HOSTNAME}")
    print(f"\n  Next: Update APP_BASE_URL in .env to https://{NEW_HOSTNAME}")
    print(f"  Then run: uv run python scripts/patch_n8n_telegram_credentials.py")
    print(f"  And run:  (the $vars patcher script) to update n8n workflow URLs")

    client.close()


if __name__ == "__main__":
    main()
