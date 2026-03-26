"use client";

import { useEffect } from "react";

/**
 * Fires POST /performance/snapshot on app startup so today's snapshot
 * is always up-to-date when the user first opens the dashboard.
 * Silently ignores errors (endpoint returns 200 or {"status":"exists"}).
 */
export function SnapshotInit() {
  useEffect(() => {
    const url =
      (process.env.NEXT_PUBLIC_API_URL ?? "https://investapi.ovelha.us") +
      "/performance/snapshot";
    fetch(url, { method: "POST" }).catch(() => {});
  }, []);

  return null;
}
