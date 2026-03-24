# GitHub Actions Secrets Setup

Required for the keep-alive workflow: `.github/workflows/keep-alive.yml`

## Quick Setup (gh CLI)

```bash
cd D:/python/ovelhainvest/backend
bash scripts/setup_github_secrets.sh
```

## Manual Setup

Go to: **https://github.com/OvelhaGod/ovelhainvest/settings/secrets/actions**

Click **"New repository secret"** for each row:

| Secret Name | Where to get it | Required |
|---|---|---|
| `SUPABASE_URL` | `backend/.env` → `SUPABASE_URL` | ✅ |
| `SUPABASE_SERVICE_KEY` | `backend/.env` → `SUPABASE_SERVICE_KEY` | ✅ |
| `TELEGRAM_BOT_TOKEN` | `backend/.env` → `TELEGRAM_BOT_TOKEN` | Optional |
| `TELEGRAM_CHAT_ID` | `backend/.env` → `TELEGRAM_CHAT_ID` | Optional |
| `APP_BASE_URL` | `https://ovelhainvest.ovelha.us` | Optional |

## Trigger a Test Run

1. Go to: https://github.com/OvelhaGod/ovelhainvest/actions
2. Click **"Keep Services Alive"**
3. Click **"Run workflow"** → **"Run workflow"**
4. Watch the logs — Supabase ping should return 200 or 404 (both are fine)

## Schedule

Runs automatically every **Monday and Thursday at 8AM UTC**.
