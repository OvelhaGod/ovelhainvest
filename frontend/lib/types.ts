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

// ── Alert types (Phase 6) ─────────────────────────────────────────────────────

export interface AlertHistoryItem {
  id: string;
  alert_rule_id: string;
  triggered_at: string;
  payload: Record<string, unknown> | null;
  channel: string;
  delivered: boolean;
  alert_rules?: {
    rule_name: string;
    rule_type: string;
    user_id: string;
  } | null;
}

export interface AlertRule {
  id: string;
  user_id: string;
  rule_name: string;
  rule_type: string;
  conditions: Record<string, unknown>;
  is_active: boolean;
  last_triggered: string | null;
  created_at: string;
  source?: string;
}

// ── Admin types (Phase 6) ─────────────────────────────────────────────────────

export interface AdminStatus {
  automation_paused: boolean;
  pause_reason: string | null;
  last_daily_check: string | null;
  last_valuation_update: string | null;
  last_alert_dispatched: string | null;
  pending_approvals: number;
  telegram_connected: boolean;
  redis_connected: boolean;
  supabase_connected: boolean;
  anthropic_connected: boolean;
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
  fair_value_estimate_dcf: number | null;
  margin_of_safety_pct: number | null;
  buy_target: number | null;
  hold_range_low: number | null;
  hold_range_high: number | null;
  sell_target: number | null;
  moat_rating: string | null;
  rank_in_universe: number | null;
  tier: string | null;
  passes_buy_gate: boolean;
  dcf_assumptions: Record<string, unknown> | null;
  // Asset metadata joined
  moat_score: number | null;
  sector: string | null;
  region: string | null;
  currency: string;
  is_dcf_eligible: boolean;
}

export interface ValuationSummaryResponse {
  as_of_date: string | null;
  assets_scored: number;
  positive_mos_count: number;
  negative_mos_count: number;
  opportunity_count: number;
  top_by_composite: Partial<AssetValuation>[];
  top_opportunities: Partial<AssetValuation>[];
  margin_of_safety_distribution: Record<string, number>;
}

export interface ValuationUpdateResponse {
  assets_updated: number;
  top_opportunities: Partial<AssetValuation>[];
  notable_changes: string[];
  errors: string[];
  economic_season: string;
  run_timestamp: string;
}

// ── Performance (Phase 4) ──────────────────────────────────────────────────

export interface PeriodReturn {
  period: string;
  twr: number | null;
  mwr: number | null;
  benchmark_return: number | null;
  active_return: number | null;
}

export interface RatioInterpretation {
  value: number | null;
  label: string;
}

export interface DrawdownInfo {
  max_drawdown_pct: number | null;
  peak_date: string | null;
  trough_date: string | null;
  current_drawdown_pct: number | null;
}

export interface PerformanceSummaryResponse {
  user_id: string | null;
  as_of_date: string | null;
  period_returns: PeriodReturn[];
  sharpe: RatioInterpretation;
  sortino: RatioInterpretation;
  calmar: RatioInterpretation;
  beta: number | null;
  information_ratio: number | null;
  volatility_annualized: number | null;
  drawdown: DrawdownInfo;
  data_points: number;
}

export interface SleeveAttributionDetail {
  sleeve: string;
  portfolio_weight: number;
  benchmark_weight: number;
  portfolio_return: number;
  benchmark_return: number;
  allocation_effect: number;
  selection_effect: number;
  interaction_effect: number;
  total_effect: number;
}

export interface AttributionResponse {
  user_id: string | null;
  period_start: string | null;
  period_end: string | null;
  portfolio_return: number | null;
  benchmark_return: number | null;
  active_return: number | null;
  total_allocation_effect: number | null;
  total_selection_effect: number | null;
  total_interaction_effect: number | null;
  fx_contribution: number | null;
  per_sleeve: SleeveAttributionDetail[];
}

export interface BenchmarkComparisonResponse {
  benchmark_symbol: string;
  period: string;
  portfolio_return: number | null;
  benchmark_return: number | null;
  active_return: number | null;
  beta: number | null;
  correlation: number | null;
  information_ratio: number | null;
}

export interface RollingReturnsResponse {
  user_id: string | null;
  data_points: Record<string, number | null>[];
  windows: string[];
}

export interface RiskSummaryResponse {
  user_id: string | null;
  as_of_date: string | null;
  var_95: number | null;
  var_99: number | null;
  cvar_95: number | null;
  diversification_ratio: number | null;
  risk_parity_weights: Record<string, number>;
  actual_weights: Record<string, number>;
  correlation_matrix: Record<string, Record<string, number>>;
  high_correlation_pairs: Record<string, unknown>[];
}
