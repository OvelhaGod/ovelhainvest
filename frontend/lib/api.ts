/**
 * FastAPI client wrapper.
 * All backend calls go through here — never inline fetch in components.
 */

import type {
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
};
