-- OvelhaInvest — Migration 004: Decision Journal & Alert System
-- Run after 003_performance_tables.sql

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
CREATE INDEX decision_journal_user_date_idx ON decision_journal(user_id, event_date);

CREATE TABLE alert_rules (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  rule_name text NOT NULL,
  rule_type text NOT NULL,             -- "drawdown", "drift", "opportunity", "sell_target", "darf", "deposit", "correlation", "fx_move", "earnings"
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
CREATE INDEX alert_history_rule_time_idx ON alert_history(alert_rule_id, triggered_at);
