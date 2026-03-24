"use client";

/**
 * /performance — Full 4-tab performance analytics page.
 * Tabs: Summary | Attribution | Rolling | Risk
 * CLAUDE.md Section 17 + Stitch glassmorphism design system.
 */

import { useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "@/lib/api";
import { CorrelationHeatmap } from "@/components/charts/CorrelationHeatmap";
import type {
  AttributionResponse,
  BenchmarkComparisonResponse,
  PerformanceSummaryResponse,
  RiskSummaryResponse,
  RollingReturnsResponse,
} from "@/lib/types";

// ── Helpers ────────────────────────────────────────────────────────────────

function pct(v: number | null | undefined, dp = 1): string {
  if (v == null) return "—";
  const sign = v >= 0 ? "+" : "";
  return `${sign}${(v * 100).toFixed(dp)}%`;
}

function num(v: number | null | undefined, dp = 2): string {
  if (v == null) return "—";
  return v.toFixed(dp);
}

function colorPct(v: number | null | undefined): string {
  if (v == null) return "text-[#94a3b8]";
  return v >= 0 ? "text-[#10b981]" : "text-[#ef4444]";
}

const RATIO_COLORS: Record<string, string> = {
  Excellent: "text-primary bg-primary/10 border-primary/20",
  Good: "text-primary bg-primary/10 border-primary/20",
  Fair: "text-tertiary bg-tertiary/10 border-tertiary/20",
  Poor: "text-error bg-error/10 border-error/20",
  "—": "text-[#475569] bg-[rgba(71,85,105,0.12)] border-[rgba(71,85,105,0.25)]",
};

const SLEEVE_COLORS: Record<string, string> = {
  us_equity: "#6366f1",
  intl_equity: "#8b5cf6",
  bonds: "#3b82f6",
  brazil_equity: "#10b981",
  crypto: "#f59e0b",
  cash: "#475569",
};

const PERIOD_LABELS: Record<string, string> = {
  "1mo": "1M", "3mo": "3M", "6mo": "6M",
  ytd: "YTD", "1yr": "1Y", "3yr": "3Y", all_time: "All",
};

// ── Sub-components ─────────────────────────────────────────────────────────

function GlassCard({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`glass-card p-5 ${className}`}>
      {children}
    </div>
  );
}

function RatioCard({
  label,
  value,
  interpretation,
  subtitle,
}: {
  label: string;
  value: number | null;
  interpretation: string;
  subtitle?: string;
}) {
  const colorClass = RATIO_COLORS[interpretation] || RATIO_COLORS["—"];
  return (
    <GlassCard>
      <p className="text-xs text-[#475569] uppercase tracking-wider mb-1">{label}</p>
      <p className="text-3xl font-bold font-mono text-[#f1f5f9] mt-1">{num(value)}</p>
      <span className={`mt-2 inline-block text-xs font-semibold px-2.5 py-0.5 rounded-full border ${colorClass}`}>
        {interpretation}
      </span>
      {subtitle && <p className="text-xs text-[#475569] mt-1">{subtitle}</p>}
    </GlassCard>
  );
}

function PeriodReturnGrid({ data }: { data: PerformanceSummaryResponse }) {
  const periods = data.period_returns;
  return (
    <div className="grid grid-cols-7 gap-2">
      {periods.map((p) => {
        const label = PERIOD_LABELS[p.period] || p.period;
        const twr = p.twr;
        const active = p.active_return;
        return (
          <GlassCard key={p.period} className="!p-3 text-center">
            <p className="text-[10px] text-[#475569] uppercase tracking-wider">{label}</p>
            <p className={`text-lg font-bold font-mono mt-1 ${colorPct(twr)}`}>{pct(twr)}</p>
            {active != null && (
              <p className={`text-[10px] font-mono mt-0.5 ${colorPct(active)}`}>
                {pct(active)} α
              </p>
            )}
          </GlassCard>
        );
      })}
    </div>
  );
}

// ── Summary Tab ────────────────────────────────────────────────────────────

function SummaryTab({ data, benchmark }: { data: PerformanceSummaryResponse; benchmark: BenchmarkComparisonResponse | null }) {
  const dd = data.drawdown;
  return (
    <div className="space-y-4">
      {/* Period returns */}
      <div>
        <h2 className="text-xs font-semibold text-[#475569] uppercase tracking-wider mb-3">
          Period Returns
        </h2>
        <PeriodReturnGrid data={data} />
      </div>

      {/* Ratio cards */}
      <div>
        <h2 className="text-xs font-semibold text-[#475569] uppercase tracking-wider mb-3">
          Risk-Adjusted Metrics
        </h2>
        <div className="grid grid-cols-3 gap-4">
          <RatioCard
            label="Sharpe Ratio"
            value={data.sharpe.value}
            interpretation={data.sharpe.label}
            subtitle="Risk-adjusted return"
          />
          <RatioCard
            label="Sortino Ratio"
            value={data.sortino.value}
            interpretation={data.sortino.label}
            subtitle="Downside-risk adjusted"
          />
          <RatioCard
            label="Calmar Ratio"
            value={data.calmar.value}
            interpretation={data.calmar.label}
            subtitle="Return / max drawdown"
          />
        </div>
      </div>

      {/* Secondary metrics */}
      <div className="grid grid-cols-4 gap-3">
        <GlassCard>
          <p className="text-xs text-[#475569] uppercase tracking-wider">Volatility</p>
          <p className="text-xl font-bold font-mono text-[#f1f5f9] mt-1">{pct(data.volatility_annualized)}</p>
          <p className="text-xs text-[#475569]">Annualized</p>
        </GlassCard>
        <GlassCard>
          <p className="text-xs text-[#475569] uppercase tracking-wider">Max Drawdown</p>
          <p className={`text-xl font-bold font-mono mt-1 ${colorPct(dd.max_drawdown_pct)}`}>
            {pct(dd.max_drawdown_pct)}
          </p>
          <p className="text-xs text-[#475569]">
            {dd.peak_date ? `Peak ${dd.peak_date}` : "All-time"}
          </p>
        </GlassCard>
        <GlassCard>
          <p className="text-xs text-[#475569] uppercase tracking-wider">Beta (vs SPY)</p>
          <p className="text-xl font-bold font-mono text-[#f1f5f9] mt-1">{num(data.beta)}</p>
          <p className="text-xs text-[#475569]">Market sensitivity</p>
        </GlassCard>
        <GlassCard>
          <p className="text-xs text-[#475569] uppercase tracking-wider">Info Ratio</p>
          <p className={`text-xl font-bold font-mono mt-1 ${colorPct(data.information_ratio)}`}>
            {num(data.information_ratio)}
          </p>
          <p className="text-xs text-[#475569]">Alpha consistency</p>
        </GlassCard>
      </div>

      {/* Benchmark comparison */}
      {benchmark && (
        <GlassCard>
          <div className="flex items-center gap-2 mb-3">
            <h2 className="text-sm font-semibold text-[#f1f5f9]">vs {benchmark.benchmark_symbol}</h2>
            <span className="text-xs text-[#475569] uppercase tracking-wider px-2 py-0.5 rounded-full border border-white/[0.06] bg-white/[0.03]">
              {benchmark.period.toUpperCase()}
            </span>
          </div>
          <div className="grid grid-cols-3 gap-4">
            <div>
              <p className="text-xs text-[#475569]">Portfolio</p>
              <p className={`text-2xl font-bold font-mono ${colorPct(benchmark.portfolio_return)}`}>
                {pct(benchmark.portfolio_return)}
              </p>
            </div>
            <div>
              <p className="text-xs text-[#475569]">Benchmark</p>
              <p className={`text-2xl font-bold font-mono ${colorPct(benchmark.benchmark_return)}`}>
                {pct(benchmark.benchmark_return)}
              </p>
            </div>
            <div>
              <p className="text-xs text-[#475569]">Alpha</p>
              <p className={`text-2xl font-bold font-mono ${colorPct(benchmark.active_return)}`}>
                {pct(benchmark.active_return)}
              </p>
            </div>
          </div>
        </GlassCard>
      )}
    </div>
  );
}

// ── Attribution Tab ────────────────────────────────────────────────────────

interface FxAttributionData {
  has_data: boolean;
  message?: string;
  brazil_return_brl?: number;
  brazil_return_usd?: number;
  fx_contribution?: number;
  usd_brl_start?: number;
  usd_brl_end?: number;
  usd_brl_change_pct?: number;
  interpretation?: string;
  rate_history?: Array<{ date: string; rate: number }>;
}

function FxAttributionCard({ data }: { data: FxAttributionData | null }) {
  if (!data) return null;

  if (!data.has_data) {
    return (
      <GlassCard className="border-l-2 border-l-[#10b981]/40">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-base">🇧🇷</span>
          <h3 className="text-sm font-semibold text-[#f1f5f9]">Brazil Sleeve — Currency Effect</h3>
        </div>
        <p className="text-xs text-[#475569]">{data.message ?? "No Brazil sleeve data for this period."}</p>
        {data.rate_history && data.rate_history.length > 0 && (
          <div className="mt-3">
            <p className="text-xs text-[#475569] mb-2">USD/BRL Rate</p>
            <ResponsiveContainer width="100%" height={80}>
              <LineChart data={data.rate_history}>
                <Line type="monotone" dataKey="rate" stroke="#10b981" strokeWidth={1.5} dot={false} />
                <XAxis dataKey="date" hide />
                <YAxis domain={["auto", "auto"]} hide />
                <Tooltip
                  contentStyle={{ background: "#0d0d14", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 8, fontSize: 11 }}
                  labelStyle={{ color: "#f1f5f9" }}
                  formatter={(val: number) => [val.toFixed(4), "USD/BRL"]}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </GlassCard>
    );
  }

  const fxIsNegative = (data.fx_contribution ?? 0) < 0;

  return (
    <GlassCard className={`border-l-2 ${fxIsNegative ? "border-l-[#ef4444]/40" : "border-l-[#10b981]/40"}`}>
      <div className="flex items-center gap-2 mb-3">
        <span className="text-base">🇧🇷</span>
        <h3 className="text-sm font-semibold text-[#f1f5f9]">Brazil Sleeve — Currency Effect</h3>
      </div>

      <div className="grid grid-cols-4 gap-3 mb-3">
        <div>
          <p className="text-[10px] text-[#475569] uppercase tracking-wider">Return in BRL</p>
          <p className={`text-lg font-bold font-mono mt-0.5 ${colorPct(data.brazil_return_brl)}`}>
            {pct(data.brazil_return_brl)}
          </p>
          <p className="text-[10px] text-[#475569]">Local currency</p>
        </div>
        <div>
          <p className="text-[10px] text-[#475569] uppercase tracking-wider">Return in USD</p>
          <p className={`text-lg font-bold font-mono mt-0.5 ${colorPct(data.brazil_return_usd)}`}>
            {pct(data.brazil_return_usd)}
          </p>
          <p className="text-[10px] text-[#475569]">After FX</p>
        </div>
        <div>
          <p className="text-[10px] text-[#475569] uppercase tracking-wider">BRL Change</p>
          <p className={`text-lg font-bold font-mono mt-0.5 ${colorPct(-(data.usd_brl_change_pct ?? 0))}`}>
            {/* BRL strengthens when USD/BRL falls */}
            {pct(-(data.usd_brl_change_pct ?? 0))}
          </p>
          <p className="text-[10px] text-[#475569]">
            {(data.usd_brl_start ?? 0).toFixed(2)} → {(data.usd_brl_end ?? 0).toFixed(2)}
          </p>
        </div>
        <div>
          <p className="text-[10px] text-[#475569] uppercase tracking-wider">Net FX Effect</p>
          <p className={`text-lg font-bold font-mono mt-0.5 ${colorPct(data.fx_contribution)}`}>
            {pct(data.fx_contribution)}
          </p>
          <p className="text-[10px] text-[#475569]">
            {fxIsNegative ? "Drag on returns" : "Boost to returns"}
          </p>
        </div>
      </div>

      {data.interpretation && (
        <p className="text-xs text-[#94a3b8] mb-3 italic">{data.interpretation}</p>
      )}

      {data.rate_history && data.rate_history.length > 0 && (
        <div>
          <p className="text-[10px] text-[#475569] uppercase tracking-wider mb-2">USD/BRL Rate History</p>
          <ResponsiveContainer width="100%" height={80}>
            <LineChart data={data.rate_history}>
              <Line type="monotone" dataKey="rate" stroke="#10b981" strokeWidth={1.5} dot={false} />
              <XAxis
                dataKey="date"
                tick={{ fill: "#475569", fontSize: 9 }}
                axisLine={false}
                tickLine={false}
                tickFormatter={(v: string) => v.slice(5)}
                interval={Math.floor(data.rate_history!.length / 4)}
              />
              <YAxis domain={["auto", "auto"]} tick={{ fill: "#475569", fontSize: 9 }} axisLine={false} tickLine={false} width={40} tickFormatter={(v: number) => v.toFixed(2)} />
              <Tooltip
                contentStyle={{ background: "#0d0d14", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 8, fontSize: 11 }}
                labelStyle={{ color: "#f1f5f9" }}
                formatter={(val: number) => [val.toFixed(4), "USD/BRL"]}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </GlassCard>
  );
}

function AttributionTab({
  data,
  fxAttribution,
}: {
  data: AttributionResponse | null;
  fxAttribution: FxAttributionData | null;
}) {
  if (!data || data.per_sleeve.length === 0) {
    return (
      <div className="space-y-4">
        <GlassCard>
          <p className="text-sm text-[#475569] text-center py-8">
            No attribution data yet — run the daily snapshot to populate.
          </p>
        </GlassCard>
        <FxAttributionCard data={fxAttribution} />
      </div>
    );
  }

  const chartData = useMemo(
    () =>
      data.per_sleeve.map((s) => ({
        name: s.sleeve.replace("_", " "),
        allocation: parseFloat((s.allocation_effect * 100).toFixed(2)),
        selection: parseFloat((s.selection_effect * 100).toFixed(2)),
        interaction: parseFloat((s.interaction_effect * 100).toFixed(2)),
      })),
    [data.per_sleeve]
  );

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-4 gap-3">
        {[
          { label: "Portfolio Return", val: data.portfolio_return },
          { label: "Benchmark Return", val: data.benchmark_return },
          { label: "Active Return", val: data.active_return },
          { label: "FX Contribution", val: data.fx_contribution },
        ].map(({ label, val }) => (
          <GlassCard key={label}>
            <p className="text-xs text-[#475569] uppercase tracking-wider">{label}</p>
            <p className={`text-xl font-bold font-mono mt-1 ${colorPct(val)}`}>{pct(val)}</p>
          </GlassCard>
        ))}
      </div>

      <GlassCard>
        <h2 className="text-sm font-semibold text-[#f1f5f9] mb-4">
          Brinson-Hood-Beebower Attribution by Sleeve
        </h2>
        <ResponsiveContainer width="100%" height={240}>
          <BarChart data={chartData} layout="vertical" margin={{ left: 20, right: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" horizontal={false} />
            <XAxis type="number" tickFormatter={(v) => `${v}%`} tick={{ fill: "#475569", fontSize: 11 }} axisLine={false} tickLine={false} />
            <YAxis type="category" dataKey="name" tick={{ fill: "#94a3b8", fontSize: 11 }} axisLine={false} tickLine={false} width={90} />
            <Tooltip
              contentStyle={{ background: "#0d0d14", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 8 }}
              labelStyle={{ color: "#f1f5f9" }}
              itemStyle={{ color: "#94a3b8" }}
              formatter={(val: number) => [`${val}%`]}
            />
            <Legend iconType="square" iconSize={8} wrapperStyle={{ paddingTop: 8, color: "#94a3b8", fontSize: 11 }} />
            <ReferenceLine x={0} stroke="rgba(255,255,255,0.15)" />
            <Bar dataKey="allocation" name="Allocation" stackId="a" fill="#6366f1" radius={[0, 2, 2, 0]} />
            <Bar dataKey="selection" name="Selection" stackId="a" fill="#10b981" radius={[0, 2, 2, 0]} />
            <Bar dataKey="interaction" name="Interaction" stackId="a" fill="#f59e0b" radius={[0, 2, 2, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </GlassCard>

      {/* Per-sleeve table */}
      <GlassCard>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-white/[0.06]">
              {["Sleeve", "Port Wt", "Bench Wt", "Port Ret", "Bench Ret", "Alloc", "Select", "Total"].map((h) => (
                <th key={h} className="text-left py-2 px-3 text-xs text-[#475569] uppercase tracking-wider font-medium">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.per_sleeve.map((s) => (
              <tr key={s.sleeve} className="border-b border-white/[0.04] hover:bg-white/[0.02]">
                <td className="py-2 px-3 text-[#f1f5f9] font-medium">{s.sleeve.replace("_", " ")}</td>
                <td className="py-2 px-3 text-[#94a3b8] font-mono">{pct(s.portfolio_weight, 1)}</td>
                <td className="py-2 px-3 text-[#94a3b8] font-mono">{pct(s.benchmark_weight, 1)}</td>
                <td className={`py-2 px-3 font-mono ${colorPct(s.portfolio_return)}`}>{pct(s.portfolio_return)}</td>
                <td className={`py-2 px-3 font-mono ${colorPct(s.benchmark_return)}`}>{pct(s.benchmark_return)}</td>
                <td className={`py-2 px-3 font-mono ${colorPct(s.allocation_effect)}`}>{pct(s.allocation_effect, 2)}</td>
                <td className={`py-2 px-3 font-mono ${colorPct(s.selection_effect)}`}>{pct(s.selection_effect, 2)}</td>
                <td className={`py-2 px-3 font-mono font-semibold ${colorPct(s.total_effect)}`}>{pct(s.total_effect, 2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </GlassCard>

      {/* FX Attribution card — Brazil sleeve currency effect */}
      <FxAttributionCard data={fxAttribution} />
    </div>
  );
}

// ── Rolling Tab ────────────────────────────────────────────────────────────

function RollingTab({ data }: { data: RollingReturnsResponse | null }) {
  if (!data || data.data_points.length === 0) {
    return (
      <GlassCard>
        <p className="text-sm text-[#475569] text-center py-8">
          No rolling return data yet — at least 21 snapshots needed.
        </p>
      </GlassCard>
    );
  }

  const WINDOW_COLORS: Record<string, string> = {
    "1mo": "#f59e0b",
    "3mo": "#6366f1",
    "1yr": "#10b981",
  };

  // Sample to last 60 points for display
  const displayData = useMemo(() => data.data_points.slice(-60), [data.data_points]);

  return (
    <div className="space-y-4">
      <GlassCard>
        <h2 className="text-sm font-semibold text-[#f1f5f9] mb-4">Rolling Returns</h2>
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={displayData} margin={{ left: 10, right: 10, top: 5, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" vertical={false} />
            <XAxis
              dataKey="date"
              tick={{ fill: "#475569", fontSize: 10 }}
              axisLine={false}
              tickLine={false}
              tickFormatter={(v) => (v as string).slice(5)}
              interval={Math.floor(displayData.length / 6)}
            />
            <YAxis
              tick={{ fill: "#475569", fontSize: 10 }}
              axisLine={false}
              tickLine={false}
              tickFormatter={(v) => `${(v * 100).toFixed(0)}%`}
            />
            <Tooltip
              contentStyle={{ background: "#0d0d14", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 8 }}
              labelStyle={{ color: "#f1f5f9", fontSize: 11 }}
              formatter={(val: number) => [`${(val * 100).toFixed(1)}%`]}
            />
            <ReferenceLine y={0} stroke="rgba(255,255,255,0.15)" />
            {data.windows.map((w) => (
              <Line
                key={w}
                type="monotone"
                dataKey={w}
                stroke={WINDOW_COLORS[w] || "#8b5cf6"}
                strokeWidth={1.5}
                dot={false}
                name={w}
                connectNulls={false}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
        <div className="flex gap-4 mt-2 justify-center">
          {data.windows.map((w) => (
            <div key={w} className="flex items-center gap-1.5">
              <div className="w-3 h-0.5 rounded" style={{ backgroundColor: WINDOW_COLORS[w] || "#8b5cf6" }} />
              <span className="text-xs text-[#475569]">{w}</span>
            </div>
          ))}
        </div>
      </GlassCard>
    </div>
  );
}

// ── Risk Tab ───────────────────────────────────────────────────────────────

interface CorrelationHistoryData {
  pairs: Array<{
    sleeves: [string, string];
    current_correlation: number;
    history: Array<{ date: string; correlation: number }>;
  }>;
  highest_pair: { sleeves: [string, string]; current_correlation: number } | null;
}

const DONUT_COLORS = ["#6366f1", "#8b5cf6", "#3b82f6", "#10b981", "#f59e0b", "#475569"];

function DonutChart({
  data,
  title,
}: {
  data: Array<{ name: string; value: number }>;
  title: string;
}) {
  return (
    <div>
      <p className="text-xs text-[#475569] uppercase tracking-wider mb-2 text-center">{title}</p>
      <ResponsiveContainer width="100%" height={160}>
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius={42}
            outerRadius={65}
            paddingAngle={2}
            dataKey="value"
          >
            {data.map((_entry, index) => (
              <Cell key={index} fill={DONUT_COLORS[index % DONUT_COLORS.length]} opacity={0.85} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{ background: "#0d0d14", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 8, fontSize: 11 }}
            formatter={(val: number, name: string) => [`${(val * 100).toFixed(1)}%`, name]}
          />
        </PieChart>
      </ResponsiveContainer>
      <div className="flex flex-wrap gap-x-3 gap-y-1 justify-center mt-1">
        {data.map((entry, i) => (
          <div key={entry.name} className="flex items-center gap-1">
            <div className="w-2 h-2 rounded-full" style={{ backgroundColor: DONUT_COLORS[i % DONUT_COLORS.length] }} />
            <span className="text-[9px] text-[#475569]">{entry.name.replace("_", " ")}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function RiskTab({
  data,
  correlationHistory,
}: {
  data: RiskSummaryResponse | null;
  correlationHistory: CorrelationHistoryData | null;
}) {
  if (!data) {
    return (
      <GlassCard>
        <p className="text-sm text-[#475569] text-center py-8">No risk metrics available yet.</p>
      </GlassCard>
    );
  }

  const sleeves = useMemo(() => Object.keys(data.risk_parity_weights), [data.risk_parity_weights]);
  const comparisonData = useMemo(
    () =>
      sleeves.map((s) => ({
        name: s.replace("_", " "),
        actual: parseFloat(((data.actual_weights[s] || 0) * 100).toFixed(1)),
        riskParity: parseFloat(((data.risk_parity_weights[s] || 0) * 100).toFixed(1)),
      })),
    [sleeves, data.actual_weights, data.risk_parity_weights]
  );

  const corrSleeves = useMemo(() => Object.keys(data.correlation_matrix), [data.correlation_matrix]);

  // Check for high-risk concentration: any sleeve with risk parity weight > 50%
  const dominantSleeve = useMemo(
    () => sleeves.find((s) => (data.risk_parity_weights[s] || 0) > 0.5),
    [sleeves, data.risk_parity_weights]
  );

  // Build donut data
  const actualDonutData = useMemo(
    () =>
      sleeves
        .filter((s) => (data.actual_weights[s] || 0) > 0)
        .map((s) => ({ name: s, value: data.actual_weights[s] || 0 })),
    [sleeves, data.actual_weights]
  );

  const rpDonutData = useMemo(
    () =>
      sleeves
        .filter((s) => (data.risk_parity_weights[s] || 0) > 0)
        .map((s) => ({ name: s, value: data.risk_parity_weights[s] || 0 })),
    [sleeves, data.risk_parity_weights]
  );

  // Risk vs Dollar comparison data
  const riskDollarData = useMemo(
    () =>
      sleeves.map((s) => ({
        name: s.replace("_", " "),
        dollar: parseFloat(((data.actual_weights[s] || 0) * 100).toFixed(1)),
        risk: parseFloat(((data.risk_parity_weights[s] || 0) * 100).toFixed(1)),
      })),
    [sleeves, data.actual_weights, data.risk_parity_weights]
  );

  // Highest-correlation pair from history
  const highestPair = correlationHistory?.highest_pair;
  const highestPairHistory = highestPair
    ? correlationHistory?.pairs.find(
        (p) =>
          (p.sleeves[0] === highestPair.sleeves[0] && p.sleeves[1] === highestPair.sleeves[1]) ||
          (p.sleeves[0] === highestPair.sleeves[1] && p.sleeves[1] === highestPair.sleeves[0])
      )
    : null;

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-3 gap-4">
        <GlassCard>
          <p className="text-xs text-[#475569] uppercase tracking-wider">VaR 95% (1-day)</p>
          <p className="text-2xl font-bold font-mono text-[#ef4444] mt-1">
            {data.var_95 != null ? `-${(data.var_95 * 100).toFixed(2)}%` : "—"}
          </p>
          <p className="text-xs text-[#475569] mt-1">Historical percentile</p>
        </GlassCard>
        <GlassCard>
          <p className="text-xs text-[#475569] uppercase tracking-wider">VaR 99% (1-day)</p>
          <p className="text-2xl font-bold font-mono text-[#ef4444] mt-1">
            {data.var_99 != null ? `-${(data.var_99 * 100).toFixed(2)}%` : "—"}
          </p>
          <p className="text-xs text-[#475569] mt-1">Tail risk (1% chance)</p>
        </GlassCard>
        <GlassCard>
          <p className="text-xs text-[#475569] uppercase tracking-wider">Diversification Ratio</p>
          <p className="text-2xl font-bold font-mono text-[#10b981] mt-1">
            {data.diversification_ratio != null ? data.diversification_ratio.toFixed(2) : "—"}
          </p>
          <p className="text-xs text-[#475569] mt-1">{">"} 1.0 = diversified</p>
        </GlassCard>
      </div>

      {/* Risk Concentration Alert */}
      {dominantSleeve && (
        <div className="px-4 py-3 rounded-xl bg-tertiary/10 border border-tertiary/20 text-sm text-tertiary">
          ⚠️ Risk concentration: <span className="font-semibold">{dominantSleeve.replace("_", " ")}</span> contributes over 50% of total portfolio risk in the risk-parity model. Consider reducing exposure or hedging.
        </div>
      )}

      {/* Dalio All-Weather: two donuts side-by-side */}
      {(actualDonutData.length > 0 || rpDonutData.length > 0) && (
        <GlassCard>
          <h2 className="text-sm font-semibold text-[#f1f5f9] mb-1">
            Dalio All-Weather Comparison
          </h2>
          <p className="text-xs text-[#475569] mb-4">
            Left: your current dollar allocation — Right: risk-parity equivalent (equal risk contribution per sleeve)
          </p>
          <div className="grid grid-cols-2 gap-4">
            <DonutChart data={actualDonutData} title="Current Dollar Weights" />
            <DonutChart data={rpDonutData} title="Risk Parity Weights" />
          </div>
        </GlassCard>
      )}

      {/* Risk vs Dollar grouped bar chart */}
      {riskDollarData.length > 0 && (
        <GlassCard>
          <h2 className="text-sm font-semibold text-[#f1f5f9] mb-4">
            Dollar Allocation vs Risk Contribution
          </h2>
          <p className="text-xs text-[#475569] mb-3">
            Dollar allocation (blue) vs risk parity weight (violet) — large gaps indicate sleeves that dominate risk disproportionately to their dollar size.
          </p>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={riskDollarData} layout="vertical" margin={{ left: 20, right: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" horizontal={false} />
              <XAxis type="number" tickFormatter={(v) => `${v}%`} tick={{ fill: "#475569", fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis type="category" dataKey="name" tick={{ fill: "#94a3b8", fontSize: 11 }} axisLine={false} tickLine={false} width={90} />
              <Tooltip
                contentStyle={{ background: "#0d0d14", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 8 }}
                labelStyle={{ color: "#f1f5f9" }}
                formatter={(val: number) => [`${val}%`]}
              />
              <Legend iconSize={8} wrapperStyle={{ color: "#94a3b8", fontSize: 11 }} />
              <Bar dataKey="dollar" name="Dollar Alloc" fill="#3b82f6" radius={[0, 3, 3, 0]} />
              <Bar dataKey="risk" name="Risk Weight" fill="rgba(239,68,68,0.6)" radius={[0, 3, 3, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </GlassCard>
      )}

      {/* Actual vs risk parity (original chart preserved) */}
      {comparisonData.length > 0 && (
        <GlassCard>
          <h2 className="text-sm font-semibold text-[#f1f5f9] mb-4">
            Actual Weights vs Dalio Risk-Parity Weights
          </h2>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={comparisonData} layout="vertical" margin={{ left: 20, right: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" horizontal={false} />
              <XAxis type="number" tickFormatter={(v) => `${v}%`} tick={{ fill: "#475569", fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis type="category" dataKey="name" tick={{ fill: "#94a3b8", fontSize: 11 }} axisLine={false} tickLine={false} width={90} />
              <Tooltip
                contentStyle={{ background: "#0d0d14", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 8 }}
                labelStyle={{ color: "#f1f5f9" }}
                formatter={(val: number) => [`${val}%`]}
              />
              <Legend iconSize={8} wrapperStyle={{ color: "#94a3b8", fontSize: 11 }} />
              <Bar dataKey="actual" name="Actual" fill="#6366f1" radius={[0, 3, 3, 0]} />
              <Bar dataKey="riskParity" name="Risk Parity" fill="rgba(139,92,246,0.4)" radius={[0, 3, 3, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </GlassCard>
      )}

      {/* Correlation Heatmap */}
      {corrSleeves.length > 0 && (
        <GlassCard>
          <h2 className="text-sm font-semibold text-[#f1f5f9] mb-4">Correlation Matrix (90-day)</h2>
          <CorrelationHeatmap matrix={data.correlation_matrix} sleeves={corrSleeves} />
        </GlassCard>
      )}

      {/* Rolling correlation for highest-corr pair */}
      {highestPair && highestPairHistory && highestPairHistory.history.length > 0 && (
        <GlassCard>
          <div className="flex items-center gap-2 mb-1">
            <h2 className="text-sm font-semibold text-[#f1f5f9]">
              Highest Correlation Pair: {highestPair.sleeves[0].replace("_", " ")} ↔ {highestPair.sleeves[1].replace("_", " ")}
            </h2>
            <span
              className={`text-xs font-mono px-2 py-0.5 rounded-full border ${
                highestPair.current_correlation > 0.85
                  ? "text-tertiary bg-tertiary/10 border-tertiary/20"
                  : "text-[#94a3b8] bg-white/[0.04] border-white/[0.08]"
              }`}
            >
              {highestPair.current_correlation.toFixed(3)}
            </span>
          </div>
          <p className="text-xs text-[#475569] mb-3">Rolling 90-day correlation — higher means less diversification benefit</p>
          <ResponsiveContainer width="100%" height={140}>
            <LineChart data={highestPairHistory.history.slice(-52)} margin={{ left: 10, right: 10, top: 5, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" vertical={false} />
              <XAxis
                dataKey="date"
                tick={{ fill: "#475569", fontSize: 10 }}
                axisLine={false}
                tickLine={false}
                tickFormatter={(v: string) => v.slice(5)}
                interval={Math.floor(highestPairHistory.history.length / 5)}
              />
              <YAxis
                domain={[-1, 1]}
                tick={{ fill: "#475569", fontSize: 10 }}
                axisLine={false}
                tickLine={false}
                tickFormatter={(v: number) => v.toFixed(1)}
              />
              <Tooltip
                contentStyle={{ background: "#0d0d14", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 8 }}
                labelStyle={{ color: "#f1f5f9", fontSize: 11 }}
                formatter={(val: number) => [val.toFixed(3), "Correlation"]}
              />
              <ReferenceLine y={0.85} stroke="rgba(245,158,11,0.5)" strokeDasharray="4 2" label={{ value: "⚠️ 0.85", fill: "#f59e0b", fontSize: 9 }} />
              <ReferenceLine y={0} stroke="rgba(255,255,255,0.15)" />
              <Line
                type="monotone"
                dataKey="correlation"
                stroke="#6366f1"
                strokeWidth={2}
                dot={false}
                name="Correlation"
              />
            </LineChart>
          </ResponsiveContainer>
        </GlassCard>
      )}
    </div>
  );
}

// ── Main Page ──────────────────────────────────────────────────────────────

type Tab = "summary" | "attribution" | "rolling" | "risk";

const BENCH_PERIODS = ["1mo", "3mo", "6mo", "ytd", "1yr", "3yr"] as const;
type BenchPeriod = typeof BENCH_PERIODS[number];

export default function PerformancePage() {
  const [activeTab, setActiveTab] = useState<Tab>("summary");
  const [benchPeriod, setBenchPeriod] = useState<BenchPeriod>("ytd");

  const [summary, setSummary] = useState<PerformanceSummaryResponse | null>(null);
  const [attribution, setAttribution] = useState<AttributionResponse | null>(null);
  const [benchmark, setBenchmark] = useState<BenchmarkComparisonResponse | null>(null);
  const [rolling, setRolling] = useState<RollingReturnsResponse | null>(null);
  const [risk, setRisk] = useState<RiskSummaryResponse | null>(null);
  const [fxAttribution, setFxAttribution] = useState<FxAttributionData | null>(null);
  const [correlationHistory, setCorrelationHistory] = useState<CorrelationHistoryData | null>(null);

  const [loadingSummary, setLoadingSummary] = useState(true);
  const [loadingAttribution, setLoadingAttribution] = useState(false);
  const [loadingRolling, setLoadingRolling] = useState(false);
  const [loadingRisk, setLoadingRisk] = useState(false);

  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoadingSummary(true);
    Promise.all([api.performanceSummary(), api.performanceBenchmark("SPY", benchPeriod)])
      .then(([s, b]) => {
        setSummary(s);
        setBenchmark(b);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoadingSummary(false));
  }, [benchPeriod]);

  useEffect(() => {
    if (activeTab === "attribution" && !attribution) {
      setLoadingAttribution(true);
      Promise.all([
        api.performanceAttribution(),
        api.performanceFxAttribution("ytd"),
      ])
        .then(([attr, fx]) => {
          setAttribution(attr);
          setFxAttribution(fx as unknown as FxAttributionData);
        })
        .catch(() => {
          setAttribution(null);
          setFxAttribution(null);
        })
        .finally(() => setLoadingAttribution(false));
    }
    if (activeTab === "rolling" && !rolling) {
      setLoadingRolling(true);
      api.performanceRolling()
        .then(setRolling)
        .catch(() => setRolling(null))
        .finally(() => setLoadingRolling(false));
    }
    if (activeTab === "risk" && !risk) {
      setLoadingRisk(true);
      Promise.all([
        api.performanceRisk(),
        api.performanceCorrelationHistory(365),
      ])
        .then(([r, corrHist]) => {
          setRisk(r);
          setCorrelationHistory(corrHist as unknown as CorrelationHistoryData);
        })
        .catch(() => {
          setRisk(null);
          setCorrelationHistory(null);
        })
        .finally(() => setLoadingRisk(false));
    }
  }, [activeTab]);

  const tabs: { id: Tab; label: string }[] = [
    { id: "summary", label: "Summary" },
    { id: "attribution", label: "Attribution" },
    { id: "rolling", label: "Rolling" },
    { id: "risk", label: "Risk" },
  ];

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-xl font-semibold text-[#f1f5f9]">Performance Analytics</h1>
        <p className="text-xs text-[#475569] mt-0.5">TWR · Sharpe · Attribution · Risk Parity</p>
      </div>

      {/* Period selector (for benchmark comparison) */}
      <div className="flex items-center gap-2">
        <span className="text-xs text-[#475569]">Benchmark period:</span>
        <div className="flex gap-1 p-1 rounded-lg bg-white/[0.03] border border-white/[0.06]">
          {BENCH_PERIODS.map((p) => (
            <button
              key={p}
              onClick={() => setBenchPeriod(p)}
              className={`px-2.5 py-1 rounded-md text-xs font-medium transition-all ${
                benchPeriod === p
                  ? "bg-indigo-500/20 text-indigo-300 border border-indigo-500/30"
                  : "text-[#475569] hover:text-[#94a3b8]"
              }`}
            >
              {PERIOD_LABELS[p] ?? p}
            </button>
          ))}
        </div>
      </div>

      {/* Tab bar */}
      <div className="flex gap-1 p-1 rounded-xl bg-white/[0.03] border border-white/[0.06] w-fit">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-1.5 rounded-full text-sm font-medium transition-all duration-150 ${
              activeTab === tab.id
                ? "bg-primary/10 text-primary"
                : "text-on-surface-variant hover:text-on-surface"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Content */}
      {error && (
        <div className="rounded-xl border border-error/20 bg-error/10 px-4 py-3 text-error text-sm flex items-center justify-between">
          <span>{error} — Ensure the backend is running and /performance/snapshot has been called.</span>
          <button
            onClick={() => {
              setError(null);
              setLoadingSummary(true);
              Promise.all([api.performanceSummary(), api.performanceBenchmark("SPY", "ytd")])
                .then(([s, b]) => { setSummary(s); setBenchmark(b); })
                .catch((e) => setError(e.message))
                .finally(() => setLoadingSummary(false));
            }}
            className="text-error/70 hover:text-error underline text-xs ml-4 shrink-0"
          >Retry</button>
        </div>
      )}

      {activeTab === "summary" && (
        loadingSummary ? (
          <div className="space-y-4">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="h-24 rounded-2xl bg-white/[0.03] animate-pulse" />
            ))}
          </div>
        ) : summary ? (
          <SummaryTab data={summary} benchmark={benchmark} />
        ) : (
          <GlassCard>
            <p className="text-sm text-[#475569] text-center py-12">
              No performance data yet. Run{" "}
              <code className="font-mono text-[#a78bfa]">POST /performance/snapshot</code>{" "}
              to seed the first snapshot.
            </p>
          </GlassCard>
        )
      )}

      {activeTab === "attribution" && (
        loadingAttribution ? (
          <div className="h-64 rounded-2xl bg-white/[0.03] animate-pulse" />
        ) : (
          <AttributionTab data={attribution} fxAttribution={fxAttribution} />
        )
      )}

      {activeTab === "rolling" && (
        loadingRolling ? (
          <div className="h-64 rounded-2xl bg-white/[0.03] animate-pulse" />
        ) : (
          <RollingTab data={rolling} />
        )
      )}

      {activeTab === "risk" && (
        loadingRisk ? (
          <div className="h-64 rounded-2xl bg-white/[0.03] animate-pulse" />
        ) : (
          <RiskTab data={risk} correlationHistory={correlationHistory} />
        )
      )}
    </div>
  );
}
