"use client";

/**
 * /markets — Live market overview, portfolio vs benchmarks, sector heatmap.
 * Perplexity Finance-inspired layout: clickable tickers, sector sparklines,
 * expandable holdings rows.
 */

import React, { useCallback, useState } from "react";
import useSWR from "swr";
import { X } from "lucide-react";
import { fetcher, CACHE_TTL } from "@/lib/swr-config";
import { AssetLogo } from "@/lib/asset-logos";
import { MiniChart } from "@/components/charts/MiniChart";
import { PortfolioChart } from "@/components/charts/PortfolioChart";
import { PriceChart } from "@/components/charts/PriceChart";

// ── Types ──────────────────────────────────────────────────────────────────────
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

// ── Helpers ────────────────────────────────────────────────────────────────────
function fmtPrice(n: number | null | undefined): string {
  if (n == null) return "—";
  if (n >= 1000) return `$${n.toLocaleString("en-US", { maximumFractionDigits: 0 })}`;
  return `$${n.toFixed(2)}`;
}

function fmtPct(n: number | null | undefined, dp = 2): string {
  if (n == null) return "—";
  const sign = n >= 0 ? "+" : "";
  return `${sign}${n.toFixed(dp)}%`;
}

function pctColor(n: number | null | undefined): string {
  if (n == null) return "text-white/40";
  if (n > 0) return "text-[#10b981]";
  if (n < 0) return "text-[#f43f5e]";
  return "text-white/60";
}

function sectorBg(chg: number | null): string {
  if (chg == null) return "rgba(255,255,255,0.03)";
  if (chg > 2.0) return "rgba(6,78,59,0.85)";
  if (chg > 1.0) return "rgba(6,95,70,0.65)";
  if (chg > 0)   return "rgba(6,78,59,0.35)";
  if (chg > -1.0) return "rgba(76,16,16,0.40)";
  if (chg > -2.0) return "rgba(76,16,16,0.65)";
  return "rgba(91,26,26,0.85)";
}

function sectorBorder(chg: number | null): string {
  if (chg == null) return "rgba(255,255,255,0.06)";
  if (chg > 0) return "rgba(16,185,129,0.25)";
  return "rgba(244,63,94,0.20)";
}

// Mini inline SVG sparkline
function Sparkline({ data, color }: { data: number[]; color: string }) {
  if (!data || data.length < 2)
    return <div className="w-10 h-6 opacity-30 bg-white/5 rounded" />;
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

function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse rounded bg-white/[0.06] ${className}`} />;
}

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

  return (
    <div className="space-y-2">
      <div className="flex items-end justify-between">
        <span className="text-4xl font-mono font-bold" style={{ color }}>{value}</span>
        <span className="text-sm font-medium mb-1" style={{ color }}>{label}</span>
      </div>
      <div className="h-2 rounded-full bg-white/[0.08] overflow-hidden">
        <div className="h-full rounded-full transition-all duration-500"
          style={{
            width: `${value}%`,
            background: "linear-gradient(90deg, #f43f5e 0%, #f59e0b 25%, #94a3b8 50%, #10b981 75%, #06b6d4 100%)"
          }} />
      </div>
      <div className="flex justify-between text-[10px] text-white/30">
        <span>Fear</span><span>Neutral</span><span>Greed</span>
      </div>
    </div>
  );
}

// ── Sector symbols for sparkline batch fetch ───────────────────────────────────
const SECTOR_SYMBOLS = ["XLK", "XLE", "XLV", "XLF", "XLRE", "XLY", "XLU", "XLB", "XLI", "XLC"];

// ── Main component ─────────────────────────────────────────────────────────────
export default function MarketsPage() {
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null);
  const [expandedHolding, setExpandedHolding] = useState<string | null>(null);

  const { data: overview, isLoading: loadingOverview } = useSWR(
    "/markets/overview", fetcher, { refreshInterval: 60_000 }
  );
  const { data: pvMarket, isLoading: loadingPvM } = useSWR(
    "/markets/portfolio_vs_market", fetcher, { refreshInterval: 60_000 }
  );
  const { data: movers, isLoading: loadingMovers } = useSWR(
    "/markets/movers", fetcher, { refreshInterval: 60_000 }
  );

  // Batch sparklines for held assets
  const heldAssetsRaw = (movers as any)?.held_assets as HeldAsset[] | undefined;
  const heldAssets = heldAssetsRaw
    ? Object.values(
        heldAssetsRaw.reduce<Record<string, HeldAsset>>((acc, a) => {
          if (acc[a.symbol]) {
            acc[a.symbol] = { ...acc[a.symbol], quantity: acc[a.symbol].quantity + a.quantity };
          } else {
            acc[a.symbol] = { ...a };
          }
          return acc;
        }, {})
      )
    : undefined;

  const heldSymbols = (heldAssets ?? []).map((a) => a.symbol).join(",");
  const { data: holdingSparklines } = useSWR<Record<string, number[]>>(
    heldSymbols ? `/price_history/batch?symbols=${heldSymbols}&period=1m` : null,
    fetcher,
    { refreshInterval: CACHE_TTL.MEDIUM }
  );

  // Batch sparklines for sectors (1M period)
  const { data: sectorSparklines } = useSWR<Record<string, number[]>>(
    `/price_history/batch?symbols=${SECTOR_SYMBOLS.join(",")}&period=1m`,
    fetcher,
    { refreshInterval: CACHE_TTL.SLOW }
  );

  const fearGreed = useCallback(() => {
    if (!overview) return 50;
    const indices = (overview as any).indices as IndexTicker[] | undefined;
    const vix = indices?.find((i) => i.symbol === "VIX" || i.name === "VIX");
    if (!vix?.price) return 50;
    return Math.max(5, Math.min(95, Math.round(100 - ((vix.price - 10) / 30) * 90)));
  }, [overview]);

  const indices = (overview as any)?.indices as IndexTicker[] | undefined;
  const sectors = (overview as any)?.sectors as SectorData[] | undefined;
  const fx = (overview as any)?.fx as FxData[] | undefined;
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

      {/* ── TICKER STRIP — clickable ── */}
      <div className="rounded-xl border border-white/[0.07] bg-white/[0.03]">
        <div className="flex overflow-x-auto scrollbar-hide rounded-t-xl overflow-hidden">
          {(indices ?? []).map((t) => {
            const isSelected = selectedTicker === t.symbol;
            const chgColor = (t.change_pct ?? 0) >= 0 ? "#10b981" : "#f43f5e";
            return (
              <button
                key={t.symbol}
                onClick={() => setSelectedTicker(isSelected ? null : t.symbol)}
                className={`flex items-center gap-2.5 px-4 py-2.5 border-r border-white/[0.06] shrink-0 min-w-[160px]
                  transition-all duration-150
                  ${isSelected
                    ? "bg-white/[0.06] border-b-2 border-b-emerald-500"
                    : "hover:bg-white/[0.03] border-b-2 border-b-transparent"
                  }`}
              >
                <Sparkline data={t.sparkline ?? []} color={chgColor} />
                <div className="text-left">
                  <div className="flex items-center gap-1.5">
                    <span className="text-xs font-mono font-semibold text-white/90">{t.symbol}</span>
                    <span className="text-[10px] font-mono" style={{ color: chgColor }}>
                      {fmtPct(t.change_pct)}
                    </span>
                  </div>
                  <div className="text-[10px] font-mono text-white/40">{fmtPrice(t.price)}</div>
                </div>
              </button>
            );
          })}
        </div>

        {/* Expanded chart panel for selected ticker */}
        {selectedTicker && (
          <div className="border-t border-white/[0.06] p-4 bg-white/[0.02]">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <span className="text-sm font-semibold font-mono text-white/90">{selectedTicker}</span>
                <span className="text-xs text-white/40">
                  {indices?.find((i) => i.symbol === selectedTicker)?.name ?? ""}
                </span>
              </div>
              <button
                onClick={() => setSelectedTicker(null)}
                className="text-white/30 hover:text-white/60 transition-colors"
              >
                <X size={14} />
              </button>
            </div>
            <PriceChart
              symbol={selectedTicker}
              height={160}
              showPeriodSelector={true}
              defaultPeriod="1D"
              variant="minimal"
            />
          </div>
        )}
      </div>

      {/* ── MAIN GRID ── */}
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_300px] gap-4">

        {/* LEFT COLUMN */}
        <div className="space-y-4">

          {/* PORTFOLIO VS MARKET TABLE */}
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
                              {val != null ? fmtPct(val * 100, 1) : "—"}
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

          {/* PORTFOLIO EVOLUTION CHART */}
          <div className="rounded-2xl border border-white/[0.08] bg-white/[0.03] p-4">
            <h2 className="text-sm font-semibold text-white/80 mb-1">Portfolio Evolution</h2>
            <p className="text-[10px] text-white/30 mb-3">Indexed to 100 at period start · vs SPY, QQQ, ACWI</p>
            <PortfolioChart height={180} defaultPeriod="3M" />
          </div>

          {/* SECTOR HEATMAP with sparklines */}
          <div className="rounded-2xl border border-white/[0.08] bg-white/[0.03] p-4">
            <h2 className="text-sm font-semibold text-white/80 mb-3">Sector Performance</h2>
            {loadingOverview ? (
              <div className="grid grid-cols-4 gap-2">
                {[...Array(8)].map((_, i) => <Skeleton key={i} className="h-20" />)}
              </div>
            ) : (
              <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-5 gap-2">
                {(sectors ?? []).map(s => {
                  const spark = sectorSparklines?.[s.symbol] ?? [];
                  const chgColor = (s.change_pct ?? 0) >= 0 ? "#10b981" : "#f43f5e";
                  return (
                    <div key={s.symbol}
                      className="rounded-xl p-3 border transition-all hover:brightness-110 cursor-default"
                      style={{ background: sectorBg(s.change_pct), borderColor: sectorBorder(s.change_pct) }}>
                      <div className="text-[10px] text-white/50 mb-0.5">{s.symbol}</div>
                      <div className="text-xs font-medium text-white/80 leading-tight truncate">{s.name}</div>
                      <div className={`text-sm font-mono font-bold mt-1 ${pctColor(s.change_pct)}`}>
                        {fmtPct(s.change_pct)}
                      </div>
                      {spark.length >= 2 && (
                        <div className="mt-1.5">
                          <MiniChart data={spark} height={28} width={80} color={chgColor} showGradient={false} />
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* YOUR HOLDINGS TODAY — expandable rows */}
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
                      <th className="text-right pb-2 text-white/40 font-medium px-2">1M</th>
                      <th className="text-right pb-2 text-white/40 font-medium">Qty</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(heldAssets ?? []).slice(0, 12).map(a => (
                      <React.Fragment key={a.symbol}>
                        <tr
                          onClick={() =>
                            setExpandedHolding(expandedHolding === a.symbol ? null : a.symbol)
                          }
                          className="border-b border-white/[0.04] hover:bg-white/[0.02] transition-colors cursor-pointer"
                        >
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
                          <td className="py-2 px-2 text-right">
                            {holdingSparklines?.[a.symbol] && holdingSparklines[a.symbol].length >= 2 ? (
                              <div className="flex justify-end">
                                <MiniChart data={holdingSparklines[a.symbol]} height={24} width={52} />
                              </div>
                            ) : (
                              <span className="text-white/20 text-[10px]">—</span>
                            )}
                          </td>
                          <td className="py-2 text-right font-mono text-white/50">
                            {a.quantity < 1 ? a.quantity.toFixed(4) : a.quantity.toFixed(2)}
                          </td>
                        </tr>
                        {expandedHolding === a.symbol && (
                          <tr>
                            <td colSpan={5} className="px-2 pb-4 pt-1 bg-white/[0.02]">
                              <PriceChart
                                symbol={a.symbol}
                                height={150}
                                showPeriodSelector={true}
                                defaultPeriod="1D"
                                variant="minimal"
                              />
                            </td>
                          </tr>
                        )}
                      </React.Fragment>
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

          {/* MARKET MOVERS */}
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
