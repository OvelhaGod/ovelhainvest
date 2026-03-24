"""
Redeploy backend + frontend with updated API hostname (investapi.ovelha.us).
Run: cd backend && uv run python scripts/_redeploy_v123.py
"""
import io
import time
import paramiko

HOST = "10.0.0.201"
KEY_PATH = "C:/Users/Thiago/.ssh/id_ed25519"
REMOTE_DIR = "/home/thiago/docker/ovelhainvest"

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
print(f"=== OvelhaInvest v1.2.3 Redeploy ===\nSSH OK to {HOST}\n")

# Pull latest code
step("Pulling latest code...")
code, out, err = run(client, f"cd {REMOTE_DIR} && git fetch && git checkout dev && git pull 2>&1", timeout=30)
print(f"  {out.strip()[-120:]}")

# Copy .env
step("Copying backend .env...")
with open("D:/python/ovelhainvest/backend/.env", "rb") as f:
    env_bytes = f.read()
sftp = client.open_sftp()
sftp.putfo(io.BytesIO(env_bytes), f"{REMOTE_DIR}/backend/.env")
sftp.close()
print("  .env OK")

# Rebuild backend (CORS now includes investapi.ovelha.us)
step("Rebuilding backend Docker image...")
code, out, err = run(
    client,
    f"cd {REMOTE_DIR}/backend && docker build -t ovelhainvest-api . 2>&1 | tail -3",
    timeout=300,
)
print(f"  Build exit={code}: {out.strip()[-80:]}")

run(client, "docker stop ovelhainvest-api 2>/dev/null; docker rm -f ovelhainvest-api 2>/dev/null")
code, out, err = run(
    client,
    f"docker run -d --name ovelhainvest-api --restart unless-stopped -p 8090:8000 "
    f"--env-file {REMOTE_DIR}/backend/.env -e APP_ENV=production ovelhainvest-api",
    timeout=20,
)
print(f"  Backend start: exit={code}")
time.sleep(5)
code, out, err = run(client, "wget -qO- http://localhost:8090/health 2>&1 | head -1")
print(f"  Backend health: {out.strip()[:120]}")

# Rebuild frontend (new API URL baked in)
step("Rebuilding frontend Docker image (~3 min)...")
build_cmd = (
    f"cd {REMOTE_DIR} && docker build "
    f"--build-arg NEXT_PUBLIC_API_URL={FRONTEND_API_URL} "
    f"--build-arg NEXT_PUBLIC_SUPABASE_URL={SUPABASE_URL} "
    f"--build-arg NEXT_PUBLIC_SUPABASE_ANON_KEY={SUPABASE_ANON_KEY} "
    f"-t ovelhainvest-frontend ./frontend/ 2>&1 | tail -5"
)
code, out, err = run(client, build_cmd, timeout=600)
print(f"  Frontend build exit={code}")
print(f"  {out.strip()[-200:]}")
if code != 0:
    print(f"  BUILD FAILED: {err[-200:]}")
    client.close()
    raise SystemExit(1)

# Restart frontend container on port 3002
run(client, "docker stop ovelhainvest-frontend 2>/dev/null; docker rm -f ovelhainvest-frontend 2>/dev/null")
code, out, err = run(
    client,
    "docker run -d --name ovelhainvest-frontend --restart unless-stopped -p 3002:3000 ovelhainvest-frontend",
    timeout=20,
)
print(f"  Frontend start: exit={code} {(out + err).strip()[-60:]}")
time.sleep(8)
code, out, err = run(client, "wget -qO- http://localhost:3002/ 2>&1 | head -1")
print(f"  Frontend health: {out.strip()[:80]}")

# Show running containers
code, out, err = run(client, "docker ps --filter name=ovelhainvest --format '{{.Names}} {{.Status}} {{.Ports}}'")
print(f"  Containers:\n    {out.strip()}")

# Restart cloudflared via SSH jump to 10.0.0.151
step("Restarting cloudflared (SSH jump 10.0.0.201 -> 10.0.0.151)...")
code, out, err = run(
    client,
    'ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 10.0.0.151 "docker restart cloudflared" 2>&1',
    timeout=30,
)
print(f"  cloudflared restart: exit={code} {(out + err).strip()[:80]}")

client.close()
print("\n=== Redeploy Complete ===")
print(f"  Frontend: https://invest.ovelha.us")
print(f"  Backend API: https://investapi.ovelha.us")
