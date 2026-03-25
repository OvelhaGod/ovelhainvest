"use client";

/**
 * /markets — Live market overview, portfolio vs benchmarks, sector heatmap.
 * Perplexity Finance-inspired layout with glassmorphism design.
 */

import { useEffect, useState, useCallback } from "react";
import useSWR from "swr";
import { fetcher } from "@/lib/swr-config";
import { AssetLogo } from "@/lib/asset-logos";

// ── Types ─────────────────────────────────────────────────────────────────────
interface IndexTicker {
  symbol: string;
  name: string;
  price: number | null;
  change_pct: number | null;
  sparkline: number[];
}

interface SectorData {
  name: string;
  symbol: string;
  change_pct: number | null;
}

interface FxData {
  pair: string;
  rate: number | null;
  change_pct: number | null;
}

interface HeldAsset {
  symbol: string;
  name: string;
  price: number | null;
  change_pct: number | null;
  quantity: number;
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function fmtPrice(n: number | null | undefined): string {
  if (n == null) return "—";
  if (n >= 1000) return `$${n.toLocaleString("en-US", { maximumFractionDigits: 0 })}`;
  if (n >= 100)  return `$${n.toFixed(2)}`;
  return `$${n.toFixed(2)}`;
}

function fmtPct(n: number | null | undefined, dp = 2): string {
  if (n == null) return "—";
  const sign = n >= 0 ? "+" : "";
  return `${sign}${n.toFixed(dp)}%`;
}

function pctColor(n: number | null | undefined): string {
  if (n == null) return "text-white/40";
  if (n > 0)  return "text-[#10b981]";
  if (n < 0)  return "text-[#f43f5e]";
  return "text-white/60";
}

function sectorBg(chg: number | null): string {
  if (chg == null) return "rgba(255,255,255,0.04)";
  if (chg > 1.5)   return "rgba(16,185,129,0.25)";
  if (chg > 0.5)   return "rgba(16,185,129,0.14)";
  if (chg > 0)     return "rgba(16,185,129,0.06)";
  if (chg > -0.5)  return "rgba(244,63,94,0.06)";
  if (chg > -1.5)  return "rgba(244,63,94,0.14)";
  return "rgba(244,63,94,0.25)";
}

// Mini SVG sparkline (no lib, lightweight)
function Sparkline({ data, color }: { data: number[]; color: string }) {
  if (!data || data.length < 2) return <div className="w-10 h-6 opacity-30 bg-white/5 rounded" />;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const W = 40, H = 22;
  const pts = data
    .map((v, i) => `${(i / (data.length - 1)) * W},${H - ((v - min) / range) * H}`)
    .join(" ");
  return (
    <svg viewBox={`0 0 ${W} ${H}`} width={W} height={H} preserveAspectRatio="none" className="shrink-0">
      <polyline points={pts} fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

// Skeleton loader
function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse rounded bg-white/[0.06] ${className}`} />;
}

// Fear & Greed gauge
function FearGreedGauge({ value }: { value: number }) {
  const label =
    value <= 20 ? "Extreme Fear" :
    value <= 40 ? "Fear" :
    value <= 60 ? "Neutral" :
    value <= 80 ? "Greed" : "Extreme Greed";
  const color =
    value <= 20 ? "#f43f5e" :
    value <= 40 ? "#f59e0b" :
    value <= 60 ? "#94a3b8" :
    value <= 80 ? "#10b981" : "#06b6d4";
  const pct = `${value}%`;

  return (
    <div className="space-y-2">
      <div className="flex items-end justify-between">
        <span className="text-4xl font-mono font-bold" style={{ color }}>{value}</span>
        <span className="text-sm font-medium mb-1" style={{ color }}>{label}</span>
      </div>
      <div className="h-2 rounded-full bg-white/[0.08] overflow-hidden">
        <div className="h-full rounded-full transition-all duration-500"
          style={{ width: pct, background: `linear-gradient(90deg, #f43f5e 0%, #f59e0b 25%, #94a3b8 50%, #10b981 75%, #06b6d4 100%)` }} />
      </div>
      <div className="flex justify-between text-[10px] text-white/30">
        <span>Fear</span><span>Neutral</span><span>Greed</span>
      </div>
    </div>
  );
}

// ── Main component ─────────────────────────────────────────────────────────────
export default function MarketsPage() {
  const { data: overview, isLoading: loadingOverview } = useSWR(
    "/markets/overview", fetcher, { refreshInterval: 60_000 }
  );
  const { data: pvMarket, isLoading: loadingPvM } = useSWR(
    "/markets/portfolio_vs_market", fetcher, { refreshInterval: 60_000 }
  );
  const { data: movers, isLoading: loadingMovers } = useSWR(
    "/markets/movers", fetcher, { refreshInterval: 60_000 }
  );

  // Compute fear/greed from VIX
  const fearGreed = useCallback(() => {
    if (!overview) return 50;
    const indices = (overview as any).indices as IndexTicker[] | undefined;
    if (!indices) return 50;
    const vix = indices.find((i) => i.symbol === "VIX" || i.name === "VIX");
    if (!vix?.price) return 50;
    // VIX inverse: VIX 10=90 (extreme greed), VIX 40=5 (extreme fear)
    const raw = Math.max(5, Math.min(95, Math.round(100 - ((vix.price - 10) / 30) * 90)));
    return raw;
  }, [overview]);

  const indices = (overview as any)?.indices as IndexTicker[] | undefined;
  const sectors = (overview as any)?.sectors as SectorData[] | undefined;
  const fx      = (overview as any)?.fx as FxData[] | undefined;
  const heldAssets = (movers as any)?.held_assets as HeldAsset[] | undefined;
  const periods = (pvMarket as any)?.periods as string[] | undefined;
  const pRows = pvMarket as any;

  const PERIOD_LABELS: Record<string, string> = { "1w": "1W", "1m": "1M", "3m": "3M", "ytd": "YTD", "1y": "1Y" };
  const PERIOD_LIST = ["1w", "1m", "3m", "ytd", "1y"];

  return (
    <div className="min-h-screen p-4 md:p-6 space-y-4"
      style={{
        background: "radial-gradient(ellipse 80% 50% at 50% -20%, rgba(99,102,241,0.10) 0%, transparent 60%), #050508"
      }}>
      {/* ── Page header ── */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white/90">Markets</h1>
          <p className="text-xs text-white/40 mt-0.5">Live data · refreshes every 60s</p>
        </div>
        {overview && (
          <span className="text-[10px] text-white/30 font-mono">
            {new Date((overview as any).updated_at).toLocaleTimeString()}
          </span>
        )}
      </div>

      {/* ── TICKER STRIP ── */}
      <div className="relative overflow-hidden rounded-xl border border-white/[0.07] bg-white/[0.03]">
        <div className="flex gap-0 ticker-scroll">
          {[...(indices ?? []), ...(indices ?? [])].map((t, i) => (
            <div key={i} className="flex items-center gap-2 px-4 py-2.5 border-r border-white/[0.06] shrink-0 min-w-[160px]">
              <Sparkline
                data={t.sparkline ?? []}
                color={(t.change_pct ?? 0) >= 0 ? "#10b981" : "#f43f5e"}
              />
              <div>
                <div className="flex items-center gap-1.5">
                  <span className="text-xs font-mono font-semibold text-white/90">{t.symbol}</span>
                  <span className={`text-[10px] font-mono ${pctColor(t.change_pct)}`}>
                    {fmtPct(t.change_pct)}
                  </span>
                </div>
                <div className="text-[10px] font-mono text-white/40">{fmtPrice(t.price)}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ── MAIN GRID ── */}
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_300px] gap-4">

        {/* LEFT COLUMN */}
        <div className="space-y-4">

          {/* PORTFOLIO VS MARKET */}
          <div className="rounded-2xl border border-white/[0.08] bg-white/[0.03] p-4">
            <h2 className="text-sm font-semibold text-white/80 mb-3">Portfolio vs Market</h2>
            {loadingPvM ? (
              <div className="space-y-2">
                {[...Array(5)].map((_, i) => <Skeleton key={i} className="h-8 w-full" />)}
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b border-white/[0.06]">
                      <th className="text-left pb-2 text-white/40 font-medium w-36">Benchmark</th>
                      {PERIOD_LIST.map(p => (
                        <th key={p} className="text-right pb-2 text-white/40 font-medium px-2">
                          {PERIOD_LABELS[p]}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {[
                      { label: "Your Portfolio", key: "portfolio", accent: true },
                      { label: "S&P 500 (SPY)",  key: "spy" },
                      { label: "NASDAQ (QQQ)",   key: "qqq" },
                      { label: "ACWI (Global)",  key: "acwi" },
                      { label: "Alpha vs SPY",   key: "alpha_vs_spy", isAlpha: true },
                    ].map(({ label, key, accent, isAlpha }) => (
                      <tr key={key} className={`border-b border-white/[0.04] ${isAlpha ? "bg-white/[0.02]" : ""}`}>
                        <td className={`py-2 pr-3 font-medium ${accent ? "text-white" : isAlpha ? "text-[#8b5cf6]" : "text-white/60"}`}>
                          {label}
                        </td>
                        {PERIOD_LIST.map(p => {
                          const val = pRows?.[key]?.[p] as number | null;
                          return (
                            <td key={p} className={`py-2 px-2 text-right font-mono ${pctColor(val != null ? val * 100 : null)}`}>
                              {val != null ? (
                                <span className="flex items-center justify-end gap-0.5">
                                  {isAlpha && val > 0 ? "↑" : isAlpha && val < 0 ? "↓" : ""}
                                  {fmtPct(val * 100, 1)}
                                </span>
                              ) : "—"}
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* SECTOR HEATMAP */}
          <div className="rounded-2xl border border-white/[0.08] bg-white/[0.03] p-4">
            <h2 className="text-sm font-semibold text-white/80 mb-3">Sector Performance Today</h2>
            {loadingOverview ? (
              <div className="grid grid-cols-4 gap-2">
                {[...Array(8)].map((_, i) => <Skeleton key={i} className="h-16" />)}
              </div>
            ) : (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                {(sectors ?? []).map(s => (
                  <div key={s.symbol}
                    className="rounded-xl p-3 border border-white/[0.06] transition-all hover:border-white/10"
                    style={{ background: sectorBg(s.change_pct) }}>
                    <div className="text-[10px] text-white/50 mb-0.5">{s.symbol}</div>
                    <div className="text-xs font-medium text-white/80 leading-tight">{s.name}</div>
                    <div className={`text-sm font-mono font-bold mt-1 ${pctColor(s.change_pct)}`}>
                      {fmtPct(s.change_pct)}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* YOUR HOLDINGS TODAY */}
          <div className="rounded-2xl border border-white/[0.08] bg-white/[0.03] p-4">
            <h2 className="text-sm font-semibold text-white/80 mb-3">Your Holdings Today</h2>
            {loadingMovers ? (
              <div className="space-y-2">
                {[...Array(5)].map((_, i) => <Skeleton key={i} className="h-10 w-full" />)}
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b border-white/[0.06]">
                      <th className="text-left pb-2 text-white/40 font-medium">Asset</th>
                      <th className="text-right pb-2 text-white/40 font-medium px-2">Price</th>
                      <th className="text-right pb-2 text-white/40 font-medium px-2">Today</th>
                      <th className="text-right pb-2 text-white/40 font-medium">Qty</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(heldAssets ?? []).slice(0, 12).map(a => (
                      <tr key={a.symbol} className="border-b border-white/[0.04] hover:bg-white/[0.02] transition-colors">
                        <td className="py-2 pr-2">
                          <div className="flex items-center gap-2">
                            <AssetLogo symbol={a.symbol} size={20} />
                            <div>
                              <div className="font-mono font-semibold text-white/90">{a.symbol}</div>
                              <div className="text-[10px] text-white/40 truncate max-w-[100px]">{a.name}</div>
                            </div>
                          </div>
                        </td>
                        <td className="py-2 px-2 text-right font-mono text-white/70">{fmtPrice(a.price)}</td>
                        <td className={`py-2 px-2 text-right font-mono font-semibold ${pctColor(a.change_pct)}`}>
                          {fmtPct(a.change_pct)}
                        </td>
                        <td className="py-2 text-right font-mono text-white/50">
                          {a.quantity < 1 ? a.quantity.toFixed(4) : a.quantity.toFixed(2)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>

        {/* RIGHT SIDEBAR */}
        <div className="space-y-4">

          {/* MACRO INDICATORS */}
          <div className="rounded-2xl border border-white/[0.08] bg-white/[0.03] p-4">
            <h2 className="text-sm font-semibold text-white/80 mb-3">Macro Indicators</h2>
            <div className="space-y-2.5">
              {loadingOverview ? (
                [...Array(6)].map((_, i) => <Skeleton key={i} className="h-6 w-full" />)
              ) : (
                <>
                  {(fx ?? []).map(f => (
                    <div key={f.pair} className="flex items-center justify-between text-xs">
                      <span className="text-white/50">{f.pair}</span>
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-white/80">{f.rate?.toFixed(4) ?? "—"}</span>
                        <span className={`font-mono text-[10px] ${pctColor(f.change_pct)}`}>
                          {fmtPct(f.change_pct)}
                        </span>
                      </div>
                    </div>
                  ))}
                  <div className="border-t border-white/[0.06] pt-2 space-y-2">
                    {(indices ?? []).filter(i => ["GLD", "TLT"].includes(i.symbol)).map(t => (
                      <div key={t.symbol} className="flex items-center justify-between text-xs">
                        <span className="text-white/50">{t.name}</span>
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-white/80">{fmtPrice(t.price)}</span>
                          <span className={`font-mono text-[10px] ${pctColor(t.change_pct)}`}>
                            {fmtPct(t.change_pct)}
                          </span>
                        </div>
                      </div>
                    ))}
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-white/50">VIX</span>
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-white/80">
                          {(indices ?? []).find(i => i.name === "VIX")?.price?.toFixed(2) ?? "—"}
                        </span>
                        <span className={`font-mono text-[10px] ${pctColor((indices ?? []).find(i => i.name === "VIX")?.change_pct)}`}>
                          {fmtPct((indices ?? []).find(i => i.name === "VIX")?.change_pct)}
                        </span>
                      </div>
                    </div>
                  </div>
                </>
              )}
            </div>
          </div>

          {/* FEAR & GREED */}
          <div className="rounded-2xl border border-white/[0.08] bg-white/[0.03] p-4">
            <h2 className="text-sm font-semibold text-white/80 mb-3">Fear & Greed Proxy</h2>
            {loadingOverview
              ? <Skeleton className="h-20 w-full" />
              : <FearGreedGauge value={fearGreed()} />
            }
            <p className="text-[10px] text-white/30 mt-2">Derived from VIX + SPY momentum</p>
          </div>

          {/* MARKET GAINERS/LOSERS */}
          <div className="rounded-2xl border border-white/[0.08] bg-white/[0.03] p-4">
            <h2 className="text-sm font-semibold text-white/80 mb-3">Market Movers</h2>
            {loadingMovers ? (
              <Skeleton className="h-32 w-full" />
            ) : (
              <div className="space-y-3">
                <div>
                  <p className="text-[10px] text-[#10b981] uppercase tracking-wider mb-1.5 font-medium">Top Gainers</p>
                  {((movers as any)?.market_gainers ?? []).map((m: any) => (
                    <div key={m.symbol} className="flex justify-between items-center py-1 text-xs border-b border-white/[0.04]">
                      <span className="font-mono font-semibold text-white/80">{m.symbol}</span>
                      <span className="font-mono text-[#10b981]">{fmtPct(m.change_pct)}</span>
                    </div>
                  ))}
                </div>
                <div>
                  <p className="text-[10px] text-[#f43f5e] uppercase tracking-wider mb-1.5 font-medium">Top Losers</p>
                  {((movers as any)?.market_losers ?? []).map((m: any) => (
                    <div key={m.symbol} className="flex justify-between items-center py-1 text-xs border-b border-white/[0.04]">
                      <span className="font-mono font-semibold text-white/80">{m.symbol}</span>
                      <span className="font-mono text-[#f43f5e]">{fmtPct(m.change_pct)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
