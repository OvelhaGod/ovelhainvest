/**
 * FastAPI client wrapper.
 * All backend calls go through here — never inline fetch in components.
 */

import type {
  AdminStatus,
  AlertHistoryItem,
  AlertRule,
  AllocationRunResponse,
  AssetValuation,
  AttributionResponse,
  BenchmarkComparisonResponse,
  DailyStatusResponse,
  PerformanceSummaryResponse,
  RiskSummaryResponse,
  RollingReturnsResponse,
  SignalsRun,
  ValuationSummaryResponse,
  ValuationUpdateResponse,
} from "@/lib/types";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    throw new Error(`API ${res.status}: ${res.statusText} — ${path}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () =>
    request<{ status: string; supabase: string; version: string }>("/health"),

  dailyStatus: (userId?: string) =>
    request<DailyStatusResponse>(
      `/daily_status${userId ? `?user_id=${userId}` : ""}`
    ),

  runAllocation: (body: { user_id?: string; event_type?: string; notes?: string }) =>
    request<AllocationRunResponse>("/run_allocation", {
      method: "POST",
      body: JSON.stringify({ event_type: "daily_check", ...body }),
    }),

  updateSignalStatus: (runId: string, status: string) =>
    request<{ id: string; status: string }>(`/signals/${runId}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    }),

  // ── Valuation (Phase 3) ──────────────────────────────────────────────────

  valuationSummary: (userId?: string) =>
    request<ValuationSummaryResponse>(
      `/valuation_summary${userId ? `?user_id=${userId}` : ""}`
    ),

  valuationDetail: (symbol: string) =>
    request<AssetValuation>(`/valuation/${symbol.toUpperCase()}`),

  runValuationUpdate: (body?: { dry_run?: boolean; economic_season?: string }) =>
    request<ValuationUpdateResponse>("/valuation_update", {
      method: "POST",
      body: JSON.stringify({ user_id: undefined, dry_run: false, ...body }),
    }),

  seedDevData: () =>
    request<{ status: string; inserted: number; total: number; errors: string[] }>(
      "/admin/seed",
      { method: "POST" }
    ),

  // Latest valuations (uses valuation_summary for the table)
  getLatestValuations: () =>
    request<ValuationSummaryResponse>("/valuation_summary").then(
      (r) => r.top_by_composite as AssetValuation[]
    ),

  // ── Performance (Phase 4) ─────────────────────────────────────────────────

  performanceSummary: (userId?: string) =>
    request<PerformanceSummaryResponse>(
      `/performance/summary${userId ? `?user_id=${userId}` : ""}`
    ),

  performanceAttribution: (periodStart?: string, periodEnd?: string, userId?: string) => {
    const params = new URLSearchParams();
    if (userId) params.set("user_id", userId);
    if (periodStart) params.set("period_start", periodStart);
    if (periodEnd) params.set("period_end", periodEnd);
    const qs = params.toString();
    return request<AttributionResponse>(`/performance/attribution${qs ? `?${qs}` : ""}`);
  },

  performanceBenchmark: (benchmark = "SPY", period = "ytd", userId?: string) => {
    const params = new URLSearchParams({ benchmark, period });
    if (userId) params.set("user_id", userId);
    return request<BenchmarkComparisonResponse>(`/performance/benchmark?${params}`);
  },

  performanceRolling: (windows = "1mo,3mo,1yr", userId?: string) => {
    const params = new URLSearchParams({ windows });
    if (userId) params.set("user_id", userId);
    return request<RollingReturnsResponse>(`/performance/rolling?${params}`);
  },

  performanceRisk: (userId?: string) =>
    request<RiskSummaryResponse>(
      `/performance/risk${userId ? `?user_id=${userId}` : ""}`
    ),

  triggerSnapshot: (userId?: string) =>
    request<{ status: string; snapshot_date: string; message: string }>(
      `/performance/snapshot${userId ? `?user_id=${userId}` : ""}`,
      { method: "POST" }
    ),

  // ── Journal (Phase 5) ─────────────────────────────────────────────────────

  listJournal: (params?: { limit?: number; offset?: number; action_type?: string; user_id?: string }) => {
    const qs = new URLSearchParams();
    if (params?.user_id) qs.set("user_id", params.user_id);
    if (params?.limit != null) qs.set("limit", String(params.limit));
    if (params?.offset != null) qs.set("offset", String(params.offset));
    if (params?.action_type) qs.set("action_type", params.action_type);
    return request<Record<string, unknown>[]>(`/journal${qs.toString() ? `?${qs}` : ""}`);
  },

  createJournalEntry: (body: {
    action_type: string;
    reasoning?: string;
    signal_run_id?: string;
    asset_id?: string;
    system_recommendation?: Record<string, unknown>;
    actual_action?: Record<string, unknown>;
  }, userId?: string) =>
    request<Record<string, unknown>>(
      `/journal${userId ? `?user_id=${userId}` : ""}`,
      { method: "POST", body: JSON.stringify(body) }
    ),

  journalStats: (userId?: string) =>
    request<Record<string, unknown>>(
      `/journal/stats${userId ? `?user_id=${userId}` : ""}`
    ),

  patchJournalOutcome: (entryId: string, outcome_30d?: number, outcome_90d?: number) =>
    request<Record<string, unknown>>(`/journal/${entryId}/outcome`, {
      method: "PATCH",
      body: JSON.stringify({ outcome_30d, outcome_90d }),
    }),

  // ── Alerts (Phase 6) ──────────────────────────────────────────────────────

  listAlertHistory: (params?: { limit?: number; rule_type?: string; user_id?: string }) => {
    const qs = new URLSearchParams();
    if (params?.user_id) qs.set("user_id", params.user_id);
    if (params?.limit != null) qs.set("limit", String(params.limit));
    if (params?.rule_type) qs.set("rule_type", params.rule_type);
    return request<AlertHistoryItem[]>(`/alerts/history${qs.toString() ? `?${qs}` : ""}`);
  },

  listAlertRules: (params?: { include_inactive?: boolean; user_id?: string }) => {
    const qs = new URLSearchParams();
    if (params?.user_id) qs.set("user_id", params.user_id);
    if (params?.include_inactive) qs.set("include_inactive", "true");
    return request<AlertRule[]>(`/alerts/rules${qs.toString() ? `?${qs}` : ""}`);
  },

  toggleAlertRule: (ruleId: string, updates?: Record<string, unknown>) =>
    request<AlertRule>(`/alerts/rules/${ruleId}`, {
      method: "PATCH",
      body: updates ? JSON.stringify(updates) : undefined,
    }),

  testAlertRule: (ruleId: string, userId?: string) =>
    request<{ sent: boolean; rule_name: string }>(
      `/alerts/test/${ruleId}${userId ? `?user_id=${userId}` : ""}`,
      { method: "POST" }
    ),

  // ── Admin (Phase 6) ───────────────────────────────────────────────────────

  adminStatus: () => request<AdminStatus>("/admin/status"),

  adminResume: (secret: string) =>
    request<{ resumed: boolean; message: string }>(`/admin/resume?authorization=${secret}`, { method: "POST" }),

  adminPause: (secret: string, reason?: string) =>
    request<{ paused: boolean; message: string }>(
      `/admin/pause?authorization=${secret}`,
      { method: "POST", body: JSON.stringify({ reason }) }
    ),

  // ── Simulation (Phase 7) ──────────────────────────────────────────────────

  simulationDashboardPreview: (body?: { monthly_contribution?: number }) =>
    request<{
      median_10yr: number;
      median_20yr: number;
      swr_probability: number;
      current_value: number;
      monthly_contribution: number;
      years_simulated: number;
      n_simulations: number;
    }>("/simulation/dashboard_preview", {
      method: "POST",
      body: JSON.stringify(body ?? {}),
    }),
};
