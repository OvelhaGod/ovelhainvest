"use client";

/**
 * /journal — Decision log, override accuracy scorecard, pattern analysis.
 * Phase 5: live data from /journal and /journal/stats API endpoints.
 */

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";

// ── Design tokens ─────────────────────────────────────────────────────────────
const glass = "rounded-2xl border border-white/[0.08] bg-white/[0.03] backdrop-blur-sm";

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

// ── Helpers ───────────────────────────────────────────────────────────────────
function fmtPct(n: number | null | undefined, decimals = 1): string {
  if (n == null) return "—";
  const sign = n >= 0 ? "+" : "";
  return `${sign}${(n * 100).toFixed(decimals)}%`;
}

function fmtDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "2-digit" });
}

function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse rounded bg-white/[0.06] ${className}`} />;
}

// ── Action badge ─────────────────────────────────────────────────────────────
const ACTION_CONFIG = {
  followed:     { label: "Followed",     color: "#10b981" },
  overrode:     { label: "Overrode",     color: "#f43f5e" },
  deferred:     { label: "Deferred",     color: "#f59e0b" },
  manual_trade: { label: "Manual",       color: "#8b5cf6" },
} as const;

function ActionBadge({ type }: { type: keyof typeof ACTION_CONFIG }) {
  const cfg = ACTION_CONFIG[type] ?? ACTION_CONFIG.manual_trade;
  return (
    <span
      className="text-[10px] font-medium px-2 py-0.5 rounded-full border"
      style={{ color: cfg.color, background: `${cfg.color}14`, borderColor: `${cfg.color}30` }}
    >
      {cfg.label}
    </span>
  );
}

// ── Outcome cell ─────────────────────────────────────────────────────────────
function OutcomeCell({ value }: { value: number | null }) {
  if (value == null) return <span className="text-white/20 font-mono text-xs">—</span>;
  const positive = value >= 0;
  return (
    <span
      className="font-mono text-xs font-medium"
      style={{ color: positive ? "#10b981" : "#ef4444" }}
    >
      {fmtPct(value)}
    </span>
  );
}

// ── Log Decision Modal ────────────────────────────────────────────────────────
function LogDecisionModal({ onClose, onSaved }: { onClose: () => void; onSaved: () => void }) {
  const [actionType, setActionType] = useState<string>("followed");
  const [reasoning, setReasoning] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSave() {
    if (!reasoning.trim()) { setError("Reasoning is required"); return; }
    setSaving(true);
    setError(null);
    try {
      await api.createJournalEntry({ action_type: actionType, reasoning: reasoning.trim() });
      onSaved();
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className={`${glass} p-6 w-full max-w-md space-y-4`}>
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-white/90">Log Decision</h2>
          <button onClick={onClose} className="text-white/40 hover:text-white/70 text-lg">×</button>
        </div>

        <div>
          <label className="text-[10px] text-white/40 uppercase tracking-widest block mb-2">Action Type</label>
          <div className="flex gap-2 flex-wrap">
            {(["followed", "overrode", "deferred", "manual_trade"] as const).map((t) => {
              const cfg = ACTION_CONFIG[t];
              return (
                <button
                  key={t}
                  onClick={() => setActionType(t)}
                  className="px-3 py-1.5 text-xs rounded-lg border transition-all"
                  style={{
                    color: cfg.color,
                    background: actionType === t ? `${cfg.color}20` : "transparent",
                    borderColor: actionType === t ? `${cfg.color}50` : "rgba(255,255,255,0.08)",
                  }}
                >
                  {cfg.label}
                </button>
              );
            })}
          </div>
        </div>

        <div>
          <label className="text-[10px] text-white/40 uppercase tracking-widest block mb-2">Reasoning</label>
          <textarea
            value={reasoning}
            onChange={(e) => setReasoning(e.target.value)}
            placeholder="Why did you follow, override, or defer the system recommendation?"
            rows={4}
            className="w-full text-xs text-white/80 bg-white/[0.04] border border-white/[0.08] rounded-lg px-3 py-2 resize-none outline-none focus:border-violet-500/40 placeholder:text-white/20"
          />
        </div>

        {error && <p className="text-xs text-rose-400">{error}</p>}

        <div className="flex gap-3 justify-end pt-1">
          <button
            onClick={onClose}
            className="px-4 py-2 text-xs text-white/50 hover:text-white/70 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-4 py-2 text-xs font-medium rounded-lg transition-all"
            style={{ background: "rgba(139,92,246,0.2)", color: "#a78bfa", border: "1px solid rgba(139,92,246,0.35)" }}
          >
            {saving ? "Saving…" : "Save Entry"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Override Accuracy Scorecard ───────────────────────────────────────────────
function AccuracyScorecard({ stats, loading }: { stats: JournalStats | null; loading: boolean }) {
  if (loading) {
    return (
      <div className="grid grid-cols-2 gap-4">
        <Skeleton className="h-32" />
        <Skeleton className="h-32" />
      </div>
    );
  }

  const followedAvg90 = stats?.avg_outcome_followed_90d;
  const overrodeAvg90 = stats?.avg_outcome_overrode_90d;
  const outperf90 = stats?.system_outperformance_90d;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
      {/* Followed card */}
      <div
        className={`${glass} p-5`}
        style={{ boxShadow: "0 0 30px rgba(16,185,129,0.08)", borderColor: "rgba(16,185,129,0.2)" }}
      >
        <div className="flex items-center gap-2 mb-3">
          <span className="text-base">✓</span>
          <p className="text-xs font-medium text-white/70">When You Followed the System</p>
        </div>
        <p
          className="text-3xl font-bold font-mono"
          style={{ color: followedAvg90 != null && followedAvg90 >= 0 ? "#10b981" : "#ef4444" }}
        >
          {fmtPct(followedAvg90)}
        </p>
        <p className="text-[10px] text-white/40 mt-1">avg 90-day outcome</p>
        <div className="flex gap-3 mt-3 pt-3 border-t border-white/[0.06]">
          <div>
            <p className="text-[10px] text-white/30">Count</p>
            <p className="text-sm font-mono text-white/70">{stats?.followed_count ?? "—"}</p>
          </div>
          <div>
            <p className="text-[10px] text-white/30">30d avg</p>
            <p className="text-sm font-mono" style={{ color: "#10b981" }}>{fmtPct(stats?.avg_outcome_followed_30d)}</p>
          </div>
        </div>
      </div>

      {/* Overrode card */}
      <div
        className={`${glass} p-5`}
        style={{ boxShadow: "0 0 30px rgba(245,158,11,0.08)", borderColor: "rgba(245,158,11,0.2)" }}
      >
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <span className="text-base">⚠</span>
            <p className="text-xs font-medium text-white/70">When You Overrode the System</p>
          </div>
          {outperf90 != null && (
            <span
              className="text-[10px] px-2 py-0.5 rounded-full border font-mono"
              style={{
                color: outperf90 >= 0 ? "#10b981" : "#ef4444",
                background: outperf90 >= 0 ? "rgba(16,185,129,0.1)" : "rgba(239,68,68,0.1)",
                borderColor: outperf90 >= 0 ? "rgba(16,185,129,0.25)" : "rgba(239,68,68,0.25)",
              }}
            >
              System {outperf90 >= 0 ? "+" : ""}{fmtPct(outperf90)} vs overrides
            </span>
          )}
        </div>
        <p
          className="text-3xl font-bold font-mono"
          style={{ color: overrodeAvg90 != null && overrodeAvg90 >= 0 ? "#10b981" : "#f59e0b" }}
        >
          {fmtPct(overrodeAvg90)}
        </p>
        <p className="text-[10px] text-white/40 mt-1">avg 90-day outcome</p>
        <div className="flex gap-3 mt-3 pt-3 border-t border-white/[0.06]">
          <div>
            <p className="text-[10px] text-white/30">Count</p>
            <p className="text-sm font-mono text-white/70">{stats?.overrode_count ?? "—"}</p>
          </div>
          <div>
            <p className="text-[10px] text-white/30">30d avg</p>
            <p className="text-sm font-mono" style={{ color: "#f59e0b" }}>{fmtPct(stats?.avg_outcome_overrode_30d)}</p>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Pattern Analysis Card ─────────────────────────────────────────────────────
function PatternCard({ stats }: { stats: JournalStats | null }) {
  if (!stats || stats.total_decisions < 5) {
    return (
      <div
        className={`${glass} p-4`}
        style={{ borderLeft: "2px solid rgba(139,92,246,0.4)" }}
      >
        <p className="text-[10px] text-violet-400 uppercase tracking-widest mb-2">✦ AI Behavioral Analysis</p>
        <p className="text-xs text-white/40">
          Log at least 5 decisions to unlock pattern analysis. Currently {stats?.total_decisions ?? 0} decision{stats?.total_decisions === 1 ? "" : "s"} tracked.
        </p>
      </div>
    );
  }

  const outperf = stats.system_outperformance_90d;
  const systemWins = outperf != null && outperf > 0;

  return (
    <div
      className={`${glass} p-4`}
      style={{ borderLeft: "2px solid rgba(139,92,246,0.4)" }}
    >
      <p className="text-[10px] text-violet-400 uppercase tracking-widest mb-2">✦ Behavioral Pattern Summary</p>
      <p className="text-xs text-white/65 leading-relaxed">
        {systemWins
          ? `The system outperformed your overrides by ${fmtPct(outperf)} on a 90-day horizon (${stats.followed_count} followed vs ${stats.overrode_count} overrode). Consider trusting the engine more during high-conviction signals.`
          : `Your overrides have outperformed the system by ${fmtPct(Math.abs(outperf ?? 0))} on a 90-day basis. ${stats.overrode_count} overrides tracked — your judgment is adding alpha.`
        }
        {" "}You&apos;ve deferred {stats.deferred_count} time{stats.deferred_count !== 1 ? "s" : ""} and executed {stats.manual_count} manual trade{stats.manual_count !== 1 ? "s" : ""} outside the system.
      </p>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────
export default function JournalPage() {
  const [entries, setEntries] = useState<JournalEntry[]>([]);
  const [stats, setStats] = useState<JournalStats | null>(null);
  const [loadingEntries, setLoadingEntries] = useState(true);
  const [loadingStats, setLoadingStats] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionFilter, setActionFilter] = useState<string>("all");
  const [showModal, setShowModal] = useState(false);
  const [offset, setOffset] = useState(0);
  const PAGE_SIZE = 25;

  const loadEntries = useCallback(async () => {
    setLoadingEntries(true);
    try {
      const data = await api.listJournal({
        limit: PAGE_SIZE,
        offset,
        action_type: actionFilter !== "all" ? actionFilter : undefined,
      });
      setEntries(data as unknown as JournalEntry[]);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load journal");
    } finally {
      setLoadingEntries(false);
    }
  }, [offset, actionFilter]);

  const loadStats = useCallback(async () => {
    setLoadingStats(true);
    try {
      const data = await api.journalStats();
      setStats(data as unknown as JournalStats);
    } catch {
      // stats are optional — don't block the page
    } finally {
      setLoadingStats(false);
    }
  }, []);

  useEffect(() => { loadEntries(); }, [loadEntries]);
  useEffect(() => { loadStats(); }, [loadStats]);

  function handleSaved() {
    loadEntries();
    loadStats();
  }

  return (
    <div className="min-h-screen p-6 space-y-5" style={{ background: "#050508" }}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-white/95 tracking-tight">Decision Journal</h1>
          <p className="text-xs text-white/40 mt-0.5">
            {stats?.total_decisions ?? "—"} decisions tracked · override accuracy analytics
          </p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="px-4 py-2 text-xs font-medium rounded-lg transition-all"
          style={{ background: "rgba(139,92,246,0.15)", color: "#a78bfa", border: "1px solid rgba(139,92,246,0.3)" }}
        >
          + Log Decision
        </button>
      </div>

      {/* Override accuracy scorecard */}
      <AccuracyScorecard stats={stats} loading={loadingStats} />

      {/* Pattern analysis */}
      <PatternCard stats={stats} />

      {/* Decision log table */}
      <div className={glass}>
        {/* Filter bar */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-white/[0.06]">
          <p className="text-[10px] text-white/30 uppercase tracking-widest">Decision Log</p>
          <select
            value={actionFilter}
            onChange={(e) => { setActionFilter(e.target.value); setOffset(0); }}
            className="text-[10px] px-2 py-1 rounded-lg border border-white/[0.08] bg-white/[0.03] text-white/60 outline-none"
          >
            <option value="all">All Actions</option>
            <option value="followed">Followed</option>
            <option value="overrode">Overrode</option>
            <option value="deferred">Deferred</option>
            <option value="manual_trade">Manual</option>
          </select>
        </div>

        {/* Table header */}
        <div className="grid grid-cols-12 gap-3 px-4 py-2 border-b border-white/[0.04]">
          {[
            ["DATE",       "col-span-1"],
            ["ACTION",     "col-span-2"],
            ["ASSET",      "col-span-1"],
            ["REASONING",  "col-span-4"],
            ["SYS REC",    "col-span-1"],
            ["30D",        "col-span-1"],
            ["90D",        "col-span-1"],
            ["SIGNAL",     "col-span-1"],
          ].map(([label, span]) => (
            <div key={label} className={`text-[10px] font-medium text-white/25 uppercase tracking-widest ${span}`}>
              {label}
            </div>
          ))}
        </div>

        {/* Rows */}
        {loadingEntries ? (
          <div className="p-4 space-y-2">
            {Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-10 rounded-xl" />)}
          </div>
        ) : error ? (
          <div className="p-8 text-center">
            <p className="text-sm text-rose-400">⚠ {error}</p>
          </div>
        ) : entries.length === 0 ? (
          <div className="p-12 text-center">
            <p className="text-sm text-white/20">No journal entries yet</p>
            <p className="text-xs text-white/10 mt-1">Use the signals page to log decisions, or click &quot;Log Decision&quot; above.</p>
          </div>
        ) : (
          entries.map((entry) => (
            <div
              key={entry.id}
              className="grid grid-cols-12 gap-3 px-4 py-3 border-b border-white/[0.03] hover:bg-white/[0.015] transition-colors items-center"
            >
              {/* Date */}
              <div className="col-span-1 text-[10px] font-mono text-white/40">
                {fmtDate(entry.event_date)}
              </div>

              {/* Action badge */}
              <div className="col-span-2">
                <ActionBadge type={entry.action_type} />
              </div>

              {/* Asset */}
              <div className="col-span-1 text-xs font-mono text-white/50 truncate">
                {entry.asset_id ? entry.asset_id.slice(0, 8) + "…" : "—"}
              </div>

              {/* Reasoning */}
              <div className="col-span-4 text-xs text-white/50 truncate" title={entry.reasoning ?? undefined}>
                {entry.reasoning ?? <span className="text-white/20">—</span>}
              </div>

              {/* System recommendation summary */}
              <div className="col-span-1 text-[10px] text-white/30 truncate">
                {entry.system_recommendation
                  ? <span className="text-white/40">json</span>
                  : <span className="text-white/20">—</span>}
              </div>

              {/* 30d outcome */}
              <div className="col-span-1">
                <OutcomeCell value={entry.outcome_30d} />
              </div>

              {/* 90d outcome */}
              <div className="col-span-1">
                <OutcomeCell value={entry.outcome_90d} />
              </div>

              {/* Signal run link */}
              <div className="col-span-1 text-[10px] text-white/25 truncate">
                {entry.signal_run_id
                  ? <span className="text-violet-400/60">{entry.signal_run_id.slice(0, 8)}…</span>
                  : "—"}
              </div>
            </div>
          ))
        )}

        {/* Pagination */}
        {entries.length === PAGE_SIZE && (
          <div className="px-4 py-3 flex justify-end">
            <button
              onClick={() => setOffset((o) => o + PAGE_SIZE)}
              className="text-[10px] text-white/40 hover:text-white/60 transition-colors px-3 py-1 rounded-lg border border-white/[0.06] hover:border-white/[0.12]"
            >
              Load more →
            </button>
          </div>
        )}
        {offset > 0 && (
          <div className="px-4 py-1 flex justify-start">
            <button
              onClick={() => setOffset((o) => Math.max(0, o - PAGE_SIZE))}
              className="text-[10px] text-white/40 hover:text-white/60 transition-colors"
            >
              ← Back
            </button>
          </div>
        )}
      </div>

      {/* Log Decision modal */}
      {showModal && <LogDecisionModal onClose={() => setShowModal(false)} onSaved={handleSaved} />}
    </div>
  );
}
