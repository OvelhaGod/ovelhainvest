-- OvelhaInvest — Migration 002: Tax Lots
-- Run after 001_initial_schema.sql

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
