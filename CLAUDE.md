# OvelhaInvest — Claude Code Project Brief
> Version 3.0 | Single-user personal wealth OS for Thiago
> Read this file COMPLETELY before writing any code. Every section matters.

---

## 1. PROJECT IDENTITY

**App name:** OvelhaInvest (product brand) / Thiago Wealth OS (system name)
**Type:** Personal, single-user, private robo-advisor / portfolio operating system
**Ambition:** Best-in-class personal wealth management app in the world — not a consumer toy

**NOT:** a public SaaS, a brokerage, a trading bot, a financial advisor
**YES:** a private portfolio operating system that rivals institutional tools

**Core principle:** Deterministic Python engine is the source of truth. AI is validator + explainer only. Never the decision-maker.

**Design aesthetic:** Modern glassmorphism with depth. Think Linear.app meets Vercel dashboard meets a premium trading terminal. Dark mode always. Frosted glass cards with subtle backdrop blur, soft purple/blue/green gradient accents on key metrics, smooth micro-animations on state changes, variable rounded corners (never fully squared). Data-dense but breathable — tight spacing where it matters, generous padding on hero metrics. Typography: Inter for UI copy, Geist Mono for all numbers and tickers. Color language: emerald green (#10b981) for gains/positive, rose red (#f43f5e) for losses/negative, amber (#f59e0b) for warnings, violet (#8b5cf6) as brand accent. Every screen should feel like a premium 2026 AI product — NOT boxy default shadcn, NOT plain tables, NOT generic fintech.

---

## 2. TECH STACK (FINAL — DO NOT DEVIATE WITHOUT ASKING)

| Layer | Choice |
|---|---|
| Frontend | Next.js 14 (App Router) |
| Styling | Tailwind CSS + shadcn/ui |
| Charts | Recharts (standard) + D3.js (Monte Carlo fan charts) |
| Backend | FastAPI (Python 3.12) |
| Analytics libs | pandas, numpy, scipy |
| Database + Auth | Supabase (Postgres + Supabase Auth) |
| Caching | Redis via Upstash (free tier) |
| Orchestration | n8n (self-hosted on Proxmox) |
| AI Layer | Anthropic Claude API (`claude-sonnet-4-20250514`) |
| Market Data | yfinance (primary, free) + Finnhub (news/earnings, free tier) |
| Notifications | Telegram Bot API (real-time alerts) |
| PDF Reports | WeasyPrint |
| Package Manager (Python) | uv |
| Package Manager (JS) | pnpm |

---

## 3. PROJECT STRUCTURE

```
ovelhainvest/
  CLAUDE.md                          ← this file
  README.md

  backend/
    pyproject.toml                   ← uv-managed
    app/
      main.py                        ← FastAPI app entry point
      config.py                      ← env/settings via pydantic-settings
      api/
        allocation.py                ← /run_allocation, /daily_status
        valuation.py                 ← /valuation_update
        performance.py               ← /performance_summary, /performance_attribution
        simulation.py                ← /monte_carlo, /scenario, /stress_test
        tax.py                       ← /tax_lots, /tax_estimate, /brazil_darf
        alerts.py                    ← /alerts/rules, /alerts/history
        reports.py                   ← /reports/generate, /reports/list
        backtest.py                  ← /backtest (Phase 6+)
      services/
        allocation_engine.py         ← sleeve weights, drift detection
        rebalancing.py               ← soft/hard rebalance proposals
        volatility_regime.py         ← VIX/move thresholds → regime state
        opportunity_detector.py      ← Tier 1/2 evaluation (Marks-inspired)
        valuation_engine.py          ← factor scoring orchestrator
        dcf.py                       ← DCF for eligible stocks (Graham/Buffett margin of safety)
        tax_heuristics.py            ← US + Brazil tax logic
        tax_lot_engine.py            ← FIFO/HIFO/Spec ID lot tracking
        performance_engine.py        ← TWR, MWR, attribution, Sharpe, Sortino, Calmar
        simulation_engine.py         ← Monte Carlo, scenario, stress testing
        contribution_optimizer.py    ← optimal account routing, tax-location
        risk_engine.py               ← risk parity, correlation matrix, VaR
        ai_advisor.py                ← Claude API integration
        market_data.py               ← yfinance + Finnhub wrapper
        fx_engine.py                 ← USD/BRL normalization, FX attribution
        alert_engine.py              ← rule evaluation, Telegram dispatch
        report_builder.py            ← PDF report generation
        journal_engine.py            ← decision log, override tracking
        broker_sync.py               ← account data sync (CSV + Plaid stubs)
      db/
        supabase_client.py
        redis_client.py
        repositories/
          accounts.py
          assets.py
          holdings.py
          tax_lots.py
          signals.py
          valuations.py
          snapshots.py
          performance.py
          alerts.py
          journal.py
      schemas/
        allocation_models.py
        valuation_models.py
        performance_models.py
        simulation_models.py
        ai_models.py
        tax_models.py
      migrations/
        001_initial_schema.sql
        002_tax_lots.sql
        003_performance_tables.sql
        004_journal_alerts.sql

  frontend/
    package.json
    app/
      layout.tsx
      page.tsx                       ← redirect to /dashboard
      dashboard/page.tsx             ← net worth, sleeves, vaults, regime
      signals/page.tsx               ← signals_runs, AI commentary
      assets/page.tsx                ← valuations, scores, DCF detail
      performance/page.tsx           ← TWR/MWR, Sharpe/Sortino/Calmar, attribution
      projections/page.tsx           ← Monte Carlo, contribution sim, stress tests
      tax/page.tsx                   ← lot tracker, HIFO/FIFO, Brazil DARF
      research/page.tsx              ← news, earnings, research docs
      journal/page.tsx               ← decision log, override history
      config/page.tsx                ← strategy_configs viewer
    components/
      ui/                            ← shadcn/ui (do not modify)
      cards/
        NetWorthCard.tsx
        SleeveAllocationChart.tsx
        VaultBalancesCard.tsx
        RegimeStatusBadge.tsx
        RiskScoreCard.tsx
      tables/
        SignalsTable.tsx
        AssetValuationsTable.tsx
        TaxLotTable.tsx
        JournalTable.tsx
      charts/
        AllocationDonut.tsx
        PortfolioTimelineChart.tsx
        MonteCarloFanChart.tsx
        PerformanceAttributionChart.tsx
        DrawdownChart.tsx
        CorrelationHeatmap.tsx
        RiskReturnScatter.tsx
      filters/
        AssetFilters.tsx
    lib/
      supabase.ts
      api.ts
      types.ts

  automation/
    n8n/
      daily_check.json
      valuation_pipeline.json
      opportunity_scan.json
      approval_flow.json
      earnings_digest.json
      monthly_report.json

  docs/
    01_investment_policy_statement.yaml
    02_strategy_config_schema.json
    03_supabase_schema.sql
    04_system_architecture.md
    05_valuation_playbook.md
    06_tax_rules_and_heuristics.md
    07_ai_agent_spec.md
    08_sample_research_summaries.md
    09_example_output_from_ai_agent.json
    10_investment_frameworks.md      ← new: Swensen, Dalio, Marks, Graham, Buffett
```

---

## 4. DATABASE SCHEMA

### Migration 001 — Core Schema
```sql
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE users (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  email text UNIQUE NOT NULL,
  display_name text,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE accounts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name text NOT NULL,
  broker text NOT NULL,
  account_type text NOT NULL,
  tax_treatment text NOT NULL,
  currency text NOT NULL DEFAULT 'USD',
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE vaults (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  account_id uuid NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
  vault_type text NOT NULL,
  min_balance numeric(18,2),
  max_balance numeric(18,2),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE assets (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  symbol text NOT NULL,
  name text NOT NULL,
  asset_class text NOT NULL,
  region text,
  sector text,
  currency text NOT NULL,
  benchmark_symbol text,
  is_dcf_eligible boolean NOT NULL DEFAULT false,
  moat_rating text,                  -- "wide", "narrow", "none", "unknown" (Buffett moat)
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX assets_symbol_unique ON assets(symbol, currency);

CREATE TABLE holdings (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  account_id uuid NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
  asset_id uuid NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
  quantity numeric(38,10) NOT NULL,
  avg_cost_basis numeric(18,6),
  last_updated timestamptz NOT NULL DEFAULT now(),
  UNIQUE (account_id, asset_id)
);

CREATE TABLE transactions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  account_id uuid NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
  asset_id uuid REFERENCES assets(id) ON DELETE SET NULL,
  type text NOT NULL,
  quantity numeric(38,10),
  price numeric(18,6),
  fees numeric(18,6),
  gross_amount numeric(18,2),
  currency text NOT NULL,
  executed_at timestamptz NOT NULL,
  notes text
);
CREATE INDEX transactions_account_time_idx ON transactions(account_id, executed_at);

CREATE TABLE asset_valuations (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  asset_id uuid NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
  as_of_date date NOT NULL,
  price numeric(18,6) NOT NULL,
  pe numeric(18,6),
  ps numeric(18,6),
  dividend_yield numeric(9,6),
  vol_30d numeric(9,6),
  drawdown_from_6_12m_high_pct numeric(9,6),
  value_score numeric(9,6),
  momentum_score numeric(9,6),
  quality_score numeric(9,6),
  composite_score numeric(9,6),
  fair_value_estimate numeric(18,6),
  fair_value_estimate_dcf numeric(18,6),
  margin_of_safety_pct numeric(9,6),    -- (fair_value - price) / fair_value
  buy_target numeric(18,6),
  hold_range_low numeric(18,6),
  hold_range_high numeric(18,6),
  sell_target numeric(18,6),
  moat_score numeric(9,6),              -- Buffett economic moat proxy
  rank_in_universe integer,
  tier text,
  dcf_assumptions jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (asset_id, as_of_date)
);

CREATE TABLE strategy_configs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  version text NOT NULL,
  is_active boolean NOT NULL DEFAULT false,
  config jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE signals_runs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  run_timestamp timestamptz NOT NULL DEFAULT now(),
  event_type text NOT NULL,
  inputs_summary jsonb,
  proposed_trades jsonb,
  ai_validation_summary jsonb,
  status text NOT NULL DEFAULT 'pending',
  notes text
);
CREATE INDEX signals_runs_user_time_idx ON signals_runs(user_id, run_timestamp);

CREATE TABLE news_items (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source text, url text,
  asset_id uuid REFERENCES assets(id) ON DELETE SET NULL,
  category text,
  summary text,
  published_at timestamptz,
  importance_score integer,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE research_docs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  title text NOT NULL, source text,
  related_assets jsonb, tags text[],
  url_or_storage_path text,
  importance_score integer,
  published_at timestamptz,
  summary text,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE opportunity_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  asset_id uuid REFERENCES assets(id) ON DELETE SET NULL,
  event_name text NOT NULL,
  start_date date NOT NULL,
  tier_1_trigger_date date,
  tier_1_deployed_fraction_of_vault numeric(9,6),
  tier_2_trigger_date date,
  tier_2_deployed_fraction_of_vault numeric(9,6),
  closed_date date,
  notes text
);

CREATE TABLE benchmarks (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  symbol text NOT NULL, description text,
  blend_weights jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE portfolio_snapshots (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  snapshot_date date NOT NULL,
  total_value_usd numeric(18,2) NOT NULL,
  total_value_brl numeric(18,2),
  usd_brl_rate numeric(10,6),
  sleeve_weights jsonb,
  benchmark_symbol text,
  benchmark_return numeric(9,6),
  portfolio_return_twr numeric(9,6),       -- Time-Weighted Return
  portfolio_return_mwr numeric(9,6),       -- Money-Weighted Return / IRR
  portfolio_return_ytd numeric(9,6),
  sharpe_ratio numeric(9,6),
  sortino_ratio numeric(9,6),
  calmar_ratio numeric(9,6),
  drawdown_from_peak_pct numeric(9,6),
  volatility_annualized numeric(9,6),
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (user_id, snapshot_date)
);
```

### Migration 002 — Tax Lots
```sql
CREATE TABLE tax_lots (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  account_id uuid NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
  asset_id uuid NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
  acquisition_date date NOT NULL,
  quantity numeric(38,10) NOT NULL,
  cost_basis_per_unit numeric(18,6) NOT NULL,
  cost_basis_total numeric(18,2) NOT NULL,
  lot_type text NOT NULL DEFAULT 'long',    -- "long" (>1yr), "short" (<1yr)
  is_closed boolean NOT NULL DEFAULT false,
  closed_date date,
  proceeds numeric(18,2),
  realized_gain_loss numeric(18,2),
  wash_sale_flag boolean DEFAULT false,
  notes text,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX tax_lots_account_asset_idx ON tax_lots(account_id, asset_id, acquisition_date);

CREATE TABLE brazil_darf_tracker (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  year integer NOT NULL,
  month integer NOT NULL,
  gross_sales_brl numeric(18,2) NOT NULL DEFAULT 0,
  realized_gain_brl numeric(18,2) NOT NULL DEFAULT 0,
  exemption_used boolean NOT NULL DEFAULT false,
  darf_due numeric(18,2),
  notes text,
  UNIQUE (user_id, year, month)
);
```

### Migration 003 — Performance Tables
```sql
CREATE TABLE performance_attribution (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  period_start date NOT NULL,
  period_end date NOT NULL,
  total_return numeric(9,6),
  benchmark_return numeric(9,6),
  active_return numeric(9,6),          -- alpha vs benchmark
  attribution_by_sleeve jsonb,          -- { "us_equity": {"weight": 0.45, "return": 0.08, "contribution": 0.036} }
  attribution_by_asset jsonb,           -- top contributors + detractors
  fx_contribution numeric(9,6),         -- how much USD/BRL move contributed
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE risk_metrics (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  as_of_date date NOT NULL,
  beta_vs_primary numeric(9,6),
  correlation_matrix jsonb,
  var_95_1day numeric(9,6),            -- Value at Risk
  var_99_1day numeric(9,6),
  risk_parity_weights jsonb,           -- Dalio-style risk-equal weights
  effective_diversification_ratio numeric(9,6),
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (user_id, as_of_date)
);
```

### Migration 004 — Journal & Alerts
```sql
CREATE TABLE decision_journal (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  event_date timestamptz NOT NULL DEFAULT now(),
  signal_run_id uuid REFERENCES signals_runs(id) ON DELETE SET NULL,
  action_type text NOT NULL,           -- "followed", "overrode", "deferred", "manual_trade"
  asset_id uuid REFERENCES assets(id) ON DELETE SET NULL,
  system_recommendation jsonb,
  actual_action jsonb,
  reasoning text,                      -- free-text: why you overrode or followed
  outcome_30d numeric(9,6),            -- filled in later by automation
  outcome_90d numeric(9,6),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE alert_rules (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  rule_name text NOT NULL,
  rule_type text NOT NULL,             -- "drawdown", "drift", "opportunity", "sell_target", "darf", "deposit"
  conditions jsonb NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  last_triggered timestamptz,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE alert_history (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  alert_rule_id uuid NOT NULL REFERENCES alert_rules(id) ON DELETE CASCADE,
  triggered_at timestamptz NOT NULL DEFAULT now(),
  payload jsonb,
  channel text NOT NULL DEFAULT 'telegram',
  delivered boolean NOT NULL DEFAULT false
);
```

---

## 5. TARGET ALLOCATION (Thiago's IPS — Hardcoded Reference)

```python
SLEEVE_TARGETS = {
    "us_equity":     {"target": 0.45, "min": 0.40, "max": 0.50},
    "intl_equity":   {"target": 0.15, "min": 0.10, "max": 0.20},
    "bonds":         {"target": 0.20, "min": 0.10, "max": 0.30},
    "brazil_equity": {"target": 0.10, "min": 0.05, "max": 0.15},
    "crypto":        {"target": 0.07, "min": 0.05, "max": 0.10},
    "cash":          {"target": 0.03, "min": 0.02, "max": 0.10},
}

CRYPTO_TARGETS = {
    "btc_fraction_of_crypto": {"target": 0.65, "min": 0.50, "max": 0.80},
    "eth_fraction_of_crypto": {"target": 0.25, "min": 0.15, "max": 0.40},
    "satellites_max_fraction": 0.20,
    "max_single_satellite": 0.10,
}

ACCOUNTS = [
    {"name": "Thiago 401k",     "broker": "Empower",    "type": "401k",    "tax": "tax_deferred"},
    {"name": "Spouse 401k",     "broker": "Principal",  "type": "401k",    "tax": "tax_deferred"},
    {"name": "Thiago Roth IRA", "broker": "M1 Finance", "type": "Roth_IRA","tax": "tax_free"},
    {"name": "M1 Taxable",      "broker": "M1 Finance", "type": "Taxable", "tax": "taxable"},
    {"name": "Binance US",      "broker": "Binance US", "type": "Crypto",  "tax": "taxable"},
    {"name": "Clear Corretora", "broker": "Clear",      "type": "Taxable", "tax": "brazil_taxable", "currency": "BRL"},
    {"name": "SoFi Checking",   "broker": "SoFi",       "type": "Bank",    "tax": "bank"},
]

VAULTS = [
    {"type": "future_investments", "min_balance": 500,  "investable": True,  "approval_required": False},
    {"type": "opportunity",        "min_balance": 1000, "investable": True,  "approval_required": True},
    {"type": "emergency",          "min_balance": None, "investable": False, "approval_required": "NEVER"},
]
```

---

## 6. INVESTMENT PHILOSOPHY & FRAMEWORKS ENCODED IN THE APP

This section defines the intellectual foundations that must be encoded into the engine logic and AI prompts. These are not optional decoration — they are functional specifications.

### 6.1 David Swensen / Yale Endowment Model (Primary Allocation Framework)
**Source:** *Unconventional Success* (2005) + Yale Endowment annual reports

Core principles to encode:
- Diversify across 6+ uncorrelated asset classes; avoid concentration in any one
- Bias heavily toward equity-like assets for long-term wealth building (70%+ equity-orientation)
- Include real assets (REITs via VNQ) for inflation protection + non-correlation
- Prefer low-cost index vehicles — minimize fee drag at all costs
- Rebalance disciplined back to targets — don't let drift compound
- Emerging markets exposure deserved (Brazil sleeve serves this role)
- Liquidity is often overvalued — be willing to accept some illiquidity premium

**Engine implementation:**
- Asset location optimizer considers Swensen's tax-location logic (bonds in tax-deferred, equities in Roth/taxable)
- REITs allocated within US equity sleeve; tracked separately
- Fee drag calculator: estimate annual drag from expense ratios across all holdings

### 6.2 Ray Dalio / All Weather / Risk Parity (Risk Framework)
**Source:** Bridgewater's *All Weather Story* + *Principles*

Core principles to encode:
- Economic seasons framework: assets perform differently across rising/falling growth + rising/falling inflation
- Risk parity: balance RISK across sleeves, not just dollar weights — a 45% equity allocation carries 80%+ of portfolio risk
- True diversification means low correlation, not just many positions
- Don't bet the farm on any single macro scenario
- Four regime quadrants determine positioning:
  - Rising growth + low inflation → equities win
  - Falling growth + low inflation → bonds win
  - Rising inflation → real assets, TIPS, commodities win
  - Falling growth + high inflation (stagflation) → gold, commodities, TIPS

**Engine implementation:**
- `risk_parity_weights` computed and stored in `risk_metrics` — shows what allocation SHOULD be if equalizing risk contributions
- `correlation_matrix` computed across sleeves — alert when correlations spike toward 1.0 (diversification breaking down)
- Macro regime classifier (simplified): use VIX + inflation proxies → classify current quadrant → surface in dashboard
- Risk contribution per sleeve shown alongside dollar weight in dashboard

### 6.3 Howard Marks / Market Cycles + Second-Level Thinking (Opportunity Framework)
**Source:** *The Most Important Thing* + *Mastering the Market Cycle*

Core principles to encode:
- Market cycles are predictable in direction, not timing — position for what's probable, not certain
- "High prices imply high risk, low prices imply low risk" — price paid matters more than asset quality
- Second-level thinking: what does everyone else think? What does that mean for what I should do?
- Contrarianism is not just opposing consensus; it's finding where consensus is WRONG
- The credit/liquidity cycle is the most volatile and impactful cycle
- Opportunity mode is most justified when fear is highest and everyone else is selling

**Engine implementation:**
- Opportunity tier triggers (Tier 1/2) are fundamentally Marks-style: buy when there's a margin of safety AND when others are panicking
- Cycle position indicator: simple composite of VIX, P/E ratios, yield spreads → "Early / Mid / Late / Peak" cycle stage
- Market sentiment gauge stored in `signals_runs.inputs_summary.market_sentiment`
- AI advisor explicitly instructed to ask: "Is this a case where fear/greed is distorting prices?"

### 6.4 Benjamin Graham / Warren Buffett (Valuation Framework)
**Source:** *The Intelligent Investor*, *Security Analysis*, Buffett's annual letters

Core principles to encode:
- **Margin of safety:** Only buy when price is meaningfully below intrinsic value — not by a whisker, but with room to breathe
  - Formula: `margin_of_safety_pct = (fair_value - current_price) / fair_value`
  - Buy zone requires minimum 15% margin of safety for individual stocks
  - ETFs use spread to long-term fair value instead
- **Mr. Market:** Treat market prices as an offer, not a verdict — sometimes they're wrong; exploit that
- **Circle of competence:** Only run DCF on businesses you understand; flag others as "outside circle"
- **Economic moat:** Assets with wide moats deserve premium valuation multiples
  - Moat types: brand power, switching costs, network effects, cost advantages, efficient scale
  - Stored in `assets.moat_rating` + `asset_valuations.moat_score`
- **Quality over cheapness:** Graham's cigar-butts evolved into Buffett's "wonderful companies at fair prices"
  - Quality score must be high before a cheap valuation triggers a buy

**Engine implementation:**
- `margin_of_safety_pct` computed for all assets with fair values, stored in `asset_valuations`
- Buy zone requires: `margin_of_safety_pct >= 0.15` AND `quality_score >= 0.6`
- DCF eligible only for stocks with stable FCF and moat_rating != "none"
- AI advisor references: "Does this trade respect margin of safety principles?"

### 6.5 Jack Bogle / Index Investing Principles (Cost Discipline)
**Source:** *The Little Book of Common Sense Investing*

Core principles to encode:
- Costs are the enemy of returns — every basis point of fees compounds against you
- Broad market exposure beats stock-picking for the majority of the portfolio
- Simplicity + consistency outperforms complexity + cleverness over long horizons
- Tax efficiency of index funds dramatically compounds over time

**Engine implementation:**
- Expense ratio tracker: aggregate weighted average fee across all holdings
- Benchmark: cost-optimized equivalent portfolio — "what would this look like in pure VTI/VXUS/BND?"
- Alert: if individual stock sleeve exceeds 25% of equity without justification

---

## 7. BUSINESS RULES (Engine Must Enforce All of These)

### Allocation & Rebalancing
- Drift threshold: 5% before triggering rebalance consideration
- Hard rebalance: max once every 30 days
- Execution frequency: max 1 day per week
- Min reinvest cadence: at least every 14 days
- **Soft rebalance first** (new money routing before selling positions)
- Min trade size: $50 USD
- Max single trade: 5% of portfolio
- Max daily trades: 10% of portfolio

### Volatility Regime Rules
```python
HIGH_VOL_TRIGGERS = {
    "vix_threshold": 30,
    "equity_daily_move_pct": 0.03,
    "crypto_daily_move_pct": 0.10,
    "defer_dca_days": (1, 3),
    "allow_opportunity_if_discounted": True,
}
DRAWDOWN_THRESHOLDS = {
    "alert": 0.25,           # 25% → alert + flag in UI
    "pause_automation": 0.40, # 40% → pause automated runs, require manual override
    "behavioral_max": 0.35,   # 35% → reference for IPS compliance discussion
}
```

### Opportunity Tiers (Marks-inspired)
```python
OPPORTUNITY_RULES = {
    "max_events_per_year": 5,
    "required_min_margin_of_safety": 0.15,   # Graham: never buy without safety buffer
    "tier_1": {
        "drawdown_from_6_12m_high": 0.30,
        "deploy_fraction_of_vault": 0.20,
        "max_portfolio_fraction": 0.02,
    },
    "tier_2": {
        "drawdown_from_6_12m_high": 0.50,
        "deploy_additional_vault_fraction": 0.30,
        "max_total_portfolio_fraction": 0.05,
    },
}
```

### Concentration Limits (Graham/Buffett-inspired)
- Max single stock: 7% of portfolio
- Max single sector: 25% of equity sleeve
- Max single country (ex-US): 15% of portfolio
- Crypto max: 10%, min: 3%
- Individual stocks max: 30% of equity sleeve (rest in ETFs)

### Tax Rules
- US taxable: prefer HIFO lot method to minimize short-term gains
- US taxable: harvest losses if unrealized loss > 10% AND no wash sale risk
- Brazil: R$20,000/month stock sale exemption (DARF triggered above)
- Brazil: prefer splitting large sales across months when near threshold
- Account location priority: bonds → tax-deferred accounts; growth → Roth IRA; income payers → avoid taxable

---

## 8. API ENDPOINTS

```python
# Allocation
POST  /run_allocation         # sleeve weights + drift + proposed trades → signals_run
GET   /daily_status           # total_value, sleeves vs targets, vault balances, regime, approvals

# Valuation
POST  /valuation_update       # triggers weekly valuation pipeline
GET   /valuation_summary      # latest rankings, margin of safety distribution

# Performance (NEW)
GET   /performance/summary    # TWR, MWR, Sharpe, Sortino, Calmar, max drawdown — all time periods
GET   /performance/attribution  # sleeve + asset attribution for given period
GET   /performance/benchmark    # portfolio vs benchmark comparison
GET   /performance/rolling      # rolling 1mo/3mo/1yr returns

# Simulation (NEW)
POST  /simulation/monte_carlo     # N=5000 simulations, contribution schedule, projection horizon
POST  /simulation/stress_test     # 2008-style, 2020-style, 2022-style drawdown scenarios
POST  /simulation/contribution_optimizer  # given $X, which account + asset optimizes drift + tax?
POST  /simulation/rebalance_preview  # show portfolio before/after proposed rebalance

# Tax (NEW)
GET   /tax/lots               # all open lots with FIFO/HIFO/Spec ID options
GET   /tax/estimate           # estimated annual tax liability (US)
GET   /tax/brazil_darf        # monthly running total vs R$20k exemption
POST  /tax/harvest_candidates # identify loss harvesting opportunities

# Alerts (NEW)
GET   /alerts/rules           # active alert rules
POST  /alerts/rules           # create new alert rule
GET   /alerts/history         # triggered alert history

# Reports (NEW)
POST  /reports/generate       # generate PDF report (daily/monthly/annual)
GET   /reports/list           # list generated reports

# Journal (NEW)
GET   /journal                # decision log entries
POST  /journal                # log a decision (followed/overrode/deferred)

# System
GET   /health
```

---

## 9. PERFORMANCE ENGINE (Full Implementation Spec)

All metrics computed in `services/performance_engine.py` using `pandas` and `numpy`.

### Time-Weighted Return (TWR)
The gold standard for measuring investment performance independent of cash flows.
```python
def compute_twr(daily_values: pd.Series, cash_flows: pd.DataFrame) -> float:
    """
    Modified Dietz / sub-period linking method.
    For each sub-period between cash flows: r = (V_end - V_start - CF) / (V_start + weighted_CF)
    TWR = product of (1 + r_i) for all sub-periods - 1
    """
```

### Money-Weighted Return (MWR / IRR)
Reflects the actual return given YOUR timing of contributions.
```python
def compute_mwr(cash_flows: list[tuple[date, float]], current_value: float) -> float:
    """
    Solve for IRR: NPV = 0 using scipy.optimize.brentq
    Positive cash flows = contributions, negative = withdrawals
    """
```

### Risk-Adjusted Metrics
```python
RISK_FREE_RATE = 0.045  # Update quarterly to current 10yr Treasury yield

def compute_sharpe(returns: pd.Series, rf: float = RISK_FREE_RATE) -> float:
    """(annualized_return - rf) / annualized_std"""

def compute_sortino(returns: pd.Series, rf: float = RISK_FREE_RATE) -> float:
    """(annualized_return - rf) / annualized_downside_std
    Downside std uses only negative returns — Sortino is superior to Sharpe for
    long-only investors because it doesn't penalize upside volatility."""

def compute_calmar(returns: pd.Series) -> float:
    """annualized_return / max_drawdown — best for evaluating drawdown resilience"""

def compute_max_drawdown(values: pd.Series) -> tuple[float, date, date]:
    """Returns (max_drawdown_pct, peak_date, trough_date)"""

def compute_beta(portfolio_returns: pd.Series, benchmark_returns: pd.Series) -> float:
    """Covariance(portfolio, benchmark) / Variance(benchmark)"""

def compute_information_ratio(active_returns: pd.Series) -> float:
    """Mean active return / std of active returns — measures consistency of alpha"""
```

### Performance Attribution (Brinson-Hood-Beebower)
```python
def compute_attribution(
    portfolio_weights: dict,
    portfolio_returns: dict,
    benchmark_weights: dict,
    benchmark_returns: dict,
) -> dict:
    """
    For each sleeve:
    - Allocation effect: (w_p - w_b) * (r_b - r_total_b)
    - Selection effect: w_b * (r_p - r_b)
    - Interaction effect: (w_p - w_b) * (r_p - r_b)
    Total active return = sum of all effects
    """
```

---

## 10. SIMULATION ENGINE (Full Implementation Spec)

### Monte Carlo Projection
```python
def run_monte_carlo(
    current_value: float,
    monthly_contribution: float,
    years: int,
    sleeve_weights: dict,
    n_simulations: int = 5000,
    return_assumptions: dict = None,  # per-sleeve mean + std
) -> MonteCarloResult:
    """
    Run N simulations using:
    1. Historical bootstrap (default): randomly sample from historical monthly returns
    2. Parametric: use mean/std assumptions per sleeve
    
    Returns:
    - Percentile bands: 5th, 10th, 25th, 50th (median), 75th, 90th, 95th
    - Probability of reaching target values
    - Probability of portfolio surviving 30yr withdrawal at 4% rate
    
    Visualize as fan chart with shaded percentile bands.
    """

RETURN_ASSUMPTIONS = {
    # Historical annualized returns (conservative estimates)
    "us_equity":     {"mean": 0.095, "std": 0.165},  # VTI historical
    "intl_equity":   {"mean": 0.075, "std": 0.175},
    "bonds":         {"mean": 0.035, "std": 0.065},
    "brazil_equity": {"mean": 0.090, "std": 0.280},  # higher vol
    "crypto":        {"mean": 0.150, "std": 0.700},  # BTC/ETH long-term
    "cash":          {"mean": 0.045, "std": 0.010},
}
```

### Stress Testing
```python
STRESS_SCENARIOS = {
    "2008_gfc": {
        "name": "2008 Global Financial Crisis",
        "us_equity": -0.51, "intl_equity": -0.46, "bonds": +0.12,
        "brazil_equity": -0.58, "crypto": None, "cash": 0.0,
    },
    "2020_covid": {
        "name": "2020 COVID Crash (Feb–Mar)",
        "us_equity": -0.34, "intl_equity": -0.33, "bonds": +0.04,
        "brazil_equity": -0.46, "crypto": -0.40, "cash": 0.0,
    },
    "2022_rate_shock": {
        "name": "2022 Rate Shock",
        "us_equity": -0.19, "intl_equity": -0.16, "bonds": -0.15,
        "brazil_equity": +0.08, "crypto": -0.65, "cash": +0.02,
    },
    "stagflation_1970s": {
        "name": "1970s Stagflation Analog",
        "us_equity": -0.45, "intl_equity": -0.40, "bonds": -0.25,
        "brazil_equity": -0.30, "crypto": -0.50, "cash": +0.06,
    },
    "brazil_crisis": {
        "name": "Brazil Currency/Political Crisis",
        "us_equity": -0.05, "intl_equity": -0.08, "bonds": 0.0,
        "brazil_equity": -0.50, "crypto": -0.20, "cash": 0.0,
    },
}
```

---

## 11. RISK ENGINE (Full Implementation Spec)

```python
def compute_risk_parity_weights(
    sleeve_vols: dict,         # annualized volatility per sleeve
    correlation_matrix: np.ndarray,
) -> dict:
    """
    Dalio All-Weather logic: compute weights such that each sleeve contributes
    equal risk to the total portfolio variance.
    Uses scipy.optimize.minimize to find weights w such that:
    risk_contribution_i = w_i * (Sigma * w)_i / portfolio_volatility
    is equal for all i.
    Returns risk-parity weights for COMPARISON only — not for forced rebalancing.
    Shows "what your allocation would look like if you balanced risk, not dollars."
    """

def compute_correlation_matrix(returns_by_sleeve: dict) -> pd.DataFrame:
    """
    Rolling 90-day correlation matrix across sleeves.
    Alert when any pair correlation exceeds 0.85 (diversification breakdown).
    """

def compute_var(portfolio_returns: pd.Series, confidence: float = 0.95) -> float:
    """
    Historical VaR: return the Nth percentile of daily returns.
    95% VaR: "On 95% of days, daily loss will not exceed X%"
    """
```

---

## 12. FX ENGINE (USD/BRL)

```python
def normalize_to_usd(
    brl_value: float,
    usd_brl_rate: float,
) -> float:
    """Convert BRL values to USD for portfolio-level aggregation."""

def compute_fx_attribution(
    brazil_sleeve_return_brl: float,
    brazil_sleeve_return_usd: float,
) -> float:
    """
    FX contribution = difference between USD and BRL return.
    Positive = BRL strengthened vs USD (helped your USD returns)
    Negative = BRL weakened (hurt your USD returns)
    """

FX_DATA_SOURCE = "yfinance"  # symbol: "USDBRL=X"
FX_ALERT_THRESHOLD = 0.10    # alert when USD/BRL moves >10% in 30 days
```

---

## 13. TAX LOT ENGINE

```python
class LotMethod(Enum):
    FIFO = "fifo"            # First in, first out (IRS default)
    HIFO = "hifo"            # Highest cost first (minimizes gains) ← preferred
    SPEC_ID = "spec_id"      # Specific lot identification

def select_lots_to_sell(
    lots: list[TaxLot],
    quantity_to_sell: float,
    method: LotMethod = LotMethod.HIFO,
    account_tax_treatment: str = "taxable",
) -> list[TaxLot]:
    """
    For taxable accounts: default to HIFO to minimize realized gains.
    For tax-advantaged (401k, Roth): tax method irrelevant, use FIFO.
    Flag wash sales (buy same security within 30 days of sale at a loss).
    """

def estimate_tax_impact(
    lot: TaxLot,
    current_price: float,
    marginal_rate_lt: float = 0.15,    # long-term cap gains rate
    marginal_rate_st: float = 0.32,    # short-term rate (ordinary income)
) -> dict:
    """Returns estimated tax, after-tax proceeds, holding period classification."""
```

---

## 14. AI ADVISOR (Claude API Integration)

### Model
`claude-sonnet-4-20250514` — non-negotiable.

### Behavioral Constraints
- AI is NOT the source of truth. Python engine is.
- AI receives structured JSON, returns structured JSON.
- Malformed AI response → log error, store fallback, do NOT crash the run.
- AI output stored in `signals_runs.ai_validation_summary`.

### Investment Philosophy Instructions for AI System Prompt
The AI advisor system prompt MUST include these philosophical anchors:
```
You are the AI advisor for a sophisticated private wealth OS. Apply these frameworks:

1. SWENSEN: Is the proposed allocation consistent with long-term diversification across 
   uncorrelated asset classes? Are costs minimized?

2. DALIO/RISK PARITY: Does each sleeve contribute proportional risk, not just proportional 
   dollars? What economic season does the current environment resemble?

3. MARKS/CYCLES: Where are we in the market cycle? Is fear or greed dominant? 
   Is this trade contrarian in a good way or just contrarian?

4. GRAHAM/BUFFETT: Is there a sufficient margin of safety on any individual stock trade?
   Does the business have a durable economic moat? Are we paying fair value or overpaying?

5. BOGLE: What is the fee drag of this portfolio? Would a simpler, cheaper alternative 
   achieve the same outcome?

Always validate: Does the proposed action respect these principles? 
Flag violations clearly. Never override the Python engine's numerical constraints.
```

### Input Payload Structure
```json
{
  "run_context": {"timestamp", "event_type", "volatility_regime", "market_cycle_stage", "notes"},
  "ips_summary": {"risk_profile", "max_crypto_pct", "target_allocations"},
  "strategy_config": {},
  "portfolio_snapshot": {"total_value_usd", "sleeve_weights", "risk_parity_weights", "correlation_summary"},
  "valuation_snapshot": {"top_value_candidates", "tier_opportunities", "margin_of_safety_distribution"},
  "performance_snapshot": {"twr_ytd", "vs_benchmark", "sharpe", "max_drawdown"},
  "news_and_research": {"macro_summary", "macro_regime", "asset_news", "earnings_alerts"},
  "proposed_trades": [{"account", "type", "symbol", "amount_usd", "reason", "tax_risk_level", "margin_of_safety_pct"}]
}
```

### Output Structure
```json
{
  "validation": {"overall_status": "ok|warning|block", "issues": []},
  "investment_framework_check": {
    "swensen_alignment": "pass|warning|fail",
    "dalio_risk_balance": "pass|warning|fail",
    "marks_cycle_read": "string — where in the cycle and what it implies",
    "graham_margin_of_safety": "pass|warning|fail",
    "bogle_cost_check": "pass|warning|fail"
  },
  "trade_recommendations": {"summary", "per_trade_feedback": [], "suggested_adjustments": []},
  "portfolio_assessment": {"risk_posture", "diversification_comment", "factor_tilts", "benchmark_comparison"},
  "macro_and_opportunity_commentary": {"macro_regime", "cycle_position", "macro": [], "opportunities": [], "risks_to_watch": []},
  "explanation_for_user": {"short_summary": "", "detailed_bullets": []}
}
```

---

## 15. REAL-TIME ALERT SYSTEM

### Alert Rules (All Must Be Implemented)
```python
BUILT_IN_ALERT_RULES = [
    # Portfolio-level
    {"name": "Drawdown Alert",          "type": "drawdown",     "threshold": 0.25, "channel": "telegram"},
    {"name": "Automation Pause",        "type": "drawdown",     "threshold": 0.40, "channel": "telegram", "action": "pause_runs"},
    {"name": "Sleeve Drift Breach",     "type": "drift",        "threshold": 0.05, "channel": "telegram"},
    {"name": "Correlation Spike",       "type": "correlation",  "threshold": 0.85, "channel": "telegram"},
    
    # Opportunity
    {"name": "Tier 1 Opportunity",      "type": "opportunity",  "tier": 1, "channel": "telegram", "priority": "HIGH"},
    {"name": "Tier 2 Opportunity",      "type": "opportunity",  "tier": 2, "channel": "telegram", "priority": "HIGH"},
    
    # Asset-level
    {"name": "Asset Hits Sell Target",  "type": "sell_target",  "channel": "telegram"},
    {"name": "Earnings Alert",          "type": "earnings",     "days_ahead": 3, "channel": "telegram"},
    
    # Brazil tax
    {"name": "DARF Warning",            "type": "brazil_darf",  "threshold_pct": 0.80, "channel": "telegram"},
    
    # FX
    {"name": "BRL Weakens >10%",        "type": "fx_move",      "pair": "USDBRL", "threshold": 0.10, "channel": "telegram"},
    
    # Deposit
    {"name": "Deposit Detected",        "type": "deposit",      "channel": "telegram"},
]
```

### Telegram Integration
```python
# All alerts sent via Telegram Bot API
# Message format: emoji + title + key numbers + recommended action + link to app
# Approval flows: inline keyboard buttons → approve/reject → webhook back to API
TELEGRAM_BOT_TOKEN = env("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = env("TELEGRAM_CHAT_ID")
```

---

## 16. DECISION JOURNAL

One of the most differentiated features. Every time the system proposes something and you act (or don't), capture why. Then track outcomes.

```python
class JournalActionType(Enum):
    FOLLOWED = "followed"           # system said X, you did X
    OVERRODE = "overrode"           # system said X, you did Y
    DEFERRED = "deferred"           # system said X, you waited
    MANUAL_TRADE = "manual_trade"   # trade not from system recommendation

# Automated outcome backfill (n8n workflow, runs 30d and 90d after each journal entry):
# 1. Find journal entries without outcome_30d
# 2. Compute asset/portfolio return since decision_date
# 3. Compare against what would have happened if system recommendation was followed
# 4. Store delta in outcome_30d / outcome_90d
```

**Journal page in UI shows:**
- Decision log table (date, action type, asset, system rec vs actual, reasoning)
- Override accuracy: when you overrode the system, were you right? (30d/90d outcome)
- Follow accuracy: when you followed the system, did it work? (30d/90d outcome)
- Pattern detection: "You override the system most often during high volatility periods. Your 90-day outcomes when overriding are X% vs Y% when following."

---

## 17. PERFORMANCE PAGE SPEC

URL: `/performance`

**Section 1 — Returns Summary** (all time periods: 1mo, 3mo, 6mo, YTD, 1yr, 3yr, all-time)
- TWR vs MWR side-by-side
- Benchmark comparison (primary + secondary)
- Annualized return, total return

**Section 2 — Risk Metrics**
- Sharpe, Sortino, Calmar ratios with interpretation badges (poor/fair/good/excellent)
- Max drawdown + duration (peak date → trough date → recovery date)
- Annualized volatility vs benchmark volatility
- Beta, R²

**Section 3 — Attribution** (Brinson-Hood-Beebower)
- Stacked bar: allocation effect + selection effect by sleeve
- Top 5 contributors, bottom 5 detractors (by asset)
- FX contribution (BRL/USD impact)

**Section 4 — Rolling Analysis**
- Rolling 12-month Sharpe (line chart)
- Rolling return distribution (histogram: how often have you beaten benchmark?)

**Section 5 — Risk Parity Comparison**
- Your actual allocation vs risk-parity-equivalent weights
- Risk contribution donut (how much risk does each sleeve actually contribute?)

---

## 18. PROJECTIONS PAGE SPEC

URL: `/projections`

**Tab 1 — Monte Carlo**
- Inputs: monthly contribution, projection years (default 20), allocation model (current vs Swensen vs All-Weather)
- Fan chart: 5th/25th/50th/75th/95th percentile bands
- Key outputs: median ending value, probability of reaching $X target, 4% SWR survival probability

**Tab 2 — Contribution Simulator**
- "If I add $2,000 this paycheck, where should it go?"
- Shows optimal allocation across accounts + assets to minimize drift + maximize tax efficiency
- Before/after allocation donut

**Tab 3 — Stress Test**
- Select scenario: GFC 2008, COVID 2020, 2022 Rate Shock, Stagflation, Brazil Crisis
- Show portfolio value impact + recovery time projection
- Compare: "With your current allocation" vs "With risk-parity weights"

**Tab 4 — Retirement Readiness**
- Target retirement age input
- 4% SWR analysis (Trinity Study)
- Required savings rate to hit target
- Current trajectory vs needed trajectory

---

## 19. FRONTEND PAGES — COMPLETE SPEC

### /dashboard
Cards: Net Worth (USD + BRL equivalent), Sleeve Allocation donut (actual vs target with drift indicators), Vault Balances (3 cards: Future/Opportunity/Emergency), Regime Status Badge (Normal/High-Vol/Opportunity + cycle position indicator)
Quick stats: Today's P&L, YTD TWR vs benchmark, Max drawdown

### /signals
Table: signals_runs newest first. Expandable row: proposed_trades + AI investment framework check + status badges.
Filter by: status, event_type, date range.
Approval buttons inline for needs_approval rows.

### /assets
Sortable table: symbol, class, price, margin_of_safety, value_score, momentum_score, quality_score, moat_rating, fair_value, buy_target, sell_target, rank.
Filters: asset_class, region, tier, min_margin_of_safety, moat.
Detail drawer: full DCF assumptions, score breakdown, Graham margin of safety visualization, news feed for asset.

### /performance
Full spec in Section 17.

### /projections
Full spec in Section 18.

### /tax
Open lots table: symbol, account, acquisition_date, quantity, cost_basis, current_value, unrealized_gain, holding_period (ST/LT), tax_impact_if_sold.
Lot method selector (FIFO/HIFO/Spec ID per account).
Brazil DARF tracker: monthly progress bar to R$20k limit.
Loss harvesting candidates: flagged lots with suggested pairs (avoid wash sales).

### /research
News feed (Finnhub, sorted by importance + recency, filtered to held/watched assets only).
Earnings calendar: next 30 days for positions.
Research docs: curated long-form with AI summary + "impact on my valuation" field.

### /journal
Decision log table. Override accuracy scorecard. Pattern analysis (Claude AI-generated monthly).

### /config
Active strategy config JSON viewer. Version history. Allocation model comparison (current vs Swensen vs All-Weather vs user-defined).

---

## 20. SEED DATA (Assets)

```python
SEED_ASSETS = [
    # Core ETFs
    {"symbol": "VTI",  "name": "Vanguard Total Stock Market ETF", "class": "US_equity",   "expense_ratio": 0.0003},
    {"symbol": "VXUS", "name": "Vanguard Total Intl Stock ETF",   "class": "Intl_equity",  "expense_ratio": 0.0007},
    {"symbol": "BND",  "name": "Vanguard Total Bond Market ETF",  "class": "Bond",          "expense_ratio": 0.0003},
    {"symbol": "BNDX", "name": "Vanguard Total Intl Bond ETF",    "class": "Bond",          "expense_ratio": 0.0007},
    {"symbol": "VNQ",  "name": "Vanguard Real Estate ETF",        "class": "US_equity",    "sector": "REIT", "expense_ratio": 0.0012},
    {"symbol": "TIP",  "name": "iShares TIPS Bond ETF",           "class": "Bond",          "expense_ratio": 0.0019},  # Swensen inflation hedge
    # Individual stocks
    {"symbol": "GOOG", "class": "US_equity", "moat": "wide",   "dcf_eligible": True},
    {"symbol": "AMZN", "class": "US_equity", "moat": "wide",   "dcf_eligible": True},
    {"symbol": "AAPL", "class": "US_equity", "moat": "wide",   "dcf_eligible": True},
    {"symbol": "META", "class": "US_equity", "moat": "wide",   "dcf_eligible": True},
    {"symbol": "MSFT", "class": "US_equity", "moat": "wide",   "dcf_eligible": True},
    {"symbol": "NVDA", "class": "US_equity", "moat": "narrow", "dcf_eligible": True},
    {"symbol": "CRM",  "class": "US_equity", "moat": "narrow", "dcf_eligible": True},
    {"symbol": "PLTR", "class": "US_equity", "moat": "narrow", "dcf_eligible": False},
    {"symbol": "ARM",  "class": "US_equity", "moat": "narrow", "dcf_eligible": False},
    # Crypto
    {"symbol": "BTC",  "class": "Crypto", "dcf_eligible": False},
    {"symbol": "ETH",  "class": "Crypto", "dcf_eligible": False},
    {"symbol": "SOL",  "class": "Crypto", "dcf_eligible": False},
    {"symbol": "LINK", "class": "Crypto", "dcf_eligible": False},
    # Brazil
    {"symbol": "PETR4", "class": "Brazil_equity", "currency": "BRL"},
    {"symbol": "VALE3", "class": "Brazil_equity", "currency": "BRL"},
    {"symbol": "ITUB4", "class": "Brazil_equity", "currency": "BRL"},
    # Benchmarks
    {"symbol": "SPY",   "class": "Benchmark"},
    {"symbol": "ACWI",  "class": "Benchmark"},
    {"symbol": "AGG",   "class": "Benchmark"},
]
```

---

## 21. ENVIRONMENT VARIABLES

```bash
# backend/.env
SUPABASE_URL=
SUPABASE_SERVICE_KEY=
ANTHROPIC_API_KEY=
FINNHUB_API_KEY=            # free tier, for news + earnings
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
REDIS_URL=                  # Upstash Redis URL
MARKET_DATA_PROVIDER=yfinance
APP_ENV=development
SECRET_KEY=

# frontend/.env.local
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## 22. CODING STANDARDS

### Python (Backend)
- All business logic in `services/`, never in `api/` routes
- All DB access via `repositories/`, never raw SQL in services
- Pydantic models for all request/response (no raw dicts)
- All config values from `strategy_configs` table; never hardcoded in services
- Every function: type hints + docstring + error handling
- Logging: structured Python `logging`, always log run_id
- Never swallow exceptions silently

### TypeScript (Frontend)
- All Supabase/API calls in `lib/` — never inline in components
- No `any` types
- Loading + error states for every data fetch
- Monetary: USD 2dp, BRL 2dp with "R$" prefix, percentages 1dp with +/- sign
- All charts use consistent color scheme: green=positive/above-target, red=negative/below-target, yellow=warning

### Performance
- Redis cache: market data (15min TTL), portfolio snapshots (5min TTL)
- Monte Carlo runs async (background task) — don't block API response
- Heavy computations (attribution, correlation matrix) computed nightly by n8n, cached

---

## 23. ADDITIONAL PYTHON DEPENDENCIES

```toml
[tool.uv.dependencies]
fastapi = ">=0.115"
uvicorn = ">=0.30"
supabase = ">=2.0"
pydantic-settings = ">=2.0"
yfinance = ">=0.2"
anthropic = ">=0.40"
pandas = ">=2.0"
numpy = ">=1.26"
scipy = ">=1.12"        # Monte Carlo, optimization, statistics
redis = ">=5.0"          # Upstash Redis client
httpx = ">=0.27"         # Async HTTP (Telegram, Finnhub)
weasyprint = ">=62"      # PDF report generation
python-dateutil = ">=2.9"
python-dotenv = ">=1.0"
```

---

## 24. PHASE BUILD PLAN

### Phase 1 — Foundation (Start here after reading this file)
**Goal:** Running app, real data, health check green.
- Directory scaffold, pyproject.toml, Next.js init with shadcn/ui
- FastAPI main.py + /health endpoint
- Supabase schema (migrations 001–004)
- Dashboard page with hardcoded placeholder data
- README with setup instructions

**Success:** `uvicorn app.main:app` → 200 on /health. `pnpm dev` → dashboard renders.

### Phase 2 — Portfolio Engine
- Allocation engine: sleeve weights, drift detection, soft rebalance
- Volatility regime detection
- /run_allocation endpoint writing to signals_runs
- Signals page in UI

### Phase 3 — Valuation Engine
- Factor scoring (value/momentum/quality) + moat scoring
- DCF for eligible stocks (Graham margin of safety)
- Margin of safety computation for all assets
- Assets page in UI with score filters + detail drawer

### Phase 4 — Performance Analytics
- TWR, MWR engines (pandas/numpy)
- Sharpe, Sortino, Calmar
- Performance attribution (Brinson-Hood-Beebower)
- Performance page in UI
- portfolio_snapshots written daily by n8n

### Phase 5 — AI Layer
- Claude API integration with investment philosophy prompt
- Full payload construction + response validation
- AI commentary surfaced in signals page + journal

### Phase 6 — Real-Time Alerts + Automations
- Telegram bot setup
- Alert rule engine
- n8n daily check workflow
- Opportunity scan workflow

### Phase 7 — Simulation + Projections
- Monte Carlo engine (5000 simulations, fan chart)
- Stress test scenarios
- Contribution optimizer
- Projections page in UI

### Phase 8 — Tax Engine
- Tax lot tracking (HIFO/FIFO/Spec ID)
- Brazil DARF tracker
- Loss harvesting candidates
- Tax page in UI

### Phase 9 — Decision Journal + Reports
- Journal engine + outcome backfill automation
- Override accuracy analytics
- Monthly PDF report generation
- Journal page in UI

### Phase 10 — PWA + Polish
- PWA manifest + service worker (offline read-only mode)
- Push notifications via Telegram deeplink
- FX attribution
- Risk parity comparison view
- Correlation heatmap

---

## 25. HARD CONSTRAINTS (NEVER VIOLATE)

- **Emergency vault is NEVER investable** — any code path touching it for investment is a bug
- **Opportunity vault requires explicit approval** — never auto-execute
- **No full auto-execution** in v1 — propose only; approve manually or via Telegram
- **No financial advice** — this is a personal automation tool
- **AI validation failures must NOT block runs** — degrade gracefully, log, continue
- **No deletion of accounts, lots, journal entries** — soft-delete only (`is_active = false`)
- **All amounts normalized to USD for portfolio-level math** — BRL positions converted using live rate
- **Single user only** — no multi-tenant logic

---

## 26. FACTOR RESEARCH — ACADEMIC FOUNDATIONS (Engine Implementation Guide)

This section defines the academic framework that must be encoded in `services/valuation_engine.py` and `services/risk_engine.py`. These are not optional — they are functional specifications grounded in 50+ years of peer-reviewed research.

### 26.1 Fama-French Five-Factor Model (Primary Academic Backbone)
**Source:** Fama & French (2015), *Journal of Financial Economics*

The five factors with documented persistent return premiums:

| Factor | Definition | How It Scores in OvelhaInvest |
|---|---|---|
| **Market (Beta)** | Excess return over risk-free rate | Already tracked via beta_vs_primary |
| **Size (SMB)** | Small minus big — small caps outperform | Embedded in asset_class weighting |
| **Value (HML)** | High minus low B/P — cheap beats expensive | Core of `value_score` |
| **Profitability (RMW)** | Robust minus weak operating profitability | Core of `quality_score` |
| **Investment (CMA)** | Conservative minus aggressive asset growth | Secondary quality input |

**Momentum (Carhart 4th Factor)** — not in Fama-French 5 but universally accepted:
- 12-month price return excluding most recent month (12-1 momentum)
- Core of `momentum_score`

```python
# Factor score mapping in valuation_engine.py
FACTOR_SCORE_INPUTS = {
    "value_score": {
        "inputs": ["pe_percentile_inverse", "ps_percentile_inverse", "pb_percentile_inverse", "dividend_yield_normalized"],
        "weights": [0.35, 0.25, 0.25, 0.15],
        "fama_french": "HML",
    },
    "momentum_score": {
        "inputs": ["return_12_1_month", "return_3_month", "earnings_revision_trend"],
        "weights": [0.60, 0.25, 0.15],
        "fama_french": "Carhart_MOM",
    },
    "quality_score": {
        "inputs": ["roe_normalized", "operating_margin_normalized", "debt_to_equity_inverse", "earnings_stability"],
        "weights": [0.30, 0.25, 0.25, 0.20],
        "fama_french": "RMW + CMA",
    },
}
```

### 26.2 Factor Regime Rules (Dynamic Weighting)
**Source:** MSCI 50-year factor study (2025), iShares Dynamic Factor research

Factor performance is cyclical and regime-dependent. The composite score weights must SHIFT based on detected macro regime:

```python
FACTOR_COMPOSITE_WEIGHTS_BY_REGIME = {
    # Dalio Economic Season → Factor Tilt
    "rising_growth_low_inflation": {    # Bull market, tech-driven
        "value_weight": 0.25,
        "momentum_weight": 0.45,        # Momentum dominates in trending markets
        "quality_weight": 0.30,
        "rationale": "Momentum strongest in sustained bull runs (2023-2024 Magnificent 7)"
    },
    "falling_growth_low_inflation": {   # Recession
        "value_weight": 0.40,           # Value + quality defensive
        "momentum_weight": 0.15,        # Momentum crashes on trend reversals
        "quality_weight": 0.45,
        "rationale": "Quality resilient in downturns; momentum prone to crash"
    },
    "rising_inflation": {               # Inflation shock (2022-style)
        "value_weight": 0.50,           # Value / real assets outperform
        "momentum_weight": 0.20,
        "quality_weight": 0.30,
        "rationale": "Value and real assets hedge inflation; growth gets destroyed"
    },
    "falling_inflation_growth_recovery": {  # Post-crash recovery
        "value_weight": 0.35,
        "momentum_weight": 0.35,
        "quality_weight": 0.30,
        "rationale": "Balanced — recovery rewards both value and early momentum"
    },
    "normal": {                         # Default / unclear regime
        "value_weight": 0.40,
        "momentum_weight": 0.30,
        "quality_weight": 0.30,
        "rationale": "Fama-French baseline weights; no regime conviction"
    },
}
```

### 26.3 Multi-Factor Combination Rule
**Source:** 150-year momentum study (Alpha Architect, 2025); Robeco factor research

Key rule: **factors must be combined, never used in isolation.**

```python
def compute_composite_score(
    value_score: float,
    momentum_score: float,
    quality_score: float,
    regime: str = "normal",
) -> float:
    """
    CRITICAL: Low-vol is NOT a separate score. It is a MODIFIER on quality.
    A high-quality stock with low volatility gets a quality bonus (+0.05).
    A high-quality stock with high volatility gets no bonus.
    This prevents the low-vol crowding problem (2015-2024 underperformance).
    
    Regime-aware weighting from FACTOR_COMPOSITE_WEIGHTS_BY_REGIME.
    """

# Rule: Require all three factors to be above threshold for buy signal
# (Prevents "cheap but deteriorating" and "high momentum but junk quality" traps)
BUY_SIGNAL_REQUIREMENTS = {
    "min_value_score": 0.40,      # Not wildly overvalued
    "min_momentum_score": 0.35,   # Not in active downtrend
    "min_quality_score": 0.55,    # Quality is the non-negotiable floor
    "min_composite_score": 0.55,  # Overall composite minimum
    "min_margin_of_safety": 0.10, # Graham floor (reduced for ETFs)
}
```

### 26.4 Backtesting Benchmarks (What "Good" Looks Like)
**Source:** MSCI World factor indexes, 50-year data (1975-2025)

These are the reference points your valuation engine should be calibrated against:

| Factor | 50yr Ann. Return | Sharpe | Max Drawdown | Notes |
|---|---|---|---|---|
| Market (MSCI World) | ~10.5% | 0.45 | -54% | Baseline |
| Momentum | 13.5% | 0.62 | -65% | Best return, crash risk |
| Enhanced Value | 13.3% | 0.58 | -58% | Second best |
| Quality | 11.8% | 0.55 | -45% | Best risk-adjusted of equity factors |
| Min Volatility | 10.2% | **0.70** | -38% | **Best Sharpe, lowest drawdown** |
| Multi-factor blend | 12.1% | 0.65 | -42% | Best combined |

**Key insight encoded in the engine:** Quality has the best risk-adjusted return among pure equity factors AND the lowest drawdown among growth factors. Quality is the anchor. Momentum and value are tilts.

### 26.5 Factor Timing Signals (Macro Regime Classifier Inputs)
```python
MACRO_REGIME_SIGNALS = {
    # Growth signals
    "ism_manufacturing": "yfinance or Finnhub macro feed",  # >50 = expansion
    "yield_curve_slope": "10yr - 2yr Treasury spread",     # inverted = recession risk
    "vix_level": "already tracked",
    
    # Inflation signals
    "tips_breakeven": "TIP vs IEF spread proxy",           # implied inflation expectations
    "commodity_momentum": "DJP or GSG 3mo return",
    
    # Credit signals
    "hy_spread_proxy": "HYG vs AGG spread",               # credit stress = risk-off
    
    # Derived regime (simplified):
    # growth_up = ISM > 50 AND yield curve not inverted
    # inflation_up = TIPS breakeven > 2.5% OR commodities momentum > 10%
    # → Map to Dalio 4-quadrant → → → select FACTOR_COMPOSITE_WEIGHTS_BY_REGIME key
}
```

---

## 27. GOOGLE STITCH + DESIGN WORKFLOW

### 27.1 Tool Roles — What Each Does

| Tool | Role | When Used |
|---|---|---|
| **Google Stitch** | AI UI design → high-fidelity mockups → DESIGN.md export | Before writing any React component |
| **Stitch MCP** | Live design context piped into Claude Code | During all frontend development |
| **Nano Banana 2** | AI image generation (icons, illustrations, empty states) | Visual assets only, not layouts |
| **Claude Code** | Builds the actual React/Next.js code using design context | After DESIGN.md is committed |

### 27.2 Stitch MCP Setup (One-Time, Required Before Phase 2 Frontend)

```bash
# 1. Enable Stitch API in Google Cloud
gcloud auth login
gcloud config set project YOUR_GOOGLE_PROJECT_ID
gcloud auth application-default login
gcloud beta services mcp enable stitch.googleapis.com

# 2. Install the official Stitch skill for Claude Code
npx skills add google-labs-code/stitch-skills --skill stitch-design --global

# 3. Add Stitch MCP to Claude Code config (~/.claude.json)
# (Claude Code handles this automatically after skill install)
# Manual fallback:
{
  "mcpServers": {
    "stitch": {
      "command": "npx",
      "args": ["-y", "stitch-mcp"],
      "env": { "GOOGLE_CLOUD_PROJECT": "YOUR_PROJECT_ID" }
    }
  }
}

# 4. Verify connection
claude mcp list | grep stitch
```

### 27.3 DESIGN.md — The Design System Contract

After generating designs in Stitch, export DESIGN.md and commit it to the repo root.
This file is the single source of truth for all frontend styling decisions.
Claude Code reads it automatically when building components.

The DESIGN.md for OvelhaInvest must specify:
- Color palette: dark background (#0a0a0a), surface (#141414), border (#222), text-primary (#f5f5f5), text-muted (#888)
- Accent: green (#22c55e) for positive/gains, red (#ef4444) for negative/losses, amber (#f59e0b) for warnings
- Typography: Inter (UI), JetBrains Mono (numbers/tickers)
- Component patterns: dense tables, compact cards, minimal whitespace
- Chart palette: green/red for P&L, blue spectrum for multi-series

### 27.4 Design System — OvelhaInvest Visual Language

Before generating Stitch screens, internalize this design system. Every screen must follow it exactly.

**Design Inspiration:** Linear.app + Vercel Dashboard + Raycast + Stripe Dashboard — 2026 premium AI product aesthetic. NOT Bloomberg boxy. NOT default shadcn. NOT squared-off corporate.

**Core Visual Principles:**
- Glassmorphism cards: `backdrop-blur-xl bg-white/5 border border-white/10 rounded-2xl`
- Subtle gradient backgrounds: deep space dark `#050508` with faint radial glow behind hero elements
- Gradient accents: emerald-to-cyan for positive `(#10b981 → #06b6d4)`, rose-to-red for negative `(#f43f5e → #ef4444)`, violet-to-purple for AI/intelligence features
- Floating sidebar: glassmorphic, blurred, not solid black
- Cards have soft inner glow on hover: `shadow-[0_0_30px_rgba(16,185,129,0.15)]`
- Numbers use Geist Mono or JetBrains Mono — large, confident, with color-coded signs
- Typography: Geist Sans (headings) + Inter (body) + JetBrains Mono (all financial numbers)
- Smooth transitions: 200ms ease on all interactive elements
- Charts: glowing line strokes with area fill gradient, NOT flat bars
- Status badges: pill-shaped with colored glow, NOT squared chips
- Empty states: subtle animated gradient placeholder, NOT blank white boxes
- Spacing: generous padding inside cards (p-6), tight between data rows

**Color Tokens:**
```
Background:     #050508  (deep space)
Surface:        rgba(255,255,255,0.04)  (glass card)
Surface-hover:  rgba(255,255,255,0.07)
Border:         rgba(255,255,255,0.08)
Border-accent:  rgba(16,185,129,0.3)   (green glow border)
Text-primary:   #f8fafc
Text-secondary: #94a3b8
Text-muted:     #475569
Positive:       #10b981  (emerald)
Positive-glow:  rgba(16,185,129,0.2)
Negative:       #f43f5e  (rose)
Negative-glow:  rgba(244,63,94,0.2)
Warning:        #f59e0b  (amber)
AI-accent:      #8b5cf6  (violet — for AI features)
Brazil:         #22c55e  (green flag accent)
```

### 27.5 Stitch Prompts for Each OvelhaInvest Page

**IMPORTANT:** Paste the GLOBAL STYLE BLOCK first in Stitch as a new project, then generate each screen within that project so Stitch maintains consistency.

**GLOBAL STYLE BLOCK — paste this first, before any screen prompt:**
```
Design system for OvelhaInvest — a premium AI-powered wealth management app.

Visual style: 2026 glassmorphism. Inspired by Linear.app, Vercel dashboard, and Raycast. 
Dark mode only. Deep space background #050508. 
Cards are frosted glass: semi-transparent with backdrop blur, subtle white border at 8% opacity, rounded-2xl corners.
Gradient accents: emerald (#10b981) for gains/positive, rose (#f43f5e) for losses/negative, violet (#8b5cf6) for AI features.
Typography: Geist Sans for headings, Inter for body text, JetBrains Mono for all numbers and tickers.
Charts have glowing colored strokes with translucent gradient fills beneath them — no flat bars.
Buttons: gradient fills with subtle glow shadows. Not flat. Not squared.
Status badges: pill-shaped, colored background at 15% opacity, matching text color and left-border glow.
Sidebar: fixed left, glassmorphic, blurred background, icon + label navigation items with active state showing emerald left-border accent and subtle background highlight.
All interactive elements: smooth 200ms hover transitions with glow intensification.
No pure white or pure black anywhere. Everything lives in the dark glass world.
```

---

**Screen 1 — Dashboard:**
```
OvelhaInvest Dashboard screen. Apply the project design system.

Layout: fixed glassmorphic left sidebar (240px) + main content area.
Sidebar: OvelhaInvest logo with sheep emoji at top, nav items (Dashboard, Signals, Assets, Performance, Projections, Tax, Journal, Config) with icons, Dashboard item active with emerald left-border glow.

Main content — top row (4 metric cards in a glass card grid):
- "Net Worth" card: large number $284,420 in white Geist Mono, subtitle "↑ $1,240 today" in emerald, secondary line "R$ 1.42M" in muted text. Card has faint emerald glow border.
- "Today's P&L" card: "+$1,240" large in emerald with glow, "+0.44%" badge pill, sparkline chart below in emerald.
- "YTD Return" card: "+18.4%" large, "vs benchmark +14.2%" in muted, "+4.2% alpha" emerald badge.
- "Max Drawdown" card: "-8.3%" in amber, "from peak Mar 2024" muted subtitle.

Middle row — two columns:
Left (60%): Allocation donut chart — 6 glowing arc segments (emerald US Equity, cyan Intl, blue Bonds, green Brazil, violet Crypto, slate Cash). Center shows "45% US Equity". Outer ring shows target vs actual in lighter stroke. Chart title "Asset Allocation" with "vs targets" toggle.
Right (40%): Three vault cards stacked — "Future Investments" glass card with emerald progress bar at 68%, balance $8,400. "Opportunity" card with amber bar at 22%, $2,800. "Emergency" card with slate bar at 100%, $15,000 with lock icon.

Bottom row: "Market Regime" banner — pill badge "NORMAL" in emerald glow. Recent signals mini-table (3 rows): timestamp, event type colored badge, summary text, status badge. "View all signals →" link in muted.
```

---

**Screen 2 — Signals & Activity:**
```
OvelhaInvest Signals page. Apply the project design system.

Header: "Signals & Activity" title + filter bar row — status dropdown (glass select), event type dropdown, date range picker, all with glass styling and subtle borders.

Main: Full-width table in a large glass card.
Table header row: Timestamp | Event Type | Proposed Trades | AI Status | Execution | Actions — all in muted uppercase small caps.
3 visible rows with subtle hover glow:
Row 1: "Today 09:14" | "DAILY CHECK" emerald pill badge | "Buy VTI $600, Buy BTC $300" | "✓ OK" emerald glow badge | "Pending Approval" amber badge | "Approve / Reject" gradient buttons.
Row 2: "Yesterday 09:15" | "DAILY CHECK" | "Buy VXUS $400" | "⚠ Warning" amber badge | "Executed" slate badge | "View" link.
Row 3: "Mar 18" | "OPPORTUNITY" violet pill badge | "Buy BTC $1,500 (Tier 1)" | "✓ OK" | "Approved" emerald badge | "View" link.

Expanded row detail (show Row 1 expanded): inner glass panel showing — 5 framework check indicators in a row (Swensen ✓, Dalio ✓, Marks ⚠, Graham ✓, Bogle ✓) as colored icon+label pills. Below: proposed trades list with amounts. Bottom: gradient "Approve All" button and ghost "Reject" button.
```

---

**Screen 3 — Assets & Valuations:**
```
OvelhaInvest Assets page. Apply the project design system.

Header: "Assets & Valuations" + filter bar — asset class multi-select, region dropdown, "Min Margin of Safety" range slider showing 15%, tier filter.

Main: large glass card containing sortable table.
Columns: Symbol | Class | Price | MoS% | Value | Momentum | Quality | Moat | Fair Value | Buy Target | Rank
Column headers in muted small caps with sort arrows.
4 visible rows:
- VTI: ETF badge (blue pill), $218.40, MoS +12% amber pill, three score bars (value 0.62, momentum 0.71, quality 0.83) as small colored progress bars, moat "—", Fair $247, Buy $197, Rank #3
- NVDA: Stock badge (violet), $124.80, MoS +28% emerald pill, scores (0.58, 0.89, 0.76), moat "Narrow" orange pill, Fair $173, Buy $147, Rank #1
- BTC: Crypto badge (amber), $82,400, MoS +31% emerald pill, scores (0.71, 0.83, "N/A"), moat "—", Fair $115k, Buy $92k, Rank #2
- PLTR: Stock badge (violet), $24.10, MoS -8% rose pill, scores (0.31, 0.77, 0.54), moat "Narrow", Fair $22, Buy $18, Rank #8

Right side drawer (visible for NVDA row): glass panel sliding in from right — "NVDA Detail" header, DCF assumptions accordion (FCF $28B, growth 22%, rate 10%), three score breakdown bar charts with labels, recent news feed (3 items with source favicon).
```

---

**Screen 4 — Performance Analytics:**
```
OvelhaInvest Performance page. Apply the project design system.

Horizontal tab bar: Summary | Attribution | Rolling | Risk — glass pill tabs, active tab has emerald underline glow.

Summary tab content:
Top row — 6 period cards in glass: 1mo, 3mo, 6mo, YTD, 1yr, All-Time. Each shows TWR % large, benchmark delta small below ("vs +14.2% bench" in muted), colored by positive/negative.

Middle row — 3 ratio cards:
- Sharpe 1.42 — large number, "Good" emerald badge, subtitle "Risk-adjusted return"
- Sortino 1.89 — large number, "Excellent" emerald glow badge
- Calmar 0.87 — large number, "Fair" amber badge

Bottom: Portfolio vs Benchmark line chart — two glowing lines (emerald portfolio, slate benchmark) on dark chart canvas with gradient area fill. X-axis: 12 months. Hover tooltip with glass styling.

Attribution tab (visible in background): stacked horizontal bar chart by sleeve showing allocation vs selection effects in emerald/violet. Top contributors table below (5 rows, NVDA +2.1%, BTC +1.8%, VTI +0.9%...).
```

---

**Screen 5 — Projections:**
```
OvelhaInvest Projections page. Apply the project design system.

Horizontal pill tabs: Monte Carlo | Contribution Sim | Stress Test | Retirement — Monte Carlo active.

Input row (glass card): "Monthly Contribution" input $2,000, "Projection Years" slider 20yr, "Model" dropdown "Current Allocation", "Run Simulation" emerald gradient button.

Main chart — Monte Carlo fan chart: 5 translucent shaded bands spreading outward from today's value $284k. Bands colored from darkest (5th percentile, near-flat line, rose-tinted) to lightest (95th, steep rise, emerald-tinted). Median line (50th) is bright emerald stroke. X-axis: years 0-20. Y-axis: $0-2M. Chart canvas is dark with very subtle grid lines.

Stats row below chart — 3 glass cards:
- "Median at 20yr" — "$892,000" large emerald
- "Reach $1M probability" — "61%" large  
- "4% SWR survival" — "94%" large emerald with "Safe" badge
```

---

**Screen 6 — Tax Optimization:**
```
OvelhaInvest Tax page. Apply the project design system.

Top section — Brazil DARF tracker glass card:
"Brazil Monthly Exemption" label. Large progress bar (amber gradient fill) at 34% — "R$6,800 of R$20,000 used this month". Right side: "Projected month-end: R$11,200 — Safe" emerald badge. "Days remaining: 9" muted.

Method selector row: three pill toggle buttons "FIFO | HIFO ✓ | Spec ID" — HIFO active with emerald glow border.

Main table — glass card:
Columns: Symbol | Account | Acquired | Qty | Cost Basis | Current Value | Unrealized G/L | Holding | Est. Tax
4 rows:
- NVDA: M1 Taxable, Jun 2022, 50 shares, $4,200, $6,240, +$2,040 emerald, LT green badge, $306
- BTC: Binance, Jan 2023, 0.12, $3,600, $9,888, +$6,288 emerald, LT green badge, $943
- PLTR: M1 Taxable, Nov 2024, 100, $2,100, $2,410, +$310 emerald, ST amber badge, $99
- VTI: M1 Roth, multiple lots — "Tax-free" slate badge spanning columns

Loss harvesting panel (bottom, glass card with amber left border glow):
"2 Harvest Candidates" amber heading. List: "BNDX: -$420 unrealized — harvest before Dec 31, pair with BND to avoid wash sale" with "Review" button.
```

---

**Screen 7 — Decision Journal:**
```
OvelhaInvest Journal page. Apply the project design system.

Top — Override Accuracy scorecard (two glass cards side by side with colored glow):
Left card (emerald glow): "When You Followed the System" — "+12.4% avg 90-day outcome" large emerald number, "47 decisions tracked" muted subtitle, emerald checkmark icon.
Right card (amber glow): "When You Overrode the System" — "+7.1% avg 90-day outcome" large amber number, "12 overrides" muted subtitle, amber warning icon. Subtle label: "System outperformed your overrides by 5.3%"

Main table — glass card:
Columns: Date | Action | Asset | System Said | Your Reasoning | 30d | 90d
3 rows:
- Mar 15: "Followed" emerald pill | BTC | "Buy $300 Tier-1" | "Agreed with drawdown signal" | +8.2% emerald | +22.1% emerald
- Mar 10: "Overrode" rose pill | NVDA | "Hold — no buy signal" | "Felt momentum was strong" | +4.1% | +11.2%
- Feb 28: "Deferred" amber pill | VTI | "Buy $600 DCA" | "Waited for lower price" | -1.2% rose | +3.8%

Bottom — AI Pattern Analysis glass card with violet left glow:
Violet sparkle icon. "AI Behavioral Analysis" heading. Text: "You override the system most during high-volatility periods (VIX > 25). Your 90-day outcomes when overriding during high-vol are +4.2% vs system's +14.8%. Consider trusting the engine more during volatile markets." Glass card, violet accent.
```

---

**Screen 8 — Config:**
```
OvelhaInvest Config page. Apply the project design system.

Two-column layout:
Left column (35%) — Version history glass card:
Title "Strategy Configs". List of versions — "v1.0.0 (Active)" row highlighted with emerald left glow, emerald "Active" badge, timestamp. Below: "v0.9.1" muted row, "v0.9.0" muted row. "Create new version" ghost button at bottom.

Right column (65%) — two stacked glass cards:
Top card: Allocation targets donut chart — same 6-slice glowing arc design as dashboard. Below donut: three toggle buttons "Current | Swensen | All-Weather". When Swensen active, a second ghost ring overlays showing Swensen targets for comparison.

Bottom card: JSON config viewer with syntax highlighting. Dark code area with colored tokens: keys in violet, numbers in emerald, booleans in amber. Monospace font. "v1.0.0 — Read Only" label in top-right with slate badge. Scrollable, 12 visible lines showing targets, constraints, volatility_rules keys.
```

---

## 28. GIT WORKFLOW — GITEA + GITHUB DUAL REMOTE

### 28.1 Repository Setup
```bash
# Two remotes: Gitea (primary/private) + GitHub (mirror/backup)
git remote add origin https://git.ovelha.us/thiago/ovelhainvest.git
git remote add github https://github.com/OvelhaGod/ovelhainvest.git

# Push to both simultaneously via push config
git config --local remote.origin.pushurl https://git.ovelha.us/thiago/ovelhainvest.git
git remote set-url --add --push origin https://github.com/OvelhaGod/ovelhainvest.git

# Verify
git remote -v
# origin  → fetch: Gitea, push: Gitea + GitHub
```

### 28.2 Commit Convention (Conventional Commits — ENFORCED)
```
feat(scope): short description       # new feature
fix(scope): short description        # bug fix
chore(scope): short description      # tooling, deps, config
docs(scope): short description       # documentation only
refactor(scope): short description   # code change, no behavior change
test(scope): short description       # tests only
perf(scope): short description       # performance improvement

# Scopes: backend, frontend, db, ai, tax, perf, sim, alerts, journal, infra, docs

# Examples:
feat(backend): add allocation engine sleeve drift detection
feat(frontend): add dashboard net worth card with BRL/USD toggle
fix(db): correct tax_lot acquisition_date index
chore(infra): add Stitch MCP config to .claude.json
docs(design): commit DESIGN.md from Stitch export
```

### 28.3 Branching Strategy
```
main          ← always deployable, protected
dev           ← integration branch, all features merge here first
phase/N       ← one branch per build phase (phase/2, phase/3, etc.)
feat/name     ← individual feature branches off phase/N
fix/name      ← hotfix branches
```

### 28.4 Claude Code Git Rules (ALWAYS FOLLOW)
- After completing any task unit (file, function, endpoint, page): `git add -A && git commit -m "feat(...): ..."` 
- After completing a full phase: `git push origin dev && git push origin dev`
- After merging phase branch to main: `git push origin main && git push origin main`
- Never leave uncommitted work at end of a session
- `.env` files are NEVER committed — `.gitignore` must cover all secrets
- `CLAUDE.md`, `DESIGN.md`, `STITCH_PROMPT.md` ARE committed — they are project docs

### 28.5 .gitignore Requirements
```gitignore
# Secrets — never commit
.env
.env.*
*.pem
*.key
service_account.json
gcloud_credentials.json

# Python
__pycache__/
*.pyc
.venv/
dist/
*.egg-info/

# Node
node_modules/
.next/
out/

# OS
.DS_Store
Thumbs.db

# Tools
.claude/cache/
```

---

## 29. COMPLETE SETUP SEQUENCE FOR CLAUDE CODE

This is the authoritative sequence. Execute in order. Do not skip steps.

### Step 0 — Before Running Claude Code
Manually complete these prerequisites:
1. Create Supabase project → get URL + service key + anon key
2. Create Upstash Redis instance → get Redis URL
3. Get Anthropic API key (already have)
4. Get Finnhub API key (free at finnhub.io)
5. Create Telegram bot via @BotFather → get token + chat ID
6. Create Gitea repo: `https://git.ovelha.us/thiago/ovelhainvest`
7. Create GitHub repo: `github.com/[username]/ovelhainvest` (private)
8. Create Google Cloud project → enable Stitch API (for later)

### Step 1 — Initialize Project
```bash
mkdir ovelhainvest && cd ovelhainvest
# Place CLAUDE.md here (this file)
git init
git checkout -b main
git remote add origin https://git.ovelha.us/thiago/ovelhainvest.git
git remote set-url --add --push origin https://git.ovelha.us/thiago/ovelhainvest.git
git remote set-url --add --push origin https://github.com/OvelhaGod/ovelhainvest.git
git config core.autocrlf input
```

### Step 2 — First Claude Code Session (Phase 1 + Stitch Prep)
Run `claude` in the project directory. First prompt:

```
Read CLAUDE.md completely — all 29 sections. Then execute this exact sequence:

PART A — PROJECT SCAFFOLD:
1. Create full directory structure from Section 3
2. Initialize backend: `uv init backend && cd backend && uv add fastapi uvicorn supabase pydantic-settings yfinance anthropic pandas numpy scipy redis httpx weasyprint python-dateutil python-dotenv`
3. Create backend/app/main.py with FastAPI app, CORS, /health endpoint
4. Create backend/app/config.py with Settings class reading from .env
5. Create backend/app/db/supabase_client.py and redis_client.py
6. Create backend/app/migrations/001_initial_schema.sql through 004_journal_alerts.sql (full SQL from CLAUDE.md Sections 4)
7. Create all service file stubs (empty files with module docstrings + function signatures only — no implementation) for every file in Section 3
8. Create all API route file stubs similarly
9. Initialize frontend: `pnpm create next-app@latest frontend -- --typescript --tailwind --app --no-src-dir`
10. Install shadcn/ui: `cd frontend && pnpm dlx shadcn@latest init` (use default dark theme)
11. Install frontend deps: `pnpm add recharts d3 @supabase/supabase-js date-fns`
12. Create frontend/app/layout.tsx with dark mode, sidebar navigation (all 8 pages)
13. Create frontend/app/dashboard/page.tsx with placeholder cards (hardcoded data, no API calls yet)
14. Create frontend/lib/supabase.ts and api.ts stubs
15. Create .gitignore from Section 28.5
16. Create README.md with full setup instructions (how to run backend, frontend, apply migrations)
17. Create .env.example with all variables from Section 21 (empty values)

PART B — STITCH DESIGN PREP:
18. Create STITCH_PROMPT.md in repo root containing all 8 Stitch prompts from Section 27.4, formatted for copy-paste into stitch.withgoogle.com
19. Create DESIGN.md placeholder with comment: "# DESIGN.md — Export from Google Stitch and replace this file before building any React components"

PART C — GIT SETUP:
20. Create initial commit: `git add -A && git commit -m "chore(infra): initial project scaffold — all stubs, migrations, frontend shell"`
21. Push to both remotes: `git push -u origin main && git push origin main`

PART D — VERIFY:
22. Run `cd backend && uvicorn app.main:app --reload` — confirm /health returns 200
23. Run `cd frontend && pnpm dev` — confirm dashboard renders without errors
24. Commit verification: `git add -A && git commit -m "chore(infra): verified Phase 1 scaffold running" && git push origin main && git push origin main`

Report back what's done and what needs my input before proceeding to Phase 2.
```

### Step 3 — Stitch Design Session (Do This Yourself, ~2 hours)
1. Go to stitch.withgoogle.com
2. Use each prompt from STITCH_PROMPT.md
3. Generate all 8 page designs
4. Export DESIGN.md from Stitch
5. Replace the placeholder DESIGN.md in repo root
6. Install Stitch skill: `npx skills add google-labs-code/stitch-skills --skill stitch-design --global`
7. Commit: `git add DESIGN.md && git commit -m "docs(design): add Stitch DESIGN.md — design system contract" && git push origin main && git push origin main`

### Step 4 — Phase 2 (Portfolio Engine) — After DESIGN.md Is Committed
```
DESIGN.md is now in the repo. Begin Phase 2 — Portfolio Engine.

Implement in this exact order. Commit after each item.

1. backend/app/services/allocation_engine.py
   - compute_current_sleeve_weights(holdings, accounts, prices) → dict
   - compute_total_portfolio_value(holdings, prices, fx_rates) → float  
   - map_asset_to_sleeve(asset) → str
   - detect_drift_vs_targets(current_weights, targets, config) → dict of drifts
   - All amounts in USD; BRL assets converted via fx_engine stub
   Commit: "feat(backend): allocation engine — sleeve weights + drift detection"

2. backend/app/services/rebalancing.py
   - propose_soft_rebalance_trades(drift, vault_balance, config) → list[Trade]
   - propose_hard_rebalance_trades(drift, holdings, config) → list[Trade]
   - apply_trade_size_limits(trades, portfolio_value, config) → list[Trade]
   - enforce_cadence_rules(trades, last_execution_date, config) → list[Trade]
   Commit: "feat(backend): rebalancing — soft/hard proposals with IPS constraints"

3. backend/app/services/volatility_regime.py
   - detect_volatility_regime(vix, equity_move, crypto_move, config) → RegimeState
   - should_defer_core_dca(regime, config) → tuple[bool, int]
   - allow_opportunity_mode(regime, asset_discounted, config) → bool
   Commit: "feat(backend): volatility regime detection — Dalio 4-season aware"

4. backend/app/services/opportunity_detector.py
   - evaluate_tier_1_trigger(drawdown_pct, margin_of_safety, config) → bool
   - evaluate_tier_2_trigger(drawdown_pct, margin_of_safety, existing_event, config) → bool
   - create_or_update_opportunity_event(db, user_id, asset_id, tier, config) → OpportunityEvent
   Commit: "feat(backend): opportunity detector — Marks Tier 1/2 triggers"

5. backend/app/api/allocation.py
   - POST /run_allocation → calls all services above → writes signals_run → returns AllocResponse
   - GET /daily_status → returns status summary
   Commit: "feat(backend): allocation API endpoints wired to engine"

6. backend/app/db/repositories/signals.py + holdings.py + accounts.py
   - All DB read/write operations for the above
   Commit: "feat(db): repositories for signals, holdings, accounts"

7. frontend/app/signals/page.tsx
   - Fetch signals_runs from API
   - Render table per DESIGN.md spec
   - Expandable row with proposed trades + status badges
   - Match Stitch design exactly
   Commit: "feat(frontend): signals page — table with expandable AI commentary"

8. frontend/app/dashboard/page.tsx — REPLACE hardcoded with live data
   - Wire to /daily_status endpoint
   - Sleeve allocation donut chart
   - Net worth card (USD + BRL)
   - Vault balances
   - Regime badge
   Commit: "feat(frontend): dashboard — live data from /daily_status"

After all 8 commits: push to both remotes.
`git push origin dev && git push origin dev`

Then open a PR: dev → main, merge, push main.
`git checkout main && git merge dev && git push origin main && git push origin main`
```

---

## 30. ONGOING GIT RULES FOR CLAUDE CODE

Claude Code must follow these git rules in every session, without being reminded:

1. **Every completed function or file = one commit.** Never batch 10 files into one commit.
2. **Every completed phase = push to both remotes.**
3. **Commit message format is non-negotiable** — use conventional commits from Section 28.2.
4. **Before starting any new feature:** `git pull origin dev` to sync.
5. **Never commit directly to main** — always via dev branch.
6. **If a push fails** (remote conflict), resolve with rebase not merge: `git pull --rebase origin dev`.
7. **After every session ends:** `git status` → commit anything uncommitted → push.
8. **The .env file is NEVER committed.** If it shows in `git status`, add to .gitignore immediately.
9. **CLAUDE.md and DESIGN.md are project artifacts** — commit any updates to them immediately.
---

## 31. PERSONAL FINANCE OS — MONARCH REPLACEMENT (Phase 11+)

> **HARD GATE:** Do not touch anything in this section until Phase 10 (PWA/Polish) is fully complete and merged to main. The investment engine must be fully operational before adding budgeting features.

### 31.1 Vision

OvelhaInvest Phase 11 becomes a complete personal finance OS — the only app where spending decisions, savings behavior, and investment strategy share the same data model and inform each other in real time.

**What no other app does:**
- Budget cuts reflected in Monte Carlo retirement projections
- Payday cashflow automatically routed to investment vaults
- Net worth breakdown: market gains vs new savings vs debt paydown
- Savings rate shown alongside portfolio performance on the same dashboard
- "If I cut dining by $300/month, how does my 20-year projection change?"

**What we are NOT building (keep scope tight):**
- Bill pay or payment initiation
- Credit score monitoring
- Shared/household budgets
- Tax filing
- Subscription cancellation flows
- Anything requiring OAuth to banks beyond read-only Plaid/Teller aggregation

### 31.2 New Database Tables (Migration 005)

```sql
-- Migration 005: Personal Finance OS tables

-- Liabilities (completes the net worth picture)
CREATE TABLE liabilities (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name text NOT NULL,
  liability_type text NOT NULL,       -- "mortgage", "auto", "credit_card", "student", "personal", "other"
  current_balance numeric(18,2) NOT NULL,
  original_balance numeric(18,2),
  interest_rate numeric(9,6),
  minimum_payment numeric(18,2),
  due_day integer,                     -- day of month (1-31)
  payoff_date date,
  account_linked_id uuid REFERENCES accounts(id) ON DELETE SET NULL,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

-- Spending transactions (separate from investment transactions)
CREATE TABLE spending_transactions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  account_id uuid REFERENCES accounts(id) ON DELETE SET NULL,
  amount numeric(18,2) NOT NULL,
  direction text NOT NULL,             -- "debit" (expense), "credit" (income)
  merchant_name text,
  merchant_name_clean text,            -- normalized for categorization
  category text,                       -- top-level: "Housing", "Food", "Transport", etc.
  subcategory text,                    -- "Groceries", "Restaurants", "Gas", etc.
  date date NOT NULL,
  is_recurring boolean NOT NULL DEFAULT false,
  recurring_item_id uuid,
  notes text,
  source text NOT NULL DEFAULT 'manual', -- "plaid", "teller", "manual", "csv_import"
  external_id text,                    -- dedup key from Plaid/Teller
  is_hidden boolean NOT NULL DEFAULT false,
  is_reviewed boolean NOT NULL DEFAULT false,
  currency text NOT NULL DEFAULT 'USD',
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX spending_txn_user_date_idx ON spending_transactions(user_id, date DESC);
CREATE UNIQUE INDEX spending_txn_external_id_idx ON spending_transactions(user_id, external_id)
  WHERE external_id IS NOT NULL;

-- Category rules (rule-based categorization engine)
CREATE TABLE category_rules (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  priority integer NOT NULL DEFAULT 100,  -- lower = higher priority
  match_field text NOT NULL,              -- "merchant_name", "amount", "description"
  match_type text NOT NULL,               -- "contains", "equals", "starts_with", "regex", "amount_range"
  match_value text NOT NULL,
  category text NOT NULL,
  subcategory text,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now()
);

-- Budget envelopes (monthly targets per category)
CREATE TABLE budgets (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  category text NOT NULL,
  monthly_target numeric(18,2) NOT NULL,
  rollover boolean NOT NULL DEFAULT false,  -- unused budget carries to next month
  alert_at_pct numeric(5,2) DEFAULT 0.80,   -- alert when 80% spent
  color text,                               -- hex color for UI
  emoji text,                               -- display emoji
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (user_id, category)
);

-- Recurring items (bills + income schedule)
CREATE TABLE recurring_items (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name text NOT NULL,
  amount numeric(18,2) NOT NULL,
  direction text NOT NULL,              -- "income", "expense"
  frequency text NOT NULL,             -- "monthly", "biweekly", "weekly", "annual", "quarterly"
  anchor_date date NOT NULL,           -- reference date for frequency calculation
  next_date date NOT NULL,
  category text,
  account_id uuid REFERENCES accounts(id) ON DELETE SET NULL,
  notes text,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now()
);

-- Cashflow snapshots (daily/monthly aggregates)
CREATE TABLE cashflow_snapshots (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  snapshot_date date NOT NULL,
  period_type text NOT NULL DEFAULT 'monthly',  -- "daily", "monthly"
  total_income numeric(18,2) NOT NULL DEFAULT 0,
  total_expenses numeric(18,2) NOT NULL DEFAULT 0,
  net_cashflow numeric(18,2) GENERATED ALWAYS AS (total_income - total_expenses) STORED,
  savings_amount numeric(18,2) NOT NULL DEFAULT 0,  -- amount actually invested/saved
  savings_rate numeric(9,6),                         -- savings / income
  amount_available_for_investing numeric(18,2),      -- feeds contribution optimizer
  projected_period_end_balance numeric(18,2),
  income_by_category jsonb,            -- { "Salary": 8500, "Freelance": 500 }
  expenses_by_category jsonb,          -- { "Housing": 2200, "Food": 800, ... }
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (user_id, snapshot_date, period_type)
);

-- Net worth snapshots (investment assets + bank + liabilities)
CREATE TABLE net_worth_snapshots (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  snapshot_date date NOT NULL,
  total_assets_usd numeric(18,2) NOT NULL,
  investment_assets_usd numeric(18,2) NOT NULL,   -- from portfolio_snapshots
  bank_assets_usd numeric(18,2) NOT NULL,          -- checking + savings + vaults
  other_assets_usd numeric(18,2) DEFAULT 0,        -- real estate, vehicles (manual)
  total_liabilities_usd numeric(18,2) NOT NULL DEFAULT 0,
  net_worth_usd numeric(18,2) GENERATED ALWAYS AS
    (total_assets_usd - total_liabilities_usd) STORED,
  change_from_market numeric(18,2),    -- portfolio gain/loss contribution
  change_from_savings numeric(18,2),   -- new money invested
  change_from_debt_paydown numeric(18,2),
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (user_id, snapshot_date)
);

-- Spending categories master list (reference)
-- Populated by seed data, not user-created
CREATE TABLE spending_categories (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL UNIQUE,
  parent_category text,
  emoji text,
  color text,
  is_income boolean NOT NULL DEFAULT false,
  display_order integer
);
```

### 31.3 Spending Category Taxonomy (Seed Data)

```python
SPENDING_CATEGORIES = [
    # Income
    {"name": "Salary",           "parent": "Income",      "emoji": "💼", "is_income": True},
    {"name": "Freelance",        "parent": "Income",      "emoji": "💻", "is_income": True},
    {"name": "Investment Income","parent": "Income",      "emoji": "📈", "is_income": True},
    {"name": "Other Income",     "parent": "Income",      "emoji": "💰", "is_income": True},

    # Fixed Expenses
    {"name": "Rent/Mortgage",    "parent": "Housing",     "emoji": "🏠"},
    {"name": "Insurance",        "parent": "Housing",     "emoji": "🛡️"},
    {"name": "HOA/Condo",        "parent": "Housing",     "emoji": "🏢"},
    {"name": "Utilities",        "parent": "Housing",     "emoji": "⚡"},
    {"name": "Internet/Phone",   "parent": "Housing",     "emoji": "📡"},

    # Variable Expenses
    {"name": "Groceries",        "parent": "Food",        "emoji": "🛒"},
    {"name": "Restaurants",      "parent": "Food",        "emoji": "🍽️"},
    {"name": "Coffee",           "parent": "Food",        "emoji": "☕"},

    {"name": "Gas",              "parent": "Transport",   "emoji": "⛽"},
    {"name": "Car Payment",      "parent": "Transport",   "emoji": "🚗"},
    {"name": "Car Insurance",    "parent": "Transport",   "emoji": "🚗"},
    {"name": "Uber/Lyft",        "parent": "Transport",   "emoji": "🚕"},
    {"name": "Parking",          "parent": "Transport",   "emoji": "🅿️"},

    {"name": "Streaming",        "parent": "Subscriptions","emoji": "📺"},
    {"name": "Software",         "parent": "Subscriptions","emoji": "💿"},
    {"name": "Gym",              "parent": "Subscriptions","emoji": "🏋️"},

    {"name": "Doctor/Medical",   "parent": "Health",      "emoji": "🏥"},
    {"name": "Pharmacy",         "parent": "Health",      "emoji": "💊"},

    {"name": "Shopping",         "parent": "Personal",    "emoji": "🛍️"},
    {"name": "Personal Care",    "parent": "Personal",    "emoji": "💇"},
    {"name": "Clothing",         "parent": "Personal",    "emoji": "👕"},

    {"name": "Travel",           "parent": "Lifestyle",   "emoji": "✈️"},
    {"name": "Entertainment",    "parent": "Lifestyle",   "emoji": "🎭"},
    {"name": "Gifts",            "parent": "Lifestyle",   "emoji": "🎁"},

    {"name": "Tuition",          "parent": "Education",   "emoji": "🎓"},
    {"name": "Books/Courses",    "parent": "Education",   "emoji": "📚"},

    {"name": "Federal Tax",      "parent": "Taxes",       "emoji": "🏛️"},
    {"name": "State Tax",        "parent": "Taxes",       "emoji": "🏛️"},
    {"name": "Brazil Tax/DARF",  "parent": "Taxes",       "emoji": "🇧🇷"},

    {"name": "Investment",       "parent": "Savings",     "emoji": "📈"},
    {"name": "Emergency Fund",   "parent": "Savings",     "emoji": "🛡️"},

    {"name": "Uncategorized",    "parent": None,          "emoji": "❓"},
]
```

### 31.4 New Service Files

Add to `backend/app/services/`:

```
budget_engine.py          ← monthly actuals vs targets, rollover logic, alerts
cashflow_engine.py        ← income/expense aggregation, savings rate, forecasting
categorization_engine.py  ← rule-based + Claude AI fallback categorization
net_worth_engine.py       ← assets + liabilities → net worth + change attribution
recurring_engine.py       ← upcoming bills/income, next-date computation
transaction_sync.py       ← Plaid/Teller pull, CSV import, dedup logic
```

### 31.5 New API Endpoints

```python
# Budget
GET  /budget/summary          # current month: category actuals vs targets
GET  /budget/history          # month-by-month budget performance
POST /budget/categories       # create/update budget envelope

# Transactions
GET  /transactions            # paginated, filterable spending transaction feed
POST /transactions            # manual transaction entry
PATCH /transactions/{id}      # update category, notes, hidden flag
POST /transactions/import/csv # bulk CSV import

# Cashflow
GET  /cashflow/summary        # current month income, expenses, savings rate
GET  /cashflow/forecast       # projected cashflow for next 30/60/90 days
GET  /cashflow/history        # month-by-month cashflow history

# Net Worth
GET  /networth/summary        # current net worth + change attribution
GET  /networth/history        # net worth timeline
POST /networth/liabilities    # add/update liability
GET  /networth/liabilities    # list liabilities

# Recurring
GET  /recurring               # all active recurring items
POST /recurring               # add recurring item
GET  /recurring/upcoming      # next 30 days bill/income calendar
```

### 31.6 Categorization Engine

```python
def categorize_transaction(
    merchant_name: str,
    amount: float,
    direction: str,
    user_rules: list[CategoryRule],
) -> tuple[str, str]:
    """
    Three-pass categorization:

    Pass 1 — User rules (highest priority, exact match)
      Apply user-defined category_rules in priority order.
      If match found: return immediately.

    Pass 2 — Global rules (built-in merchant name patterns)
      GLOBAL_RULES = {
        r"(?i)amazon|amzn":           ("Shopping", "Online"),
        r"(?i)uber eats|doordash|grubhub": ("Food", "Delivery"),
        r"(?i)netflix|spotify|hulu":  ("Subscriptions", "Streaming"),
        r"(?i)shell|chevron|exxon|bp|sunoco": ("Transport", "Gas"),
        r"(?i)publix|kroger|whole foods|trader joe": ("Food", "Groceries"),
        r"(?i)walmart|target|costco": ("Shopping", "General"),
        r"(?i)uber|lyft":             ("Transport", "Rideshare"),
        # ... 100+ patterns
      }

    Pass 3 — Claude AI fallback (only if passes 1+2 fail)
      Send merchant_name + amount + direction to Claude API.
      Prompt: "Categorize this transaction for personal budgeting.
               Merchant: {merchant_name}, Amount: ${amount}, Type: {direction}.
               Return JSON: {category: string, subcategory: string}
               from this list: {SPENDING_CATEGORIES}"
      Cache result in Redis (merchant_name → category, 30-day TTL).
      Store as new user rule so same merchant is never sent to AI again.

    Returns: (category, subcategory)
    """
```

### 31.7 Cashflow → Investment Engine Integration

This is the critical integration point that makes OvelhaInvest unique:

```python
# In cashflow_engine.py
def compute_available_for_investing(
    monthly_income: float,
    fixed_expenses: float,
    variable_expenses_actual: float,
    emergency_fund_target: float,
    current_emergency_balance: float,
) -> float:
    """
    Available = Income - Fixed - Variable - Emergency_top_up
    This value flows into:
    1. contribution_optimizer.py (which account + asset to buy)
    2. vault_funding_suggestion (how much to route to Future Investments vault)
    3. Monte Carlo projections (realistic monthly contribution input)
    """

# In n8n payday workflow — ENHANCED:
# Step 1: detect deposit in SoFi
# Step 2: compute cashflow_engine.compute_available_for_investing()
# Step 3: subtract fixed recurring bills due this pay period
# Step 4: remainder → suggest vault funding split
# Step 5: call /simulation/contribution_optimizer with real available amount
# Step 6: send Telegram digest: "Paycheck received. After bills: $X available.
#          Suggested: $Y → Future Investments vault, $Z → keep as buffer."
```

### 31.8 Budget Impact on Monte Carlo

```python
# In simulation_engine.py — ENHANCED for Phase 11
def run_monte_carlo_with_budget(
    current_value: float,
    monthly_contribution: float,        # from cashflow snapshot
    budget_scenario: dict | None = None, # optional: {"dining": -300, "subscriptions": -50}
) -> MonteCarloResult:
    """
    If budget_scenario provided:
      adjusted_contribution = monthly_contribution + sum(budget_scenario.values())
      # Negative values = spending cuts = more available to invest
      # e.g. {"dining": -300} means $300 less dining = $300 more invested

    Run both base and scenario side-by-side.
    Return comparison: base_median_20yr vs scenario_median_20yr.
    UI shows: "Cutting dining by $300/month adds $X to your projected net worth in 20 years."
    """
```

### 31.9 Net Worth Attribution Engine

```python
def compute_net_worth_change_attribution(
    prev_snapshot: NetWorthSnapshot,
    curr_snapshot: NetWorthSnapshot,
    cashflow_snapshot: CashflowSnapshot,
    portfolio_return: float,
) -> dict:
    """
    Decompose net worth change into 3 buckets:

    change_from_market = portfolio_value * portfolio_return
      → "Markets moved your wealth by $X"

    change_from_savings = new_money_invested + bank_balance_increase
      → "You added $X in new savings"

    change_from_debt_paydown = prev_liabilities - curr_liabilities - interest_paid
      → "Debt paydown increased your net worth by $X"

    residual = total_change - sum(above)  # should be near zero
    """
```

---

## 32. PERSONAL FINANCE PAGES — UI SPEC

### /networth
**The single most important page in the whole app.**

Top: Big number — Net Worth today in USD (and BRL equivalent). Change from last month with attribution breakdown: "↑ $4,200 this month — Markets: +$2,800 | New Savings: +$1,100 | Debt Paydown: +$300"

Assets section: Investment assets (from portfolio_snapshots) + Bank accounts + Other assets (manual)
Liabilities section: Each liability with balance, rate, minimum payment, payoff timeline bar

Net worth timeline chart: all-time line chart, toggle: 1mo / 3mo / 1yr / all-time

---

### /budget
**Monthly budget envelopes — Monarch-style but connected to investment engine.**

Top: Month selector. Key metrics: Income this month | Spent | Remaining | Savings Rate %

Budget grid: cards per category. Each card: emoji + name + progress bar (actual/target) + $ remaining. Color: green < 70%, amber 70-90%, red > 90%.

Bottom: "Budget Surplus → Investment Impact" card: "You're $320 under budget this month. If invested, that adds $X to your 20-year projection." Button: "Route to Future Investments Vault"

---

### /cashflow
**Income vs expenses timeline. Where the money actually goes.**

Top row: This month — Income, Expenses, Net Cashflow, Savings Rate (all with MoM delta)

Main chart: Stacked area chart — income (green) vs expenses (red) by week, current month + last 3 months

Cashflow calendar: Next 30 days. Each day shows: upcoming bills (red badges), expected income (green badges), projected daily balance

Savings rate trend: 12-month line chart. Benchmark line at 20% (target savings rate)

---

### /transactions
**Spending transaction feed. Full control.**

Filter bar: date range, account, category, direction (income/expense), search by merchant

Table: Date | Merchant | Category (editable inline dropdown) | Amount | Account | Reviewed checkbox

Bulk actions: select multiple → recategorize, hide, mark reviewed

Category spending breakdown: right panel or bottom — pie chart of current month by category

CSV import button: drag-drop, auto-parse, preview before import

---

### /recurring
**Bills and income schedule. Never miss a payment.**

"Upcoming 30 days" timeline: calendar-style list of upcoming bills and income

Two sections: Fixed Income (salary, freelance) | Fixed Expenses (rent, subscriptions, car)

Each item: name, amount, next date, frequency, account, days-until countdown badge

Monthly fixed cost total vs monthly fixed income total → "Fixed coverage ratio: X%"

Alert: items without a matched transaction in last period (possible missed payment)

---

## 33. UPDATED PHASE BUILD PLAN (Complete)

| Phase | Scope | Gate |
|---|---|---|
| 1 | Foundation — scaffold, migrations, health check | ✅ Done |
| 2 | Portfolio Engine — allocation, rebalancing, volatility, signals | Phase 1 complete |
| 3 | Valuation Engine — factor scoring, DCF, margin of safety | Phase 2 complete |
| 4 | Performance Analytics — TWR/MWR, Sharpe/Sortino/Calmar, attribution | Phase 3 complete |
| 5 | AI Advisor Layer — Claude API, philosophy prompt, commentary | Phase 4 complete |
| 6 | Alerts + Automation — Telegram, n8n workflows, opportunity scan | Phase 5 complete |
| 7 | Simulation + Projections — Monte Carlo, stress tests, contribution optimizer | Phase 6 complete |
| 8 | Tax Engine — lot tracking, HIFO/FIFO, Brazil DARF | Phase 7 complete |
| 9 | Decision Journal + Reports — override tracking, PDF export | Phase 8 complete |
| 10 | PWA + Polish — offline, push, FX attribution, risk parity view | ✅ Done |
| **11** | **Personal Finance OS — transactions, budget, cashflow, net worth, recurring** | **Phase 10 complete** |
| 12 | Integration Layer — budget feeds Monte Carlo, cashflow feeds vault optimizer | Phase 11 complete |
| 13 | Advanced Analytics — spending pattern ML, savings optimization suggestions | Phase 12 complete |

### Phase 11 Sub-Phases (Internal Sequence)

```
11a — Data model: migration 005, seed spending_categories
11b — Transaction engine: spending_transactions table, CSV import, manual entry
11c — Categorization engine: rule-based + Claude AI fallback
11d — Budget engine: monthly actuals vs targets, rollover, alerts
11e — Recurring engine: bill/income schedule, next-date computation
11f — Cashflow engine: aggregation, savings rate, 30-day forecast
11g — Net worth engine: assets + liabilities + attribution
11h — API endpoints: all 15 new endpoints
11i — Frontend: /transactions page
11j — Frontend: /budget page
11k — Frontend: /cashflow page
11l — Frontend: /recurring page
11m — Frontend: /networth page + update /dashboard with new cards
11n — Integration: cashflow → contribution_optimizer
11o — Integration: budget scenarios → Monte Carlo
11p — n8n: enhanced payday workflow using real cashflow data
```

---

## 34. COMPLETE FEATURE COMPARISON

| Feature | Monarch | Empower | Betterment | OvelhaInvest (Complete) |
|---|---|---|---|---|
| Transaction categorization | ✅ | ✅ | ❌ | ✅ Phase 11 |
| Budget envelopes | ✅ | ✅ | ❌ | ✅ Phase 11 |
| Net worth tracking | ✅ | ✅ | ✅ | ✅ Phase 11 |
| Cashflow forecasting | ✅ | ✅ | ❌ | ✅ Phase 11 |
| Recurring bills | ✅ | ✅ | ❌ | ✅ Phase 11 |
| Investment portfolio | Limited | Limited | ✅ | ✅ Phase 2-3 |
| Factor scoring (Value/Mom/Quality) | ❌ | ❌ | ❌ | ✅ Phase 3 |
| DCF + margin of safety | ❌ | ❌ | ❌ | ✅ Phase 3 |
| Risk parity analysis | ❌ | ❌ | ❌ | ✅ Phase 4 |
| Monte Carlo projections | ❌ | ✅ Basic | ✅ Basic | ✅ Phase 7 |
| Stress testing | ❌ | ❌ | ❌ | ✅ Phase 7 |
| Performance attribution | ❌ | ❌ | Limited | ✅ Phase 4 |
| Tax lot tracking (HIFO) | ❌ | ❌ | ✅ | ✅ Phase 8 |
| Brazil DARF tracking | ❌ | ❌ | ❌ | ✅ Phase 8 |
| AI investment advisor | ❌ | ❌ | ❌ | ✅ Phase 5 |
| Decision journal + override tracking | ❌ | ❌ | ❌ | ✅ Phase 9 |
| Real-time Telegram alerts | ❌ | ❌ | ❌ | ✅ Phase 6 |
| Budget → retirement projection link | ❌ | ❌ | ❌ | ✅ Phase 12 |
| Cashflow → vault routing | ❌ | ❌ | ❌ | ✅ Phase 12 |
| Multi-currency (USD + BRL) | ❌ | ❌ | ❌ | ✅ Phase 2 |
| Swensen/Dalio/Marks/Graham engine | ❌ | ❌ | ❌ | ✅ Phase 2-3 |
| PWA (offline access) | ✅ | ✅ | ✅ | ✅ Phase 10 |
| Self-hosted / private | ❌ | ❌ | ❌ | ✅ All phases |
| Cost | $99/yr | Free | 0.25%/yr | $0 (self-hosted) |

---

## 35. DESIGN SYSTEM — GLASSMORPHISM + PREMIUM DARK THEME

> This section is the single source of truth for all visual decisions.
> Claude Code reads this alongside DESIGN.md (Stitch export) when building any component.
> DESIGN.md takes precedence for layout structure. This section governs all styling tokens.

### 35.1 Design Language

**Aesthetic:** Premium glassmorphism — the visual language of modern AI tools (Linear, Vercel, Raycast, Perplexity). Frosted glass cards floating on dark gradient backgrounds. Subtle depth, motion, and light effects. NOT Bloomberg terminal anymore — that was the data philosophy. The visual is modern AI-native.

**Keywords:** Glass panels, gradient accents, soft glows, smooth curves, premium typography, subtle animations, depth through blur and shadow — not through borders and flat color blocks.

### 35.2 Color Tokens

```css
:root {
  /* Backgrounds — layered depth */
  --bg-base:        #050508;   /* deepest — page background */
  --bg-surface:     #0d0d14;   /* cards, panels */
  --bg-elevated:    #13131f;   /* hover states, dropdowns */
  --bg-overlay:     #1a1a2e;   /* modals, tooltips */

  /* Glass effect */
  --glass-bg:       rgba(255, 255, 255, 0.04);
  --glass-border:   rgba(255, 255, 255, 0.08);
  --glass-hover:    rgba(255, 255, 255, 0.07);
  --glass-blur:     12px;

  /* Brand gradients */
  --gradient-primary:   linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #a78bfa 100%);
  --gradient-green:     linear-gradient(135deg, #10b981 0%, #34d399 100%);
  --gradient-amber:     linear-gradient(135deg, #f59e0b 0%, #fbbf24 100%);
  --gradient-red:       linear-gradient(135deg, #ef4444 0%, #f87171 100%);
  --gradient-blue:      linear-gradient(135deg, #3b82f6 0%, #60a5fa 100%);
  --gradient-surface:   linear-gradient(135deg, rgba(99,102,241,0.08) 0%, rgba(139,92,246,0.04) 100%);

  /* Glow effects */
  --glow-purple:    0 0 40px rgba(139, 92, 246, 0.15);
  --glow-green:     0 0 40px rgba(16, 185, 129, 0.15);
  --glow-blue:      0 0 40px rgba(59, 130, 246, 0.12);

  /* Semantic colors */
  --color-positive:     #10b981;   /* gains, above target */
  --color-negative:     #ef4444;   /* losses, below target */
  --color-warning:      #f59e0b;   /* drift, approaching limit */
  --color-neutral:      #6b7280;

  /* Text */
  --text-primary:   #f1f5f9;
  --text-secondary: #94a3b8;
  --text-muted:     #475569;
  --text-disabled:  #334155;

  /* Borders */
  --border-subtle:  rgba(255, 255, 255, 0.06);
  --border-default: rgba(255, 255, 255, 0.10);
  --border-strong:  rgba(255, 255, 255, 0.16);

  /* Radius */
  --radius-sm:  8px;
  --radius-md:  12px;
  --radius-lg:  16px;
  --radius-xl:  24px;
  --radius-full: 9999px;

  /* Shadows */
  --shadow-sm:  0 1px 3px rgba(0,0,0,0.4), 0 1px 2px rgba(0,0,0,0.3);
  --shadow-md:  0 4px 16px rgba(0,0,0,0.5), 0 2px 8px rgba(0,0,0,0.3);
  --shadow-lg:  0 20px 60px rgba(0,0,0,0.6), 0 8px 24px rgba(0,0,0,0.4);
  --shadow-glow: 0 0 0 1px rgba(139,92,246,0.2), 0 8px 32px rgba(139,92,246,0.12);
}
```

### 35.3 Typography

```css
/* Font stack */
--font-sans:  'Inter var', 'Inter', system-ui, sans-serif;
--font-mono:  'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace;
--font-display: 'Cal Sans', 'Inter var', sans-serif; /* headings */

/* Scale */
--text-xs:   0.75rem;   /* 12px — table labels, badges */
--text-sm:   0.875rem;  /* 14px — body, table cells */
--text-base: 1rem;      /* 16px — default */
--text-lg:   1.125rem;  /* 18px — card titles */
--text-xl:   1.25rem;   /* 20px — section headers */
--text-2xl:  1.5rem;    /* 24px — page titles */
--text-3xl:  1.875rem;  /* 30px — big numbers */
--text-4xl:  2.25rem;   /* 36px — hero numbers (net worth) */
--text-5xl:  3rem;      /* 48px — dashboard headline number */

/* Weights */
--font-normal:   400;
--font-medium:   500;
--font-semibold: 600;
--font-bold:     700;

/* Numbers always use mono font */
.number { font-family: var(--font-mono); font-variant-numeric: tabular-nums; }
```

### 35.4 Component Patterns

**Glass Card (primary surface)**
```css
.glass-card {
  background: var(--glass-bg);
  backdrop-filter: blur(var(--glass-blur));
  -webkit-backdrop-filter: blur(var(--glass-blur));
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  transition: all 0.2s ease;
}
.glass-card:hover {
  background: var(--glass-hover);
  border-color: rgba(255,255,255,0.12);
  box-shadow: var(--shadow-glow);
  transform: translateY(-1px);
}
```

**Metric Card (dashboard KPI)**
```css
.metric-card {
  /* glass base */
  background: linear-gradient(135deg, var(--glass-bg), rgba(99,102,241,0.03));
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-lg);
  padding: 20px 24px;
  position: relative;
  overflow: hidden;
}
.metric-card::before {
  /* subtle top accent line */
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 1px;
  background: var(--gradient-primary);
  opacity: 0.6;
}
.metric-card .label  { font-size: var(--text-xs); color: var(--text-muted); letter-spacing: 0.08em; text-transform: uppercase; }
.metric-card .value  { font-size: var(--text-4xl); font-family: var(--font-mono); font-weight: var(--font-bold); color: var(--text-primary); line-height: 1.1; margin: 8px 0 4px; }
.metric-card .change { font-size: var(--text-sm); font-family: var(--font-mono); }
.metric-card .change.positive { color: var(--color-positive); }
.metric-card .change.negative { color: var(--color-negative); }
```

**Glow Badge (regime status)**
```css
.badge-normal      { background: rgba(16,185,129,0.12); color: #34d399; border: 1px solid rgba(16,185,129,0.25); }
.badge-high-vol    { background: rgba(245,158,11,0.12); color: #fbbf24; border: 1px solid rgba(245,158,11,0.25); }
.badge-opportunity { background: rgba(99,102,241,0.12); color: #a78bfa; border: 1px solid rgba(99,102,241,0.25); }
/* All badges: border-radius: var(--radius-full); padding: 4px 12px; font-size: var(--text-xs); font-weight: 600; */
```

**Data Table**
```css
.data-table { border-collapse: separate; border-spacing: 0; width: 100%; }
.data-table th { font-size: var(--text-xs); color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.08em; font-weight: 500; padding: 10px 16px; border-bottom: 1px solid var(--border-subtle); }
.data-table td { font-size: var(--text-sm); color: var(--text-secondary); padding: 12px 16px; border-bottom: 1px solid var(--border-subtle); }
.data-table tr:hover td { background: rgba(255,255,255,0.02); color: var(--text-primary); }
.data-table td.number { font-family: var(--font-mono); }
```

**Sidebar Navigation**
```css
.sidebar {
  background: linear-gradient(180deg, rgba(13,13,20,0.95) 0%, rgba(5,5,8,0.98) 100%);
  backdrop-filter: blur(20px);
  border-right: 1px solid var(--border-subtle);
  width: 240px;
}
.nav-item { display: flex; align-items: center; gap: 10px; padding: 10px 16px; border-radius: var(--radius-md); color: var(--text-muted); font-size: var(--text-sm); font-weight: 500; transition: all 0.15s ease; }
.nav-item:hover { background: var(--glass-bg); color: var(--text-secondary); }
.nav-item.active { background: linear-gradient(135deg, rgba(99,102,241,0.15), rgba(139,92,246,0.08)); color: #a78bfa; border: 1px solid rgba(99,102,241,0.2); }
```

**Chart Colors (Recharts palette)**
```javascript
export const CHART_COLORS = {
  primary:    '#6366f1',  // indigo — primary series
  secondary:  '#8b5cf6',  // purple — secondary series
  positive:   '#10b981',  // emerald — gains
  negative:   '#ef4444',  // red — losses
  warning:    '#f59e0b',  // amber — alerts
  neutral:    '#475569',  // slate — muted
  us_equity:  '#6366f1',
  intl_equity:'#8b5cf6',
  bonds:      '#3b82f6',
  brazil:     '#10b981',
  crypto:     '#f59e0b',
  cash:       '#475569',
  // Monte Carlo bands
  p5:   'rgba(239,68,68,0.15)',
  p25:  'rgba(245,158,11,0.15)',
  p50:  'rgba(99,102,241,0.5)',   // median line, solid
  p75:  'rgba(16,185,129,0.15)',
  p95:  'rgba(16,185,129,0.25)',
}
```

**Page Background (each page)**
```css
.page-bg {
  min-height: 100vh;
  background:
    radial-gradient(ellipse 80% 50% at 50% -20%, rgba(99,102,241,0.12) 0%, transparent 60%),
    radial-gradient(ellipse 60% 40% at 80% 80%, rgba(139,92,246,0.06) 0%, transparent 50%),
    var(--bg-base);
}
```

### 35.5 Animation Standards

```css
/* Micro-interactions */
--transition-fast:   0.1s ease;
--transition-base:   0.2s ease;
--transition-slow:   0.3s cubic-bezier(0.4, 0, 0.2, 1);

/* Number counter animation on load — all metric cards */
@keyframes countUp {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}
.metric-value { animation: countUp 0.4s ease forwards; }

/* Skeleton loader */
@keyframes shimmer {
  0%   { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}
.skeleton {
  background: linear-gradient(90deg, var(--bg-surface) 25%, var(--bg-elevated) 50%, var(--bg-surface) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  border-radius: var(--radius-sm);
}
```

### 35.6 Next.js / Tailwind Implementation Notes

```javascript
// tailwind.config.js additions needed
module.exports = {
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        bg: { base: '#050508', surface: '#0d0d14', elevated: '#13131f' },
        brand: { purple: '#6366f1', violet: '#8b5cf6', lavender: '#a78bfa' },
        positive: '#10b981',
        negative: '#ef4444',
        warning: '#f59e0b',
      },
      fontFamily: {
        sans: ['Inter var', 'Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'glass': 'linear-gradient(135deg, rgba(255,255,255,0.04), rgba(255,255,255,0.02))',
      },
      boxShadow: {
        'glow-purple': '0 0 40px rgba(139, 92, 246, 0.15)',
        'glow-green':  '0 0 40px rgba(16, 185, 129, 0.15)',
        'glass': '0 4px 16px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.08)',
      },
      backdropBlur: { glass: '12px' },
    }
  }
}
```

```html
<!-- Add to frontend/app/layout.tsx <head> — Google Fonts -->
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet" />
```

---

## 36. STITCH MCP — DESIGN CONTEXT INTEGRATION

### Connection Status
- **Stitch Project ID:** `11580419759191253062`
- **Stitch Project URL:** `https://stitch.withgoogle.com/u/1/projects/11580419759191253062`
- **MCP Package:** `@_davideast/stitch-mcp` (v installed globally)
- **Claude Code config:** `C:/Users/Thiago/.claude.json` → project `D:/python/ovelhainvest` → `mcpServers.stitch`

### Auth Method
**API Key (no gcloud required).**
Key is read from `STITCH_API_KEY` environment variable.

To activate:
1. Open `https://stitch.withgoogle.com/u/1/settings` → API Keys
2. Generate a persistent API key
3. Add to Windows environment variables: `STITCH_API_KEY=your-key`
4. Restart Claude Code — the `stitch` MCP server will connect automatically

### MCP Config (already in `.claude.json`)
```json
{
  "mcpServers": {
    "stitch": {
      "command": "npx",
      "args": ["@_davideast/stitch-mcp", "proxy"],
      "env": {
        "STITCH_API_KEY": "REPLACE_WITH_KEY_FROM_STITCH_SETTINGS"
      }
    }
  }
}
```

### Available MCP Tools (once auth is active)
| Tool | Purpose |
|---|---|
| `list_projects` | List all Stitch projects |
| `list_screens` | List all screens in project |
| `get_screen` | Get screen metadata |
| `get_screen_code` | Download screen HTML/CSS |
| `get_screen_image` | Download screen PNG (base64) |
| `extract_design_context` | Extract Design DNA (colors, fonts, layouts) |
| `generate_screen_from_text` | Generate new screen from prompt |
| `build_site` | Build all screens into structured site |

### Design Files Location
- `design/screens/` — HTML + PNG per screen (populated by `scripts/load_stitch_context.ps1`)
- `design/DESIGN.md` — Screen index with IDs and file links
- `STITCH_PROMPT.md` — Full design spec used to generate screens

### Load Design Context
```powershell
$env:STITCH_API_KEY = "your-key"
.\scripts\load_stitch_context.ps1
```

### Screen Naming (per STITCH_PROMPT.md)
| # | Screen Name | Route |
|---|---|---|
| 1 | Dashboard | `/dashboard` |
| 2 | Signals | `/signals` |
| 3 | Assets | `/assets` |
| 4 | Performance | `/performance` |
| 5 | Projections | `/projections` |
| 6 | Tax | `/tax` |
| 7 | Journal | `/journal` |
| 8 | Config | `/config` |

