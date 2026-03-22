/** Shared TypeScript types derived from the Supabase DB schema and API models. */

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

export type RegimeState = "normal" | "high_vol" | "opportunity" | "paused";

export type EconomicSeason =
  | "rising_growth_low_inflation"
  | "falling_growth_low_inflation"
  | "rising_inflation"
  | "falling_inflation_growth_recovery"
  | "normal";

// ── API response types ────────────────────────────────────────────────────────

export interface SleeveWeight {
  sleeve: string;
  current_weight: number;
  target_weight: number;
  min_weight: number;
  max_weight: number;
  drift: number;
  drift_pct: number;
  is_breached: boolean;
  current_value_usd: number;
}

export interface VaultBalance {
  vault_type: VaultType;
  balance_usd: number;
  min_balance: number | null;
  is_investable: boolean;
  approval_required: boolean;
  progress_pct: number | null;
}

export interface ProposedTrade {
  account_name: string;
  account_id: string | null;
  trade_type: "buy" | "sell" | "rebalance";
  symbol: string;
  asset_class: string;
  amount_usd: number;
  quantity_estimate: number | null;
  reason: string;
  sleeve: string;
  tax_risk_level: "low" | "medium" | "high";
  requires_approval: boolean;
  opportunity_tier: number | null;
  margin_of_safety_pct: number | null;
}

export interface DailyStatusResponse {
  total_value_usd: number;
  total_value_brl: number;
  usd_brl_rate: number;
  sleeve_weights: SleeveWeight[];
  vault_balances: VaultBalance[];
  regime_state: RegimeState;
  economic_season: EconomicSeason;
  pending_approvals: number;
  last_run_timestamp: string | null;
  today_pnl_usd: number | null;
  today_pnl_pct: number | null;
  ytd_return_twr: number | null;
  max_drawdown_pct: number | null;
  portfolio_snapshot_date: string | null;
}

export interface AllocationRunResponse {
  run_id: string;
  run_timestamp: string;
  event_type: string;
  regime_state: RegimeState;
  economic_season: EconomicSeason;
  sleeve_weights: SleeveWeight[];
  vault_balances: VaultBalance[];
  proposed_trades: ProposedTrade[];
  total_value_usd: number;
  total_value_brl: number;
  usd_brl_rate: number;
  approval_required_count: number;
  deferred_dca: boolean;
  deferred_reason: string | null;
  status: SignalStatus;
}

export interface SignalsRun {
  id: string;
  user_id: string;
  run_timestamp: string;
  event_type: string;
  inputs_summary: Record<string, unknown> | null;
  proposed_trades: ProposedTrade[] | null;
  ai_validation_summary: Record<string, unknown> | null;
  status: SignalStatus;
  notes: string | null;
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
  is_dcf_eligible: boolean;
  moat_rating: string | null;
  is_active: boolean;
}

export interface AssetValuation {
  id: string;
  asset_id: string;
  symbol: string;
  name: string;
  asset_class: AssetClass;
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
  composite_score: number | null;
  fair_value_estimate: number | null;
  margin_of_safety_pct: number | null;
  buy_target: number | null;
  hold_range_low: number | null;
  hold_range_high: number | null;
  sell_target: number | null;
  moat_score: number | null;
  rank_in_universe: number | null;
  tier: string | null;
}
