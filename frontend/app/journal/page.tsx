"use client";

/**
 * /journal — Decision log, override accuracy scorecard, behavioral patterns, AI insight.
 * Phase 9: full implementation with backfill trigger, CSV export, pagination.
 */

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { OIBadge } from "@/components/ui/oi/OIBadge";

// ── Design tokens ─────────────────────────────────────────────────────────────
const glass = "glass-card";

// ── Types ─────────────────────────────────────────────────────────────────────
interface JournalEntry {
  id: string;
  event_date: string;
  action_type: "followed" | "overrode" | "deferred" | "manual_trade";
  asset_id: string | null;
  reasoning: string | null;
  system_recommendation: Record<string, unknown> | null;
  actual_action: Record<string, unknown> | null;
  outcome_30d: number | null;
  outcome_90d: number | null;
  signal_run_id: string | null;
}

interface JournalStats {
  followed_count: number;
  overrode_count: number;
  deferred_count: number;
  manual_count: number;
  total_decisions: number;
  avg_outcome_followed_30d: number | null;
  avg_outcome_overrode_30d: number | null;
  avg_outcome_followed_90d: number | null;
  avg_outcome_overrode_90d: number | null;
  system_outperformance_30d: number | null;
  system_outperformance_90d: number | null;
}

interface BehavioralPattern {
  pattern_type: string;
  description: string;
  severity: string;
  supporting_data: Record<string, unknown>;
}

interface JournalInsight {
  insight: string;
  has_enough_data: boolean;
  followed_count: number;
  overrode_count: number;
  system_outperformance_30d: number | null;
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function pct(v: number | null, digits = 1) {
  if (v == null) return "—";
  return `${v >= 0 ? "+" : ""}${(v * 100).toFixed(digits)}%`;
}

function fmtDate(iso: string) {
  const d = new Date(iso);
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

const ACTION_STYLES: Record<string, { bg: string; text: string; border: string; label: string; variant: "positive" | "negative" | "warning" | "neutral" }> = {
  followed:     { bg: "bg-primary/10",   text: "text-primary",   border: "border-primary/20",   label: "Followed",  variant: "positive" },
  overrode:     { bg: "bg-error/10",     text: "text-error",     border: "border-error/20",     label: "Overrode",  variant: "negative" },
  deferred:     { bg: "bg-tertiary/10",  text: "text-tertiary",  border: "border-tertiary/20",  label: "Deferred",  variant: "warning"  },
  manual_trade: { bg: "bg-secondary/10", text: "text-secondary", border: "border-secondary/20", label: "Manual",    variant: "neutral"  },
};

const SEVERITY_COLORS: Record<string, string> = {
  high: "text-error",
  medium: "text-tertiary",
  low: "text-outline",
};

// ── Component ─────────────────────────────────────────────────────────────────
export default function JournalPage() {
  const [entries, setEntries]       = useState<JournalEntry[]>([]);
  const [stats, setStats]           = useState<JournalStats | null>(null);
  const [patterns, setPatterns]     = useState<BehavioralPattern[]>([]);
  const [insight, setInsight]       = useState<JournalInsight | null>(null);
  const [loading, setLoading]       = useState(true);
  const [error, setError]           = useState<string | null>(null);
  const [page, setPage]             = useState(0);
  const [filterAction, setFilter]   = useState<string>("all");
  const [backfilling, setBackfilling] = useState(false);
  const [backfillMsg, setBackfillMsg] = useState<string | null>(null);
  const [expandedRow, setExpanded]  = useState<string | null>(null);

  const PAGE_SIZE = 20;

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [entriesRes, statsRes, patternsRes, insightRes] = await Promise.allSettled([
        api.listJournal({ limit: 200, action_type: filterAction === "all" ? undefined : filterAction }),
        api.journalStats(),
        api.journalPatterns(),
        api.journalInsight(),
      ]);
      if (entriesRes.status === "fulfilled") setEntries(entriesRes.value as JournalEntry[]);
      if (statsRes.status === "fulfilled")   setStats(statsRes.value as JournalStats);
      if (patternsRes.status === "fulfilled") setPatterns(patternsRes.value as BehavioralPattern[]);
      if (insightRes.status === "fulfilled")  setInsight(insightRes.value as JournalInsight);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load journal");
    } finally {
      setLoading(false);
    }
  }, [filterAction]);

  useEffect(() => { load(); }, [load]);

  const handleBackfill = async () => {
    setBackfilling(true);
    setBackfillMsg(null);
    try {
      const res = await api.triggerJournalBackfill() as { queued: number; message: string };
      setBackfillMsg(res.message);
    } catch {
      setBackfillMsg("Backfill request failed.");
    } finally {
      setBackfilling(false);
    }
  };

  const handleExport = () => {
    window.open(
      `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/journal/export`,
      "_blank"
    );
  };

  // Paginated slice
  const pageEntries = entries.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);
  const totalPages  = Math.ceil(entries.length / PAGE_SIZE);

  const delta30 = stats?.system_outperformance_30d;
  const delta90 = stats?.system_outperformance_90d;

  return (
    <div className="min-h-screen bg-[#050508] text-on-surface">
      {/* Ambient glows */}
      <div className="fixed top-[-10%] right-[-10%] w-[500px] h-[500px] bg-primary/5 blur-[120px] rounded-full pointer-events-none -z-10" />
      <div className="fixed bottom-[-10%] left-[200px] w-[400px] h-[400px] bg-secondary/5 blur-[100px] rounded-full pointer-events-none -z-10" />

      <div className="p-8 space-y-8">
        {/* Header */}
        <div className="flex items-end justify-between">
          <div>
            <h1 className="text-4xl font-black tracking-tight text-on-surface uppercase">
              Decision Journal
            </h1>
            <p className="text-on-surface-variant mt-1 text-sm">
              Audit psychological performance and system fidelity metrics.
            </p>
          </div>
          <div className="flex gap-3">
            <button
              onClick={handleBackfill}
              disabled={backfilling}
              className="px-4 py-2 rounded-xl border border-white/10 bg-white/[0.04] text-sm text-slate-300 hover:bg-white/[0.08] transition-all disabled:opacity-50"
            >
              {backfilling ? "Backfilling…" : "↻ Backfill Outcomes"}
            </button>
            <button
              onClick={handleExport}
              className="px-4 py-2 rounded-xl border border-white/10 bg-white/[0.04] text-sm text-slate-300 hover:bg-white/[0.08] transition-all"
            >
              ↓ Export CSV
            </button>
          </div>
        </div>

        {backfillMsg && (
          <div className="text-sm text-primary bg-primary/10 border border-primary/20 rounded-xl px-4 py-2">
            {backfillMsg}
          </div>
        )}

        {error && (
          <div className="rounded-xl border border-error/20 bg-error/10 px-4 py-3 text-error text-sm flex items-center justify-between">
            <span>{error}</span>
            <button onClick={load} className="text-error/70 hover:text-error underline text-xs">Retry</button>
          </div>
        )}

        {/* ── Accuracy Scorecard ── */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Followed System */}
          <div className={`${glass} p-8 border-l-4 border-l-primary`}
               style={{ boxShadow: "0 0 20px rgba(78,222,163,0.08)" }}>
            <div className="flex justify-between items-start mb-6">
              <div>
                <span className="text-[10px] font-mono uppercase tracking-[0.2em] text-primary">
                  Fidelity Protocol
                </span>
                <h3 className="text-xl font-bold mt-1">Followed System</h3>
              </div>
              <span className="text-2xl p-2 rounded-lg bg-primary/10">✅</span>
            </div>
            {loading ? (
              <div className="h-16 w-32 rounded-lg bg-white/5 animate-pulse" />
            ) : (
              <>
                <div className="flex items-baseline gap-2">
                  <span className="text-6xl font-bold font-mono text-primary tracking-tighter">
                    {stats ? pct(stats.avg_outcome_followed_90d) : "—"}
                  </span>
                </div>
                <div className="mt-3 text-sm text-on-surface-variant font-mono">
                  {stats?.followed_count ?? 0} decisions · avg 30d: {pct(stats?.avg_outcome_followed_30d ?? null)}
                </div>
              </>
            )}
          </div>

          {/* Overrode System */}
          <div className={`${glass} p-8 border-l-4 border-l-tertiary`}>
            <div className="flex justify-between items-start mb-6">
              <div>
                <span className="text-[10px] font-mono uppercase tracking-[0.2em] text-tertiary">
                  Manual Deviation
                </span>
                <h3 className="text-xl font-bold mt-1">Overrode System</h3>
              </div>
              <span className="text-2xl p-2 rounded-lg bg-tertiary/10">⚠️</span>
            </div>
            {loading ? (
              <div className="h-16 w-32 rounded-lg bg-white/5 animate-pulse" />
            ) : (
              <>
                <div className="flex items-baseline gap-2">
                  <span className="text-6xl font-bold font-mono text-tertiary tracking-tighter">
                    {stats ? pct(stats.avg_outcome_overrode_90d) : "—"}
                  </span>
                </div>
                <div className="mt-3 text-sm text-on-surface-variant font-mono">
                  {stats?.overrode_count ?? 0} overrides · avg 30d: {pct(stats?.avg_outcome_overrode_30d ?? null)}
                </div>
                {delta30 != null && (
                  <div className={`mt-2 text-sm font-mono font-semibold ${delta30 >= 0 ? "text-primary" : "text-error"}`}>
                    System outperforms overrides by {pct(delta30)} (30d)
                  </div>
                )}
              </>
            )}
          </div>
        </div>

        {/* ── Behavioral Patterns ── */}
        {patterns.length > 0 && (
          <div className={`${glass} p-6`}>
            <h3 className="font-bold text-lg mb-4">
              🔍 Behavioral Patterns
            </h3>
            <div className="space-y-3">
              {patterns.map((p, i) => (
                <div key={i} className="flex items-start gap-4 p-4 rounded-xl bg-white/[0.02] border border-white/5">
                  <span className={`text-xs font-mono uppercase font-bold mt-0.5 ${SEVERITY_COLORS[p.severity] ?? "text-slate-400"}`}>
                    {p.severity}
                  </span>
                  <div>
                    <div className="text-sm font-medium text-on-surface">{p.description}</div>
                    <div className="text-xs text-outline font-mono mt-1">
                      {p.pattern_type.replace(/_/g, " ")}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ── Decision Log Table ── */}
        <div className={glass}>
          <div className="p-6 border-b border-white/5 flex flex-wrap items-center gap-3">
            <h3 className="font-bold text-lg flex-1">Execution Ledger</h3>
            {/* Filter pills */}
            {["all", "followed", "overrode", "deferred", "manual_trade"].map((f) => (
              <button
                key={f}
                onClick={() => { setFilter(f); setPage(0); }}
                className={`px-3 py-1 rounded-full text-xs font-mono uppercase transition-all border ${
                  filterAction === f
                    ? "bg-white/10 border-white/20 text-slate-100"
                    : "bg-white/[0.02] border-white/[0.06] text-slate-400 hover:bg-white/5"
                }`}
              >
                {f === "all" ? "All" : ACTION_STYLES[f]?.label ?? f}
              </button>
            ))}
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="text-[10px] uppercase tracking-widest text-outline font-mono border-b border-white/5">
                  <th className="px-6 py-4 font-normal">Date</th>
                  <th className="px-6 py-4 font-normal">Action</th>
                  <th className="px-6 py-4 font-normal">Asset</th>
                  <th className="px-6 py-4 font-normal">Reasoning</th>
                  <th className="px-6 py-4 font-normal text-right">30d</th>
                  <th className="px-6 py-4 font-normal text-right">90d</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.04]">
                {loading &&
                  Array.from({ length: 5 }).map((_, i) => (
                    <tr key={i}>
                      {Array.from({ length: 6 }).map((_, j) => (
                        <td key={j} className="px-6 py-4">
                          <div className="h-4 rounded bg-white/5 animate-pulse" />
                        </td>
                      ))}
                    </tr>
                  ))}
                {!loading && pageEntries.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-6 py-12 text-center text-outline text-sm">
                      No journal entries yet. Decisions will appear here after your first allocation run.
                    </td>
                  </tr>
                )}
                {!loading &&
                  pageEntries.map((e) => {
                    const style = ACTION_STYLES[e.action_type] ?? ACTION_STYLES.manual_trade;
                    const isExpanded = expandedRow === e.id;
                    const out30Color =
                      e.outcome_30d == null ? "text-outline"
                      : e.outcome_30d >= 0 ? "text-primary"
                      : "text-error";
                    const out90Color =
                      e.outcome_90d == null ? "text-outline"
                      : e.outcome_90d >= 0 ? "text-primary"
                      : "text-error";

                    return (
                      <>
                        <tr
                          key={e.id}
                          onClick={() => setExpanded(isExpanded ? null : e.id)}
                          className="hover:bg-white/[0.025] transition-colors cursor-pointer"
                        >
                          <td className="px-6 py-4 text-sm text-on-surface-variant font-mono whitespace-nowrap">
                            {fmtDate(e.event_date)}
                          </td>
                          <td className="px-6 py-4">
                            <OIBadge variant={style.variant}>
                              {style.label}
                            </OIBadge>
                          </td>
                          <td className="px-6 py-4 font-mono text-sm text-on-surface">
                            {e.asset_id ? e.asset_id.slice(0, 8) + "…" : "—"}
                          </td>
                          <td className="px-6 py-4 text-sm text-on-surface-variant max-w-[300px] truncate italic">
                            {e.reasoning ?? "—"}
                          </td>
                          <td className={`px-6 py-4 text-right font-mono text-sm ${out30Color}`}>
                            {pct(e.outcome_30d)}
                          </td>
                          <td className={`px-6 py-4 text-right font-mono text-sm ${out90Color}`}>
                            {pct(e.outcome_90d)}
                          </td>
                        </tr>
                        {isExpanded && (
                          <tr key={`${e.id}-expand`} className="bg-white/[0.015]">
                            <td colSpan={6} className="px-8 py-4">
                              <div className="grid grid-cols-2 gap-6 text-sm">
                                <div>
                                  <div className="text-xs text-outline uppercase font-mono mb-1">System Recommendation</div>
                                  <pre className="text-on-surface text-xs bg-white/[0.04] rounded-lg p-3 overflow-auto max-h-32">
                                    {e.system_recommendation
                                      ? JSON.stringify(e.system_recommendation, null, 2)
                                      : "—"}
                                  </pre>
                                </div>
                                <div>
                                  <div className="text-xs text-outline uppercase font-mono mb-1">Actual Action</div>
                                  <pre className="text-on-surface text-xs bg-white/[0.04] rounded-lg p-3 overflow-auto max-h-32">
                                    {e.actual_action
                                      ? JSON.stringify(e.actual_action, null, 2)
                                      : "—"}
                                  </pre>
                                </div>
                              </div>
                              {e.signal_run_id && (
                                <div className="mt-2 text-xs text-outline font-mono">
                                  Signal run: {e.signal_run_id}
                                </div>
                              )}
                            </td>
                          </tr>
                        )}
                      </>
                    );
                  })}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="px-6 py-4 border-t border-white/5 flex items-center justify-between text-sm text-on-surface-variant">
              <span className="font-mono">
                Showing {page * PAGE_SIZE + 1}–{Math.min((page + 1) * PAGE_SIZE, entries.length)} of {entries.length}
              </span>
              <div className="flex gap-2">
                <button
                  disabled={page === 0}
                  onClick={() => setPage((p) => p - 1)}
                  className="px-3 py-1 rounded-lg border border-white/10 bg-white/[0.03] hover:bg-white/[0.06] disabled:opacity-30 transition-all"
                >
                  ← Prev
                </button>
                <button
                  disabled={page >= totalPages - 1}
                  onClick={() => setPage((p) => p + 1)}
                  className="px-3 py-1 rounded-lg border border-white/10 bg-white/[0.03] hover:bg-white/[0.06] disabled:opacity-30 transition-all"
                >
                  Next →
                </button>
              </div>
            </div>
          )}
        </div>

        {/* ── AI Behavioral Insight ── */}
        <div
          className={`${glass} p-8 relative overflow-hidden border-l-2 border-secondary`}
          style={{ boxShadow: "0 0 30px rgba(208,188,255,0.07)" }}
        >
          <div className="flex flex-col md:flex-row gap-8">
            <div className="md:w-1/3 space-y-4">
              <div className="flex items-center gap-3">
                <span className="text-secondary text-2xl">🧠</span>
                <h4 className="text-xl font-bold">Behavioral Insight</h4>
              </div>
              <div className="p-4 bg-secondary/5 rounded-xl border border-secondary/10">
                <p className="text-xs text-secondary font-mono uppercase mb-1">System vs Override</p>
                <p className="text-2xl font-bold font-mono">
                  {delta90 != null ? pct(delta90) : "—"}
                </p>
                <p className="text-xs text-outline mt-1">90d system outperformance</p>
              </div>
              <div className="p-4 bg-white/[0.03] rounded-xl border border-white/5">
                <p className="text-xs text-outline font-mono uppercase mb-1">Total Decisions</p>
                <p className="text-2xl font-bold font-mono">
                  {stats?.total_decisions ?? "—"}
                </p>
              </div>
            </div>

            <div className="flex-1">
              <h5 className="text-secondary font-mono text-xs uppercase tracking-widest mb-4">
                AI Analysis
              </h5>
              {loading ? (
                <div className="space-y-3">
                  {[1,2,3].map(i => (
                    <div key={i} className="h-4 rounded bg-white/5 animate-pulse" style={{ width: `${85 - i * 10}%` }} />
                  ))}
                </div>
              ) : insight?.has_enough_data ? (
                <p className="text-on-surface leading-relaxed text-sm max-w-2xl">
                  {insight.insight}
                </p>
              ) : (
                <p className="text-outline text-sm italic">
                  {insight
                    ? "Not enough data yet — make more decisions and check back after 10+ entries."
                    : "AI insight unavailable. Check API connection."}
                </p>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
