/**
 * Shared chart colors and rating utilities for OvelhaInvest.
 * Single source of truth for all chart styling decisions.
 */

// ── Sleeve/asset class colors ────────────────────────────────────────────────
export const SLEEVE_COLORS: Record<string, string> = {
  us_equity:     "#10b981",
  intl_equity:   "#06b6d4",
  bonds:         "#3b82f6",
  brazil_equity: "#22c55e",
  crypto:        "#8b5cf6",
  cash:          "#64748b",
};

// ── Multi-series chart palette ────────────────────────────────────────────────
export const CHART_PALETTE = ["#6366f1", "#10b981", "#f59e0b", "#ef4444", "#06b6d4", "#8b5cf6"];

// ── Monte Carlo percentile band colors ────────────────────────────────────────
export const MC_BANDS = {
  p5:  "rgba(239,68,68,0.12)",
  p25: "rgba(245,158,11,0.12)",
  p50: "#6366f1",          // median line — solid
  p75: "rgba(16,185,129,0.12)",
  p95: "rgba(16,185,129,0.22)",
};

// ── Risk ratio rating (client-side, always correct) ──────────────────────────
// Ignores backend label — compute from value directly so negative ratios
// never falsely appear as "Good".

export type RatioRating = "Excellent" | "Good" | "Fair" | "Poor" | "—";

export function getRatioRating(
  value: number | null | undefined,
  type: "sharpe" | "sortino" | "calmar" = "sharpe",
): RatioRating {
  if (value == null) return "—";

  // All ratios: negative is always Poor
  if (value < 0) return "Poor";

  switch (type) {
    case "sharpe":
      if (value >= 1.5) return "Excellent";
      if (value >= 0.8) return "Good";
      if (value >= 0.3) return "Fair";
      return "Poor";

    case "sortino":
      // Sortino has higher threshold since it excludes upside vol
      if (value >= 2.0) return "Excellent";
      if (value >= 1.0) return "Good";
      if (value >= 0.4) return "Fair";
      return "Poor";

    case "calmar":
      if (value >= 1.0) return "Excellent";
      if (value >= 0.5) return "Good";
      if (value >= 0.25) return "Fair";
      return "Poor";
  }
}

export const RATIO_BADGE_CLASSES: Record<RatioRating, string> = {
  Excellent: "text-[#10b981] bg-[rgba(16,185,129,0.12)] border-[rgba(16,185,129,0.25)]",
  Good:      "text-[#34d399] bg-[rgba(52,211,153,0.10)] border-[rgba(52,211,153,0.22)]",
  Fair:      "text-[#f59e0b] bg-[rgba(245,158,11,0.10)] border-[rgba(245,158,11,0.22)]",
  Poor:      "text-[#ef4444] bg-[rgba(239,68,68,0.10)] border-[rgba(239,68,68,0.22)]",
  "—":       "text-[#475569] bg-[rgba(71,85,105,0.12)] border-[rgba(71,85,105,0.20)]",
};
