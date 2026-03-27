-- Migration 007: Phase 11 Personal Finance OS
-- Extends existing accounts table + adds 6 new tables for spending, budgeting, cashflow, net worth.
-- Safe to run multiple times (IF NOT EXISTS / ADD COLUMN IF NOT EXISTS).

-- ── Extend existing accounts table ─────────────────────────────────────────
-- The existing accounts table stores investment accounts (broker, tax_treatment).
-- Phase 11 adds personal finance fields: balance, credit card support, Pluggy sync.
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS current_balance  NUMERIC(15,2) DEFAULT 0;
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS credit_limit     NUMERIC(15,2);
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS is_liability     BOOLEAN DEFAULT FALSE;
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS pluggy_item_id   TEXT;
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS pluggy_account_id TEXT;
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS last_synced_at   TIMESTAMPTZ;
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS institution      TEXT;
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS updated_at       TIMESTAMPTZ DEFAULT NOW();

-- Backfill institution from broker (existing column)
UPDATE accounts SET institution = broker WHERE institution IS NULL;

-- ── Categories ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS categories (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     TEXT NOT NULL DEFAULT 'default',
  name        TEXT NOT NULL,
  type        TEXT NOT NULL CHECK (type IN ('income','expense','transfer','investment')),
  color       TEXT DEFAULT '#6366f1',
  icon        TEXT DEFAULT 'tag',
  is_system   BOOLEAN DEFAULT FALSE,
  parent_id   UUID REFERENCES categories(id),
  created_at  TIMESTAMPTZ DEFAULT NOW()
);
CREATE UNIQUE INDEX IF NOT EXISTS categories_user_name_idx ON categories(user_id, name);

-- ── Spending transactions (separate from investment transactions) ────────────
CREATE TABLE IF NOT EXISTS spending_transactions (
  id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id                 TEXT NOT NULL DEFAULT 'default',
  account_id              UUID REFERENCES accounts(id) ON DELETE SET NULL,
  category_id             UUID REFERENCES categories(id),
  date                    DATE NOT NULL,
  description             TEXT NOT NULL,
  amount                  NUMERIC(15,2) NOT NULL,
  currency                TEXT DEFAULT 'USD',
  amount_usd              NUMERIC(15,2),
  type                    TEXT NOT NULL CHECK (type IN ('income','expense','transfer','investment')),
  status                  TEXT DEFAULT 'cleared' CHECK (status IN ('pending','cleared','reconciled')),
  pluggy_transaction_id   TEXT UNIQUE,
  is_recurring            BOOLEAN DEFAULT FALSE,
  notes                   TEXT,
  tags                    TEXT[],
  created_at              TIMESTAMPTZ DEFAULT NOW(),
  updated_at              TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS spending_txn_user_date_idx ON spending_transactions(user_id, date DESC);
CREATE INDEX IF NOT EXISTS spending_txn_account_idx   ON spending_transactions(account_id);
CREATE INDEX IF NOT EXISTS spending_txn_category_idx  ON spending_transactions(category_id);

-- ── Budgets ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS budgets (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     TEXT NOT NULL DEFAULT 'default',
  category_id UUID REFERENCES categories(id),
  month       DATE NOT NULL,
  amount      NUMERIC(15,2) NOT NULL,
  currency    TEXT DEFAULT 'USD',
  created_at  TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id, category_id, month)
);
CREATE INDEX IF NOT EXISTS budgets_user_month_idx ON budgets(user_id, month);

-- ── Recurring items ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS recurring_items (
  id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id            TEXT NOT NULL DEFAULT 'default',
  name               TEXT NOT NULL,
  category_id        UUID REFERENCES categories(id),
  amount             NUMERIC(15,2) NOT NULL,
  currency           TEXT DEFAULT 'USD',
  frequency          TEXT NOT NULL CHECK (frequency IN ('weekly','biweekly','monthly','annual')),
  day_of_month       INTEGER CHECK (day_of_month BETWEEN 1 AND 31),
  type               TEXT NOT NULL CHECK (type IN ('income','expense')),
  is_active          BOOLEAN DEFAULT TRUE,
  next_expected_date DATE,
  created_at         TIMESTAMPTZ DEFAULT NOW()
);

-- ── Net worth snapshots ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS net_worth_snapshots (
  id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id               TEXT NOT NULL DEFAULT 'default',
  snapshot_date         DATE NOT NULL,
  total_assets_usd      NUMERIC(15,2),
  total_liabilities_usd NUMERIC(15,2),
  net_worth_usd         NUMERIC(15,2),
  investment_value_usd  NUMERIC(15,2),
  cash_usd              NUMERIC(15,2),
  breakdown             JSONB,
  created_at            TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id, snapshot_date)
);
CREATE INDEX IF NOT EXISTS nw_snapshots_user_date_idx ON net_worth_snapshots(user_id, snapshot_date DESC);

-- ── Cashflow events ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS cashflow_events (
  id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id            TEXT NOT NULL DEFAULT 'default',
  name               TEXT NOT NULL,
  amount             NUMERIC(15,2) NOT NULL,
  currency           TEXT DEFAULT 'USD',
  expected_date      DATE NOT NULL,
  type               TEXT NOT NULL CHECK (type IN ('income','expense','investment','tax','one_time')),
  is_confirmed       BOOLEAN DEFAULT FALSE,
  recurring_item_id  UUID REFERENCES recurring_items(id),
  created_at         TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS cashflow_events_date_idx ON cashflow_events(user_id, expected_date);

-- ── Seed default categories ─────────────────────────────────────────────────
INSERT INTO categories (user_id, name, type, color, icon, is_system) VALUES
  ('default', 'Salary',           'income',     '#10b981', 'briefcase',      TRUE),
  ('default', 'Freelance',        'income',     '#06b6d4', 'laptop',         TRUE),
  ('default', 'Investment Income','income',     '#8b5cf6', 'trending-up',    TRUE),
  ('default', 'Other Income',     'income',     '#6366f1', 'plus-circle',    TRUE),
  ('default', 'Housing',          'expense',    '#ef4444', 'home',           TRUE),
  ('default', 'Food & Dining',    'expense',    '#f59e0b', 'utensils',       TRUE),
  ('default', 'Transport',        'expense',    '#f97316', 'car',            TRUE),
  ('default', 'Healthcare',       'expense',    '#ec4899', 'heart',          TRUE),
  ('default', 'Shopping',         'expense',    '#a78bfa', 'shopping-bag',   TRUE),
  ('default', 'Entertainment',    'expense',    '#fb923c', 'tv',             TRUE),
  ('default', 'Subscriptions',    'expense',    '#60a5fa', 'repeat',         TRUE),
  ('default', 'Utilities',        'expense',    '#4ade80', 'zap',            TRUE),
  ('default', 'Travel',           'expense',    '#f472b6', 'plane',          TRUE),
  ('default', 'Education',        'expense',    '#34d399', 'book',           TRUE),
  ('default', 'Investment Buy',   'investment', '#10b981', 'trending-up',    TRUE),
  ('default', 'Investment Sell',  'investment', '#ef4444', 'trending-down',  TRUE),
  ('default', 'Transfer',         'transfer',   '#71717a', 'arrow-right',    TRUE),
  ('default', 'Other Expense',    'expense',    '#6b7280', 'more-horizontal',TRUE)
ON CONFLICT DO NOTHING;
