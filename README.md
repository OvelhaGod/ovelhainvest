# OvelhaInvest — Personal Wealth OS v1.0.0

> Thiago's private portfolio operating system. Rivals institutional tools. Self-hosted, single-user, no SaaS fees.

## What This Is

A full-stack personal wealth management platform with:
- **Portfolio Engine** — sleeve allocation, drift detection, rebalancing (Swensen/Dalio/Marks/Graham)
- **Valuation Engine** — factor scoring (value/momentum/quality), DCF, margin of safety
- **Performance Analytics** — TWR, MWR, Sharpe/Sortino/Calmar, attribution (Brinson-Hood-Beebower)
- **AI Advisor** — Claude API integration with investment philosophy framework checks
- **Real-Time Alerts** — Telegram bot for drawdown, opportunity, and drift alerts
- **Monte Carlo Projections** — 5,000-simulation fan charts with stress testing
- **Tax Engine** — HIFO/FIFO lot tracking, Brazil DARF tracker, loss harvesting
- **Decision Journal** — Override tracking, behavioral pattern analysis, outcome measurement
- **PDF Reports** — Monthly/annual PDF generation via WeasyPrint
- **PWA** — Offline-capable progressive web app with mobile nav

## Tech Stack

| Layer | Tech |
|---|---|
| Frontend | Next.js 14 (App Router), Tailwind CSS, Recharts |
| Backend | FastAPI (Python 3.12), pandas, numpy, scipy |
| Database | Supabase (Postgres) |
| Cache | Redis (Upstash) |
| AI | Anthropic Claude API |
| Market Data | yfinance + Finnhub |
| Alerts | Telegram Bot API |
| Automation | n8n (self-hosted) |
| PDF | WeasyPrint |

## Prerequisites

- Python 3.12+ with `uv` (`pip install uv`)
- Node.js 20+ with `pnpm` (`npm i -g pnpm`)
- Supabase project (free tier works)
- Upstash Redis (free tier works)
- Anthropic API key
- Telegram bot (via @BotFather)

## Setup

### 1. Clone and configure environment

```bash
git clone https://github.com/OvelhaGod/ovelhainvest.git
cd ovelhainvest
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local
# Fill in all values in both .env files
```

### 2. Apply database migrations

Run each migration in order in your Supabase SQL editor:
```
backend/app/migrations/001_initial_schema.sql
backend/app/migrations/002_tax_lots.sql
backend/app/migrations/003_performance_tables.sql
backend/app/migrations/004_journal_alerts.sql
```

### 3. Start the backend

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

Visit `http://localhost:8000/health` — should return `{"status": "ok"}`.

### 4. Start the frontend

```bash
cd frontend
pnpm install
pnpm dev
```

Visit `http://localhost:3000` — redirects to `/dashboard`.

### 5. Seed development data (optional)

```bash
curl -X POST http://localhost:8000/admin/seed
```

## Running Tests

```bash
cd backend
uv run pytest tests/test_integration.py -v
```

## Architecture

```
ovelhainvest/
  backend/          FastAPI app (Python 3.12)
    app/
      api/          Route handlers (thin — call services)
      services/     All business logic
      db/           Supabase client + repositories
      templates/    Jinja2 HTML templates for PDF reports
  frontend/         Next.js 14 app
    app/            App Router pages
    components/     React components
    lib/            API client + types
  automation/       n8n workflow JSON exports
  docs/             Investment policy, architecture docs
```

## Pages

| Route | Description |
|---|---|
| `/dashboard` | Net worth, sleeve allocation, regime, vaults |
| `/signals` | Allocation run history, AI commentary, approvals |
| `/assets` | Factor scores, DCF, margin of safety per asset |
| `/performance` | TWR/MWR, attribution, rolling returns, risk parity |
| `/projections` | Monte Carlo, contribution sim, stress tests |
| `/tax` | Tax lots, HIFO/FIFO, Brazil DARF tracker |
| `/journal` | Decision log, override accuracy, behavioral patterns |
| `/reports` | Generate and download PDF reports |

## Environment Variables

### backend/.env
```
SUPABASE_URL=
SUPABASE_SERVICE_KEY=
ANTHROPIC_API_KEY=
FINNHUB_API_KEY=
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
REDIS_URL=
APP_ENV=development
SECRET_KEY=
```

### frontend/.env.local
```
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Hard Constraints

- Emergency vault is **NEVER** investable
- Opportunity vault requires **explicit approval** — never auto-execute
- **No real trade execution** in v1 — propose only
- AI validation failures must **NOT** block runs — degrade gracefully
- No deletion of accounts, lots, journal entries — soft-delete only
- **Never commit `.env` files**

## Git Workflow

```bash
# Two remotes configured (dual push on every push)
# Gitea (primary):  https://gitea.ovelha.us/thiago/ovelhainvest.git
# GitHub (mirror):  https://github.com/OvelhaGod/ovelhainvest.git

git push origin dev     # pushes to both remotes simultaneously
```

Conventional commits enforced: `feat(scope):`, `fix(scope):`, `chore(scope):`, etc.

## License

Private — personal use only.
