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
          <h2 className="text-xs font-semibold text-[#475569] uppercase tracking-wider">
            News Feed
          </h2>

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

          {!loadingNews && news.map((item, i) => (
            <div
              key={i}
              className="glass-card p-4 hover:bg-white/[0.06] transition-all duration-200 group"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  {/* Symbol badge + source row */}
                  <div className="flex items-center gap-2 mb-1.5">
                    {item.related_symbol && (
                      <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-indigo-500/15 text-indigo-400 border border-indigo-500/25 font-mono">
                        {item.related_symbol.replace("-USD", "")}
                      </span>
                    )}
                    {item.source && (
                      <span className="text-[10px] text-[#475569]">{item.source}</span>
                    )}
                    {item.category && (
                      <span className="text-[10px] text-[#475569]">{item.category}</span>
                    )}
                    <span className="text-[10px] text-[#334155] ml-auto">{timeAgo(item.published_at)}</span>
                  </div>

                  {/* Headline */}
                  {item.url ? (
                    <a
                      href={item.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm font-medium text-[#e2e8f0] group-hover:text-[#f1f5f9] leading-snug transition-colors line-clamp-2"
                    >
                      {item.headline || "Untitled"}
                    </a>
                  ) : (
                    <p className="text-sm font-medium text-[#e2e8f0] leading-snug line-clamp-2">
                      {item.headline || "Untitled"}
                    </p>
                  )}

                  {/* Summary */}
                  {item.summary && (
                    <p className="text-xs text-[#64748b] mt-1 line-clamp-2 leading-relaxed">
                      {item.summary}
                    </p>
                  )}
                </div>
              </div>
            </div>
          ))}
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
