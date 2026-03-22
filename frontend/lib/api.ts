/**
 * FastAPI client wrapper.
 * All backend calls go through here — never inline fetch in components.
 */

import type {
  AllocationRunResponse,
  DailyStatusResponse,
  SignalsRun,
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
};
