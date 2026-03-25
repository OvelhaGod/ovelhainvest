"use client";

/**
 * /dashboard — Phase 2: live data from GET /daily_status, glassmorphism design.
 * Auto-refreshes every 60 seconds.
 */

import { useEffect, useState } from "react";
import useSWR from "swr";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, AreaChart, Area, XAxis, YAxis } from "recharts";
import { fetcher, CACHE_TTL } from "@/lib/swr-config";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "https://investapi.ovelha.us";

async function postFetcher(path: string) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  });
  if (!res.ok) throw new Error(`${res.status}`);
  return res.json();
}
import { OIErrorState } from "@/components/ui/oi";
import type { AdminStatus, AlertHistoryItem, DailyStatusResponse, SleeveWeight, ValuationSummaryResponse, VaultBalance } from "@/lib/types";

// ── Design tokens (DESIGN.md) ─────────────────────────────────────────────────
const SLEEVE_COLORS: Record<string, string> = {
  us_equity:     "#10b981", // emerald
  intl_equity:   "#06b6d4", // cyan
  bonds:         "#3b82f6", // blue
  brazil_equity: "#22c55e", // green
  crypto:        "#8b5cf6", // violet
  cash:          "#64748b", // slate
};

const SLEEVE_LABELS: Record<string, string> = {
  us_equity:     "US Equity",
  intl_equity:   "Intl Equity",
  bonds:         "Bonds",
  brazil_equity: "Brazil Eq.",
  crypto:        "Crypto",
  cash:          "Cash",
};

const REGIME_CONFIG = {
  normal:      { label: "NORMAL REGIME",      color: "#10b981", bg: "rgba(16,185,129,0.08)", border: "rgba(16,185,129,0.25)" },
  high_vol:    { label: "HIGH VOLATILITY",    color: "#f59e0b", bg: "rgba(245,158,11,0.08)", border: "rgba(245,158,11,0.25)" },
  opportunity: { label: "OPPORTUNITY MODE",   color: "#8b5cf6", bg: "rgba(139,92,246,0.08)", border: "rgba(139,92,246,0.25)" },
  paused:      { label: "AUTOMATION PAUSED",  color: "#ef4444", bg: "rgba(239,68,68,0.08)", border: "rgba(239,68,68,0.25)" },
};

const ALERT_TYPE_CONFIG: Record<string, { icon: string; color: string }> = {
  drawdown:     { icon: "📉", color: "#ef4444" },
  drift:        { icon: "⚖️", color: "#f59e0b" },
  opportunity:  { icon: "🚨", color: "#8b5cf6" },
  sell_target:  { icon: "🎯", color: "#10b981" },
  earnings:     { icon: "📅", color: "#06b6d4" },
  brazil_darf:  { icon: "🇧🇷", color: "#22c55e" },
  fx_move:      { icon: "💱", color: "#f59e0b" },
  correlation:  { icon: "🔗", color: "#f43f5e" },
  deposit:      { icon: "💰", color: "#10b981" },
};

// Factor weights per Dalio economic season (from CLAUDE.md Section 26)
const FACTOR_WEIGHTS_BY_SEASON: Record<string, { value: number; momentum: number; quality: number }> = {
  rising_growth_low_inflation:       { value: 0.25, momentum: 0.45, quality: 0.30 },
  falling_growth_low_inflation:      { value: 0.40, momentum: 0.15, quality: 0.45 },
  rising_inflation:                  { value: 0.50, momentum: 0.20, quality: 0.30 },
  falling_inflation_growth_recovery: { value: 0.35, momentum: 0.35, quality: 0.30 },
  normal:                            { value: 0.40, momentum: 0.30, quality: 0.30 },
};

const VAULT_CONFIG = {
  future_investments: { label: "Future Investments", color: "#10b981", icon: "💰" },
  opportunity:        { label: "Opportunity",         color: "#f59e0b", icon: "🎯" },
  emergency:          { label: "Emergency",           color: "#64748b", icon: "🔒" },
};

// ── Glass card base style ─────────────────────────────────────────────────────
const glass = "glass-card";
const glassInner = `${glass} p-5`;

// ── Formatters ────────────────────────────────────────────────────────────────
function fmtUSD(n: number) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(n);
}
function fmtBRL(n: number) {
  return "R$ " + new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 0 }).format(n);
}
function fmtPct(n: number, signed = true) {
  const s = (n * 100).toFixed(1) + "%";
  return signed && n > 0 ? "+" + s : s;
}

// ── Skeleton ──────────────────────────────────────────────────────────────────
function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse rounded bg-white/[0.06] ${className}`} />;
}

// ── Background sparkline (pure SVG, no Recharts, ~0 overhead) ─────────────────
function SparklineBg({ data, color }: { data: number[]; color: string }) {
  if (!data || data.length < 2) return null;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const W = 100, H = 40;
  const points = data
    .map((v, i) => `${(i / (data.length - 1)) * W},${H - ((v - min) / range) * H}`)
    .join(" ");
  return (
    <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none"
      className="absolute inset-0 w-full h-full opacity-[0.10] pointer-events-none">
      <polyline points={points} fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

// ── Custom donut tooltip ──────────────────────────────────────────────────────
function DonutTooltip({ active, payload }: { active?: boolean; payload?: { name: string; value: number }[] }) {
  if (!active || !payload?.length) return null;
  return (
    <div className={`${glass} p-3 text-xs`}>
      <div className="font-medium text-on-surface/90">{payload[0].name}</div>
      <div className="text-primary font-mono">{fmtPct(payload[0].value, false)}</div>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────
export default function DashboardPage() {
  // SWR for /daily_status — use global fetcher so NEXT_PUBLIC_API_URL is always respected
  const {
    data: status,
    error: statusError,
    isLoading,
    mutate: refetchStatus,
  } = useSWR<DailyStatusResponse>(
    "/daily_status",
    fetcher,
    { refreshInterval: 60_000 }
  );

  const loading = isLoading;
  const error = statusError ? (statusError instanceof Error ? statusError.message : "Failed to load data") : null;
  const [lastRefresh, setLastRefresh]     = useState<Date>(new Date());

  // Track last-refresh time whenever new SWR data arrives
  useEffect(() => {
    if (status) setLastRefresh(new Date());
  }, [status]);

  // Secondary data via SWR — all gracefully degrade on error
  const { data: valSummary }       = useSWR<ValuationSummaryResponse>("/valuation_summary", fetcher, { refreshInterval: CACHE_TTL.SLOW });
  const { data: alertHistoryRaw }  = useSWR<AlertHistoryItem[]>("/alerts/history?limit=10", fetcher, { refreshInterval: CACHE_TTL.FAST });
  const { data: sparklineRaw }     = useSWR<{ values: number[]; dates: string[] }>("/performance/sparkline?days=30", fetcher, { refreshInterval: CACHE_TTL.SLOW });
  const { data: adminStatus }      = useSWR<AdminStatus>("/admin/status", fetcher, { refreshInterval: CACHE_TTL.FAST });
  const { data: journalStatsRaw }  = useSWR<Record<string, unknown>>("/journal/stats", fetcher, { refreshInterval: CACHE_TTL.SLOW });
  const { data: taxEstimateRaw }   = useSWR<{
    unrealized: { total_unrealized_gain: number; open_positions: number };
    worst_case: { if_close_everything_today: number };
    harvest_savings: { potential_savings_usd: number; top_candidates: unknown[] };
  }>("/tax/estimate", fetcher, { refreshInterval: CACHE_TTL.SLOW });
  const { data: taxDarfRaw }       = useSWR<{
    darf_status: { exemption_pct_used: number; is_triggered: boolean; darf_due: number | null };
  }>("/tax/brazil_darf", fetcher, { refreshInterval: CACHE_TTL.SLOW });
  const { data: mcPreview }        = useSWR<{
    median_10yr: number; median_20yr: number; swr_probability: number;
  }>("/simulation/dashboard_preview", postFetcher, { refreshInterval: CACHE_TTL.SLOW });

  // Derived values
  const alertHistory  = alertHistoryRaw ?? [];
  const sparklineData = sparklineRaw?.values ?? [];
  const journalAccuracy = journalStatsRaw ? {
    followed_count: (journalStatsRaw.followed_count as number) ?? 0,
    overrode_count: (journalStatsRaw.overrode_count as number) ?? 0,
    avg_followed_30d: (journalStatsRaw.avg_outcome_followed_30d as number | null) ?? null,
    avg_overrode_30d: (journalStatsRaw.avg_outcome_overrode_30d as number | null) ?? null,
    system_outperformance_30d: (journalStatsRaw.system_outperformance_30d as number | null) ?? null,
  } : null;
  const taxSnapshot = (taxEstimateRaw || taxDarfRaw) ? {
    unrealized_gain: taxEstimateRaw?.unrealized?.total_unrealized_gain ?? 0,
    worst_case_tax: taxEstimateRaw?.worst_case?.if_close_everything_today ?? 0,
    harvest_savings: taxEstimateRaw?.harvest_savings?.potential_savings_usd ?? 0,
    harvest_count: (taxEstimateRaw?.harvest_savings?.top_candidates?.length ?? 0) as number,
    darf_pct: taxDarfRaw?.darf_status?.exemption_pct_used ?? 0,
    darf_triggered: taxDarfRaw?.darf_status?.is_triggered ?? false,
  } : null;

  const regime = status ? (REGIME_CONFIG[status.regime_state] ?? REGIME_CONFIG.normal) : REGIME_CONFIG.normal;

  const donutData = (status?.sleeve_weights ?? []).map((sw) => ({
    name: SLEEVE_LABELS[sw.sleeve] ?? sw.sleeve,
    value: sw.current_weight,
    sleeve: sw.sleeve,
    color: SLEEVE_COLORS[sw.sleeve] ?? "#64748b",
  }));

  const donutTargetData = (status?.sleeve_weights ?? []).map((sw) => ({
    name: SLEEVE_LABELS[sw.sleeve] ?? sw.sleeve,
    value: sw.target_weight,
    sleeve: sw.sleeve,
    color: SLEEVE_COLORS[sw.sleeve] ?? "#64748b",
  }));

  const isPaused = adminStatus?.automation_paused ?? (status?.regime_state === "paused");

  return (
    <div className="min-h-screen p-5 space-y-4" style={{ background: "#050508" }}>

      {/* ── Automation Paused Banner ── */}
      {isPaused && (
        <div
          className="rounded-xl border px-4 py-3 flex items-center justify-between"
          style={{ background: "rgba(239,68,68,0.08)", borderColor: "rgba(239,68,68,0.3)" }}
        >
          <div className="flex items-center gap-3">
            <span className="text-error text-base">⛔</span>
            <div>
              <p className="text-sm font-semibold text-error">Automation Paused</p>
              <p className="text-xs text-error/60">
                {adminStatus?.pause_reason === "drawdown"
                  ? "Drawdown gate triggered (≥40%). Manual override required."
                  : adminStatus?.pause_reason
                    ? `Reason: ${adminStatus.pause_reason}`
                    : "Automation is paused. Use /admin/resume to re-enable."}
              </p>
            </div>
          </div>
          <a
            href="/config"
            className="text-xs text-error/70 hover:text-error border border-error/30 rounded px-2 py-1 transition-colors"
          >
            View Config →
          </a>
        </div>
      )}

      {/* ── Header ── */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-white/95 tracking-tight">Dashboard</h1>
          <p className="text-xs text-white/40 mt-0.5">
            {new Date().toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric" })}
            {" · "}
            {loading ? "Loading..." : error ? "⚠ Error" : `Updated ${lastRefresh.toLocaleTimeString()}`}
          </p>
        </div>
        {/* Regime badge — shows regime + Dalio season */}
        <div className="flex flex-col items-end gap-1">
          <div
            className="flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium border"
            style={{ color: regime.color, background: regime.bg, borderColor: regime.border }}
          >
            <span className="w-1.5 h-1.5 rounded-full animate-pulse" style={{ background: regime.color }} />
            {regime.label}
          </div>
          {status?.economic_season && status.economic_season !== "normal" && (
            <p className="text-[10px] text-white/30 font-mono pr-1">
              {seasonIcon(status.economic_season)} {seasonLabel(status.economic_season)}
            </p>
          )}
        </div>
      </div>

      {/* ── Top metrics row ── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        {/* Net Worth */}
        <div
          className={`${glassInner} relative overflow-hidden net-worth-card`}
          style={{ borderColor: "rgba(16,185,129,0.22)" }}
        >
          <SparklineBg
            data={sparklineData}
            color={status?.today_pnl_usd != null && status.today_pnl_usd < 0 ? "#ef4444" : "#10b981"}
          />
          <p className="text-xs text-white/40 uppercase tracking-widest mb-2">Net Worth</p>
          {loading ? (
            <Skeleton className="h-9 w-36 mb-2" />
          ) : (
            <p className="text-3xl font-bold text-white font-mono tracking-tight">
              {fmtUSD(status?.total_value_usd ?? 0)}
            </p>
          )}
          {loading ? (
            <Skeleton className="h-4 w-24 mt-1" />
          ) : (
            <>
              {status?.today_pnl_usd != null ? (
                <p className={`text-xs mt-1 font-mono ${status.today_pnl_usd >= 0 ? "text-primary" : "text-error"}`}>
                  {status.today_pnl_usd >= 0 ? "↑ " : "↓ "}
                  {fmtUSD(Math.abs(status.today_pnl_usd))} ({fmtPct(status.today_pnl_pct ?? 0)}) today
                </p>
              ) : (
                <p className="text-xs mt-1 text-white/30 font-mono">P&L: run allocation to compute</p>
              )}
              <p className="text-xs mt-0.5 text-white/30 font-mono">{fmtBRL(status?.total_value_brl ?? 0)}</p>
            </>
          )}
        </div>

        {/* YTD Return */}
        <a href="/performance" className={`${glassInner} block hover:border-white/[0.14] transition-colors`}>
          <p className="text-xs text-white/40 uppercase tracking-widest mb-2">YTD Return (TWR)</p>
          {loading ? (
            <Skeleton className="h-9 w-24 mb-2" />
          ) : status?.ytd_return_twr != null ? (
            <p className={`text-3xl font-bold font-mono ${status.ytd_return_twr >= 0 ? "text-primary" : "text-error"}`}>
              {fmtPct(status.ytd_return_twr)}
            </p>
          ) : (
            <p className="text-3xl font-bold text-white/20 font-mono">—</p>
          )}
          <p className="text-xs text-white/30 mt-1">View full analysis →</p>
        </a>

        {/* Max Drawdown */}
        <a href="/performance" className={`${glassInner} block hover:border-white/[0.14] transition-colors`}>
          <p className="text-xs text-white/40 uppercase tracking-widest mb-2">Max Drawdown</p>
          {loading ? (
            <Skeleton className="h-9 w-24 mb-2" />
          ) : status?.max_drawdown_pct != null ? (
            <p className={`text-3xl font-bold font-mono ${Math.abs(status.max_drawdown_pct) > 0.25 ? "text-error" : "text-tertiary"}`}>
              {fmtPct(status.max_drawdown_pct)}
            </p>
          ) : (
            <div className="flex items-center gap-2 mt-1">
              <span className="text-[#10b981] text-base">📈</span>
              <p className="text-sm text-[#10b981]/80 font-mono">At all-time high</p>
            </div>
          )}
          <p className="text-xs text-white/30 mt-1">View full analysis →</p>
        </a>

        {/* Sharpe Ratio (trailing 12mo) */}
        <div className={glassInner}>
          <p className="text-xs text-white/40 uppercase tracking-widest mb-2">Sharpe (12mo)</p>
          {loading ? (
            <Skeleton className="h-9 w-24 mb-2" />
          ) : status?.sharpe_trailing_12mo != null ? (
            <>
              <p className={`text-3xl font-bold font-mono ${
                status.sharpe_trailing_12mo >= 1.0 ? "text-primary"
                  : status.sharpe_trailing_12mo >= 0.5 ? "text-tertiary"
                  : "text-error"
              }`}>
                {status.sharpe_trailing_12mo.toFixed(2)}
              </p>
              <p className="text-xs mt-1 text-white/30">
                {status.sharpe_trailing_12mo >= 1.0 ? "Excellent" : status.sharpe_trailing_12mo >= 0.5 ? "Good" : "Poor"}
                {status.ytd_vs_benchmark != null && (
                  <span className={`ml-2 font-mono ${status.ytd_vs_benchmark >= 0 ? "text-primary" : "text-error"}`}>
                    {status.ytd_vs_benchmark >= 0 ? "+" : ""}{(status.ytd_vs_benchmark * 100).toFixed(1)}% vs bench
                  </span>
                )}
              </p>
            </>
          ) : (
            <>
              <div className="flex items-center gap-2 mt-1">
                <span className="text-white/30 text-lg">🕐</span>
                <p className="text-sm text-white/40 font-mono">Building history...</p>
              </div>
              <p className="text-xs text-white/25 mt-1">
                {(status?.pending_approvals ?? 0) > 0
                  ? <a href="/signals" className="text-tertiary/70 hover:text-tertiary transition-colors">{status?.pending_approvals} approval{status?.pending_approvals !== 1 ? "s" : ""} pending →</a>
                  : "Available after 20+ daily snapshots"}
              </p>
            </>
          )}
        </div>
      </div>

      {/* ── Middle row: Donut + Vaults ── */}
      <div className="grid grid-cols-1 xl:grid-cols-5 gap-4">
        {/* Allocation donut */}
        <div className={`${glassInner} lg:col-span-3`}>
          <p className="text-xs text-white/40 uppercase tracking-widest mb-4">Asset Allocation</p>
          {loading ? (
            <div className="flex gap-6">
              <Skeleton className="h-48 w-48 rounded-full" />
              <div className="flex-1 space-y-3 pt-4">
                {Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-6" />)}
              </div>
            </div>
          ) : (
            <div className="flex flex-col sm:flex-row gap-4 items-start min-h-0">
              <div className="w-44 h-44 shrink-0 min-w-[160px]">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    {/* Inner ghost ring = target weights */}
                    <Pie
                      data={donutTargetData}
                      cx="50%"
                      cy="50%"
                      innerRadius={42}
                      outerRadius={52}
                      paddingAngle={2}
                      dataKey="value"
                      strokeWidth={0}
                    >
                      {donutTargetData.map((entry) => (
                        <Cell key={entry.sleeve} fill={entry.color} opacity={0.25} />
                      ))}
                    </Pie>
                    {/* Outer ring = actual weights */}
                    <Pie
                      data={donutData}
                      cx="50%"
                      cy="50%"
                      innerRadius={58}
                      outerRadius={88}
                      paddingAngle={2}
                      dataKey="value"
                      strokeWidth={0}
                    >
                      {donutData.map((entry) => (
                        <Cell key={entry.sleeve} fill={entry.color} opacity={0.85} />
                      ))}
                    </Pie>
                    <Tooltip content={<DonutTooltip />} />
                  </PieChart>
                </ResponsiveContainer>
              </div>

              {/* Sleeve bars */}
              <div className="flex-1 min-h-0 space-y-2 w-full">
                {status?.sleeve_weights?.map((sw) => (
                  <SleeveBar key={sw.sleeve} sw={sw} />
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Vault cards */}
        <div className="lg:col-span-2 flex flex-col gap-3">
          {loading
            ? Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-24 rounded-2xl" />)
            : (status?.vault_balances ?? []).map((v) => <VaultCard key={v.vault_type} vault={v} />)}
        </div>
      </div>

      {/* ── Bottom row: Regime + FX ── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Economic Season + Factor Weights */}
        <div className={glassInner}>
          <p className="text-xs text-white/40 uppercase tracking-widest mb-3">Economic Season</p>
          {loading ? (
            <Skeleton className="h-8 w-48" />
          ) : (
            <>
              <div className="flex items-center gap-3 mb-3">
                <span className="text-lg">{seasonIcon(status?.economic_season ?? "normal")}</span>
                <div>
                  <p className="text-sm font-medium text-white/90">{seasonLabel(status?.economic_season ?? "normal")}</p>
                  <p className="text-xs text-white/30 mt-0.5">Dalio 4-season classifier</p>
                </div>
              </div>
              {/* Factor tilt weights for this season */}
              {(() => {
                const fw = FACTOR_WEIGHTS_BY_SEASON[status?.economic_season ?? "normal"] ?? FACTOR_WEIGHTS_BY_SEASON.normal;
                return (
                  <div className="space-y-1">
                    {[
                      { label: "Value",    value: fw.value,    color: "#3b82f6" },
                      { label: "Momentum", value: fw.momentum, color: "#8b5cf6" },
                      { label: "Quality",  value: fw.quality,  color: "#10b981" },
                    ].map(({ label, value, color }) => (
                      <div key={label} className="flex items-center gap-2 text-xs">
                        <span className="w-14 text-white/40">{label}</span>
                        <div className="flex-1 h-1 rounded-full bg-white/[0.06]">
                          <div className="h-full rounded-full" style={{ width: `${value * 100}%`, background: color, opacity: 0.7 }} />
                        </div>
                        <span className="w-8 text-right font-mono text-white/50">{(value * 100).toFixed(0)}%</span>
                      </div>
                    ))}
                  </div>
                );
              })()}
            </>
          )}
        </div>

        {/* FX Rate */}
        <div className={glassInner}>
          <p className="text-xs text-white/40 uppercase tracking-widest mb-3">USD/BRL Rate</p>
          {loading ? (
            <Skeleton className="h-8 w-32" />
          ) : (
            <div className="flex items-center gap-3">
              <span className="text-lg">🇧🇷</span>
              <div>
                <p className="text-2xl font-bold text-white/90 font-mono">
                  {status?.usd_brl_rate?.toFixed(4) ?? "—"}
                </p>
                <p className="text-xs text-white/30 mt-0.5">BRL per 1 USD · live via yfinance</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ── Valuation insights row ── */}
      {valSummary && (valSummary.top_opportunities.length > 0 || valSummary.top_by_composite.length > 0) && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* Top Opportunities */}
          <div className={glassInner} style={{ borderColor: "rgba(16,185,129,0.15)" }}>
            <div className="flex items-center justify-between mb-3">
              <p className="text-xs text-white/40 uppercase tracking-widest">Top Opportunities</p>
              {valSummary.opportunity_count > 0 && (
                <span className="text-[10px] px-1.5 py-0.5 rounded-full border border-primary/30 text-primary bg-primary/8">
                  {valSummary.opportunity_count} active
                </span>
              )}
            </div>
            <div className="space-y-2">
              {(valSummary.top_opportunities.length > 0
                ? valSummary.top_opportunities
                : valSummary.top_by_composite
              ).slice(0, 4).map((asset, i) => {
                const mos = asset.margin_of_safety_pct;
                const mosColor = mos != null && mos >= 0.20 ? "#10b981" : mos != null && mos >= 0.10 ? "#f59e0b" : "#94a3b8";
                return (
                  <a key={i} href="/assets" className="flex items-center justify-between py-1.5 border-b border-white/[0.04] hover:bg-white/[0.02] transition-colors rounded px-1">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono font-semibold text-white/90">{asset.symbol}</span>
                      {asset.tier && (
                        <span className="text-[9px] px-1 py-0.5 rounded bg-primary/10 text-primary border border-primary/20">
                          {asset.tier?.replace("_", " ")}
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-3 text-xs font-mono">
                      {mos != null && (
                        <span style={{ color: mosColor }}>
                          {mos >= 0 ? "+" : ""}{(mos * 100).toFixed(0)}% MoS
                        </span>
                      )}
                      <span className="text-white/30">
                        {asset.composite_score?.toFixed(2) ?? "—"}
                      </span>
                    </div>
                  </a>
                );
              })}
            </div>
            <a href="/assets" className="text-[10px] text-white/30 hover:text-white/50 mt-2 block transition-colors">
              View all assets →
            </a>
          </div>

          {/* Valuation stats + overvalued */}
          <div className={glassInner}>
            <div className="flex items-center justify-between mb-3">
              <p className="text-xs text-white/40 uppercase tracking-widest">Valuation Universe</p>
              {valSummary.as_of_date && (
                <span className="text-[10px] text-white/25 font-mono">
                  {new Date(valSummary.as_of_date).toLocaleDateString()}
                </span>
              )}
            </div>
            <div className="grid grid-cols-3 gap-3 mb-3">
              {[
                { label: "Scored",       value: valSummary.assets_scored,     color: "#94a3b8" },
                { label: "Positive MoS", value: valSummary.positive_mos_count, color: "#10b981" },
                { label: "Overvalued",   value: valSummary.negative_mos_count, color: "#ef4444" },
              ].map(({ label, value, color }) => (
                <div key={label} className="text-center rounded-xl bg-white/[0.02] p-2">
                  <div className="text-lg font-mono font-bold" style={{ color }}>{value}</div>
                  <div className="text-[10px] text-white/30">{label}</div>
                </div>
              ))}
            </div>
            {/* MoS distribution bar */}
            {valSummary.margin_of_safety_distribution && (
              <div>
                <p className="text-[10px] text-white/30 mb-1.5">Margin of Safety Distribution</p>
                <div className="flex h-2 rounded-full overflow-hidden gap-px">
                  {[
                    { key: "above_20pct", color: "#10b981" },
                    { key: "10_to_20pct", color: "#f59e0b" },
                    { key: "0_to_10pct",  color: "#94a3b8" },
                    { key: "negative",    color: "#ef4444" },
                  ].map(({ key, color }) => {
                    const count = valSummary.margin_of_safety_distribution[key] ?? 0;
                    const pct = valSummary.assets_scored > 0
                      ? (count / valSummary.assets_scored) * 100
                      : 0;
                    return pct > 0 ? (
                      <div
                        key={key}
                        className="h-full"
                        style={{ width: `${pct}%`, background: color, opacity: 0.7 }}
                        title={`${key}: ${count}`}
                      />
                    ) : null;
                  })}
                </div>
                <div className="flex gap-3 mt-1.5 text-[9px] text-white/25">
                  <span className="text-primary/70">&gt;20% safe</span>
                  <span className="text-tertiary/70">10-20%</span>
                  <span className="text-white/30">0-10%</span>
                  <span className="text-error/70">overvalued</span>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── Recent Alerts panel ── */}
      {alertHistory.length > 0 && (
        <div className={glassInner}>
          <div className="flex items-center justify-between mb-3">
            <p className="text-xs text-white/40 uppercase tracking-widest">Recent Alerts</p>
            <a href="/config" className="text-[10px] text-white/30 hover:text-white/50 transition-colors">
              Manage rules →
            </a>
          </div>
          <div className="space-y-1">
            {alertHistory.slice(0, 8).map((alert) => {
              const ruleType = alert.alert_rules?.rule_type ?? "";
              const cfg = ALERT_TYPE_CONFIG[ruleType] ?? { icon: "🔔", color: "#94a3b8" };
              const ruleName = alert.alert_rules?.rule_name ?? ruleType;
              const ts = new Date(alert.triggered_at);
              const isToday = ts.toDateString() === new Date().toDateString();
              const timeStr = isToday
                ? ts.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
                : ts.toLocaleDateString([], { month: "short", day: "numeric" });
              return (
                <div
                  key={alert.id}
                  className="flex items-center justify-between py-1.5 px-2 rounded-lg hover:bg-white/[0.02] transition-colors"
                >
                  <div className="flex items-center gap-2">
                    <span className="text-sm">{cfg.icon}</span>
                    <span className="text-xs text-white/70">{ruleName}</span>
                    {!alert.delivered && (
                      <span className="text-[9px] px-1 py-0.5 rounded bg-tertiary/10 text-tertiary border border-tertiary/20">
                        undelivered
                      </span>
                    )}
                  </div>
                  <span className="text-[10px] text-white/30 font-mono">{timeStr}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ── Monte Carlo Preview card ── (always visible) */}
      <div
        className={glassInner}
        style={{ borderColor: "rgba(99,102,241,0.2)", boxShadow: "0 0 20px rgba(99,102,241,0.06)" }}
      >
        <div className="flex items-center justify-between mb-3">
          <p className="text-xs text-white/40 uppercase tracking-widest">20-Year Projection Preview</p>
          <a href="/projections" className="text-[10px] text-violet-400/70 hover:text-violet-400 transition-colors">
            Run full simulation →
          </a>
        </div>
        {mcPreview ? (
          <div className="grid grid-cols-3 gap-4">
            <div>
              <p className="text-[10px] text-white/30 mb-1">Median at 10yr</p>
              <p className="text-xl font-bold font-mono text-white/90">
                {mcPreview.median_10yr >= 1_000_000
                  ? `$${(mcPreview.median_10yr / 1_000_000).toFixed(2)}M`
                  : `$${(mcPreview.median_10yr / 1_000).toFixed(0)}K`}
              </p>
            </div>
            <div>
              <p className="text-[10px] text-white/30 mb-1">Median at 20yr</p>
              <p className="text-xl font-bold font-mono" style={{ color: "#10b981" }}>
                {mcPreview.median_20yr >= 1_000_000
                  ? `$${(mcPreview.median_20yr / 1_000_000).toFixed(2)}M`
                  : `$${(mcPreview.median_20yr / 1_000).toFixed(0)}K`}
              </p>
            </div>
            <div>
              <p className="text-[10px] text-white/30 mb-1">4% SWR Survival</p>
              <div className="flex items-center gap-2">
                <p
                  className="text-xl font-bold font-mono"
                  style={{
                    color: mcPreview.swr_probability >= 0.80 ? "#10b981"
                      : mcPreview.swr_probability >= 0.60 ? "#f59e0b"
                      : "#ef4444",
                  }}
                >
                  {(mcPreview.swr_probability * 100).toFixed(0)}%
                </p>
                <span
                  className="text-[10px] px-1.5 py-0.5 rounded-full font-medium"
                  style={{
                    background: mcPreview.swr_probability >= 0.80 ? "rgba(16,185,129,0.1)" : "rgba(245,158,11,0.1)",
                    color: mcPreview.swr_probability >= 0.80 ? "#34d399" : "#fbbf24",
                    border: `1px solid ${mcPreview.swr_probability >= 0.80 ? "rgba(16,185,129,0.2)" : "rgba(245,158,11,0.2)"}`,
                  }}
                >
                  {mcPreview.swr_probability >= 0.80 ? "Safe" : mcPreview.swr_probability >= 0.60 ? "Fair" : "At Risk"}
                </span>
              </div>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-3 gap-4">
            {[0, 1, 2].map((i) => (
              <div key={i}>
                <Skeleton className="h-3 w-20 mb-2" />
                <Skeleton className="h-7 w-24" />
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ── Tax Snapshot card ── */}
      {taxSnapshot && (
        <a
          href="/tax"
          className={`${glassInner} block hover:border-white/[0.14] transition-colors`}
          style={{ borderColor: "rgba(245,158,11,0.15)", boxShadow: "0 0 20px rgba(245,158,11,0.04)" }}
        >
          <div className="flex items-center justify-between mb-3">
            <p className="text-xs text-white/40 uppercase tracking-widest">Tax Snapshot</p>
            <div className="flex items-center gap-2">
              {taxSnapshot.darf_triggered && (
                <span
                  className="text-[10px] px-1.5 py-0.5 rounded-full font-medium border"
                  style={{ background: "rgba(239,68,68,0.1)", color: "#f87171", borderColor: "rgba(239,68,68,0.2)" }}
                >
                  🇧🇷 DARF Due
                </span>
              )}
              <span className="text-[10px] text-white/30 hover:text-white/50 transition-colors">View details →</span>
            </div>
          </div>
          <div className="grid grid-cols-4 gap-4">
            {/* Unrealized Gains */}
            <div>
              <p className="text-[10px] text-white/30 mb-1">Unrealized Gains</p>
              <p
                className="text-lg font-bold font-mono"
                style={{ color: taxSnapshot.unrealized_gain >= 0 ? "#10b981" : "#ef4444" }}
              >
                {taxSnapshot.unrealized_gain >= 0 ? "+" : ""}
                {fmtUSD(taxSnapshot.unrealized_gain)}
              </p>
            </div>
            {/* Worst-Case Tax */}
            <div>
              <p className="text-[10px] text-white/30 mb-1">Worst-Case Tax</p>
              <p className="text-lg font-bold font-mono text-tertiary">
                {fmtUSD(taxSnapshot.worst_case_tax)}
              </p>
            </div>
            {/* Harvest Savings */}
            <div>
              <p className="text-[10px] text-white/30 mb-1">Harvest Savings</p>
              <p className="text-lg font-bold font-mono text-primary">
                {taxSnapshot.harvest_savings > 0 ? fmtUSD(taxSnapshot.harvest_savings) : "—"}
              </p>
              {taxSnapshot.harvest_count > 0 && (
                <p className="text-[10px] text-primary/60 mt-0.5">
                  {taxSnapshot.harvest_count} candidate{taxSnapshot.harvest_count !== 1 ? "s" : ""}
                </p>
              )}
            </div>
            {/* Brazil DARF */}
            <div>
              <p className="text-[10px] text-white/30 mb-1">Brazil DARF</p>
              <div className="flex items-center gap-2">
                <p
                  className="text-lg font-bold font-mono"
                  style={{
                    color: taxSnapshot.darf_triggered
                      ? "#ef4444"
                      : taxSnapshot.darf_pct >= 0.80 ? "#f59e0b" : "#10b981",
                  }}
                >
                  {(taxSnapshot.darf_pct * 100).toFixed(0)}%
                </p>
                <div className="flex-1 h-1.5 rounded-full bg-white/[0.06] overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all"
                    style={{
                      width: `${Math.min(taxSnapshot.darf_pct * 100, 100)}%`,
                      background: taxSnapshot.darf_triggered
                        ? "#ef4444"
                        : taxSnapshot.darf_pct >= 0.80 ? "#f59e0b" : "#10b981",
                    }}
                  />
                </div>
              </div>
              <p className="text-[10px] text-white/25 mt-0.5">of R$20k limit</p>
            </div>
          </div>
        </a>
      )}

      {/* ── Journal Accuracy card ── */}
      {journalAccuracy && (journalAccuracy.followed_count + journalAccuracy.overrode_count) > 0 && (
        <a
          href="/journal"
          className={`${glassInner} block hover:border-white/[0.14] transition-colors`}
          style={{ borderColor: "rgba(139,92,246,0.12)", boxShadow: "0 0 20px rgba(139,92,246,0.04)" }}
        >
          <div className="flex items-center justify-between mb-3">
            <p className="text-xs text-white/40 uppercase tracking-widest">Decision Journal</p>
            <span className="text-[10px] text-white/30 hover:text-white/50 transition-colors">View journal →</span>
          </div>
          <div className="grid grid-cols-3 gap-4">
            <div>
              <p className="text-[10px] text-white/30 mb-1">Followed System</p>
              <p className="text-lg font-bold font-mono text-primary">
                {journalAccuracy.followed_count}
                <span className="text-xs text-white/30 ml-1">decisions</span>
              </p>
              {journalAccuracy.avg_followed_30d != null && (
                <p className="text-[10px] font-mono mt-0.5" style={{ color: journalAccuracy.avg_followed_30d >= 0 ? "#10b981" : "#ef4444" }}>
                  avg 30d: {journalAccuracy.avg_followed_30d >= 0 ? "+" : ""}
                  {(journalAccuracy.avg_followed_30d * 100).toFixed(1)}%
                </p>
              )}
            </div>
            <div>
              <p className="text-[10px] text-white/30 mb-1">Overrode System</p>
              <p className="text-lg font-bold font-mono text-tertiary">
                {journalAccuracy.overrode_count}
                <span className="text-xs text-white/30 ml-1">overrides</span>
              </p>
              {journalAccuracy.avg_overrode_30d != null && (
                <p className="text-[10px] font-mono mt-0.5" style={{ color: journalAccuracy.avg_overrode_30d >= 0 ? "#10b981" : "#ef4444" }}>
                  avg 30d: {journalAccuracy.avg_overrode_30d >= 0 ? "+" : ""}
                  {(journalAccuracy.avg_overrode_30d * 100).toFixed(1)}%
                </p>
              )}
            </div>
            <div>
              <p className="text-[10px] text-white/30 mb-1">System Edge</p>
              {journalAccuracy.system_outperformance_30d != null ? (
                <>
                  <p
                    className="text-lg font-bold font-mono"
                    style={{ color: journalAccuracy.system_outperformance_30d >= 0 ? "#10b981" : "#ef4444" }}
                  >
                    {journalAccuracy.system_outperformance_30d >= 0 ? "+" : ""}
                    {(journalAccuracy.system_outperformance_30d * 100).toFixed(1)}%
                  </p>
                  <p className="text-[10px] text-white/25 mt-0.5">system vs overrides</p>
                </>
              ) : (
                <p className="text-lg font-bold font-mono text-white/20">—</p>
              )}
            </div>
          </div>
        </a>
      )}

      {/* ── Error banner ── */}
      {error && (
        <OIErrorState
          message={`API unavailable — ${error}. Start the backend: uv run uvicorn app.main:app --reload`}
          onRetry={() => refetchStatus()}
        />
      )}
    </div>
  );
}

// ── Sub-components ────────────────────────────────────────────────────────────

function SleeveBar({ sw }: { sw: SleeveWeight }) {
  const color = SLEEVE_COLORS[sw.sleeve] ?? "#64748b";
  const label = SLEEVE_LABELS[sw.sleeve] ?? sw.sleeve;
  const isBreached = sw.is_breached;

  return (
    <div className="grid grid-cols-12 items-center gap-2 text-xs">
      <span className="col-span-3 text-white/50 truncate">{label}</span>

      {/* Bar track */}
      <div className="col-span-6 h-1.5 rounded-full bg-white/[0.06] relative">
        {/* Target ghost bar */}
        <div
          className="absolute top-0 h-full rounded-full opacity-20"
          style={{ width: `${sw.target_weight * 100}%`, background: color }}
        />
        {/* Actual fill */}
        <div
          className="absolute top-0 h-full rounded-full transition-all duration-500"
          style={{
            width: `${Math.min(sw.current_weight * 100, 100)}%`,
            background: color,
            boxShadow: isBreached ? `0 0 6px ${color}` : undefined,
          }}
        />
        {/* Target marker */}
        <div
          className="absolute top-0 w-px h-full bg-white/40"
          style={{ left: `${sw.target_weight * 100}%` }}
        />
      </div>

      <span className="col-span-1 text-right text-white/70 font-mono">
        {(sw.current_weight * 100).toFixed(0)}%
      </span>
      <span
        className={`col-span-2 text-right font-mono ${isBreached ? "text-tertiary" : "text-white/30"}`}
      >
        {sw.drift_pct > 0 ? "+" : ""}{sw.drift_pct.toFixed(1)}%
        {isBreached ? " ⚠" : ""}
      </span>
    </div>
  );
}

function VaultCard({ vault }: { vault: VaultBalance }) {
  const cfg = VAULT_CONFIG[vault.vault_type as keyof typeof VAULT_CONFIG] ?? {
    label: vault.vault_type,
    color: "#64748b",
    icon: "💼",
  };
  const progress = vault.progress_pct ?? 0;

  return (
    <div
      className={`${glass} p-4`}
      style={{ borderColor: vault.is_investable ? `${cfg.color}30` : "rgba(255,255,255,0.05)" }}
    >
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs text-white/50 flex items-center gap-1.5">
          {cfg.icon} {cfg.label}
        </span>
        {!vault.is_investable && (
          <span className="text-[10px] text-white/30 border border-white/10 rounded px-1.5 py-0.5">NON-INVESTABLE</span>
        )}
        {vault.approval_required && vault.is_investable && (
          <span className="text-[10px] text-tertiary/70 border border-tertiary/20 rounded px-1.5 py-0.5">APPROVAL REQ.</span>
        )}
      </div>

      <p className="text-xl font-bold font-mono" style={{ color: cfg.color }}>
        {fmtUSD(vault.balance_usd)}
      </p>

      {vault.min_balance != null && (
        <div className="mt-2">
          <div className="h-1 rounded-full bg-white/[0.06] overflow-hidden">
            <div
              className="h-full rounded-full transition-all duration-700"
              style={{ width: `${Math.min(progress * 100, 100)}%`, background: cfg.color, opacity: 0.7 }}
            />
          </div>
          <p className="text-[10px] text-white/25 mt-1 font-mono">
            {(progress * 100).toFixed(0)}% of min {fmtUSD(vault.min_balance)}
          </p>
        </div>
      )}
    </div>
  );
}

function seasonLabel(s: string) {
  const labels: Record<string, string> = {
    rising_growth_low_inflation:      "Rising Growth / Low Inflation",
    falling_growth_low_inflation:     "Falling Growth / Low Inflation",
    rising_inflation:                 "Rising Inflation",
    falling_inflation_growth_recovery:"Recovery / Falling Inflation",
    normal:                           "Normal / Unclear Regime",
  };
  return labels[s] ?? s;
}

function seasonIcon(s: string) {
  const icons: Record<string, string> = {
    rising_growth_low_inflation:      "📈",
    falling_growth_low_inflation:     "📉",
    rising_inflation:                 "🔥",
    falling_inflation_growth_recovery:"🌱",
    normal:                           "⚖️",
  };
  return icons[s] ?? "📊";
}
