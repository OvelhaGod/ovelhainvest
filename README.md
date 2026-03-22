# OvelhaInvest — Thiago Wealth OS

> Personal portfolio operating system. Single-user. Not financial advice.
> Best-in-class private wealth management — Bloomberg terminal meets personal finance.

---

## Tech Stack

| Layer | Choice |
|---|---|
| Frontend | Next.js 14 · Tailwind CSS · shadcn/ui · Recharts · D3.js |
| Backend | FastAPI (Python 3.12) · pandas · numpy · scipy |
| Database | Supabase (Postgres + Auth) |
| Cache | Redis via Upstash |
| AI | Anthropic Claude (`claude-sonnet-4-20250514`) |
| Market Data | yfinance · Finnhub |
| Notifications | Telegram Bot API |
| Package Mgr | uv (Python) · pnpm (JS) |

---

## Prerequisites

- Python 3.12+ · `pip install uv`
- Node.js 20+ · `npm install -g pnpm`
- [Supabase](https://supabase.com) project (free tier OK)
- [Upstash Redis](https://upstash.com) instance (free tier OK)
- [Anthropic API key](https://console.anthropic.com)
- [Finnhub API key](https://finnhub.io) — free tier
- [Telegram bot](https://t.me/BotFather) — /newbot

---

## Setup

### 1. Clone & configure

```bash
git clone https://gitea.ovelha.us/thiago/ovelhainvest.git
cd ovelhainvest

# Copy and fill in all environment variables
cp .env.example backend/.env
# Edit backend/.env with your keys
```

### 2. Apply database migrations

In Supabase SQL Editor (or via CLI), run in order:
```
backend/app/migrations/001_initial_schema.sql
backend/app/migrations/002_tax_lots.sql
backend/app/migrations/003_performance_tables.sql
backend/app/migrations/004_journal_alerts.sql
```

### 3. Start backend

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload
# → http://localhost:8000/health  ✓
# → http://localhost:8000/docs    Swagger UI
```

### 4. Start frontend

```bash
cd frontend
cp ../.env.example .env.local   # then fill in NEXT_PUBLIC_* values
pnpm install
pnpm dev
# → http://localhost:3000  → /dashboard
```

---

## Phase Build Plan

| Phase | Description | Status |
|---|---|---|
| 1 | Foundation: scaffold, /health, dashboard placeholder | ✅ Done |
| 2 | Portfolio Engine: allocation, drift, regime, signals | Pending |
| 3 | Valuation Engine: factor scoring, DCF, margin of safety | Pending |
| 4 | Performance Analytics: TWR, MWR, attribution | Pending |
| 5 | AI Layer: Claude integration + philosophy prompt | Pending |
| 6 | Alerts + Telegram + n8n automations | Pending |
| 7 | Simulation + Projections: Monte Carlo, stress tests | Pending |
| 8 | Tax Engine: HIFO/FIFO, Brazil DARF | Pending |
| 9 | Decision Journal + PDF Reports | Pending |
| 10 | PWA + Polish: FX, risk parity, correlation heatmap | Pending |

---

## Before Phase 2

Complete the Stitch design session:
1. Open `STITCH_PROMPT.md`
2. Use prompts at [stitch.withgoogle.com](https://stitch.withgoogle.com)
3. Export `DESIGN.md` from Stitch
4. Replace placeholder `DESIGN.md` in repo root
5. Commit + push both remotes
6. Start Phase 2 using prompt in `CLAUDE_CODE_START.md`

---

## Hard Constraints

- Emergency vault is **NEVER** investable
- Opportunity vault requires **explicit approval** — never auto-execute
- **No real trade execution** in v1 — propose only
- AI validation failures must **NOT** block runs — degrade gracefully
- No deletion of accounts, lots, journal entries — soft-delete only
- **Never commit `.env` files**

---

## Git Workflow

```bash
# Two remotes configured (dual push on every push)
# Gitea (primary):  https://gitea.ovelha.us/thiago/ovelhainvest.git
# GitHub (mirror):  https://github.com/[username]/ovelhainvest.git

git push origin dev     # pushes to both remotes simultaneously
```

Conventional commits enforced: `feat(scope):`, `fix(scope):`, `chore(scope):`, etc.
