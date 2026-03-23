# OvelhaInvest — n8n Automation Workflows

Four n8n workflows that power the automated daily operations of OvelhaInvest.
All workflows are importable JSON files compatible with n8n v1.x.

---

## Workflows

| File | Schedule | Purpose |
|---|---|---|
| `daily_check.json` | Weekdays 7AM ET (12:00 UTC) | Performance snapshot → allocation run → Telegram digest |
| `valuation_pipeline.json` | Sundays 6AM ET (11:00 UTC) | Full valuation update → Telegram if notable changes |
| `opportunity_scan.json` | Weekdays 8AM ET (13:00 UTC) | Scan for Tier 1/2 drawdown opportunities → allocation run |
| `journal_outcome_backfill.json` | Daily 00:05 UTC | Backfill 30d/90d outcomes on journal entries |

---

## Importing Workflows

1. Open your n8n instance (e.g. `http://proxmox-ip:5678`)
2. Go to **Workflows** → **Import from File**
3. Select the `.json` file
4. Click **Save** — the workflow will be imported as **inactive**
5. Configure credentials and variables (see below), then toggle **Active**

> Repeat for all four workflows.

---

## Required n8n Credentials

Create these credentials in n8n **Settings → Credentials** before activating any workflow.

### Telegram

| Field | Value |
|---|---|
| Credential Name | `Telegram` (must match exactly — workflows reference `"id": "telegram-cred"`) |
| Type | `Telegram API` |
| Bot Token | Your `TELEGRAM_BOT_TOKEN` from @BotFather |

> After import, open each Telegram node, select the `Telegram` credential from the dropdown, and save.

---

## Required n8n Variables

Set these in **Settings → Variables** (n8n v1.x environment variables UI).

| Variable | Description | Example |
|---|---|---|
| `OVELHAINVEST_API_URL` | Backend API base URL (no trailing slash) | `https://api.yourdomain.com` or `http://10.0.0.5:8000` |
| `OVELHAINVEST_USER_ID` | Your Supabase user UUID | `00000000-0000-0000-0000-000000000001` |
| `TELEGRAM_CHAT_ID` | Your Telegram chat ID (from @userinfobot) | `123456789` |
| `APP_URL` | Frontend app URL (no trailing slash) | `https://invest.yourdomain.com` |

> In n8n, variables are referenced as `$vars.VARIABLE_NAME` in expressions.
> Go to **Settings → Variables → Add Variable** for each.

---

## Workflow Details

### daily_check.json
**Trigger:** Monday–Friday, 7AM ET (cron: `0 12 * * 1-5`)

**Flow:**
1. POST `/performance/snapshot` — records daily portfolio snapshot
2. POST `/run_allocation` — runs allocation engine, writes signals_run
3. If `status == "paused"` → Telegram: "Automation Paused (drawdown gate)"
4. Else if `approval_required_count > 0` → Telegram: "⚠️ Approval Required" with inline button → `/signals`
5. Else → Telegram: "✅ All Clear" with net worth + regime

**Telegram buttons:** "Open Signals" deep-links to `/signals` page.

---

### valuation_pipeline.json
**Trigger:** Every Sunday, 6AM ET (cron: `0 11 * * 0`)

**Flow:**
1. POST `/valuation_update` — triggers full factor scoring + DCF refresh for all assets
2. If `notable_changes > 0` → Telegram: asset count, top 3 opportunities with MoS%
3. Else → Telegram: "No notable changes"

**Timeout:** 5 minutes (valuation pipeline can be slow on first run).

---

### opportunity_scan.json
**Trigger:** Monday–Friday, 8AM ET (cron: `0 13 * * 1-5`)

**Flow:**
1. GET `/valuation_summary?min_margin_of_safety=0.20` — fetch assets with MoS ≥ 20%
2. If `tier_1_count + tier_2_count > 0` → POST `/run_allocation` with `event_type: "opportunity"`
3. Telegram: "🚨 OPPORTUNITY ALERT" with tier counts + approval prompt

**Howard Marks principle:** Fires when assets are at drawdown levels with margin of safety — buy when fear is highest.

---

### journal_outcome_backfill.json
**Trigger:** Daily at 00:05 UTC (cron: `5 0 * * *`)

**Flow:**
1. GET `/journal?limit=200` — fetch all journal entries
2. Code node filters for entries ≥30 days old with `outcome_30d == null` or ≥90 days old with `outcome_90d == null`
3. GET `/performance/summary` — fetch current period returns
4. PATCH `/journal/{id}/outcome` for each entry — fills in 1mo return for 30d, 3mo return for 90d

**Note:** Period returns are portfolio-level. For asset-specific outcomes, you would extend the Code node to fetch per-asset performance from `/performance/attribution`.

---

## Recommended Hosting: Proxmox LXC

n8n runs well as a lightweight LXC container on Proxmox.

```bash
# Create Debian 12 LXC (512MB RAM, 4GB disk is sufficient)
# Then inside the container:
apt update && apt install -y nodejs npm
npm install -g n8n

# Run as a service
cat > /etc/systemd/system/n8n.service << EOF
[Unit]
Description=n8n workflow automation
After=network.target

[Service]
Type=simple
User=root
Environment=N8N_BASIC_AUTH_ACTIVE=true
Environment=N8N_BASIC_AUTH_USER=admin
Environment=N8N_BASIC_AUTH_PASSWORD=changeme
Environment=N8N_HOST=0.0.0.0
Environment=N8N_PORT=5678
Environment=N8N_PROTOCOL=http
Environment=WEBHOOK_URL=https://n8n.yourdomain.com/
ExecStart=/usr/bin/n8n start
Restart=always

[Install]
WantedBy=multi-user.target
EOF

systemctl enable n8n
systemctl start n8n
```

Access at `http://proxmox-ip:5678` or reverse-proxy with nginx/Caddy.

---

## Webhook Setup (Telegram → Backend)

For the Telegram approval flow to work, the backend must be reachable from the internet so Telegram can POST callback_query events.

```bash
# Register webhook (done automatically on production startup via lifespan event)
# Or manually:
curl -X POST "https://api.telegram.org/bot{TOKEN}/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://api.yourdomain.com/webhooks/telegram",
    "secret_token": "YOUR_TELEGRAM_WEBHOOK_SECRET"
  }'
```

Set `TELEGRAM_WEBHOOK_SECRET` in your backend `.env` to the same value.

---

## Testing Workflows

Each workflow can be triggered manually from n8n UI:
1. Open the workflow
2. Click **Execute Workflow** (top right)
3. Check execution log for errors

For the daily_check, you can also call the API directly:
```bash
curl -X POST http://localhost:8000/run_allocation \
  -H "Content-Type: application/json" \
  -d '{"user_id": "00000000-0000-0000-0000-000000000001", "event_type": "manual_override"}'
```

> Use `event_type: "manual_override"` to bypass the automation pause gate during testing.
