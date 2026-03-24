/**
 * Shared Recharts configuration — applied consistently to ALL charts.
 * Import this in every chart component.
 */
import { chartColors } from "@/lib/design-tokens";

export const CHART_GRID = {
  stroke: "rgba(60, 74, 66, 0.4)",
  strokeDasharray: "3 3",
  vertical: false,
};

export const CHART_AXIS_STYLE = {
  tick: {
    fill: "#86948a",
    fontSize: 10,
    fontFamily: "JetBrains Mono, monospace",
  },
  axisLine: { stroke: "rgba(60, 74, 66, 0.4)" },
  tickLine: false as const,
};

export const CHART_TOOLTIP_STYLE = {
  contentStyle: {
    background: "rgba(41, 42, 43, 0.95)",
    border: "1px solid rgba(255, 255, 255, 0.08)",
    borderRadius: "0.75rem",
    fontFamily: "JetBrains Mono, monospace",
    fontSize: "12px",
    color: "#e3e2e3",
    backdropFilter: "blur(12px)",
  },
  cursor: { stroke: "rgba(78, 222, 163, 0.3)", strokeWidth: 1 },
  labelStyle: { color: "#bbcabf", marginBottom: "4px" },
};

export const CHART_LEGEND_STYLE = {
  wrapperStyle: {
    fontFamily: "JetBrains Mono, monospace",
    fontSize: "11px",
    color: "#bbcabf",
  },
};

export const SLEEVE_COLORS: Record<string, string> = {
  us_equity:   "#4edea3",
  intl_equity: "#d0bcff",
  bonds:       "#60a5fa",
  brazil:      "#ffb95f",
  crypto:      "#f97316",
  cash:        "#86948a",
};

export const SERIES_PALETTE = [
  "#4edea3", "#d0bcff", "#60a5fa", "#ffb95f", "#f97316", "#86948a",
];

// Re-export chartColors for convenience in chart components
export { chartColors };
