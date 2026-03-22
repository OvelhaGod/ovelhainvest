# OvelhaInvest — Claude Code Kickoff Prompt
> Paste the block below as your very first message in a new Claude Code session.
> Prerequisites must be completed first (see checklist at the bottom).

---

## FIRST MESSAGE TO CLAUDE CODE (copy-paste everything between the lines)

---

Read CLAUDE.md completely — all 30 sections. Do not skip any section. Confirm you've read it before writing a single line of code.

You have full access to this machine. No need to ask permission for any operation. Execute everything autonomously. When a step is done, move to the next immediately. Commit after every meaningful unit of work using conventional commits.

Your git setup: push to TWO remotes simultaneously on every push.
- Gitea (primary): https://gitea.ovelha.us/thiago/ovelhainvest.git
- GitHub (mirror): https://github.com/GITHUB_USERNAME/ovelhainvest.git

Replace GITHUB_USERNAME with the actual username before running.

---

## EXECUTE THIS FULL SEQUENCE IN ORDER. NO SKIPPING. NO SHORTCUTS.

### PART A — GIT REMOTES

```bash
git init
git remote add origin https://gitea.ovelha.us/thiago/ovelhainvest.git
git remote set-url --add --push origin https://gitea.ovelha.us/thiago/ovelhainvest.git
git remote set-url --add --push origin https://github.com/GITHUB_USERNAME/ovelhainvest.git
git checkout -b main
git checkout -b dev
git checkout dev
```

### PART B — BACKEND SCAFFOLD

```bash
cd ovelhainvest
uv init backend
cd backend
uv add fastapi "uvicorn[standard]" supabase pydantic-settings yfinance anthropic pandas numpy scipy redis httpx weasyprint python-dateutil python-dotenv
```

Create all backend files from Section 3 of CLAUDE.md:
- `backend/app/main.py` — FastAPI app with CORS + /health + /version endpoints. /health returns `{"status": "ok", "version": "1.0.0", "supabase": "connected"}` after a Supabase ping.
- `backend/app/config.py` — Pydantic Settings class reading all env vars from Section 21.
- `backend/app/db/supabase_client.py` — singleton client, lazy init, connection test function.
- `backend/app/db/redis_client.py` — Redis singleton via upstash-redis or redis-py, lazy init.
- All migration SQL files: `backend/app/migrations/001_initial_schema.sql` through `004_journal_alerts.sql` — use EXACT SQL from CLAUDE.md Section 4.
- ALL service file stubs in `backend/app/services/` — one file per service listed in Section 3. Each stub must have: module docstring, all function signatures with type hints and docstrings, `pass` as body. No implementation yet.
- ALL API route file stubs in `backend/app/api/` — same pattern.
- ALL repository stubs in `backend/app/db/repositories/`.
- ALL schema stubs in `backend/app/schemas/`.

Commit: `git add -A && git commit -m "feat(backend): FastAPI scaffold — all stubs, migrations, config"`

### PART C — FRONTEND SCAFFOLD

```bash
cd ovelhainvest
pnpm create next-app@latest frontend -- --typescript --tailwind --app --no-src-dir --no-eslint
cd frontend
pnpm dlx shadcn@latest init --defaults
pnpm add recharts d3 @supabase/supabase-js date-fns lucide-react next-themes
```

Create all frontend files:
- `frontend/app/layout.tsx` — Root layout with dark mode (class="dark"), sidebar nav with links to all 8 pages (dashboard, signals, assets, performance, projections, tax, journal, config). Use shadcn/ui components. Sidebar items include emoji icons matching each page's financial theme.
- `frontend/app/page.tsx` — redirect to `/dashboard`
- `frontend/app/dashboard/page.tsx` — PLACEHOLDER: 4 metric cards (Net Worth, P&L, YTD Return, Max Drawdown) with hardcoded zeros + "Loading live data in Phase 2" label. Sleeve allocation donut with hardcoded 6-slice data. 3 vault cards. Regime badge showing "Normal".
- `frontend/app/signals/page.tsx` — PLACEHOLDER: empty table with correct column headers.
- `frontend/app/assets/page.tsx` — PLACEHOLDER: filter bar + empty table with correct column headers.
- `frontend/app/performance/page.tsx` — PLACEHOLDER: tab navigation (Summary/Attribution/Rolling/Risk) with empty content.
- `frontend/app/projections/page.tsx` — PLACEHOLDER: tab navigation (Monte Carlo/Contribution Sim/Stress Test/Retirement) with empty content.
- `frontend/app/tax/page.tsx` — PLACEHOLDER: DARF progress bar at 0% + empty lots table.
- `frontend/app/journal/page.tsx` — PLACEHOLDER: override accuracy cards at 0 + empty table.
- `frontend/app/config/page.tsx` — PLACEHOLDER: version list + empty JSON viewer.
- `frontend/lib/supabase.ts` — Supabase browser client using env vars.
- `frontend/lib/api.ts` — typed fetch wrapper for all FastAPI endpoints (stub each endpoint function matching Section 8 of CLAUDE.md).
- `frontend/lib/types.ts` — TypeScript types for all DB tables from Section 4.
- `frontend/components/ui/` — shadcn components are auto-generated, don't create manually.
- Create stub component files for all items in Section 3: cards/, tables/, charts/, filters/.

Commit: `git add -A && git commit -m "feat(frontend): Next.js scaffold — layout, all page placeholders, lib stubs"`

### PART D — PROJECT ROOT FILES

Create in repo root:
- `.gitignore` — use EXACT content from Section 28.5 of CLAUDE.md
- `.env.example` — all variables from Section 21 with empty values + comments
- `README.md` — include: project overview, prerequisites, setup instructions (clone → copy .env → run migrations → start backend → start frontend), phase build plan summary, tech stack table
- `STITCH_PROMPT.md` — all 8 page prompts from Section 27.4, formatted exactly as written, ready to copy-paste into stitch.withgoogle.com
- `DESIGN.md` — placeholder file with content: `# DESIGN.md\n> PLACEHOLDER — Export from Google Stitch and replace this entire file before building any React components.\n> Instructions: Go to stitch.withgoogle.com → use prompts from STITCH_PROMPT.md → generate all 8 screens → export DESIGN.md → commit here.`
- `docker-compose.yml` — optional dev compose file: services for `backend` (FastAPI on 8000) and `frontend` (Next.js on 3000). No database — Supabase is hosted.

Commit: `git add -A && git commit -m "chore(infra): root files — .gitignore, .env.example, README, Stitch prompts, DESIGN placeholder"`

### PART E — STITCH MCP CONFIG

Create `.claude.json` in repo root (project-level MCP config) with:
```json
{
  "mcpServers": {
    "stitch": {
      "command": "npx",
      "args": ["-y", "stitch-mcp"],
      "env": {
        "GOOGLE_CLOUD_PROJECT": "REPLACE_WITH_GOOGLE_PROJECT_ID"
      }
    }
  }
}
```

Also create `.claude/settings.json` if it doesn't exist:
```json
{
  "autoApprove": true,
  "gitAutoCommit": false
}
```

Commit: `git add -A && git commit -m "chore(infra): Stitch MCP config for Claude Code"`

### PART F — VERIFICATION

Run these verification checks. Report pass/fail for each:

1. **Backend health:**
   ```bash
   cd backend && uvicorn app.main:app --reload --port 8000 &
   sleep 3
   curl -s http://localhost:8000/health
   # Expected: {"status": "ok", ...}
   kill %1
   ```

2. **Frontend build:**
   ```bash
   cd frontend && pnpm build
   # Expected: Build completed without errors
   ```

3. **Git remotes:**
   ```bash
   git remote -v
   # Expected: origin with both Gitea and GitHub push URLs
   ```

4. **File count check:**
   ```bash
   find . -name "*.py" | grep -v __pycache__ | wc -l
   find . -name "*.tsx" | grep -v node_modules | wc -l
   # Expected: Python files > 20, TSX files > 15
   ```

### PART G — PUSH TO BOTH REMOTES

```bash
git push -u origin main
git push -u origin dev
# This pushes to both Gitea AND GitHub simultaneously due to dual push config
```

Report push success/failure for each remote.

---

### PART H — FINAL REPORT

When done, provide:
1. List of all files created (grouped by directory)
2. Verification results (pass/fail for each check)
3. Any issues encountered and how they were resolved
4. Confirmation that both remotes received the push
5. Next step reminder: "Complete Stitch design session using STITCH_PROMPT.md, then start Phase 2"

---

## PREREQUISITES CHECKLIST (Complete These Before Running Claude Code)

Before starting your Claude Code session, make sure you have:

- [ ] **Supabase project created** → copy URL + service_key + anon_key
- [ ] **Upstash Redis** → create free instance at upstash.com → copy Redis URL
- [ ] **Anthropic API key** → already have from Claude
- [ ] **Finnhub API key** → free at finnhub.io → takes 2 minutes
- [ ] **Telegram bot** → message @BotFather → `/newbot` → copy token → get chat ID by messaging @userinfobot
- [ ] **Gitea repo created** → `https://gitea.ovelha.us/thiago/ovelhainvest` (create as empty repo)
- [ ] **GitHub repo created** → github.com → New repo → `ovelhainvest` → private → empty (no README)
- [ ] **Google Cloud project** → console.cloud.google.com → New project (for Stitch MCP later)
- [ ] **`.env` file ready** → copy `.env.example` → fill in all values → place in `backend/` folder

Once all boxes are checked, run `claude` in your `ovelhainvest/` directory and paste the prompt above.

---

## PHASE 2 PROMPT (Use After DESIGN.md Is Committed From Stitch)

After you complete the Stitch design session and commit DESIGN.md, start a new Claude Code session and paste this:

```
DESIGN.md has been committed. Read it now along with CLAUDE.md Section 6 (investment frameworks) and Section 26 (factor research).

Begin Phase 2 — Portfolio Engine. Full autonomy. Commit after every file. Push to both remotes after completing each numbered item below.

Build in this exact order:

1. backend/app/services/fx_engine.py — full implementation
   - fetch_usd_brl_rate() using yfinance symbol "USDBRL=X"  
   - normalize_to_usd(brl_value, rate) → float
   - compute_fx_attribution(return_brl, return_usd) → float
   - Cache rate in Redis with 15min TTL
   Commit + push both remotes.

2. backend/app/services/market_data.py — full implementation
   - fetch_prices(symbols: list[str]) → dict[str, float] using yfinance
   - fetch_fundamentals(symbol: str) → dict (PE, PS, dividend yield, vol30d)
   - fetch_price_history(symbol: str, period: str) → pd.Series
   - fetch_earnings_calendar(symbols: list[str]) → list[EarningsEvent] using Finnhub
   - fetch_news(symbol: str, limit: int) → list[NewsItem] using Finnhub
   - All results cached in Redis (prices: 5min TTL, fundamentals: 6hr TTL)
   Commit + push both remotes.

3. backend/app/services/allocation_engine.py — full implementation
   Per CLAUDE.md Section 7 and Section 26.1 Fama-French factor mapping.
   Commit + push both remotes.

4. backend/app/services/volatility_regime.py — full implementation
   Per CLAUDE.md Section 7 volatility rules and Section 26.5 macro signals.
   Map detected regime to FACTOR_COMPOSITE_WEIGHTS_BY_REGIME.
   Commit + push both remotes.

5. backend/app/services/rebalancing.py — full implementation  
   Per CLAUDE.md Section 7 rebalancing rules (soft-first, cadence limits, size limits).
   Commit + push both remotes.

6. backend/app/services/opportunity_detector.py — full implementation
   Per CLAUDE.md Section 7 opportunity rules (Marks Tier 1/2).
   Require margin_of_safety check (Graham floor) before any tier qualifies.
   Commit + push both remotes.

7. backend/app/db/repositories/ — implement all 6 repos
   (accounts, assets, holdings, signals, valuations, snapshots)
   Commit + push both remotes.

8. backend/app/api/allocation.py — implement POST /run_allocation + GET /daily_status
   /run_allocation: reads DB → calls all 4 services → writes signals_run → returns trades
   /daily_status: reads portfolio state → returns structured summary
   Commit + push both remotes.

9. frontend/app/dashboard/page.tsx — replace placeholder with live data
   Wire to GET /daily_status. Match DESIGN.md exactly.
   Net worth card, sleeve donut (actual vs target rings), vault cards, regime badge.
   Commit + push both remotes.

10. frontend/app/signals/page.tsx — full implementation
    Wire to signals_runs via Supabase direct query.
    Match DESIGN.md: table with expandable rows, status badges, approval buttons.
    Commit + push both remotes.

After item 10: open PR dev → main, merge, push main to both remotes.
Report completion summary.
```
