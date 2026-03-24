"use client";

/**
 * /reports — Generate and download monthly/annual PDF reports.
 * Phase 9.
 */

import { useEffect, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const glass = "rounded-2xl border border-white/[0.08] bg-white/[0.04] backdrop-blur-sm";

interface ReportRecord {
  id: string;
  report_type: string;
  year: number;
  month: number | null;
  status: string;
  size_bytes: number | null;
  created_at: string;
  download_url: string | null;
}

const MONTH_NAMES = [
  "", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];

const STATUS_STYLES: Record<string, { text: string; bg: string; border: string }> = {
  ready:      { text: "text-emerald-400", bg: "bg-emerald-500/10", border: "border-emerald-500/20" },
  generating: { text: "text-amber-400",   bg: "bg-amber-500/10",   border: "border-amber-500/20"   },
  pending:    { text: "text-slate-400",   bg: "bg-white/[0.04]",   border: "border-white/10"        },
  error:      { text: "text-rose-400",    bg: "bg-rose-500/10",    border: "border-rose-500/20"     },
};

export default function ReportsPage() {
  const [reports, setReports]         = useState<ReportRecord[]>([]);
  const [loading, setLoading]         = useState(true);
  const [loadError, setLoadError]     = useState<string | null>(null);
  const [generating, setGenerating]   = useState(false);
  const [showModal, setShowModal]     = useState(false);
  const [genType, setGenType]         = useState<"monthly" | "annual">("monthly");
  const [genYear, setGenYear]         = useState(new Date().getFullYear());
  const [genMonth, setGenMonth]       = useState(new Date().getMonth() + 1);
  const [genMsg, setGenMsg]           = useState<string | null>(null);
  const [pollId, setPollId]           = useState<string | null>(null);

  const loadReports = async () => {
    setLoadError(null);
    try {
      const res = await fetch(`${API_URL}/reports/list`);
      if (res.ok) setReports(await res.json());
      else throw new Error(`API ${res.status}: /reports/list`);
    } catch (e) {
      setLoadError(e instanceof Error ? e.message : "Failed to load reports");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadReports(); }, []);

  // Poll for task completion
  useEffect(() => {
    if (!pollId) return;
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`${API_URL}/reports/result/${pollId}`);
        if (!res.ok) return;
        const data = await res.json();
        if (data.status === "ready" || data.status === "error") {
          clearInterval(interval);
          setPollId(null);
          setGenerating(false);
          setGenMsg(
            data.status === "ready"
              ? `Report ready! Download below.`
              : `Generation failed: ${data.error ?? "unknown error"}`
          );
          loadReports();
        }
      } catch {
        /* silent */
      }
    }, 2000);
    return () => clearInterval(interval);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pollId]);

  const handleGenerate = async () => {
    setGenerating(true);
    setGenMsg(null);
    try {
      const body = {
        report_type: genType,
        year: genYear,
        month: genType === "monthly" ? genMonth : undefined,
      };
      const res = await fetch(`${API_URL}/reports/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setPollId(data.task_id);
      setShowModal(false);
      setGenMsg(`Generating report… (task ${data.task_id.slice(0, 8)})`);
    } catch (e) {
      setGenerating(false);
      setGenMsg(e instanceof Error ? e.message : "Generation failed");
    }
  };

  const currentYear = new Date().getFullYear();
  const years = Array.from({ length: 5 }, (_, i) => currentYear - i);

  return (
    <div className="min-h-screen bg-[#050508] text-slate-100">
      <div className="fixed top-[-10%] right-[-10%] w-[400px] h-[400px] bg-violet-500/5 blur-[100px] rounded-full pointer-events-none -z-10" />

      <div className="p-8 space-y-8">
        {/* Header */}
        <div className="flex items-end justify-between">
          <div>
            <h1 className="text-4xl font-black tracking-tight text-slate-100 uppercase">
              Reports
            </h1>
            <p className="text-slate-400 mt-1 text-sm">
              Generate and download monthly or annual PDF reports.
            </p>
          </div>
          <button
            onClick={() => setShowModal(true)}
            className="px-5 py-2.5 rounded-xl bg-emerald-500 text-emerald-950 text-sm font-bold hover:bg-emerald-400 transition-all shadow-[0_0_12px_rgba(16,185,129,0.3)]"
          >
            + Generate Report
          </button>
        </div>

        {genMsg && (
          <div className={`text-sm rounded-xl px-4 py-2 border ${
            genMsg.includes("ready") ? "text-emerald-400 bg-emerald-500/10 border-emerald-500/20"
            : genMsg.includes("failed") || genMsg.includes("error") ? "text-rose-400 bg-rose-500/10 border-rose-500/20"
            : "text-slate-300 bg-white/[0.04] border-white/10"
          }`}>
            {genMsg}
          </div>
        )}

        {loadError && (
          <div className="rounded-xl border border-rose-500/20 bg-rose-500/10 px-4 py-3 text-rose-400 text-sm flex items-center justify-between">
            <span>{loadError}</span>
            <button onClick={loadReports} className="text-rose-300 hover:text-rose-100 underline text-xs">Retry</button>
          </div>
        )}

        {/* Reports List */}
        <div className={glass}>
          <div className="p-6 border-b border-white/5">
            <h3 className="font-bold text-lg">Generated Reports</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="text-[10px] uppercase tracking-widest text-slate-500 font-mono border-b border-white/5">
                  <th className="px-6 py-4 font-normal">Period</th>
                  <th className="px-6 py-4 font-normal">Type</th>
                  <th className="px-6 py-4 font-normal">Status</th>
                  <th className="px-6 py-4 font-normal text-right">Size</th>
                  <th className="px-6 py-4 font-normal">Generated</th>
                  <th className="px-6 py-4 font-normal"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.04]">
                {loading && Array.from({ length: 3 }).map((_, i) => (
                  <tr key={i}>
                    {Array.from({ length: 6 }).map((_, j) => (
                      <td key={j} className="px-6 py-4">
                        <div className="h-4 rounded bg-white/5 animate-pulse" />
                      </td>
                    ))}
                  </tr>
                ))}
                {!loading && reports.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-6 py-12 text-center text-slate-500 text-sm">
                      No reports yet. Click "Generate Report" to create your first PDF.
                    </td>
                  </tr>
                )}
                {!loading && reports.map((r) => {
                  const style = STATUS_STYLES[r.status] ?? STATUS_STYLES.pending;
                  const period = r.report_type === "annual"
                    ? `${r.year} Annual`
                    : `${MONTH_NAMES[r.month ?? 1]} ${r.year}`;
                  const sizeKb = r.size_bytes ? `${(r.size_bytes / 1024).toFixed(0)} KB` : "—";
                  const createdAt = new Date(r.created_at).toLocaleDateString("en-US", {
                    month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
                  });
                  return (
                    <tr key={r.id} className="hover:bg-white/[0.025] transition-colors">
                      <td className="px-6 py-4 font-mono text-sm text-slate-200">{period}</td>
                      <td className="px-6 py-4 text-sm text-slate-400 capitalize">{r.report_type}</td>
                      <td className="px-6 py-4">
                        <span className={`px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider border ${style.bg} ${style.text} ${style.border}`}>
                          {r.status}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-right font-mono text-sm text-slate-400">{sizeKb}</td>
                      <td className="px-6 py-4 text-sm font-mono text-slate-400">{createdAt}</td>
                      <td className="px-6 py-4 text-right">
                        {r.status === "ready" && r.download_url ? (
                          <a
                            href={`${API_URL}${r.download_url}`}
                            target="_blank"
                            rel="noreferrer"
                            className="px-3 py-1.5 rounded-lg bg-white/[0.04] border border-white/10 text-xs text-slate-300 hover:bg-white/[0.08] transition-all"
                          >
                            ↓ Download
                          </a>
                        ) : (
                          <span className="text-xs text-slate-600">—</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Generate Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className={`${glass} p-8 w-full max-w-md space-y-6`}>
            <h2 className="text-xl font-bold">Generate PDF Report</h2>

            {/* Report type */}
            <div>
              <label className="block text-xs font-mono uppercase text-slate-500 mb-2">Report Type</label>
              <div className="flex gap-3">
                {(["monthly", "annual"] as const).map((t) => (
                  <button
                    key={t}
                    onClick={() => setGenType(t)}
                    className={`flex-1 py-2 rounded-xl border text-sm font-medium transition-all capitalize ${
                      genType === t
                        ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-400"
                        : "bg-white/[0.03] border-white/10 text-slate-400 hover:bg-white/[0.06]"
                    }`}
                  >
                    {t}
                  </button>
                ))}
              </div>
            </div>

            {/* Year */}
            <div>
              <label className="block text-xs font-mono uppercase text-slate-500 mb-2">Year</label>
              <select
                value={genYear}
                onChange={(e) => setGenYear(Number(e.target.value))}
                className="w-full rounded-xl bg-white/[0.04] border border-white/10 text-slate-200 px-4 py-2.5 text-sm focus:outline-none focus:border-emerald-500/50"
              >
                {years.map((y) => <option key={y} value={y}>{y}</option>)}
              </select>
            </div>

            {/* Month (monthly only) */}
            {genType === "monthly" && (
              <div>
                <label className="block text-xs font-mono uppercase text-slate-500 mb-2">Month</label>
                <select
                  value={genMonth}
                  onChange={(e) => setGenMonth(Number(e.target.value))}
                  className="w-full rounded-xl bg-white/[0.04] border border-white/10 text-slate-200 px-4 py-2.5 text-sm focus:outline-none focus:border-emerald-500/50"
                >
                  {MONTH_NAMES.slice(1).map((m, i) => (
                    <option key={i + 1} value={i + 1}>{m}</option>
                  ))}
                </select>
              </div>
            )}

            {/* Actions */}
            <div className="flex gap-3">
              <button
                onClick={() => setShowModal(false)}
                className="flex-1 py-2.5 rounded-xl border border-white/10 bg-white/[0.03] text-sm text-slate-400 hover:bg-white/[0.06] transition-all"
              >
                Cancel
              </button>
              <button
                onClick={handleGenerate}
                disabled={generating}
                className="flex-1 py-2.5 rounded-xl bg-emerald-500 text-emerald-950 text-sm font-bold hover:bg-emerald-400 transition-all disabled:opacity-50"
              >
                {generating ? "Generating…" : "Generate"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
