/** Shared TypeScript types derived from the Supabase DB schema. */

export type AssetClass =
  | "US_equity"
  | "Intl_equity"
  | "Bond"
  | "Brazil_equity"
  | "Crypto";

export type AccountType = "401k" | "Roth_IRA" | "Taxable" | "Crypto" | "Bank" | "Vault";

export type TaxTreatment =
  | "tax_deferred"
  | "tax_free"
  | "taxable"
  | "brazil_taxable"
  | "bank";

export type VaultType = "future_investments" | "opportunity" | "emergency";

export type SignalStatus = "pending" | "auto_ok" | "needs_approval" | "executed" | "ignored";

export type VolatilityRegime = "normal" | "high_vol" | "opportunity";

export interface SleeveWeights {
  us_equity: number;
  intl_equity: number;
  bonds: number;
  brazil_equity: number;
  crypto: number;
  cash: number;
}

export interface PortfolioSnapshot {
  id: string;
  user_id: string;
  snapshot_date: string;
  total_value: number;
  sleeve_weights: SleeveWeights | null;
  benchmark_symbol: string | null;
  benchmark_return: number | null;
  portfolio_return: number | null;
  drawdown_from_peak_pct: number | null;
  created_at: string;
}

export interface Asset {
  id: string;
  symbol: string;
  name: string;
  asset_class: AssetClass;
  region: string | null;
  sector: string | null;
  currency: string;
  benchmark_symbol: string | null;
  is_active: boolean;
}

export interface AssetValuation {
  id: string;
  asset_id: string;
  as_of_date: string;
  price: number;
  pe: number | null;
  ps: number | null;
  dividend_yield: number | null;
  vol_30d: number | null;
  drawdown_from_6_12m_high_pct: number | null;
  value_score: number | null;
  momentum_score: number | null;
  quality_score: number | null;
  fair_value_estimate: number | null;
  buy_target: number | null;
  hold_range_low: number | null;
  hold_range_high: number | null;
  sell_target: number | null;
  rank_in_universe: number | null;
  tier: string | null;
}

export interface SignalsRun {
  id: string;
  user_id: string;
  run_timestamp: string;
  event_type: string;
  inputs_summary: Record<string, unknown> | null;
  proposed_trades: unknown[] | null;
  ai_validation_summary: Record<string, unknown> | null;
  status: SignalStatus;
  notes: string | null;
}

export interface VaultBalance {
  vault_type: VaultType;
  balance: number;
  min_balance: number | null;
  max_balance: number | null;
}
