"use client";

/**
 * /projections — Simulation + Projections (Phase 7)
 * Tabs: Monte Carlo | Contribution Optimizer | Stress Test | Retirement Readiness
 * CLAUDE.md Section 18 + Design System Section 35
 */

import { useEffect, useMemo, useState } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

// ── Types ─────────────────────────────────────────────────────────────────────

interface MonteCarloResult {
  years: number;
  n_simulations: number;
  percentile_bands: Record<string, number[]>;
  summary: {
    median_final: number;
    p5_final: number;
    p95_final: number;
    swr_survival_probability: number;
    probability_of_target?: number;
  };
  metadata: Record<string, unknown>;
}

interface StressResult {
  scenario_key: string;
  scenario_name: string;
  portfolio_before: number;
  portfolio_after: number;
  total_loss_usd: number;
  total_loss_pct: number;
  sleeve_impacts: Record<string, { loss_usd: number; loss_pct: number | null }>;
  estimated_recovery_months: number;
  risk_parity_comparison: {
    risk_parity_loss_pct: number;
    risk_parity_loss_usd: number;
    your_loss_pct: number;
    difference: number;
  };
}

interface ContributionProposal {
  account_name: string;
  account_type: string;
  tax_treatment: string;
  asset: string;
  sleeve: string;
  amount_usd: number;
  rationale: string;
  tax_efficiency_note: string;
}

interface ContributionResult {
  total_available: number;
  proposals: ContributionProposal[];
  residual: number;
  projected_weights_after: Record<string, number>;
  current_weights_before: Record<string, number>;
}

interface RetirementResult {
  years_to_retirement: number;
  required_nest_egg: number;
  projected_median: number;
  gap: number;
  on_track: boolean;
  probability_of_success: number;
  required_additional_monthly: number;
  swr_monthly_income: number;
  current_monthly_contribution: number;
  current_value: number;
}

// ── Colour helpers ─────────────────────────────────────────────────────────────

const FMT_USD = (v: number) =>
  v >= 1_000_000
    ? `$${(v / 1_000_000).toFixed(2)}M`
    : v >= 1_000
    ? `$${(v / 1_000).toFixed(0)}K`
    : `$${v.toFixed(0)}`;

const FMT_PCT = (v: number) => `${(v * 100).toFixed(1)}%`;

// ── API helpers ────────────────────────────────────────────────────────────────

const API = process.env.NEXT_PUBLIC_API_URL ?? "https://investapi.ovelha.us";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) throw new Error(`API ${res.status}: ${path}`);
  return res.json() as Promise<T>;
}

async function pollMonteCarlo(taskId: string, maxAttempts = 30): Promise<MonteCarloResult> {
  for (let i = 0; i < maxAttempts; i++) {
    await new Promise((r) => setTimeout(r, 2000));
    const data = await apiFetch<{ status: string; result?: MonteCarloResult }>(
      `/simulation/result/${taskId}`
    );
    if (data.status === "complete" && data.result) return data.result;
    if (data.status === "error") throw new Error("Monte Carlo simulation failed");
  }
  throw new Error("Monte Carlo timed out");
}

// ── Shared sub-components ──────────────────────────────────────────────────────

function TabBar({
  tabs,
  active,
  onChange,
}: {
  tabs: { id: string; label: string }[];
  active: string;
  onChange: (id: string) => void;
}) {
  return (
    <div className="flex gap-1 p-1 rounded-xl" style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)" }}>
      {tabs.map((t) => (
        <button
          key={t.id}
          onClick={() => onChange(t.id)}
          className="px-4 py-1.5 rounded-lg text-xs font-medium transition-all duration-150"
          style={
            active === t.id
              ? { background: "rgba(99,102,241,0.2)", color: "#a78bfa", border: "1px solid rgba(99,102,241,0.3)" }
              : { color: "var(--text-muted, #475569)" }
          }
        >
          {t.label}
        </button>
      ))}
    </div>
  );
}

function GlassCard({ children, className = "", style = {} }: { children: React.ReactNode; className?: string; style?: React.CSSProperties }) {
  return (
    <div
      className={`rounded-2xl p-6 ${className}`}
      style={{
        background: "rgba(255,255,255,0.04)",
        backdropFilter: "blur(12px)",
        border: "1px solid rgba(255,255,255,0.08)",
        ...style,
      }}
    >
      {children}
    </div>
  );
}

function StatCard({ label, value, sub, color = "#f1f5f9" }: { label: string; value: string; sub?: string; color?: string }) {
  return (
    <GlassCard>
      <p className="text-xs uppercase tracking-widest" style={{ color: "#475569" }}>{label}</p>
      <p className="text-3xl font-bold mt-1" style={{ fontFamily: "JetBrains Mono, monospace", color }}>{value}</p>
      {sub && <p className="text-xs mt-1" style={{ color: "#94a3b8" }}>{sub}</p>}
    </GlassCard>
  );
}

const CustomTooltip = ({ active, payload, label }: { active?: boolean; payload?: { name: string; value: number }[]; label?: string }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-xl p-3 text-xs" style={{ background: "rgba(13,13,20,0.95)", border: "1px solid rgba(255,255,255,0.1)" }}>
      <p className="font-medium mb-1" style={{ color: "#f1f5f9" }}>Year {label}</p>
      {payload.map((p) => (
        <p key={p.name} style={{ color: "#94a3b8" }}>
          {p.name}: <span style={{ color: "#f1f5f9", fontFamily: "monospace" }}>{FMT_USD(p.value)}</span>
        </p>
      ))}
    </div>
  );
};

// ── Tab 1: Monte Carlo ─────────────────────────────────────────────────────────

function MonteCarloTab() {
  const [contribution, setContribution] = useState(2000);
  const [years, setYears] = useState(20);
  const [target, setTarget] = useState(1000000);
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<MonteCarloResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const run = async () => {
    setRunning(true);
    setError(null);
    setResult(null);
    try {
      const { task_id } = await apiFetch<{ task_id: string; status: string }>(
        "/simulation/monte_carlo",
        {
          method: "POST",
          body: JSON.stringify({ monthly_contribution: contribution, years, target_value: target }),
        }
      );
      const res = await pollMonteCarlo(task_id);
      setResult(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setRunning(false);
    }
  };

  // Build chart data: one point per year with all percentile bands
  const chartData = useMemo(
    () =>
      result
        ? Array.from({ length: result.years + 1 }, (_, i) => ({
            year: i,
            p5: result.percentile_bands["p5"]?.[i] ?? 0,
            p25: result.percentile_bands["p25"]?.[i] ?? 0,
            p50: result.percentile_bands["p50"]?.[i] ?? 0,
            p75: result.percentile_bands["p75"]?.[i] ?? 0,
            p95: result.percentile_bands["p95"]?.[i] ?? 0,
          }))
        : [],
    [result]
  );

  const swrPct = result ? result.summary.swr_survival_probability * 100 : 0;

  return (
    <div className="space-y-6">
      {/* Inputs */}
      <GlassCard>
        <div className="flex flex-wrap gap-6 items-end">
          <div>
            <label className="text-xs uppercase tracking-widest block mb-1" style={{ color: "#475569" }}>Monthly Contribution</label>
            <div className="flex items-center gap-2">
              <span style={{ color: "#94a3b8" }} className="text-sm">$</span>
              <input
                type="number"
                value={contribution}
                onChange={(e) => setContribution(Number(e.target.value))}
                className="w-28 px-3 py-1.5 rounded-lg text-sm font-mono outline-none"
                style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.1)", color: "#f1f5f9" }}
              />
            </div>
          </div>
          <div>
            <label className="text-xs uppercase tracking-widest block mb-1" style={{ color: "#475569" }}>Projection Years</label>
            <div className="flex items-center gap-3">
              <input
                type="range" min={5} max={40} value={years}
                onChange={(e) => setYears(Number(e.target.value))}
                className="w-28"
                style={{ accentColor: "#6366f1" }}
              />
              <span className="text-sm font-mono" style={{ color: "#a78bfa" }}>{years}yr</span>
            </div>
          </div>
          <div>
            <label className="text-xs uppercase tracking-widest block mb-1" style={{ color: "#475569" }}>Target Value</label>
            <div className="flex items-center gap-2">
              <span style={{ color: "#94a3b8" }} className="text-sm">$</span>
              <input
                type="number"
                value={target}
                onChange={(e) => setTarget(Number(e.target.value))}
                className="w-28 px-3 py-1.5 rounded-lg text-sm font-mono outline-none"
                style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.1)", color: "#f1f5f9" }}
              />
            </div>
          </div>
          <button
            onClick={run}
            disabled={running}
            className="px-6 py-2 rounded-xl text-sm font-semibold transition-all"
            style={{
              background: running ? "rgba(99,102,241,0.3)" : "linear-gradient(135deg, #6366f1, #8b5cf6)",
              color: "#fff",
              boxShadow: running ? "none" : "0 0 20px rgba(99,102,241,0.3)",
            }}
          >
            {running ? "Simulating…" : "Run Simulation"}
          </button>
        </div>
      </GlassCard>

      {error && (
        <div className="rounded-xl border border-error/20 bg-error/10 px-4 py-3 text-error text-sm flex items-center justify-between">
          <span>{error}</span>
          <button onClick={run} className="text-error/70 hover:text-error underline text-xs">Retry</button>
        </div>
      )}

      {running && (
        <GlassCard>
          <div className="flex items-center gap-3 justify-center py-8">
            <div className="w-5 h-5 rounded-full border-2 border-t-transparent animate-spin" style={{ borderColor: "#6366f1", borderTopColor: "transparent" }} />
            <p className="text-sm" style={{ color: "#94a3b8" }}>Running 5,000 Monte Carlo simulations…</p>
          </div>
        </GlassCard>
      )}

      {result && (
        <>
          {/* Stats row */}
          <div className="grid grid-cols-3 gap-4">
            <StatCard
              label={`Median at ${years}yr`}
              value={FMT_USD(result.summary.median_final)}
              color="#10b981"
            />
            <StatCard
              label="Reach Target Probability"
              value={result.summary.probability_of_target != null ? `${(result.summary.probability_of_target * 100).toFixed(0)}%` : "—"}
              sub={`Target: ${FMT_USD(target)}`}
              color="#a78bfa"
            />
            <StatCard
              label="4% SWR Survival"
              value={`${swrPct.toFixed(0)}%`}
              sub="30-year decumulation"
              color={swrPct >= 80 ? "#10b981" : swrPct >= 60 ? "#f59e0b" : "#ef4444"}
            />
          </div>

          {/* Fan chart */}
          <GlassCard>
            <p className="text-sm font-semibold mb-4" style={{ color: "#f1f5f9" }}>Portfolio Projection — {result.n_simulations.toLocaleString()} simulations</p>
            <ResponsiveContainer width="100%" height={320}>
              <AreaChart data={chartData} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
                <defs>
                  <linearGradient id="gp95" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#10b981" stopOpacity={0.25} />
                    <stop offset="100%" stopColor="#10b981" stopOpacity={0.02} />
                  </linearGradient>
                  <linearGradient id="gp75" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#10b981" stopOpacity={0.15} />
                    <stop offset="100%" stopColor="#10b981" stopOpacity={0.02} />
                  </linearGradient>
                  <linearGradient id="gp25" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#f59e0b" stopOpacity={0.10} />
                    <stop offset="100%" stopColor="#f59e0b" stopOpacity={0.02} />
                  </linearGradient>
                  <linearGradient id="gp5" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#ef4444" stopOpacity={0.10} />
                    <stop offset="100%" stopColor="#ef4444" stopOpacity={0.02} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                <XAxis dataKey="year" tick={{ fill: "#475569", fontSize: 11 }} tickLine={false} axisLine={false} label={{ value: "Years", position: "insideBottom", offset: -2, fill: "#475569", fontSize: 11 }} />
                <YAxis tickFormatter={(v) => FMT_USD(v)} tick={{ fill: "#475569", fontSize: 11 }} tickLine={false} axisLine={false} width={70} />
                <Tooltip content={<CustomTooltip />} />
                <Area type="monotone" dataKey="p95" name="95th pct" stroke="rgba(16,185,129,0.5)" strokeWidth={1} fill="url(#gp95)" />
                <Area type="monotone" dataKey="p75" name="75th pct" stroke="rgba(16,185,129,0.4)" strokeWidth={1} fill="url(#gp75)" />
                <Area type="monotone" dataKey="p50" name="Median" stroke="#10b981" strokeWidth={2.5} fill="none" />
                <Area type="monotone" dataKey="p25" name="25th pct" stroke="rgba(245,158,11,0.4)" strokeWidth={1} fill="url(#gp25)" />
                <Area type="monotone" dataKey="p5" name="5th pct" stroke="rgba(239,68,68,0.4)" strokeWidth={1} fill="url(#gp5)" />
              </AreaChart>
            </ResponsiveContainer>
            <div className="flex gap-4 mt-3 flex-wrap">
              {[
                { label: "95th %ile", color: "#10b981" },
                { label: "75th %ile", color: "#34d399" },
                { label: "Median", color: "#10b981", bold: true },
                { label: "25th %ile", color: "#f59e0b" },
                { label: "5th %ile", color: "#ef4444" },
              ].map((l) => (
                <div key={l.label} className="flex items-center gap-1.5">
                  <div className="w-3 h-0.5 rounded" style={{ background: l.color, opacity: l.bold ? 1 : 0.6 }} />
                  <span className="text-xs" style={{ color: "#94a3b8" }}>{l.label}</span>
                </div>
              ))}
            </div>
          </GlassCard>
        </>
      )}
    </div>
  );
}

// ── Tab 2: Contribution Optimizer ──────────────────────────────────────────────

function ContributionTab() {
  const [amount, setAmount] = useState(2000);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ContributionResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const run = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiFetch<ContributionResult>("/simulation/contribution_optimizer", {
        method: "POST",
        body: JSON.stringify({ available_amount: amount }),
      });
      setResult(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error");
    } finally {
      setLoading(false);
    }
  };

  const TAX_COLORS: Record<string, string> = {
    tax_deferred: "#6366f1",
    tax_free: "#10b981",
    taxable: "#f59e0b",
    brazil_taxable: "#22c55e",
    bank: "#475569",
  };

  return (
    <div className="space-y-6">
      <GlassCard>
        <div className="flex gap-6 items-end">
          <div>
            <label className="text-xs uppercase tracking-widest block mb-1" style={{ color: "#475569" }}>Available Amount</label>
            <div className="flex items-center gap-2">
              <span style={{ color: "#94a3b8" }} className="text-sm">$</span>
              <input
                type="number"
                value={amount}
                onChange={(e) => setAmount(Number(e.target.value))}
                className="w-32 px-3 py-1.5 rounded-lg text-sm font-mono outline-none"
                style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.1)", color: "#f1f5f9" }}
              />
            </div>
          </div>
          <button
            onClick={run}
            disabled={loading}
            className="px-6 py-2 rounded-xl text-sm font-semibold"
            style={{ background: "linear-gradient(135deg, #6366f1, #8b5cf6)", color: "#fff" }}
          >
            {loading ? "Optimizing…" : "Optimize Allocation"}
          </button>
        </div>
      </GlassCard>

      {error && (
        <div className="rounded-xl border border-error/20 bg-error/10 px-4 py-3 text-error text-sm flex items-center justify-between">
          <span>{error}</span>
          <button onClick={run} className="text-error/70 hover:text-error underline text-xs">Retry</button>
        </div>
      )}

      {result && (
        <>
          <div className="grid grid-cols-3 gap-4">
            <StatCard label="Total Available" value={FMT_USD(result.total_available)} />
            <StatCard label="Allocated" value={FMT_USD(result.total_available - result.residual)} color="#10b981" />
            <StatCard label="Residual" value={FMT_USD(result.residual)} color={result.residual > 0 ? "#f59e0b" : "#10b981"} />
          </div>

          <GlassCard>
            <p className="text-sm font-semibold mb-4" style={{ color: "#f1f5f9" }}>Routing Proposals</p>
            <div className="space-y-3">
              {result.proposals.map((p, i) => (
                <div key={i} className="flex items-center justify-between p-3 rounded-xl" style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)" }}>
                  <div className="flex items-center gap-3">
                    <span
                      className="px-2 py-0.5 rounded-full text-xs font-semibold"
                      style={{
                        background: `${TAX_COLORS[p.tax_treatment] ?? "#475569"}20`,
                        color: TAX_COLORS[p.tax_treatment] ?? "#94a3b8",
                        border: `1px solid ${TAX_COLORS[p.tax_treatment] ?? "#475569"}40`,
                      }}
                    >
                      {p.tax_treatment.replace("_", " ")}
                    </span>
                    <div>
                      <p className="text-sm font-medium" style={{ color: "#f1f5f9" }}>
                        {p.asset} — <span style={{ color: "#94a3b8" }}>{p.account_name}</span>
                      </p>
                      <p className="text-xs mt-0.5" style={{ color: "#475569" }}>{p.rationale}</p>
                    </div>
                  </div>
                  <p className="text-base font-bold font-mono" style={{ color: "#10b981" }}>{FMT_USD(p.amount_usd)}</p>
                </div>
              ))}
            </div>
          </GlassCard>

          <GlassCard>
            <p className="text-sm font-semibold mb-4" style={{ color: "#f1f5f9" }}>Sleeve Weights — Before vs After</p>
            <div className="space-y-2.5">
              {Object.entries(result.current_weights_before).map(([sleeve, before]) => {
                const after = result.projected_weights_after[sleeve] ?? before;
                const diff = after - before;
                return (
                  <div key={sleeve} className="grid grid-cols-4 gap-3 items-center text-xs">
                    <span className="capitalize" style={{ color: "#94a3b8" }}>{sleeve.replace("_", " ")}</span>
                    <div className="col-span-2 h-1.5 rounded-full" style={{ background: "rgba(255,255,255,0.08)" }}>
                      <div
                        className="h-full rounded-full transition-all"
                        style={{ width: `${(after * 100).toFixed(1)}%`, background: "linear-gradient(90deg, #6366f1, #8b5cf6)" }}
                      />
                    </div>
                    <div className="flex gap-2 font-mono">
                      <span style={{ color: "#475569" }}>{FMT_PCT(before)}</span>
                      <span style={{ color: diff > 0 ? "#10b981" : diff < 0 ? "#ef4444" : "#94a3b8" }}>
                        {diff > 0 ? "↑" : diff < 0 ? "↓" : "—"}{FMT_PCT(Math.abs(diff))}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </GlassCard>
        </>
      )}
    </div>
  );
}

// ── Tab 3: Stress Test ─────────────────────────────────────────────────────────

const SCENARIO_META: Record<string, { label: string; icon: string; color: string }> = {
  "2008_gfc":          { label: "2008 GFC",        icon: "🏦", color: "#ef4444" },
  "2020_covid":        { label: "COVID 2020",       icon: "🦠", color: "#f59e0b" },
  "2022_rate_shock":   { label: "Rate Shock 2022",  icon: "📈", color: "#f97316" },
  "stagflation_1970s": { label: "1970s Stagflation",icon: "⛽", color: "#eab308" },
  "brazil_crisis":     { label: "Brazil Crisis",    icon: "🇧🇷", color: "#ef4444" },
};

function StressTestTab() {
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<Record<string, StressResult> | null>(null);
  const [selected, setSelected] = useState<string>("2008_gfc");
  const [error, setError] = useState<string | null>(null);

  const runAll = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiFetch<Record<string, StressResult>>("/simulation/stress_test/all", { method: "POST" });
      setResults(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    runAll();
  }, []);

  const active = results?.[selected];

  const barData = useMemo(
    () =>
      active
        ? Object.entries(active.sleeve_impacts).map(([sleeve, impact]) => ({
            sleeve: sleeve.replace("_equity", "").replace("_", " "),
            loss: (impact.loss_pct ?? 0) * 100,
          }))
        : [],
    [active]
  );

  return (
    <div className="space-y-6">
      {error && (
        <div className="rounded-xl border border-error/20 bg-error/10 px-4 py-3 text-error text-sm flex items-center justify-between">
          <span>{error}</span>
          <button onClick={runAll} className="text-error/70 hover:text-error underline text-xs">Retry</button>
        </div>
      )}

      {loading && (
        <GlassCard>
          <div className="flex items-center gap-3 justify-center py-6">
            <div className="w-4 h-4 rounded-full border-2 animate-spin" style={{ borderColor: "#6366f1", borderTopColor: "transparent" }} />
            <p className="text-sm" style={{ color: "#94a3b8" }}>Running all 5 stress scenarios…</p>
          </div>
        </GlassCard>
      )}

      {results && (
        <>
          {/* Scenario selector */}
          <div className="grid grid-cols-5 gap-3">
            {Object.entries(SCENARIO_META).map(([key, meta]) => {
              const r = results[key];
              const loss = r ? r.total_loss_pct * 100 : 0;
              return (
                <button
                  key={key}
                  onClick={() => setSelected(key)}
                  className="rounded-xl p-3 text-left transition-all"
                  style={{
                    background: selected === key ? `${meta.color}15` : "rgba(255,255,255,0.03)",
                    border: `1px solid ${selected === key ? `${meta.color}40` : "rgba(255,255,255,0.06)"}`,
                    boxShadow: selected === key ? `0 0 20px ${meta.color}20` : "none",
                  }}
                >
                  <span className="text-lg">{meta.icon}</span>
                  <p className="text-xs font-medium mt-1" style={{ color: "#f1f5f9" }}>{meta.label}</p>
                  {r && (
                    <p className="text-sm font-bold font-mono mt-1" style={{ color: meta.color }}>
                      {loss.toFixed(1)}%
                    </p>
                  )}
                </button>
              );
            })}
          </div>

          {active && (
            <>
              <div className="grid grid-cols-4 gap-4">
                <StatCard label="Portfolio Before" value={FMT_USD(active.portfolio_before)} />
                <StatCard label="Portfolio After" value={FMT_USD(active.portfolio_after)} color="#ef4444" />
                <StatCard label="Total Loss" value={FMT_USD(active.total_loss_usd)} sub={`${(active.total_loss_pct * 100).toFixed(1)}%`} color="#ef4444" />
                <StatCard
                  label="Recovery Time"
                  value={`${active.estimated_recovery_months}mo`}
                  sub={`~${(active.estimated_recovery_months / 12).toFixed(1)}yr at 7% recovery`}
                  color="#f59e0b"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <GlassCard>
                  <p className="text-sm font-semibold mb-4" style={{ color: "#f1f5f9" }}>Loss by Sleeve</p>
                  <ResponsiveContainer width="100%" height={200}>
                    <BarChart data={barData} margin={{ top: 0, right: 0, bottom: 0, left: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                      <XAxis dataKey="sleeve" tick={{ fill: "#475569", fontSize: 10 }} axisLine={false} tickLine={false} />
                      <YAxis tick={{ fill: "#475569", fontSize: 10 }} axisLine={false} tickLine={false} tickFormatter={(v) => `${v}%`} />
                      <Tooltip formatter={(v: number) => [`${v.toFixed(1)}%`, "Loss"]} contentStyle={{ background: "rgba(13,13,20,0.95)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8 }} />
                      <Bar dataKey="loss" radius={[4, 4, 0, 0]}>
                        {barData.map((_, idx) => (
                          <Cell key={idx} fill="#ef4444" fillOpacity={0.7} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </GlassCard>

                <GlassCard>
                  <p className="text-sm font-semibold mb-4" style={{ color: "#f1f5f9" }}>Risk Parity Comparison</p>
                  <div className="space-y-4">
                    <div>
                      <p className="text-xs mb-1" style={{ color: "#94a3b8" }}>Your Portfolio</p>
                      <div className="flex items-center gap-3">
                        <div className="flex-1 h-3 rounded-full" style={{ background: "rgba(255,255,255,0.08)" }}>
                          <div className="h-full rounded-full bg-error" style={{ width: `${Math.min(Math.abs(active.risk_parity_comparison.your_loss_pct) * 100, 100)}%` }} />
                        </div>
                        <span className="text-sm font-mono w-14 text-right" style={{ color: "#ef4444" }}>
                          {(active.risk_parity_comparison.your_loss_pct * 100).toFixed(1)}%
                        </span>
                      </div>
                    </div>
                    <div>
                      <p className="text-xs mb-1" style={{ color: "#94a3b8" }}>Dalio All-Weather</p>
                      <div className="flex items-center gap-3">
                        <div className="flex-1 h-3 rounded-full" style={{ background: "rgba(255,255,255,0.08)" }}>
                          <div className="h-full rounded-full" style={{
                            width: `${Math.min(Math.abs(active.risk_parity_comparison.risk_parity_loss_pct) * 100, 100)}%`,
                            background: active.risk_parity_comparison.difference < 0 ? "#10b981" : "#f59e0b",
                          }} />
                        </div>
                        <span className="text-sm font-mono w-14 text-right" style={{ color: active.risk_parity_comparison.difference < 0 ? "#10b981" : "#f59e0b" }}>
                          {(active.risk_parity_comparison.risk_parity_loss_pct * 100).toFixed(1)}%
                        </span>
                      </div>
                    </div>
                    <p className="text-xs mt-2 pt-3" style={{ color: "#475569", borderTop: "1px solid rgba(255,255,255,0.06)" }}>
                      {active.risk_parity_comparison.difference < 0
                        ? `✓ All-Weather loses ${(Math.abs(active.risk_parity_comparison.difference) * 100).toFixed(1)}% less`
                        : `Your allocation loses ${(active.risk_parity_comparison.difference * 100).toFixed(1)}% less than All-Weather`}
                    </p>
                  </div>
                </GlassCard>
              </div>
            </>
          )}
        </>
      )}
    </div>
  );
}

// ── Tab 4: Retirement Readiness ────────────────────────────────────────────────

function RetirementTab() {
  const [retireAge, setRetireAge] = useState(60);
  const [monthlyIncome, setMonthlyIncome] = useState(8000);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<RetirementResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const run = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiFetch<RetirementResult>(
        `/simulation/retirement_readiness?target_retirement_age=${retireAge}&desired_monthly_income=${monthlyIncome}`
      );
      setResult(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    run();
  }, []);

  const trackColor = result
    ? result.on_track
      ? "#10b981"
      : result.probability_of_success >= 0.5
      ? "#f59e0b"
      : "#ef4444"
    : "#475569";

  return (
    <div className="space-y-6">
      <GlassCard>
        <div className="flex flex-wrap gap-6 items-end">
          <div>
            <label className="text-xs uppercase tracking-widest block mb-1" style={{ color: "#475569" }}>Target Retirement Age</label>
            <div className="flex items-center gap-3">
              <input type="range" min={45} max={75} value={retireAge} onChange={(e) => setRetireAge(Number(e.target.value))} style={{ accentColor: "#6366f1" }} className="w-28" />
              <span className="text-sm font-mono" style={{ color: "#a78bfa" }}>{retireAge}</span>
            </div>
          </div>
          <div>
            <label className="text-xs uppercase tracking-widest block mb-1" style={{ color: "#475569" }}>Desired Monthly Income</label>
            <div className="flex items-center gap-2">
              <span style={{ color: "#94a3b8" }} className="text-sm">$</span>
              <input
                type="number"
                value={monthlyIncome}
                onChange={(e) => setMonthlyIncome(Number(e.target.value))}
                className="w-32 px-3 py-1.5 rounded-lg text-sm font-mono outline-none"
                style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.1)", color: "#f1f5f9" }}
              />
            </div>
          </div>
          <button onClick={run} disabled={loading} className="px-6 py-2 rounded-xl text-sm font-semibold" style={{ background: "linear-gradient(135deg, #6366f1, #8b5cf6)", color: "#fff" }}>
            {loading ? "Calculating…" : "Recalculate"}
          </button>
        </div>
      </GlassCard>

      {error && (
        <div className="rounded-xl border border-error/20 bg-error/10 px-4 py-3 text-error text-sm flex items-center justify-between">
          <span>{error}</span>
          <button onClick={run} className="text-error/70 hover:text-error underline text-xs">Retry</button>
        </div>
      )}

      {result && (
        <>
          {/* Status banner */}
          <GlassCard style={{ borderColor: `${trackColor}30`, boxShadow: `0 0 30px ${trackColor}15` }}>
            <div className="flex items-center justify-between">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-lg">{result.on_track ? "✅" : "⚠️"}</span>
                  <p className="text-base font-semibold" style={{ color: trackColor }}>
                    {result.on_track ? "On Track" : "Gap Detected"}
                  </p>
                </div>
                <p className="text-sm" style={{ color: "#94a3b8" }}>
                  {result.years_to_retirement} years to retirement · {FMT_PCT(result.probability_of_success)} success probability
                </p>
              </div>
              <div className="text-right">
                <p className="text-xs" style={{ color: "#475569" }}>4% SWR Nest Egg Required</p>
                <p className="text-2xl font-bold font-mono" style={{ color: "#f1f5f9" }}>{FMT_USD(result.required_nest_egg)}</p>
              </div>
            </div>
          </GlassCard>

          <div className="grid grid-cols-2 gap-4">
            <GlassCard>
              <p className="text-xs uppercase tracking-widest mb-4" style={{ color: "#475569" }}>Trajectory</p>
              <div className="space-y-3 text-sm">
                {[
                  { label: "Required Nest Egg",      value: FMT_USD(result.required_nest_egg),         color: "#94a3b8" },
                  { label: "Projected Median",       value: FMT_USD(result.projected_median),          color: result.projected_median >= result.required_nest_egg ? "#10b981" : "#ef4444" },
                  { label: "Gap",                    value: result.gap > 0 ? `-${FMT_USD(result.gap)}` : "Surplus",  color: result.gap > 0 ? "#ef4444" : "#10b981" },
                  { label: "SWR Monthly Income",     value: FMT_USD(result.swr_monthly_income),         color: "#a78bfa" },
                  { label: "Current Contribution",   value: FMT_USD(result.current_monthly_contribution) + "/mo", color: "#94a3b8" },
                ].map((row) => (
                  <div key={row.label} className="flex justify-between">
                    <span style={{ color: "#475569" }}>{row.label}</span>
                    <span className="font-mono font-medium" style={{ color: row.color }}>{row.value}</span>
                  </div>
                ))}
              </div>
            </GlassCard>

            <GlassCard>
              <p className="text-xs uppercase tracking-widest mb-4" style={{ color: "#475569" }}>Action Required</p>
              {result.gap <= 0 ? (
                <div className="flex flex-col items-center justify-center h-full gap-2 py-4">
                  <span className="text-3xl">🎯</span>
                  <p className="text-sm font-medium" style={{ color: "#10b981" }}>You&apos;re on track!</p>
                  <p className="text-xs text-center" style={{ color: "#475569" }}>
                    Keep contributing {FMT_USD(result.current_monthly_contribution)}/mo to reach your goal.
                  </p>
                </div>
              ) : (
                <div className="space-y-3">
                  <div className="rounded-xl p-3" style={{ background: "rgba(245,158,11,0.08)", border: "1px solid rgba(245,158,11,0.2)" }}>
                    <p className="text-xs" style={{ color: "#f59e0b" }}>Additional monthly contribution needed:</p>
                    <p className="text-2xl font-bold font-mono mt-1" style={{ color: "#f59e0b" }}>
                      +{FMT_USD(result.required_additional_monthly)}/mo
                    </p>
                  </div>
                  <p className="text-xs" style={{ color: "#475569" }}>
                    Increasing your monthly contribution from {FMT_USD(result.current_monthly_contribution)} to{" "}
                    <span style={{ color: "#f1f5f9" }}>
                      {FMT_USD(result.current_monthly_contribution + result.required_additional_monthly)}
                    </span>{" "}
                    closes the gap to your {FMT_PCT(1 - 0.04)}-confidence target.
                  </p>
                  <p className="text-xs" style={{ color: "#475569" }}>
                    Based on Trinity Study 4% Safe Withdrawal Rate — 30-year decumulation survival.
                  </p>
                </div>
              )}
            </GlassCard>
          </div>
        </>
      )}
    </div>
  );
}

// ── Main Page ──────────────────────────────────────────────────────────────────

const TABS = [
  { id: "monte_carlo",    label: "Monte Carlo" },
  { id: "contribution",  label: "Contribution Optimizer" },
  { id: "stress",        label: "Stress Test" },
  { id: "retirement",    label: "Retirement Readiness" },
];

export default function ProjectionsPage() {
  const [tab, setTab] = useState("monte_carlo");

  return (
    <div className="p-6 space-y-6 min-h-screen" style={{ background: "radial-gradient(ellipse 80% 50% at 50% -20%, rgba(99,102,241,0.10) 0%, transparent 60%), #050508" }}>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold" style={{ color: "#f1f5f9" }}>Projections</h1>
          <p className="text-xs mt-0.5" style={{ color: "#475569" }}>Monte Carlo · Stress Tests · Retirement</p>
        </div>
        <TabBar tabs={TABS} active={tab} onChange={setTab} />
      </div>

      {tab === "monte_carlo"   && <MonteCarloTab />}
      {tab === "contribution"  && <ContributionTab />}
      {tab === "stress"        && <StressTestTab />}
      {tab === "retirement"    && <RetirementTab />}
    </div>
  );
}
