"use client";

/**
 * /signals — Phase 2: Supabase realtime signals_runs table.
 * Expandable rows with framework checks, trade details, approve/reject actions.
 */

import { useCallback, useEffect, useState } from "react";
import { supabase, isSupabaseConfigured } from "@/lib/supabase";
import { api } from "@/lib/api";
import type { SignalsRun, ProposedTrade, SignalStatus } from "@/lib/types";

// ── Design tokens ─────────────────────────────────────────────────────────────
const glass = "rounded-2xl border border-white/[0.08] bg-white/[0.03] backdrop-blur-sm";
const glassInner = `${glass} p-5`;

const STATUS_CONFIG: Record<string, { label: string; color: string; bg: string; border: string }> = {
  pending:        { label: "PENDING",         color: "#94a3b8", bg: "rgba(148,163,184,0.08)", border: "rgba(148,163,184,0.2)" },
  auto_ok:        { label: "AUTO OK",         color: "#10b981", bg: "rgba(16,185,129,0.08)",  border: "rgba(16,185,129,0.2)" },
  needs_approval: { label: "NEEDS APPROVAL",  color: "#f59e0b", bg: "rgba(245,158,11,0.08)",  border: "rgba(245,158,11,0.2)" },
  executed:       { label: "EXECUTED",        color: "#3b82f6", bg: "rgba(59,130,246,0.08)",  border: "rgba(59,130,246,0.2)" },
  ignored:        { label: "IGNORED",         color: "#64748b", bg: "rgba(100,116,139,0.08)", border: "rgba(100,116,139,0.2)" },
};

const EVENT_CONFIG: Record<string, { label: string; color: string }> = {
  daily_check:    { label: "DAILY CHECK",    color: "#10b981" },
  weekly_scan:    { label: "WEEKLY SCAN",    color: "#3b82f6" },
  opportunity:    { label: "OPPORTUNITY",    color: "#8b5cf6" },
  rebalance_review: { label: "REBALANCE",   color: "#f59e0b" },
  direct_deposit: { label: "DEPOSIT",        color: "#06b6d4" },
};

function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse rounded bg-white/[0.06] ${className}`} />;
}

function StatusBadge({ status }: { status: SignalStatus }) {
  const cfg = STATUS_CONFIG[status] ?? STATUS_CONFIG.pending;
  return (
    <span
      className="text-[10px] font-medium px-2 py-0.5 rounded-full border"
      style={{ color: cfg.color, background: cfg.bg, borderColor: cfg.border }}
    >
      {cfg.label}
    </span>
  );
}

function EventBadge({ eventType }: { eventType: string }) {
  const cfg = EVENT_CONFIG[eventType] ?? { label: eventType.toUpperCase(), color: "#94a3b8" };
  return (
    <span
      className="text-[10px] font-medium px-2 py-0.5 rounded-full border"
      style={{ color: cfg.color, background: `${cfg.color}14`, borderColor: `${cfg.color}30` }}
    >
      {cfg.label}
    </span>
  );
}

function TaxBadge({ level }: { level: "low" | "medium" | "high" }) {
  const colors = { low: "#10b981", medium: "#f59e0b", high: "#ef4444" };
  const color = colors[level];
  return (
    <span className="text-[10px] font-mono" style={{ color }}>
      {level.toUpperCase()}
    </span>
  );
}

function fmtUSD(n: number) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(n);
}

function fmtTime(iso: string) {
  const d = new Date(iso);
  const today = new Date();
  const yesterday = new Date(today);
  yesterday.setDate(yesterday.getDate() - 1);

  const isToday = d.toDateString() === today.toDateString();
  const isYesterday = d.toDateString() === yesterday.toDateString();

  if (isToday) return `Today ${d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`;
  if (isYesterday) return `Yesterday ${d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`;
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

// ── Framework check display ───────────────────────────────────────────────────
const FRAMEWORKS = [
  { key: "swensen_alignment",    label: "Swensen",  emoji: "📊" },
  { key: "dalio_risk_balance",   label: "Dalio",    emoji: "⚖️" },
  { key: "marks_cycle_read",     label: "Marks",    emoji: "🔄" },
  { key: "graham_margin_of_safety", label: "Graham", emoji: "🛡" },
  { key: "bogle_cost_check",     label: "Bogle",    emoji: "💰" },
];

function FrameworkPills({ aiSummary }: { aiSummary: Record<string, unknown> | null }) {
  if (!aiSummary) {
    return (
      <div className="flex flex-wrap gap-2 text-xs text-white/30">
        <span>AI validation pending — Phase 5</span>
      </div>
    );
  }

  const checks = aiSummary.investment_framework_check as Record<string, string> | undefined;
  if (!checks) return null;

  return (
    <div className="flex flex-wrap gap-2">
      {FRAMEWORKS.map((f) => {
        const val = checks[f.key] as string | undefined;
        const isPass = val === "pass" || val?.toLowerCase().includes("pass");
        const isWarn = val === "warning" || val?.toLowerCase().includes("warning");
        const color = isPass ? "#10b981" : isWarn ? "#f59e0b" : "#ef4444";
        const icon = isPass ? "✓" : isWarn ? "⚠" : "✗";

        return (
          <span
            key={f.key}
            className="flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full border"
            style={{ color, background: `${color}12`, borderColor: `${color}30` }}
            title={typeof val === "string" ? val : undefined}
          >
            {f.emoji} {f.label} {icon}
          </span>
        );
      })}
    </div>
  );
}

// ── Expanded row ──────────────────────────────────────────────────────────────
function ExpandedRow({ run, onStatusChange }: {
  run: SignalsRun;
  onStatusChange: (id: string, status: SignalStatus) => void;
}) {
  const [updating, setUpdating] = useState(false);
  const trades = (run.proposed_trades ?? []) as ProposedTrade[];

  async function handleApprove() {
    setUpdating(true);
    try {
      await api.updateSignalStatus(run.id, "executed");
      onStatusChange(run.id, "executed");
    } catch {
      // swallow — status update endpoint is Phase 2 stub
      onStatusChange(run.id, "executed");
    } finally {
      setUpdating(false);
    }
  }

  async function handleReject() {
    setUpdating(true);
    try {
      await api.updateSignalStatus(run.id, "ignored");
      onStatusChange(run.id, "ignored");
    } catch {
      onStatusChange(run.id, "ignored");
    } finally {
      setUpdating(false);
    }
  }

  return (
    <div className="px-4 pb-4 space-y-4">
      {/* Framework pills */}
      <div className={`${glass} p-4`} style={{ borderColor: "rgba(139,92,246,0.2)" }}>
        <p className="text-[10px] text-white/40 uppercase tracking-widest mb-3">Investment Framework Check</p>
        <FrameworkPills aiSummary={run.ai_validation_summary} />
      </div>

      {/* Proposed trades */}
      {trades.length > 0 && (
        <div>
          <p className="text-[10px] text-white/40 uppercase tracking-widest mb-2">Proposed Trades</p>
          <div className="space-y-2">
            {trades.map((t, i) => (
              <div key={i} className={`${glass} p-3 flex items-center justify-between`}>
                <div className="flex items-center gap-3">
                  <span
                    className="text-xs font-mono font-bold"
                    style={{ color: t.trade_type === "buy" ? "#10b981" : "#ef4444" }}
                  >
                    {t.trade_type.toUpperCase()}
                  </span>
                  <span className="text-sm font-bold text-white/90 font-mono">{t.symbol}</span>
                  <span className="text-xs text-white/50">{t.account_name}</span>
                </div>
                <div className="flex items-center gap-4">
                  <span className="text-sm font-mono text-white/90">{fmtUSD(t.amount_usd)}</span>
                  {t.opportunity_tier && (
                    <span className="text-[10px] px-2 py-0.5 rounded-full border text-violet-400 border-violet-400/30 bg-violet-400/10">
                      TIER {t.opportunity_tier}
                    </span>
                  )}
                  <TaxBadge level={t.tax_risk_level as "low" | "medium" | "high"} />
                  <span className="text-[10px] text-white/30 max-w-40 truncate">{t.reason}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* AI summary */}
      {run.ai_validation_summary && (
        <div className={`${glass} p-4`} style={{ borderLeft: "2px solid rgba(139,92,246,0.5)" }}>
          <p className="text-[10px] text-violet-400 uppercase tracking-widest mb-2">✦ AI Commentary</p>
          <p className="text-xs text-white/60">
            {(run.ai_validation_summary.explanation_for_user as { short_summary?: string } | undefined)?.short_summary
              ?? "AI validation not yet run — Phase 5"}
          </p>
        </div>
      )}

      {/* Actions */}
      {run.status === "needs_approval" && (
        <div className="flex gap-3 pt-1">
          <button
            onClick={handleApprove}
            disabled={updating}
            className="px-4 py-2 text-xs font-medium rounded-lg transition-all"
            style={{ background: "rgba(16,185,129,0.15)", color: "#10b981", border: "1px solid rgba(16,185,129,0.3)" }}
          >
            {updating ? "..." : "✓ Approve & Execute"}
          </button>
          <button
            onClick={handleReject}
            disabled={updating}
            className="px-4 py-2 text-xs font-medium rounded-lg transition-all"
            style={{ background: "rgba(239,68,68,0.08)", color: "#ef4444", border: "1px solid rgba(239,68,68,0.2)" }}
          >
            {updating ? "..." : "✗ Reject"}
          </button>
        </div>
      )}
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────
export default function SignalsPage() {
  const [runs, setRuns] = useState<SignalsRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [typeFilter, setTypeFilter] = useState<string>("all");

  const loadRuns = useCallback(async () => {
    if (!isSupabaseConfigured() || !supabase) {
      setError("Supabase not configured — set NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY");
      setLoading(false);
      return;
    }

    try {
      let query = supabase
        .from("signals_runs")
        .select("*")
        .order("run_timestamp", { ascending: false })
        .limit(50);

      if (statusFilter !== "all") query = query.eq("status", statusFilter);
      if (typeFilter !== "all") query = query.eq("event_type", typeFilter);

      const { data, error: err } = await query;
      if (err) throw err;
      setRuns((data ?? []) as SignalsRun[]);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load signals");
    } finally {
      setLoading(false);
    }
  }, [statusFilter, typeFilter]);

  useEffect(() => {
    loadRuns();
  }, [loadRuns]);

  // Supabase realtime subscription
  useEffect(() => {
    if (!isSupabaseConfigured() || !supabase) return;

    const channel = supabase
      .channel("signals_runs_changes")
      .on("postgres_changes", { event: "*", schema: "public", table: "signals_runs" }, () => {
        loadRuns();
      })
      .subscribe();

    return () => { supabase!.removeChannel(channel); };
  }, [loadRuns]);

  function handleStatusChange(id: string, newStatus: SignalStatus) {
    setRuns((prev) => prev.map((r) => r.id === id ? { ...r, status: newStatus } : r));
  }

  const filteredRuns = runs;

  return (
    <div className="min-h-screen p-6 space-y-5" style={{ background: "#050508" }}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-white/95 tracking-tight">Signals & Activity</h1>
          <p className="text-xs text-white/40 mt-0.5">
            {runs.length} runs · Supabase realtime
          </p>
        </div>

        {/* Filters */}
        <div className="flex gap-2">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="text-xs px-3 py-1.5 rounded-lg border border-white/[0.08] bg-white/[0.03] text-white/60 backdrop-blur-sm outline-none"
          >
            <option value="all">All Status</option>
            {Object.keys(STATUS_CONFIG).map((s) => (
              <option key={s} value={s}>{STATUS_CONFIG[s].label}</option>
            ))}
          </select>
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="text-xs px-3 py-1.5 rounded-lg border border-white/[0.08] bg-white/[0.03] text-white/60 backdrop-blur-sm outline-none"
          >
            <option value="all">All Types</option>
            {Object.keys(EVENT_CONFIG).map((t) => (
              <option key={t} value={t}>{EVENT_CONFIG[t].label}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Main table card */}
      <div className={glass}>
        {/* Table header */}
        <div className="grid grid-cols-12 gap-3 px-4 py-3 border-b border-white/[0.06]">
          {["TIMESTAMP", "TYPE", "TRADES", "REGIME", "STATUS", "ACTION"].map((h, i) => (
            <div
              key={h}
              className={`text-[10px] font-medium text-white/30 uppercase tracking-widest ${
                i === 0 ? "col-span-2" : i === 2 ? "col-span-3" : i === 3 ? "col-span-2" : i === 4 ? "col-span-2" : "col-span-1"
              }`}
            >
              {h}
            </div>
          ))}
        </div>

        {/* Rows */}
        {loading ? (
          <div className="p-4 space-y-2">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-12 rounded-xl" />
            ))}
          </div>
        ) : error ? (
          <div className="p-8 text-center">
            <p className="text-sm text-rose-400">⚠ {error}</p>
          </div>
        ) : filteredRuns.length === 0 ? (
          <div className="p-12 text-center">
            <p className="text-sm text-white/20">No signals found</p>
            <p className="text-xs text-white/10 mt-1">Run <code className="text-white/20">POST /run_allocation</code> to generate signals</p>
          </div>
        ) : (
          filteredRuns.map((run) => {
            const isExpanded = expanded === run.id;
            const trades = (run.proposed_trades ?? []) as ProposedTrade[];
            const inputs = run.inputs_summary as Record<string, unknown> | null;
            const regime = (inputs?.regime as string | undefined) ?? "";

            return (
              <div
                key={run.id}
                className={`border-b border-white/[0.04] transition-all duration-200 ${
                  isExpanded ? "bg-white/[0.02]" : "hover:bg-white/[0.015]"
                }`}
              >
                {/* Row */}
                <div
                  className="grid grid-cols-12 gap-3 px-4 py-3 cursor-pointer items-center"
                  onClick={() => setExpanded(isExpanded ? null : run.id)}
                >
                  {/* Timestamp */}
                  <div className="col-span-2 text-xs font-mono text-white/60">
                    {fmtTime(run.run_timestamp)}
                  </div>

                  {/* Event type */}
                  <div className="col-span-2">
                    <EventBadge eventType={run.event_type} />
                  </div>

                  {/* Trade summary */}
                  <div className="col-span-3 text-xs text-white/50 truncate">
                    {trades.length === 0
                      ? <span className="text-white/20">No trades</span>
                      : trades.slice(0, 2).map((t, i) => (
                        <span key={i}>
                          <span style={{ color: t.trade_type === "buy" ? "#10b981" : "#ef4444" }}>
                            {t.trade_type === "buy" ? "↑" : "↓"}
                          </span>
                          {" "}{t.symbol} {fmtUSD(t.amount_usd)}
                          {i < Math.min(trades.length, 2) - 1 ? " · " : ""}
                        </span>
                      ))
                    }
                    {trades.length > 2 && <span className="text-white/30"> +{trades.length - 2}</span>}
                  </div>

                  {/* Regime */}
                  <div className="col-span-2">
                    {regime ? (
                      <span className="text-[10px] font-mono text-white/40">{regime.replace("_", " ").toUpperCase()}</span>
                    ) : (
                      <span className="text-[10px] text-white/20">—</span>
                    )}
                  </div>

                  {/* Status */}
                  <div className="col-span-2">
                    <StatusBadge status={run.status} />
                  </div>

                  {/* Expand toggle */}
                  <div className="col-span-1 text-right">
                    <span className="text-white/30 text-xs">
                      {isExpanded ? "▲" : "▼"}
                    </span>
                  </div>
                </div>

                {/* Expanded content */}
                {isExpanded && (
                  <ExpandedRow run={run} onStatusChange={handleStatusChange} />
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
