"use client";

import { SWRConfig } from "swr";

// Cache TTLs in milliseconds
export const CACHE_TTL = {
  STATIC: 60 * 60 * 1000,      // 1 hour — strategy configs, asset metadata
  SLOW: 15 * 60 * 1000,        // 15 min — valuations, performance attribution
  MEDIUM: 5 * 60 * 1000,       // 5 min  — portfolio snapshots, daily status
  FAST: 60 * 1000,             // 1 min  — signals, alerts
  REALTIME: 30 * 1000,         // 30 sec — live prices (when needed)
};

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "https://investapi.ovelha.us";

export async function fetcher(path: string) {
  const res = await fetch(
    path.startsWith("http") ? path : `${API_BASE}${path}`,
    { headers: { "Content-Type": "application/json" } }
  );
  if (!res.ok) {
    const err = new Error(`API error ${res.status}: ${res.statusText}`);
    (err as Error & { status: number }).status = res.status;
    throw err;
  }
  return res.json();
}

export function SWRProvider({ children }: { children: React.ReactNode }) {
  return (
    <SWRConfig
      value={{
        fetcher,
        revalidateOnFocus: false,
        shouldRetryOnError: false,
        dedupingInterval: CACHE_TTL.FAST,
      }}
    >
      {children}
    </SWRConfig>
  );
}
