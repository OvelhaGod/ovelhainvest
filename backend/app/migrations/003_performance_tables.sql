-- OvelhaInvest — Migration 003: Performance Tables
-- Run after 002_tax_lots.sql

CREATE TABLE performance_attribution (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  period_start date NOT NULL,
  period_end date NOT NULL,
  total_return numeric(9,6),
  benchmark_return numeric(9,6),
  active_return numeric(9,6),          -- alpha vs benchmark
  attribution_by_sleeve jsonb,          -- {"us_equity": {"weight": 0.45, "return": 0.08, "contribution": 0.036}}
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
  var_95_1day numeric(9,6),            -- Value at Risk 95%
  var_99_1day numeric(9,6),            -- Value at Risk 99%
  risk_parity_weights jsonb,           -- Dalio-style risk-equal weights
  effective_diversification_ratio numeric(9,6),
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (user_id, as_of_date)
);
