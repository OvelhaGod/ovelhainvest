"use client";

/**
 * /performance — Full 4-tab performance analytics page.
 * Tabs: Summary | Attribution | Rolling | Risk
 * CLAUDE.md Section 17 + Stitch glassmorphism design system.
 */

import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "@/lib/api";
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
  Excellent: "text-[#10b981] bg-[rgba(16,185,129,0.12)] border-[rgba(16,185,129,0.25)]",
  Good: "text-[#34d399] bg-[rgba(52,211,153,0.12)] border-[rgba(52,211,153,0.25)]",
  Fair: "text-[#f59e0b] bg-[rgba(245,158,11,0.12)] border-[rgba(245,158,11,0.25)]",
  Poor: "text-[#ef4444] bg-[rgba(239,68,68,0.12)] border-[rgba(239,68,68,0.25)]",
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
    <div className={`rounded-2xl border border-white/[0.08] bg-white/[0.03] backdrop-blur-sm p-5 ${className}`}>
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

function AttributionTab({ data }: { data: AttributionResponse | null }) {
  if (!data || data.per_sleeve.length === 0) {
    return (
      <GlassCard>
        <p className="text-sm text-[#475569] text-center py-8">
          No attribution data yet — run the daily snapshot to populate.
        </p>
      </GlassCard>
    );
  }

  const chartData = data.per_sleeve.map((s) => ({
    name: s.sleeve.replace("_", " "),
    allocation: parseFloat((s.allocation_effect * 100).toFixed(2)),
    selection: parseFloat((s.selection_effect * 100).toFixed(2)),
    interaction: parseFloat((s.interaction_effect * 100).toFixed(2)),
  }));

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
  const displayData = data.data_points.slice(-60);

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

function RiskTab({ data }: { data: RiskSummaryResponse | null }) {
  if (!data) {
    return (
      <GlassCard>
        <p className="text-sm text-[#475569] text-center py-8">No risk metrics available yet.</p>
      </GlassCard>
    );
  }

  const sleeves = Object.keys(data.risk_parity_weights);
  const comparisonData = sleeves.map((s) => ({
    name: s.replace("_", " "),
    actual: parseFloat(((data.actual_weights[s] || 0) * 100).toFixed(1)),
    riskParity: parseFloat(((data.risk_parity_weights[s] || 0) * 100).toFixed(1)),
  }));

  const corrSleeves = Object.keys(data.correlation_matrix);

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

      {/* Risk parity vs actual */}
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

      {/* Correlation matrix */}
      {corrSleeves.length > 0 && (
        <GlassCard>
          <h2 className="text-sm font-semibold text-[#f1f5f9] mb-4">Correlation Matrix (90-day)</h2>
          <div className="overflow-x-auto">
            <table className="text-xs w-full">
              <thead>
                <tr>
                  <th className="text-left py-1 px-2 text-[#475569] w-24" />
                  {corrSleeves.map((s) => (
                    <th key={s} className="py-1 px-2 text-[#475569] text-center font-normal">
                      {s.slice(0, 4)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {corrSleeves.map((row) => (
                  <tr key={row}>
                    <td className="py-1 px-2 text-[#94a3b8] font-medium">{row.replace("_", " ")}</td>
                    {corrSleeves.map((col) => {
                      const val = data.correlation_matrix[row]?.[col] ?? 0;
                      const intensity = Math.abs(val);
                      const isDiag = row === col;
                      const bg = isDiag
                        ? "rgba(99,102,241,0.2)"
                        : val > 0
                        ? `rgba(16,185,129,${intensity * 0.4})`
                        : `rgba(239,68,68,${intensity * 0.4})`;
                      return (
                        <td
                          key={col}
                          className="py-1 px-2 text-center font-mono rounded"
                          style={{ backgroundColor: bg, color: isDiag ? "#a78bfa" : "#f1f5f9" }}
                        >
                          {val.toFixed(2)}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </GlassCard>
      )}
    </div>
  );
}

// ── Main Page ──────────────────────────────────────────────────────────────

type Tab = "summary" | "attribution" | "rolling" | "risk";

export default function PerformancePage() {
  const [activeTab, setActiveTab] = useState<Tab>("summary");

  const [summary, setSummary] = useState<PerformanceSummaryResponse | null>(null);
  const [attribution, setAttribution] = useState<AttributionResponse | null>(null);
  const [benchmark, setBenchmark] = useState<BenchmarkComparisonResponse | null>(null);
  const [rolling, setRolling] = useState<RollingReturnsResponse | null>(null);
  const [risk, setRisk] = useState<RiskSummaryResponse | null>(null);

  const [loadingSummary, setLoadingSummary] = useState(true);
  const [loadingAttribution, setLoadingAttribution] = useState(false);
  const [loadingRolling, setLoadingRolling] = useState(false);
  const [loadingRisk, setLoadingRisk] = useState(false);

  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoadingSummary(true);
    Promise.all([api.performanceSummary(), api.performanceBenchmark("SPY", "ytd")])
      .then(([s, b]) => {
        setSummary(s);
        setBenchmark(b);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoadingSummary(false));
  }, []);

  useEffect(() => {
    if (activeTab === "attribution" && !attribution) {
      setLoadingAttribution(true);
      api.performanceAttribution()
        .then(setAttribution)
        .catch(() => setAttribution(null))
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
      api.performanceRisk()
        .then(setRisk)
        .catch(() => setRisk(null))
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

      {/* Tab bar */}
      <div className="flex gap-1 p-1 rounded-xl bg-white/[0.03] border border-white/[0.06] w-fit">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-all duration-150 ${
              activeTab === tab.id
                ? "bg-[rgba(99,102,241,0.15)] text-[#a78bfa] border border-[rgba(99,102,241,0.3)] shadow-[0_0_12px_rgba(99,102,241,0.15)]"
                : "text-[#475569] hover:text-[#94a3b8]"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Content */}
      {error && (
        <div className="rounded-xl border border-[rgba(239,68,68,0.2)] bg-[rgba(239,68,68,0.06)] p-4 text-sm text-[#ef4444]">
          {error} — Ensure the backend is running and /performance/snapshot has been called.
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
          <AttributionTab data={attribution} />
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
          <RiskTab data={risk} />
        )
      )}
    </div>
  );
}
