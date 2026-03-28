"use client";
/**
 * PortfolioChart — Portfolio vs benchmarks, all indexed to 100 at period start.
 * Perplexity Finance style: multi-line, period selector, reference line at 100.
 * Used on: dashboard, performance, markets pages.
 */

import { useState } from "react";
import useSWR from "swr";
import {
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { fetcher, CACHE_TTL } from "@/lib/swr-config";
import { SkeletonChart } from "@/components/ui/skeleton";
import { tightDomain, formatIndexTick } from "@/lib/chart-utils";

const PERIODS = ["1W", "1M", "3M", "6M", "1Y"] as const;
type Period = (typeof PERIODS)[number];
const PERIOD_API: Record<Period, string> = {
  "1W": "1w",
  "1M": "1m",
  "3M": "3m",
  "6M": "6m",
  "1Y": "1y",
};

const SERIES = [
  { key: "Portfolio", color: "#10b981", strokeWidth: 2.5 },
  { key: "SPY",       color: "#6366f1", strokeWidth: 1.5 },
  { key: "QQQ",       color: "#06b6d4", strokeWidth: 1.5 },
  { key: "ACWI",      color: "#8b5cf6", strokeWidth: 1.5 },
] as const;

interface PortfolioHistoryData {
  data: { date: string; value: number }[];
  portfolio_indexed: { date: string; value: number }[];
  benchmarks: Record<string, { date: string; value: number }[]>;
  current_value: number | null;
  change_pct: number | null;
}

interface PortfolioChartProps {
  height?: number;
  defaultPeriod?: Period;
  showPeriodSelector?: boolean;
}

export function PortfolioChart({
  height = 250,
  defaultPeriod = "3M",
  showPeriodSelector = true,
}: PortfolioChartProps) {
  const [period, setPeriod] = useState<Period>(defaultPeriod);

  const { data, isLoading, error } = useSWR<PortfolioHistoryData>(
    `/portfolio_history?period=${PERIOD_API[period]}`,
    fetcher,
    {
      refreshInterval: CACHE_TTL.MEDIUM,
      errorRetryCount: 3,
      errorRetryInterval: 2000,
      keepPreviousData: true,
    }
  );

  // Rule: if data exists, ALWAYS render the chart — stale errors are ignored.
  // Error/skeleton only show when there is no data at all.
  if (!data && isLoading) return <SkeletonChart height={height + 40} />;
  if (!data && error) {
    return (
      <div
        className="flex items-center justify-center text-white/20 text-xs rounded-xl border border-white/[0.06]"
        style={{ height, background: "rgba(255,255,255,0.02)" }}
      >
        Unable to load chart data
      </div>
    );
  }
  if (!data?.data?.length && !isLoading) {
    return (
      <div
        className="flex items-center justify-center text-white/20 text-xs rounded-xl border border-white/[0.06]"
        style={{ height, background: "rgba(255,255,255,0.02)" }}
      >
        No snapshot history yet — snapshots build up over time
      </div>
    );
  }
  // At this point data is guaranteed to be defined with data.length > 0
  if (!data) return null;

  // Merge all series by date
  const allDates = new Set<string>();
  (data.portfolio_indexed ?? []).forEach((d) => allDates.add(d.date));
  Object.values(data.benchmarks ?? {}).forEach((arr) => arr.forEach((d) => allDates.add(d.date)));

  const portMap = Object.fromEntries((data.portfolio_indexed ?? []).map((d) => [d.date, d.value]));
  const benchMaps: Record<string, Record<string, number>> = {};
  for (const [sym, arr] of Object.entries(data.benchmarks ?? {})) {
    benchMaps[sym] = Object.fromEntries(arr.map((d) => [d.date, d.value]));
  }

  const sortedDates = Array.from(allDates).sort();
  const chartData = sortedDates.map((date) => ({
    date,
    Portfolio: portMap[date],
    SPY:  benchMaps["SPY"]?.[date],
    QQQ:  benchMaps["QQQ"]?.[date],
    ACWI: benchMaps["ACWI"]?.[date],
  }));

  const isPositive = (data.change_pct ?? 0) >= 0;
  const domain = tightDomain(chartData, ["Portfolio", "SPY", "QQQ", "ACWI"]);

  return (
    <div>
      {/* Header row: legend + period selector */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex flex-wrap gap-3">
          {SERIES.map((s) => (
            <div key={s.key} className="flex items-center gap-1.5">
              <div className="w-4 h-0.5 rounded" style={{ background: s.color }} />
              <span className="text-xs text-white/40">{s.key}</span>
            </div>
          ))}
          {data.change_pct != null && (
            <span
              className="text-xs font-mono font-medium ml-1"
              style={{ color: isPositive ? "#10b981" : "#ef4444" }}
            >
              {isPositive ? "+" : ""}{data.change_pct.toFixed(2)}%
            </span>
          )}
        </div>
        {showPeriodSelector && (
          <div className="flex gap-1">
            {PERIODS.map((p) => (
              <button
                key={p}
                onClick={() => setPeriod(p)}
                className={`px-2 py-0.5 text-xs rounded font-mono transition-colors ${
                  period === p
                    ? "bg-white/[0.10] text-white/90"
                    : "text-white/30 hover:text-white/60"
                }`}
              >
                {p}
              </button>
            ))}
          </div>
        )}
      </div>

      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={chartData} margin={{ top: 2, right: 4, bottom: 0, left: 0 }}>
          <XAxis
            dataKey="date"
            tick={{ fill: "#52525b", fontSize: 10, fontFamily: "var(--font-mono, monospace)" }}
            axisLine={false}
            tickLine={false}
            interval="preserveStartEnd"
            tickFormatter={(v: string) =>
              new Date(v).toLocaleDateString("en-US", { month: "short", day: "numeric" })
            }
          />
          <YAxis
            domain={domain}
            tickFormatter={formatIndexTick}
            tick={{ fill: "#52525b", fontSize: 10, fontFamily: "var(--font-mono, monospace)" }}
            axisLine={false}
            tickLine={false}
            width={32}
          />
          <ReferenceLine
            y={100}
            stroke="rgba(255,255,255,0.06)"
            strokeDasharray="4 4"
          />
          <Tooltip
            contentStyle={{
              background: "rgba(9,9,11,0.95)",
              border: "1px solid rgba(255,255,255,0.08)",
              borderRadius: "8px",
              padding: "8px 12px",
              fontSize: "12px",
              fontFamily: "var(--font-mono, monospace)",
              color: "#f4f4f5",
            }}
            formatter={(v: number, name: string) => [
              v != null ? `${v.toFixed(1)}` : "—",
              name,
            ]}
            labelFormatter={(label: string) =>
              new Date(label).toLocaleDateString("en-US", {
                month: "short",
                day: "numeric",
                year: "numeric",
              })
            }
          />
          {SERIES.map((s) => (
            <Line
              key={s.key}
              type="monotone"
              dataKey={s.key}
              stroke={s.color}
              strokeWidth={s.strokeWidth}
              dot={false}
              activeDot={{ r: 3, strokeWidth: 0 }}
              connectNulls
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
      <p className="text-[10px] text-white/20 mt-2">
        Historical values estimated using current holdings × past prices. Connect accounts via Pluggy for accurate history.
      </p>
    </div>
  );
}
