/**
 * Shared chart utility functions for Recharts components.
 * Provides tight Y-axis domain computation and consistent tick formatters.
 */

/**
 * Compute a tight Y-axis domain with configurable padding.
 * Prevents lines from hugging the top or bottom of the chart area.
 */
export function tightDomain(
  data: Record<string, unknown>[],
  keys: string[],
  padPct: number = 0.05
): [number, number] {
  const vals = data.flatMap((d) =>
    keys.map((k) => d[k] as number).filter((v) => v != null && !isNaN(v))
  );
  if (!vals.length) return [0, 100];
  const min = Math.min(...vals);
  const max = Math.max(...vals);
  const range = max - min || max * 0.1 || 1;
  return [
    Math.floor((min - range * padPct) * 100) / 100,
    Math.ceil((max + range * padPct) * 100) / 100,
  ];
}

/**
 * Format Y-axis tick for price/value charts.
 * Uses compact notation for large numbers.
 */
export function formatYTick(value: number): string {
  if (Math.abs(value) >= 10_000) return `${(value / 1000).toFixed(0)}k`;
  if (Math.abs(value) >= 1_000) return `${(value / 1000).toFixed(1)}k`;
  if (Math.abs(value) >= 10) return value.toFixed(2);
  return value.toFixed(4);
}

/**
 * Format Y-axis tick for indexed charts (relative to 100 at period start).
 */
export function formatIndexTick(value: number): string {
  return value.toFixed(0);
}

/**
 * Format currency for tooltip display.
 */
export function formatPrice(value: number): string {
  if (value >= 10_000)
    return `$${value.toLocaleString("en-US", { maximumFractionDigits: 0 })}`;
  if (value >= 100) return `$${value.toFixed(2)}`;
  return `$${value.toFixed(4)}`;
}
