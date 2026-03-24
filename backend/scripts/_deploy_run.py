"""Helper script — run via: uv run python scripts/_deploy_run.py"""
import paramiko
import io
import time

HOST = "10.0.0.201"
KEY_PATH = "C:/Users/Thiago/.ssh/id_ed25519"
REMOTE_DIR = "/home/thiago/docker/ovelhainvest"
TOKEN = "1a077b690dbdceba3e588bcd8b97d8e2b1e5d88e"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
key = paramiko.Ed25519Key.from_private_key_file(KEY_PATH)
client.connect(HOST, username="thiago", pkey=key, timeout=15)


def run(cmd, timeout=120):
    sin, sout, serr = client.exec_command(cmd, timeout=timeout)
    code = sout.channel.recv_exit_status()
    return code, sout.read().decode("utf-8", errors="replace"), serr.read().decode("utf-8", errors="replace")


print("=== Deploying OvelhaInvest backend to homelab ===\n")

# Step 1: Pull latest code
print("[1] Pulling latest code on devbox...")
code, out, err = run(f"cd {REMOTE_DIR} && git fetch 2>&1 && git checkout dev && git pull 2>&1", timeout=30)
print(f"  Pull: {out.strip()[-100:]}")

# Step 2: Copy .env
print("[2] Copying .env to devbox...")
with open("D:/python/ovelhainvest/backend/.env", "rb") as f:
    env_content = f.read()
sftp = client.open_sftp()
sftp.putfo(io.BytesIO(env_content), f"{REMOTE_DIR}/backend/.env")
sftp.close()
print("  .env copied OK")

# Verify Dockerfile is present
code, out, err = run(f"ls {REMOTE_DIR}/backend/Dockerfile 2>&1")
print(f"  Dockerfile check: {out.strip()}")

# Step 3: Build Docker image
print("[3] Building Docker image (may take ~2 min)...")
code, out, err = run(
    f"cd {REMOTE_DIR}/backend && docker build -t ovelhainvest-api . 2>&1 | tail -12",
    timeout=360,
)
print(f"  Build exit={code}")
print(out[-500:])
if code != 0:
    print("BUILD FAILED — stderr:", err[-200:])
    client.close()
    raise SystemExit(1)

# Step 4: Stop old + start new container via docker run (not compose)
print("[4] Starting container...")
run("docker stop ovelhainvest-api 2>/dev/null; docker rm ovelhainvest-api 2>/dev/null")
code, out, err = run(
    f"docker run -d "
    f"--name ovelhainvest-api "
    f"--restart unless-stopped "
    f"-p 8000:8000 "
    f"--env-file {REMOTE_DIR}/backend/.env "
    f"-e APP_ENV=production "
    f"ovelhainvest-api 2>&1",
    timeout=30,
)
print(f"  Start: exit={code} {(out+err).strip()[-100:]}")

time.sleep(8)
code, out, err = run("docker ps --filter name=ovelhainvest-api --format '{{.Names}} {{.Status}}'")
print(f"  Container: {out.strip()}")

# Step 5: Verify health
print("[5] Verifying /health...")
time.sleep(5)
code, out, err = run("wget -qO- http://localhost:8000/health 2>&1")
if '"status"' in out:
    print(f"  Health OK: {out.strip()[:150]}")
else:
    print(f"  Health FAIL: {out[:200]} {err[:100]}")
    # Show logs
    code, logs, _ = run("docker logs ovelhainvest-api 2>&1 | tail -20")
    print(f"  Container logs:\n{logs}")

print("\n=== Done! ===")
print(f"  API running at: http://10.0.0.201:8000")
print(f"  Next: add CF tunnel route invest.ovelha.us -> http://10.0.0.201:8000")

client.close()
