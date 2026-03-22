/**
 * FastAPI client wrapper.
 * All backend calls go through here — never inline fetch in components.
 */

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
  health: () => request<{ status: string; supabase: string; version: string }>("/health"),
  // Phase 2+
  dailyStatus: () => request<unknown>("/api/v1/daily_status"),
  runAllocation: (body: unknown) =>
    request<unknown>("/api/v1/run_allocation", {
      method: "POST",
      body: JSON.stringify(body),
    }),
};
