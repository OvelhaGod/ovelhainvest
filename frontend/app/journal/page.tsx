"use client";

/**
 * /journal — Decision log, override accuracy scorecard, behavioral patterns, AI insight.
 * Phase 9: full implementation with backfill trigger, CSV export, pagination.
 */

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";

// ── Design tokens ─────────────────────────────────────────────────────────────
const glass =
  "rounded-2xl border border-white/[0.08] bg-white/[0.04] backdrop-blur-sm";

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

const ACTION_STYLES: Record<string, { bg: string; text: string; border: string; label: string }> = {
  followed:     { bg: "bg-emerald-500/10", text: "text-emerald-400", border: "border-emerald-500/20", label: "Followed" },
  overrode:     { bg: "bg-rose-500/10",    text: "text-rose-400",    border: "border-rose-500/20",    label: "Overrode" },
  deferred:     { bg: "bg-amber-500/10",   text: "text-amber-400",   border: "border-amber-500/20",   label: "Deferred" },
  manual_trade: { bg: "bg-violet-500/10",  text: "text-violet-400",  border: "border-violet-500/20",  label: "Manual" },
};

const SEVERITY_COLORS: Record<string, string> = {
  high: "text-rose-400",
  medium: "text-amber-400",
  low: "text-slate-400",
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
    <div className="min-h-screen bg-[#050508] text-slate-100">
      {/* Ambient glows */}
      <div className="fixed top-[-10%] right-[-10%] w-[500px] h-[500px] bg-emerald-500/5 blur-[120px] rounded-full pointer-events-none -z-10" />
      <div className="fixed bottom-[-10%] left-[200px] w-[400px] h-[400px] bg-violet-500/5 blur-[100px] rounded-full pointer-events-none -z-10" />

      <div className="p-8 space-y-8">
        {/* Header */}
        <div className="flex items-end justify-between">
          <div>
            <h1 className="text-4xl font-black tracking-tight text-slate-100 uppercase">
              Decision Journal
            </h1>
            <p className="text-slate-400 mt-1 text-sm">
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
          <div className="text-sm text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 rounded-xl px-4 py-2">
            {backfillMsg}
          </div>
        )}

        {error && (
          <div className="rounded-xl border border-rose-500/20 bg-rose-500/10 px-4 py-3 text-rose-400 text-sm flex items-center justify-between">
            <span>{error}</span>
            <button onClick={load} className="text-rose-300 hover:text-rose-100 underline text-xs">Retry</button>
          </div>
        )}

        {/* ── Accuracy Scorecard ── */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Followed System */}
          <div className={`${glass} p-8 border-l-4 border-l-emerald-500`}
               style={{ boxShadow: "0 0 20px rgba(16,185,129,0.08)" }}>
            <div className="flex justify-between items-start mb-6">
              <div>
                <span className="text-[10px] font-mono uppercase tracking-[0.2em] text-emerald-400">
                  Fidelity Protocol
                </span>
                <h3 className="text-xl font-bold mt-1">Followed System</h3>
              </div>
              <span className="text-2xl p-2 rounded-lg bg-emerald-500/10">✅</span>
            </div>
            {loading ? (
              <div className="h-16 w-32 rounded-lg bg-white/5 animate-pulse" />
            ) : (
              <>
                <div className="flex items-baseline gap-2">
                  <span className="text-6xl font-bold font-mono text-emerald-400 tracking-tighter">
                    {stats ? pct(stats.avg_outcome_followed_90d) : "—"}
                  </span>
                </div>
                <div className="mt-3 text-sm text-slate-400 font-mono">
                  {stats?.followed_count ?? 0} decisions · avg 30d: {pct(stats?.avg_outcome_followed_30d ?? null)}
                </div>
              </>
            )}
          </div>

          {/* Overrode System */}
          <div className={`${glass} p-8 border-l-4 border-l-amber-400`}>
            <div className="flex justify-between items-start mb-6">
              <div>
                <span className="text-[10px] font-mono uppercase tracking-[0.2em] text-amber-400">
                  Manual Deviation
                </span>
                <h3 className="text-xl font-bold mt-1">Overrode System</h3>
              </div>
              <span className="text-2xl p-2 rounded-lg bg-amber-500/10">⚠️</span>
            </div>
            {loading ? (
              <div className="h-16 w-32 rounded-lg bg-white/5 animate-pulse" />
            ) : (
              <>
                <div className="flex items-baseline gap-2">
                  <span className="text-6xl font-bold font-mono text-amber-400 tracking-tighter">
                    {stats ? pct(stats.avg_outcome_overrode_90d) : "—"}
                  </span>
                </div>
                <div className="mt-3 text-sm text-slate-400 font-mono">
                  {stats?.overrode_count ?? 0} overrides · avg 30d: {pct(stats?.avg_outcome_overrode_30d ?? null)}
                </div>
                {delta30 != null && (
                  <div className={`mt-2 text-sm font-mono font-semibold ${delta30 >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
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
                    <div className="text-sm font-medium text-slate-200">{p.description}</div>
                    <div className="text-xs text-slate-500 font-mono mt-1">
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
                <tr className="text-[10px] uppercase tracking-widest text-slate-500 font-mono border-b border-white/5">
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
                    <td colSpan={6} className="px-6 py-12 text-center text-slate-500 text-sm">
                      No journal entries yet. Decisions will appear here after your first allocation run.
                    </td>
                  </tr>
                )}
                {!loading &&
                  pageEntries.map((e) => {
                    const style = ACTION_STYLES[e.action_type] ?? ACTION_STYLES.manual_trade;
                    const isExpanded = expandedRow === e.id;
                    const out30Color =
                      e.outcome_30d == null ? "text-slate-500"
                      : e.outcome_30d >= 0 ? "text-emerald-400"
                      : "text-rose-400";
                    const out90Color =
                      e.outcome_90d == null ? "text-slate-500"
                      : e.outcome_90d >= 0 ? "text-emerald-400"
                      : "text-rose-400";

                    return (
                      <>
                        <tr
                          key={e.id}
                          onClick={() => setExpanded(isExpanded ? null : e.id)}
                          className="hover:bg-white/[0.025] transition-colors cursor-pointer"
                        >
                          <td className="px-6 py-4 text-sm text-slate-400 font-mono whitespace-nowrap">
                            {fmtDate(e.event_date)}
                          </td>
                          <td className="px-6 py-4">
                            <span
                              className={`px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider border ${style.bg} ${style.text} ${style.border}`}
                            >
                              {style.label}
                            </span>
                          </td>
                          <td className="px-6 py-4 font-mono text-sm text-slate-300">
                            {e.asset_id ? e.asset_id.slice(0, 8) + "…" : "—"}
                          </td>
                          <td className="px-6 py-4 text-sm text-slate-400 max-w-[300px] truncate italic">
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
                                  <div className="text-xs text-slate-500 uppercase font-mono mb-1">System Recommendation</div>
                                  <pre className="text-slate-300 text-xs bg-white/[0.04] rounded-lg p-3 overflow-auto max-h-32">
                                    {e.system_recommendation
                                      ? JSON.stringify(e.system_recommendation, null, 2)
                                      : "—"}
                                  </pre>
                                </div>
                                <div>
                                  <div className="text-xs text-slate-500 uppercase font-mono mb-1">Actual Action</div>
                                  <pre className="text-slate-300 text-xs bg-white/[0.04] rounded-lg p-3 overflow-auto max-h-32">
                                    {e.actual_action
                                      ? JSON.stringify(e.actual_action, null, 2)
                                      : "—"}
                                  </pre>
                                </div>
                              </div>
                              {e.signal_run_id && (
                                <div className="mt-2 text-xs text-slate-500 font-mono">
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
            <div className="px-6 py-4 border-t border-white/5 flex items-center justify-between text-sm text-slate-400">
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
          className={`${glass} p-8 relative overflow-hidden`}
          style={{ borderLeft: "3px solid #8b5cf6", boxShadow: "0 0 30px rgba(139,92,246,0.07)" }}
        >
          <div className="flex flex-col md:flex-row gap-8">
            <div className="md:w-1/3 space-y-4">
              <div className="flex items-center gap-3">
                <span className="text-violet-400 text-2xl">🧠</span>
                <h4 className="text-xl font-bold">Behavioral Insight</h4>
              </div>
              <div className="p-4 bg-violet-500/5 rounded-xl border border-violet-500/10">
                <p className="text-xs text-violet-400 font-mono uppercase mb-1">System vs Override</p>
                <p className="text-2xl font-bold font-mono">
                  {delta90 != null ? pct(delta90) : "—"}
                </p>
                <p className="text-xs text-slate-500 mt-1">90d system outperformance</p>
              </div>
              <div className="p-4 bg-white/[0.03] rounded-xl border border-white/5">
                <p className="text-xs text-slate-500 font-mono uppercase mb-1">Total Decisions</p>
                <p className="text-2xl font-bold font-mono">
                  {stats?.total_decisions ?? "—"}
                </p>
              </div>
            </div>

            <div className="flex-1">
              <h5 className="text-violet-400 font-mono text-xs uppercase tracking-widest mb-4">
                AI Analysis
              </h5>
              {loading ? (
                <div className="space-y-3">
                  {[1,2,3].map(i => (
                    <div key={i} className="h-4 rounded bg-white/5 animate-pulse" style={{ width: `${85 - i * 10}%` }} />
                  ))}
                </div>
              ) : insight?.has_enough_data ? (
                <p className="text-slate-300 leading-relaxed text-sm max-w-2xl">
                  {insight.insight}
                </p>
              ) : (
                <p className="text-slate-500 text-sm italic">
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
