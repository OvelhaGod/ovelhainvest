# OvelhaInvest — Service Keep-Alive Strategy

## Why This Exists

Supabase free tier pauses projects after 7 days of inactivity.
This system uses triple redundancy to ensure the project never pauses.
Maximum gap without a ping: **2 days (weekend)** — well within the 7-day threshold.

## Coverage Map

| Day | Mon | Tue | Wed | Thu | Fri | Sat | Sun |
|-----|-----|-----|-----|-----|-----|-----|-----|
| GitHub Actions | ✅ | | | ✅ | | | |
| n8n Homelab | | ✅ | | | ✅ | | |
| run_allocation | ✅ | ✅ | ✅ | ✅ | ✅ | | |

**Supabase pause threshold:** 7 days
**Our maximum gap:** 2 days (Sat/Sun)
**Safety margin:** 5 days ✅

## Layer 1 — GitHub Actions (Monday + Thursday, 8AM UTC)

File: `.github/workflows/keep-alive.yml`

- Pings Supabase REST API (any response keeps project alive)
- Writes to `keep_alive_log` table (once migrations applied)
- Sends Telegram alert if Supabase is completely unreachable
- **Fully independent of homelab** — runs in the cloud

Secrets needed: `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, optionally `TELEGRAM_*`, `APP_BASE_URL`
Setup: see `docs/github-secrets-setup.md`

## Layer 2 — n8n Homelab (Tuesday + Friday, 10AM)

File: `automation/n8n/keep_alive.json`

- Pings `/health` endpoint
- Writes to `keep_alive_log` table
- Sends Telegram alert if API is offline
- **Fully independent of GitHub** — runs on Proxmox VM via n8n

Import: n8n UI → Workflows → Import from file → select `automation/n8n/keep_alive.json`
Configure n8n variables: `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `OVELHAINVEST_API_URL`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`

## Layer 3 — run_allocation Side Effect (Weekdays)

Every successful `/run_allocation` call writes to `keep_alive_log` as a side effect.
Completely automatic — zero extra configuration.

## If Supabase Gets Paused Anyway

1. Go to `supabase.com/dashboard`
2. Click your project → "Restore project"
3. Wait ~2 minutes
4. Run: `cd backend && uv run python scripts/verify_migrations.py`
5. Telegram alert will confirm recovery once GitHub Actions runs

## Upgrading from Free Tier

Upgrade to Supabase Pro ($25/month) when:
- Approaching 500MB database limit (transactions history)
- Need guaranteed uptime SLA
- Want daily automatic backups

Until then, this keep-alive system is sufficient for personal use.
