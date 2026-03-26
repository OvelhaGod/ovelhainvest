"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type NewsItem = {
  headline?: string;
  summary?: string;
  url?: string;
  source?: string;
  published_at?: string;
  category?: string;
  related_symbol?: string;
  importance_score?: number | null;
};

type EarningsEvent = {
  symbol?: string;
  date?: string;
  eps_estimate?: number | null;
  revenue_estimate?: number | null;
  eps_actual?: number | null;
};

function GlassCard({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`glass-card p-5 ${className}`}>
      {children}
    </div>
  );
}

function importanceBadge(score: number | null | undefined): { label: string; color: string; bg: string; border: string } {
  if (score == null || score < 3) return { label: "General", color: "#475569", bg: "rgba(71,85,105,0.12)", border: "rgba(71,85,105,0.2)" };
  if (score < 6) return { label: "Relevant", color: "#6366f1", bg: "rgba(99,102,241,0.12)", border: "rgba(99,102,241,0.25)" };
  return { label: "High Impact", color: "#10b981", bg: "rgba(16,185,129,0.12)", border: "rgba(16,185,129,0.3)" };
}

function timeAgo(iso: string | undefined): string {
  if (!iso) return "";
  const ms = Date.now() - new Date(iso).getTime();
  const h = Math.floor(ms / 3_600_000);
  if (h < 1) return "< 1h ago";
  if (h < 24) return `${h}h ago`;
  const d = Math.floor(h / 24);
  return `${d}d ago`;
}

function fmtDate(iso: string | undefined): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric" });
  } catch {
    return iso;
  }
}

function fmtNum(v: number | null | undefined): string {
  if (v == null) return "—";
  return v.toFixed(2);
}

export default function ResearchPage() {
  const [news, setNews] = useState<NewsItem[]>([]);
  const [earnings, setEarnings] = useState<EarningsEvent[]>([]);
  const [loadingNews, setLoadingNews] = useState(true);
  const [loadingEarnings, setLoadingEarnings] = useState(true);
  const [newsError, setNewsError] = useState<string | null>(null);
  const [earningsError, setEarningsError] = useState<string | null>(null);
  const [expandedIdx, setExpandedIdx] = useState<number | null>(null);
  const [aiSummaries, setAiSummaries] = useState<Record<number, string>>({});
  const [aiLoading, setAiLoading] = useState<Record<number, boolean>>({});
  const [filterRelevance, setFilterRelevance] = useState<"all" | "relevant" | "high">("all");

  useEffect(() => {
    api.newsFeed({ limit: 40 })
      .then((items) => setNews(items as unknown as NewsItem[]))
      .catch((e) => setNewsError(e.message))
      .finally(() => setLoadingNews(false));

    api.earningsCalendar()
      .then((events) => setEarnings(events as unknown as EarningsEvent[]))
      .catch((e) => setEarningsError(e.message))
      .finally(() => setLoadingEarnings(false));
  }, []);

  return (
    <div className="p-5 space-y-5">
      {/* Header */}
      <div>
        <h1 className="text-xl font-semibold text-[#f1f5f9]">Research</h1>
        <p className="text-xs text-[#475569] mt-0.5">News · Earnings Calendar · Macro</p>
      </div>

      <div className="grid grid-cols-5 gap-5">
        {/* ── News Feed (left, 3/5 width) ─────────────────────────── */}
        <div className="col-span-3 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-semibold text-[#475569] uppercase tracking-wider">
              News Feed
            </h2>
            {/* Relevance filter */}
            <div className="flex gap-1">
              {(["all", "relevant", "high"] as const).map((f) => (
                <button
                  key={f}
                  onClick={() => setFilterRelevance(f)}
                  className={`px-2 py-0.5 text-[10px] rounded font-mono transition-colors capitalize ${
                    filterRelevance === f
                      ? "bg-white/[0.10] text-white/90"
                      : "text-white/30 hover:text-white/60"
                  }`}
                >
                  {f === "all" ? "All" : f === "relevant" ? "Relevant+" : "High Impact"}
                </button>
              ))}
            </div>
          </div>

          {loadingNews && (
            <div className="space-y-3">
              {[...Array(6)].map((_, i) => (
                <div key={i} className="glass-card p-4 space-y-2">
                  <div className="skeleton h-3 w-3/4 rounded" />
                  <div className="skeleton h-2 w-full rounded" />
                  <div className="skeleton h-2 w-1/2 rounded" />
                </div>
              ))}
            </div>
          )}

          {newsError && (
            <GlassCard>
              <p className="text-sm text-[#ef4444]">Failed to load news: {newsError}</p>
            </GlassCard>
          )}

          {!loadingNews && !newsError && news.length === 0 && (
            <GlassCard>
              <p className="text-sm text-[#475569] text-center py-4">
                No news available. Add a Finnhub API key to enable live news.
              </p>
            </GlassCard>
          )}

          {!loadingNews && news
            .filter((item) => {
              if (filterRelevance === "high") return (item.importance_score ?? 0) >= 6;
              if (filterRelevance === "relevant") return (item.importance_score ?? 0) >= 3;
              return true;
            })
            .map((item, i) => {
              const badge = importanceBadge(item.importance_score);
              const isExpanded = expandedIdx === i;
              const aiSummary = aiSummaries[i];
              const isAiLoading = aiLoading[i];

              return (
                <div
                  key={i}
                  className={`glass-card p-4 transition-all duration-200 group cursor-pointer ${isExpanded ? "ring-1 ring-white/[0.10]" : "hover:bg-white/[0.04]"}`}
                  onClick={() => setExpandedIdx(isExpanded ? null : i)}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1 min-w-0">
                      {/* Symbol badge + source + impact badge row */}
                      <div className="flex items-center gap-2 mb-1.5 flex-wrap">
                        {item.related_symbol && (
                          <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-indigo-500/15 text-indigo-400 border border-indigo-500/25 font-mono">
                            {item.related_symbol.replace("-USD", "")}
                          </span>
                        )}
                        {/* Impact badge */}
                        <span
                          className="text-[9px] font-semibold px-1.5 py-0.5 rounded border"
                          style={{ color: badge.color, background: badge.bg, borderColor: badge.border }}
                        >
                          {badge.label}
                        </span>
                        {item.source && (
                          <span className="text-[10px] text-[#475569]">{item.source}</span>
                        )}
                        <span className="text-[10px] text-[#334155] ml-auto">{timeAgo(item.published_at)}</span>
                      </div>

                      {/* Headline */}
                      <p className={`text-sm font-medium text-[#e2e8f0] group-hover:text-[#f1f5f9] leading-snug transition-colors ${isExpanded ? "" : "line-clamp-2"}`}>
                        {item.headline || "Untitled"}
                      </p>

                      {/* Summary (always show; expand removes line-clamp) */}
                      {item.summary && (
                        <p className={`text-xs text-[#64748b] mt-1 leading-relaxed ${isExpanded ? "" : "line-clamp-2"}`}>
                          {item.summary}
                        </p>
                      )}

                      {/* Expanded content */}
                      {isExpanded && (
                        <div className="mt-3 space-y-2" onClick={(e) => e.stopPropagation()}>
                          {/* AI Summary on demand */}
                          {aiSummary ? (
                            <div className="rounded-lg p-3 bg-violet-500/[0.06] border border-violet-500/20">
                              <p className="text-[10px] text-violet-400 font-semibold uppercase tracking-wide mb-1">AI Summary</p>
                              <p className="text-xs text-[#94a3b8] leading-relaxed">{aiSummary}</p>
                            </div>
                          ) : (
                            <button
                              disabled={isAiLoading}
                              onClick={async () => {
                                setAiLoading((prev) => ({ ...prev, [i]: true }));
                                try {
                                  const res = await fetch(
                                    `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/news/summarize`,
                                    {
                                      method: "POST",
                                      headers: { "Content-Type": "application/json" },
                                      body: JSON.stringify({ headline: item.headline, summary: item.summary, symbol: item.related_symbol }),
                                    }
                                  );
                                  if (res.ok) {
                                    const d = await res.json();
                                    setAiSummaries((prev) => ({ ...prev, [i]: d.summary ?? d.text ?? "No summary returned." }));
                                  }
                                } catch {
                                  setAiSummaries((prev) => ({ ...prev, [i]: "AI summary unavailable." }));
                                } finally {
                                  setAiLoading((prev) => ({ ...prev, [i]: false }));
                                }
                              }}
                              className="text-[10px] px-2.5 py-1 rounded-lg bg-violet-500/10 border border-violet-500/20 text-violet-400 hover:bg-violet-500/15 transition-colors disabled:opacity-50"
                            >
                              {isAiLoading ? "Generating..." : "✦ AI Summary"}
                            </button>
                          )}
                          {/* External link */}
                          {item.url && (
                            <a
                              href={item.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-[10px] text-[#475569] hover:text-[#94a3b8] transition-colors"
                            >
                              Read full article →
                            </a>
                          )}
                        </div>
                      )}
                    </div>
                    {/* Expand chevron */}
                    <span className="text-[#334155] text-xs mt-0.5 shrink-0 transition-transform" style={{ transform: isExpanded ? "rotate(180deg)" : "none" }}>
                      ↓
                    </span>
                  </div>
                </div>
              );
            })
          }
        </div>

        {/* ── Earnings Calendar (right, 2/5 width) ────────────────── */}
        <div className="col-span-2 space-y-3">
          <h2 className="text-xs font-semibold text-[#475569] uppercase tracking-wider">
            Earnings Calendar · Next 30 Days
          </h2>

          {loadingEarnings && (
            <div className="space-y-2">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="glass-card p-3 space-y-2">
                  <div className="skeleton h-3 w-1/2 rounded" />
                  <div className="skeleton h-2 w-3/4 rounded" />
                </div>
              ))}
            </div>
          )}

          {earningsError && (
            <GlassCard>
              <p className="text-sm text-[#ef4444]">Failed to load calendar: {earningsError}</p>
            </GlassCard>
          )}

          {!loadingEarnings && !earningsError && earnings.length === 0 && (
            <GlassCard>
              <p className="text-sm text-[#475569] text-center py-4">
                No upcoming earnings for held assets.
              </p>
            </GlassCard>
          )}

          {!loadingEarnings && earnings.map((event, i) => {
            const hasActual = event.eps_actual != null;
            return (
              <div key={i} className="glass-card p-3">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-semibold font-mono text-[#f1f5f9]">
                    {event.symbol}
                  </span>
                  <span className={`text-xs px-2 py-0.5 rounded-full font-mono ${
                    hasActual
                      ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                      : "bg-indigo-500/10 text-indigo-400 border border-indigo-500/20"
                  }`}>
                    {fmtDate(event.date)}
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-x-3 text-xs mt-1.5">
                  <div>
                    <span className="text-[#475569]">EPS est. </span>
                    <span className="text-[#94a3b8] font-mono">{fmtNum(event.eps_estimate)}</span>
                  </div>
                  {hasActual && (
                    <div>
                      <span className="text-[#475569]">Actual </span>
                      <span className={`font-mono font-semibold ${
                        (event.eps_actual ?? 0) >= (event.eps_estimate ?? 0)
                          ? "text-[#10b981]"
                          : "text-[#ef4444]"
                      }`}>
                        {fmtNum(event.eps_actual)}
                      </span>
                    </div>
                  )}
                  {event.revenue_estimate != null && (
                    <div className="col-span-2 mt-0.5">
                      <span className="text-[#475569]">Rev est. </span>
                      <span className="text-[#94a3b8] font-mono">
                        ${(event.revenue_estimate / 1e9).toFixed(2)}B
                      </span>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
