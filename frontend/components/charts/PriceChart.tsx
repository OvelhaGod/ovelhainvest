"use client";
/**
 * PriceChart — interactive area chart with period selector.
 * Supports intraday (1D: 5-min bars, 1W: 30-min bars) and daily periods.
 * Variants: "standard" (with axes) | "minimal" (Perplexity-style, no axes)
 */

import { useState } from "react";
import useSWR from "swr";
import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { fetcher } from "@/lib/swr-config";
import { SkeletonChart } from "@/components/ui/skeleton";
import { tightDomain, formatYTick } from "@/lib/chart-utils";

const PERIODS = ["1D", "1W", "1M", "3M", "6M", "1Y"] as const;
type Period = (typeof PERIODS)[number];

const PERIOD_API: Record<Period, string> = {
  "1D": "1d", "1W": "1w", "1M": "1m", "3M": "3m", "6M": "6m", "1Y": "1y",
};

interface PriceChartProps {
  symbol: string;
  height?: number;
  showPeriodSelector?: boolean;
  defaultPeriod?: Period;
  variant?: "standard" | "minimal";
}

interface PriceData {
  symbol: string;
  period: string;
  data: { date: string; display?: string; close: number | null }[];
  change_pct: number | null;
  change_abs: number | null;
  current_price: number | null;
  color: string;
}

export function PriceChart({
  symbol,
  height = 200,
  showPeriodSelector = true,
  defaultPeriod = "1M",
  variant = "standard",
}: PriceChartProps) {
  const [period, setPeriod] = useState<Period>(defaultPeriod);

  const { data, isLoading, error } = useSWR<PriceData>(
    `/price_history/${symbol}?period=${PERIOD_API[period]}`,
    fetcher,
    {
      refreshInterval: period === "1D" ? 60_000 : period === "1W" ? 120_000 : 300_000,
      errorRetryCount: 3,
      errorRetryInterval: 2000,
      keepPreviousData: true,
    }
  );

  if (!data && isLoading) return <SkeletonChart height={height} />;
  if (!data?.data?.length && !isLoading) {
    return (
      <div className="flex items-center justify-center text-white/20 text-xs rounded-xl border border-white/[0.06]"
           style={{ height, background: "rgba(255,255,255,0.02)" }}>
        {error ? "Unable to load chart data" : "No data"}
      </div>
    );
  }
  if (!data) return null;

  const isPositive = (data.change_pct ?? 0) >= 0;
  const lineColor = isPositive ? "#10b981" : "#ef4444";
  const intraday = period === "1D" || period === "1W";

  const chartData = data.data.map((d) => ({
    date: intraday ? d.date : (d.date?.slice(0, 10) ?? d.date),
    label: d.display ?? (intraday ? (d.date?.slice(11, 16) ?? "") : (d.date?.slice(0, 10) ?? "")),
    value: d.close,
  }));

  const domain = tightDomain(
    chartData.filter((d) => d.value != null) as Record<string, unknown>[],
    ["value"]
  );

  const gradientId = `price-fill-${symbol}-${period}`;

  return (
    <div className="w-full">
      {showPeriodSelector && (
        <div className="flex gap-1 mb-3">
          {PERIODS.map((p) => (
            <button key={p} onClick={() => setPeriod(p)}
              className={`px-2 py-0.5 text-xs rounded font-mono transition-colors ${
                period === p ? "bg-white/[0.10] text-white/90" : "text-white/30 hover:text-white/60"
              }`}>
              {p}
            </button>
          ))}
        </div>
      )}

      {variant === "standard" && (
        <div className="flex items-baseline gap-2 mb-2">
          <span className="text-sm font-mono font-medium" style={{ color: lineColor }}>
            {isPositive ? "+" : ""}{data.change_pct?.toFixed(2)}%
          </span>
          {data.change_abs != null && (
            <span className="text-xs text-white/30 font-mono">
              {isPositive ? "+" : ""}${Math.abs(data.change_abs).toFixed(2)} this {period.toLowerCase()}
            </span>
          )}
        </div>
      )}

      <div className="relative">
        <ResponsiveContainer width="100%" height={height}>
          <AreaChart data={chartData}
            margin={{ top: 2, right: variant === "minimal" ? 0 : 4, bottom: 0, left: 0 }}>
            <defs>
              <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={lineColor} stopOpacity={variant === "minimal" ? 0.08 : 0.15} />
                <stop offset="100%" stopColor={lineColor} stopOpacity={0} />
              </linearGradient>
            </defs>
            <XAxis dataKey="label"
              tick={{ fill: "#52525b", fontSize: 10, fontFamily: "var(--font-mono, monospace)" }}
              axisLine={false} tickLine={false}
              interval="preserveStartEnd" minTickGap={variant === "minimal" ? 60 : 40}
            />
            {variant === "standard" ? (
              <YAxis domain={domain} allowDataOverflow={true}
                tickFormatter={(v: number) => v === 0 ? "" : formatYTick(v)}
                tick={{ fill: "#52525b", fontSize: 10, fontFamily: "var(--font-mono, monospace)" }}
                axisLine={false} tickLine={false} width={50}
              />
            ) : (
              <YAxis hide domain={domain} allowDataOverflow={true} />
            )}
            <Tooltip
              contentStyle={{
                background: "rgba(9,9,11,0.95)",
                border: "1px solid rgba(255,255,255,0.08)",
                borderRadius: "8px", padding: "8px 12px",
                fontSize: "12px", fontFamily: "var(--font-mono, monospace)",
                color: "#f4f4f5", boxShadow: "0 8px 32px rgba(0,0,0,0.5)",
              }}
              cursor={{ stroke: "rgba(255,255,255,0.08)", strokeWidth: 1, strokeDasharray: "4 4" }}
              formatter={(value: number) => [`$${value >= 100 ? value.toFixed(2) : value.toFixed(4)}`, symbol]}
              labelFormatter={(label: string) => label}
            />
            <Area type="monotone" dataKey="value"
              stroke={lineColor} strokeWidth={1.5}
              fill={`url(#${gradientId})`}
              baseValue={domain[0]}
              dot={false} activeDot={{ r: 3, fill: lineColor, strokeWidth: 0 }}
              connectNulls
            />
          </AreaChart>
        </ResponsiveContainer>

        {variant === "minimal" && data.current_price != null && (
          <div className="absolute top-1 right-0 font-mono text-xs font-semibold pointer-events-none"
               style={{ color: lineColor }}>
            ${data.current_price >= 100 ? data.current_price.toFixed(2) : data.current_price.toFixed(4)}
            <span className="ml-1.5 text-[10px] opacity-70">
              {isPositive ? "+" : ""}{data.change_pct?.toFixed(2)}%
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
