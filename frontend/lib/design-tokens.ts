/**
 * OvelhaInvest Design Tokens
 * Single source of truth — extracted from Stitch project 11580419759191253062
 * All values must match globals.css CSS custom properties exactly.
 */

export const colors = {
  // Backgrounds
  background: "#050508",
  surface: "#121315",
  surfaceContainerLowest: "#0d0e0f",
  surfaceContainerLow: "#1b1c1d",
  surfaceContainer: "#1f2021",
  surfaceContainerHigh: "#292a2b",
  surfaceContainerHighest: "#343536",
  surfaceBright: "#38393a",

  // Brand / semantic
  primary: "#4edea3",       // positive, gains, success
  primaryContainer: "#10b981",
  secondary: "#d0bcff",     // AI / automation features
  secondaryContainer: "#571bc1",
  tertiary: "#ffb95f",      // warnings, amber
  error: "#ffb4ab",         // negative, losses, errors

  // Text
  onSurface: "#e3e2e3",
  onSurfaceVariant: "#bbcabf",
  outline: "#86948a",
  outlineVariant: "#3c4a42",

  // Helpers (semantic)
  positive: "#4edea3",
  positiveDim: "#10b981",
  negative: "#ffb4ab",
  warning: "#ffb95f",
  ai: "#d0bcff",
} as const;

export const radius = {
  default: "1rem",
  lg: "2rem",
  xl: "3rem",
  full: "9999px",
} as const;

export const fonts = {
  geist: ["Geist Sans", "sans-serif"],
  body: ["Inter", "sans-serif"],
  mono: ["JetBrains Mono", "monospace"],
} as const;

// Tailwind class helpers for consistent usage
export const tw = {
  card: "glass-card",
  cardSubtle: "glass-card-subtle",
  textPrimary: "text-on-surface",
  textSecondary: "text-on-surface-variant",
  textMuted: "text-outline",
  positive: "text-primary",
  negative: "text-error",
  warning: "text-tertiary",
  badge: {
    positive: "bg-primary/10 text-primary border border-primary/20",
    negative: "bg-error/10 text-error border border-error/20",
    warning: "bg-tertiary/10 text-tertiary border border-tertiary/20",
    ai: "bg-secondary/10 text-secondary border border-secondary/20",
    neutral: "bg-white/5 text-on-surface-variant border border-white/10",
  },
} as const;

// Chart color palette (for Recharts)
export const chartColors = {
  positive: "#4edea3",
  negative: "#ffb4ab",
  warning: "#ffb95f",
  ai: "#d0bcff",
  neutral: "#86948a",
  // Multi-series palette (sleeves)
  usEquity: "#4edea3",
  intlEquity: "#d0bcff",
  bonds: "#60a5fa",
  brazil: "#ffb95f",
  crypto: "#f97316",
  cash: "#86948a",
  // Monte Carlo percentile bands
  p5:  "rgba(255, 180, 171, 0.12)",
  p25: "rgba(255, 185, 95, 0.10)",
  p50: "#4edea3",
  p75: "rgba(78, 222, 163, 0.12)",
  p95: "rgba(78, 222, 163, 0.20)",
  // Chart grid/axis
  grid: "rgba(60, 74, 66, 0.4)",
  axis: "#86948a",
};
