-- OvelhaInvest / Thiago Wealth OS — Supabase schema v1
-- Migration 001: Core Schema
-- Run once via Supabase SQL Editor or CLI.

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
