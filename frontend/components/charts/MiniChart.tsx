"use client";
/**
 * MiniChart — Perplexity-style inline SVG sparkline.
 * No axes, no labels — just the trend line + gradient fill.
 * Used in: assets table, markets page, dashboard cards.
 */

interface MiniChartProps {
  data: number[];
  color?: string;
  height?: number;
  width?: number;
  showGradient?: boolean;
  className?: string;
}

export function MiniChart({
  data,
  color,
  height = 40,
  width = 80,
  showGradient = true,
  className = "",
}: MiniChartProps) {
  if (!data || data.length < 2) {
    return (
      <div
        className={`rounded skeleton ${className}`}
        style={{ width, height }}
      />
    );
  }

  const trend = data[data.length - 1] >= data[0] ? "up" : "down";
  const lineColor = color ?? (trend === "up" ? "#10b981" : "#ef4444");

  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const pad = 2;
  const w = width;
  const h = height;

  const points = data
    .map((v, i) => {
      const x = pad + (i / (data.length - 1)) * (w - 2 * pad);
      const y = h - pad - ((v - min) / range) * (h - 2 * pad);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");

  // Gradient polygon: close path at bottom
  const firstX = pad;
  const lastX = pad + (w - 2 * pad);
  const gradientPoints = `${firstX},${h} ${points} ${lastX},${h}`;

  const gradientId = `mini-grad-${Math.random().toString(36).slice(2, 8)}`;

  return (
    <svg
      width={w}
      height={h}
      viewBox={`0 0 ${w} ${h}`}
      className={`overflow-visible shrink-0 ${className}`}
    >
      {showGradient && (
        <defs>
          <linearGradient id={gradientId} x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor={lineColor} stopOpacity="0.25" />
            <stop offset="100%" stopColor={lineColor} stopOpacity="0" />
          </linearGradient>
        </defs>
      )}
      {showGradient && (
        <polygon points={gradientPoints} fill={`url(#${gradientId})`} />
      )}
      <polyline
        points={points}
        fill="none"
        stroke={lineColor}
        strokeWidth="1.5"
        strokeLinejoin="round"
        strokeLinecap="round"
      />
    </svg>
  );
}
