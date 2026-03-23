"use client";

/**
 * /assets — Phase 3: Valuation screener with factor scores + detail drawer.
 * Design: CLAUDE.md Section 27.4 Screen 3 — glassmorphism, dark theme.
 *
 * Features:
 *  - Sortable table: Symbol, Class, Price, MoS%, Value/Momentum/Quality score bars,
 *    Moat badge, Fair Value, Rank
 *  - Filters: asset class, tier, min MoS slider, moat
 *  - Right drawer on row click: Overview | DCF | Scores | News tabs
 *  - Buy/hold/sell zone visualization
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { AssetValuation } from "@/lib/types";

// ── Design tokens ─────────────────────────────────────────────────────────────
const glass = "rounded-2xl border border-white/[0.08] bg-white/[0.03] backdrop-blur-sm";

const CLASS_COLORS: Record<string, string> = {
  US_equity:     "#6366f1",
  Intl_equity:   "#8b5cf6",
  Bond:          "#3b82f6",
  Brazil_equity: "#22c55e",
  Crypto:        "#f59e0b",
  Benchmark:     "#64748b",
};

const MOAT_CONFIG: Record<string, { label: string; color: string; bg: string }> = {
  wide:    { label: "Wide",    color: "#10b981", bg: "rgba(16,185,129,0.12)" },
  narrow:  { label: "Narrow",  color: "#f59e0b", bg: "rgba(245,158,11,0.12)" },
  none:    { label: "None",    color: "#64748b", bg: "rgba(100,116,139,0.12)" },
  unknown: { label: "?",       color: "#64748b", bg: "rgba(100,116,139,0.12)" },
};

const TIER_CONFIG: Record<string, { label: string; color: string }> = {
  tier_1:  { label: "Tier 1",  color: "#10b981" },
  tier_2:  { label: "Tier 2",  color: "#8b5cf6" },
  watch:   { label: "Watch",   color: "#f59e0b" },
};

// ── Helpers ───────────────────────────────────────────────────────────────────
function fmtUSD(n: number | null | undefined, decimals = 2): string {
  if (n == null) return "—";
  if (n >= 1000) return `$${n.toLocaleString("en-US", { maximumFractionDigits: 0 })}`;
  return `$${n.toFixed(decimals)}`;
}

function fmtPct(n: number | null | undefined, dp = 1): string {
  if (n == null) return "—";
  const sign = n >= 0 ? "+" : "";
  return `${sign}${(n * 100).toFixed(dp)}%`;
}

function mosColor(mos: number | null | undefined): string {
  if (mos == null) return "#64748b";
  if (mos >= 0.20) return "#10b981";
  if (mos >= 0.10) return "#f59e0b";
  if (mos >= 0)    return "#94a3b8";
  return "#ef4444";
}

type SortKey = "rank_in_universe" | "composite_score" | "margin_of_safety_pct" | "value_score" | "momentum_score" | "quality_score" | "price";

// ── Score bar component ───────────────────────────────────────────────────────
function ScoreBar({ value, color = "#6366f1" }: { value: number | null; color?: string }) {
  if (value == null) return <span className="text-[#475569] text-xs">—</span>;
  const pct = Math.round(value * 100);
  const displayColor = value >= 0.55 ? "#10b981" : value >= 0.40 ? "#f59e0b" : "#ef4444";
  return (
    <div className="flex items-center gap-1.5">
      <div className="w-14 h-1.5 rounded-full bg-white/[0.06] overflow-hidden">
        <div
          className="h-full rounded-full transition-all"
          style={{ width: `${pct}%`, background: displayColor }}
        />
      </div>
      <span className="text-[10px] font-mono tabular-nums" style={{ color: displayColor }}>
        {value.toFixed(2)}
      </span>
    </div>
  );
}

// ── Buy/Hold/Sell zone visualization ─────────────────────────────────────────
function PriceZoneBar({ asset }: { asset: AssetValuation }) {
  const { price, buy_target, hold_range_low, hold_range_high, sell_target, fair_value_estimate_dcf } = asset;
  if (!price || !buy_target || !sell_target || !fair_value_estimate_dcf) {
    return (
      <div className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.06] text-center text-[#475569] text-sm">
        DCF fair value not available for this asset
      </div>
    );
  }
  const min = buy_target * 0.85;
  const max = sell_target * 1.15;
  const range = max - min;
  const toX = (v: number) => `${Math.max(0, Math.min(100, ((v - min) / range) * 100))}%`;

  const zones = [
    { from: buy_target,      to: hold_range_low!,  label: "Buy Zone",   color: "rgba(16,185,129,0.25)" },
    { from: hold_range_low!, to: hold_range_high!,  label: "Hold Zone",  color: "rgba(99,102,241,0.20)" },
    { from: hold_range_high!,to: sell_target,        label: "Reduce Zone",color: "rgba(245,158,11,0.20)" },
    { from: sell_target,     to: max,               label: "Sell Zone",  color: "rgba(239,68,68,0.20)" },
  ];

  const priceZoneLabel = price < buy_target ? "Below Buy Target" :
    price < hold_range_low! ? "Buy Zone" :
    price < hold_range_high! ? "Hold Zone" :
    price < sell_target ? "Reduce" : "Above Sell Target";
  const priceZoneColor = price < buy_target ? "#10b981" :
    price < hold_range_low! ? "#10b981" :
    price < hold_range_high! ? "#6366f1" :
    price < sell_target ? "#f59e0b" : "#ef4444";

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between text-xs">
        <span className="text-[#475569]">Price Zone</span>
        <span className="font-semibold" style={{ color: priceZoneColor }}>{priceZoneLabel}</span>
      </div>
      <div className="relative h-8 rounded-lg overflow-hidden bg-white/[0.04]">
        {zones.map((z) => (
          <div
            key={z.label}
            className="absolute top-0 h-full"
            style={{
              left: toX(z.from),
              width: `calc(${toX(z.to)} - ${toX(z.from)})`,
              background: z.color,
            }}
          />
        ))}
        {/* Fair value line */}
        <div
          className="absolute top-0 h-full w-px bg-white/40"
          style={{ left: toX(fair_value_estimate_dcf) }}
        />
        {/* Current price marker */}
        <div
          className="absolute top-1/2 -translate-y-1/2 w-2.5 h-2.5 rounded-full border-2 border-white shadow-lg"
          style={{ left: `calc(${toX(price)} - 5px)`, background: priceZoneColor }}
        />
      </div>
      <div className="grid grid-cols-4 gap-1 text-[10px]">
        {[
          { label: "Buy",       val: buy_target,      color: "#10b981" },
          { label: "Fair Value",val: fair_value_estimate_dcf, color: "#94a3b8" },
          { label: "Current",  val: price,            color: priceZoneColor },
          { label: "Sell",     val: sell_target,      color: "#ef4444" },
        ].map(({ label, val, color }) => (
          <div key={label} className="text-center">
            <div className="font-mono" style={{ color }}>{fmtUSD(val)}</div>
            <div className="text-[#475569]">{label}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Detail drawer tabs ────────────────────────────────────────────────────────
function DetailDrawer({ asset, onClose }: { asset: AssetValuation; onClose: () => void }) {
  const [tab, setTab] = useState<"overview" | "dcf" | "scores" | "news">("overview");

  const dcf = asset.dcf_assumptions as Record<string, number> | null;

  return (
    <div
      className={`fixed right-0 top-0 h-full w-[420px] z-50 flex flex-col shadow-2xl
        border-l border-white/[0.08] bg-[#0d0d14]/95 backdrop-blur-xl`}
      style={{ animation: "slideIn 0.2s ease" }}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-white/[0.06]">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-lg font-bold text-[#f1f5f9] font-mono">{asset.symbol}</span>
            {asset.tier && TIER_CONFIG[asset.tier] && (
              <span
                className="text-[10px] px-2 py-0.5 rounded-full font-semibold border"
                style={{
                  color: TIER_CONFIG[asset.tier].color,
                  borderColor: `${TIER_CONFIG[asset.tier].color}40`,
                  background: `${TIER_CONFIG[asset.tier].color}12`,
                }}
              >
                {TIER_CONFIG[asset.tier].label}
              </span>
            )}
          </div>
          <div className="text-xs text-[#475569] mt-0.5">{asset.name || asset.symbol}</div>
        </div>
        <button
          onClick={onClose}
          className="w-8 h-8 rounded-lg bg-white/[0.05] hover:bg-white/[0.08] flex items-center justify-center transition-colors text-[#94a3b8]"
        >
          ✕
        </button>
      </div>

      {/* Tabs */}
      <div className="flex px-4 pt-3 gap-1">
        {(["overview", "dcf", "scores", "news"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium capitalize transition-all ${
              tab === t
                ? "bg-indigo-500/20 text-indigo-300 border border-indigo-500/30"
                : "text-[#475569] hover:text-[#94a3b8]"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
        {tab === "overview" && (
          <>
            {/* Key metrics */}
            <div className="grid grid-cols-2 gap-3">
              {[
                { label: "Price",       value: fmtUSD(asset.price) },
                { label: "Composite",   value: asset.composite_score?.toFixed(2) ?? "—" },
                { label: "Margin Safety", value: fmtPct(asset.margin_of_safety_pct) },
                { label: "Rank",        value: asset.rank_in_universe ? `#${asset.rank_in_universe}` : "—" },
                { label: "30d Vol",     value: fmtPct(asset.vol_30d) },
                { label: "Drawdown",    value: fmtPct(asset.drawdown_from_6_12m_high_pct) },
              ].map(({ label, value }) => (
                <div key={label} className="rounded-xl bg-white/[0.03] border border-white/[0.06] p-3">
                  <div className="text-[10px] text-[#475569] uppercase tracking-wide">{label}</div>
                  <div className="text-sm font-mono font-semibold text-[#f1f5f9] mt-1">{value}</div>
                </div>
              ))}
            </div>

            {/* Price zone visualization */}
            <div className={`${glass} p-4`}>
              <div className="text-xs font-semibold text-[#94a3b8] uppercase tracking-wide mb-3">
                Price vs Intrinsic Value
              </div>
              <PriceZoneBar asset={asset} />
            </div>

            {/* Buy gate status */}
            <div
              className={`rounded-xl p-3 border ${
                asset.passes_buy_gate
                  ? "bg-emerald-500/5 border-emerald-500/20"
                  : "bg-white/[0.02] border-white/[0.06]"
              }`}
            >
              <div className="flex items-center gap-2">
                <span className={asset.passes_buy_gate ? "text-emerald-400" : "text-[#475569]"}>
                  {asset.passes_buy_gate ? "✓" : "○"}
                </span>
                <span className="text-xs text-[#94a3b8]">
                  {asset.passes_buy_gate ? "Passes all buy signal requirements" : "Does not meet buy signal gate"}
                </span>
              </div>
            </div>
          </>
        )}

        {tab === "dcf" && (
          <div className="space-y-4">
            {!dcf ? (
              <div className="text-center text-[#475569] text-sm py-8">
                DCF not available (not eligible or insufficient FCF data)
              </div>
            ) : (
              <>
                <div className={`${glass} p-4 space-y-2`}>
                  <div className="text-xs font-semibold text-[#94a3b8] uppercase tracking-wide mb-3">
                    Two-Stage DCF Assumptions
                  </div>
                  {[
                    ["FCF (TTM Base)",  dcf.fcf_base ? `$${(dcf.fcf_base / 1e9).toFixed(1)}B` : "—"],
                    ["Stage 1 Growth (5yr)", dcf.g1 ? `${(dcf.g1 * 100).toFixed(0)}%/yr` : "—"],
                    ["Stage 2 Growth (5yr)", dcf.g2 ? `${(dcf.g2 * 100).toFixed(0)}%/yr` : "—"],
                    ["Discount Rate",   dcf.discount_rate ? `${(dcf.discount_rate * 100).toFixed(0)}%` : "—"],
                    ["Terminal Growth", dcf.g_terminal ? `${(dcf.g_terminal * 100).toFixed(0)}%` : "—"],
                    ["Net Debt",        dcf.net_debt ? `$${(dcf.net_debt / 1e9).toFixed(1)}B` : "$0"],
                  ].map(([label, value]) => (
                    <div key={label} className="flex justify-between py-1 border-b border-white/[0.04]">
                      <span className="text-xs text-[#475569]">{label}</span>
                      <span className="text-xs font-mono text-[#94a3b8]">{value}</span>
                    </div>
                  ))}
                </div>

                <div className={`${glass} p-4`}>
                  <div className="text-xs font-semibold text-[#94a3b8] uppercase tracking-wide mb-3">
                    Value Breakdown
                  </div>
                  {[
                    ["PV Stage 1",   dcf.pv_stage1 ? `$${(dcf.pv_stage1 / 1e9).toFixed(1)}B` : "—", "#10b981"],
                    ["PV Stage 2",   dcf.pv_stage2 ? `$${(dcf.pv_stage2 / 1e9).toFixed(1)}B` : "—", "#6366f1"],
                    ["PV Terminal",  dcf.pv_terminal ? `$${(dcf.pv_terminal / 1e9).toFixed(1)}B` : "—", "#8b5cf6"],
                  ].map(([label, value, color]) => (
                    <div key={label} className="flex justify-between py-1.5">
                      <span className="text-xs text-[#475569] flex items-center gap-1.5">
                        <span className="w-2 h-2 rounded-full inline-block" style={{ background: color as string }} />
                        {label}
                      </span>
                      <span className="text-xs font-mono" style={{ color: color as string }}>{value}</span>
                    </div>
                  ))}
                  <div className="mt-2 pt-2 border-t border-white/[0.08] flex justify-between">
                    <span className="text-xs font-semibold text-[#94a3b8]">Fair Value / Share</span>
                    <span className="text-sm font-mono font-bold text-[#f1f5f9]">
                      {fmtUSD(asset.fair_value_estimate_dcf)}
                    </span>
                  </div>
                </div>
              </>
            )}
          </div>
        )}

        {tab === "scores" && (
          <div className="space-y-4">
            {[
              {
                label: "Value Score",
                score: asset.value_score,
                color: "#6366f1",
                description: "Fama-French HML — low P/E, P/S, P/B vs universe",
                components: [
                  { name: "P/E inverse (35%)", desc: "Lower P/E = cheaper vs peers" },
                  { name: "P/S inverse (25%)", desc: "Lower P/S = better value" },
                  { name: "P/B inverse (25%)", desc: "Lower P/B = closer to assets" },
                  { name: "Dividend yield (15%)", desc: "Higher yield = income component" },
                ],
              },
              {
                label: "Momentum Score",
                score: asset.momentum_score,
                color: "#8b5cf6",
                description: "Carhart MOM — price trend strength",
                components: [
                  { name: "12-1 month return (60%)", desc: "Core momentum, skip recent month" },
                  { name: "3-month return (25%)", desc: "Near-term price trend" },
                  { name: "Earnings revision (15%)", desc: "Analyst estimate direction" },
                ],
              },
              {
                label: "Quality Score",
                score: asset.quality_score,
                color: "#10b981",
                description: "Fama-French RMW+CMA — profitability + balance sheet",
                components: [
                  { name: "ROE (30%)", desc: "Return on equity vs universe" },
                  { name: "Operating margin (25%)", desc: "Profitability efficiency" },
                  { name: "Debt/Equity inverse (25%)", desc: "Lower leverage = better" },
                  { name: "Earnings stability (20%)", desc: "Consistent growth signal" },
                ],
              },
            ].map(({ label, score, color, description, components }) => (
              <div key={label} className={`${glass} p-4`}>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-semibold text-[#94a3b8]">{label}</span>
                  <span className="text-base font-mono font-bold" style={{ color }}>
                    {score?.toFixed(2) ?? "—"}
                  </span>
                </div>
                <div className="w-full h-1.5 rounded-full bg-white/[0.06] mb-3">
                  <div
                    className="h-full rounded-full"
                    style={{ width: `${(score ?? 0) * 100}%`, background: color }}
                  />
                </div>
                <p className="text-[11px] text-[#475569] mb-2">{description}</p>
                <div className="space-y-1">
                  {components.map((c) => (
                    <div key={c.name} className="flex justify-between text-[10px]">
                      <span className="text-[#64748b]">{c.name}</span>
                      <span className="text-[#475569] italic">{c.desc}</span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}

        {tab === "news" && (
          <div className="space-y-3">
            <NewsFeed symbol={asset.symbol} />
          </div>
        )}
      </div>
    </div>
  );
}

// ── News feed ────────────────────────────────────────────────────────────────
function NewsFeed({ symbol }: { symbol: string }) {
  const [news, setNews] = useState<{ headline: string; source: string; url: string; published_at: string }[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetch(`${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/news/${symbol}?limit=5`)
      .then((r) => (r.ok ? r.json() : []))
      .then(setNews)
      .catch(() => setNews([]))
      .finally(() => setLoading(false));
  }, [symbol]);

  if (loading) {
    return (
      <>
        {[1, 2, 3].map((i) => (
          <div key={i} className="rounded-xl h-16 bg-white/[0.03] animate-pulse" />
        ))}
      </>
    );
  }

  if (!news.length) {
    return (
      <div className="text-center text-[#475569] text-sm py-8">
        No recent news available (Finnhub API key may not be configured)
      </div>
    );
  }

  return (
    <>
      {news.map((item, i) => (
        <a
          key={i}
          href={item.url}
          target="_blank"
          rel="noopener noreferrer"
          className={`block ${glass} p-3 hover:bg-white/[0.06] transition-colors`}
        >
          <div className="text-xs text-[#f1f5f9] leading-snug">{item.headline}</div>
          <div className="flex gap-2 mt-1.5 text-[10px] text-[#475569]">
            <span>{item.source}</span>
            <span>·</span>
            <span>{item.published_at ? new Date(item.published_at).toLocaleDateString() : "—"}</span>
          </div>
        </a>
      ))}
    </>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────
export default function AssetsPage() {
  const [data, setData]         = useState<AssetValuation[]>([]);
  const [loading, setLoading]   = useState(true);
  const [error, setError]       = useState<string | null>(null);
  const [selected, setSelected] = useState<AssetValuation | null>(null);

  // Filters
  const [filterClass, setFilterClass]   = useState<string>("");
  const [filterTier, setFilterTier]     = useState<string>("");
  const [filterMoat, setFilterMoat]     = useState<string>("");
  const [minMoS, setMinMoS]             = useState<number>(-50);

  // Sort
  const [sortKey, setSortKey]   = useState<SortKey>("rank_in_universe");
  const [sortDir, setSortDir]   = useState<1 | -1>(1);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      // Fetch all latest valuations via /valuation_summary
      const summary = await api.valuationSummary();
      const all = summary.top_by_composite as AssetValuation[];
      setData(all);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleSort = (key: SortKey) => {
    if (sortKey === key) setSortDir((d) => (d === 1 ? -1 : 1));
    else { setSortKey(key); setSortDir(key === "rank_in_universe" ? 1 : -1); }
  };

  const filtered = data
    .filter((a) => {
      if (filterClass && a.asset_class !== filterClass) return false;
      if (filterTier && a.tier !== filterTier) return false;
      if (filterMoat && a.moat_rating !== filterMoat) return false;
      if ((a.margin_of_safety_pct ?? -1) * 100 < minMoS) return false;
      return true;
    })
    .sort((a, b) => {
      const va = (a[sortKey] ?? 0) as number;
      const vb = (b[sortKey] ?? 0) as number;
      return (va - vb) * sortDir;
    });

  const SortTh = ({ col, label }: { col: SortKey; label: string }) => (
    <th
      className="px-3 py-2.5 text-left text-[10px] uppercase tracking-wider text-[#475569] font-medium cursor-pointer hover:text-[#94a3b8] transition-colors select-none whitespace-nowrap"
      onClick={() => handleSort(col)}
    >
      {label}{" "}
      {sortKey === col && <span className="text-[#6366f1]">{sortDir === 1 ? "↑" : "↓"}</span>}
    </th>
  );

  const classes  = [...new Set(data.map((a) => a.asset_class).filter(Boolean))];
  const tiers    = [...new Set(data.map((a) => a.tier).filter(Boolean))];
  const moats    = [...new Set(data.map((a) => a.moat_rating).filter(Boolean))];

  return (
    <div
      className="min-h-screen p-6"
      style={{
        background:
          "radial-gradient(ellipse 80% 50% at 50% -20%, rgba(99,102,241,0.10) 0%, transparent 60%), #050508",
      }}
    >
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-xl font-bold text-[#f1f5f9]">Assets & Valuations</h1>
        <p className="text-xs text-[#475569] mt-1">
          Fama-French multi-factor scoring · Graham margin of safety · DCF fair values
        </p>
      </div>

      {/* Filter bar */}
      <div className={`${glass} p-4 mb-5 flex flex-wrap gap-3 items-center`}>
        {/* Asset class */}
        <select
          value={filterClass}
          onChange={(e) => setFilterClass(e.target.value)}
          className="bg-white/[0.04] border border-white/[0.08] rounded-lg px-3 py-1.5 text-xs text-[#94a3b8] focus:outline-none focus:border-indigo-500/40"
        >
          <option value="">All Classes</option>
          {classes.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>

        {/* Tier */}
        <select
          value={filterTier}
          onChange={(e) => setFilterTier(e.target.value)}
          className="bg-white/[0.04] border border-white/[0.08] rounded-lg px-3 py-1.5 text-xs text-[#94a3b8] focus:outline-none focus:border-indigo-500/40"
        >
          <option value="">All Tiers</option>
          {tiers.map((t) => <option key={t!} value={t!}>{t}</option>)}
        </select>

        {/* Moat */}
        <select
          value={filterMoat}
          onChange={(e) => setFilterMoat(e.target.value)}
          className="bg-white/[0.04] border border-white/[0.08] rounded-lg px-3 py-1.5 text-xs text-[#94a3b8] focus:outline-none focus:border-indigo-500/40"
        >
          <option value="">All Moats</option>
          {moats.map((m) => <option key={m!} value={m!}>{m}</option>)}
        </select>

        {/* Min MoS slider */}
        <div className="flex items-center gap-2">
          <span className="text-xs text-[#475569] whitespace-nowrap">Min MoS:</span>
          <input
            type="range"
            min={-50} max={30} step={5}
            value={minMoS}
            onChange={(e) => setMinMoS(Number(e.target.value))}
            className="w-24 accent-indigo-500"
          />
          <span className="text-xs font-mono text-[#94a3b8] w-10">{minMoS}%</span>
        </div>

        {/* Refresh */}
        <button
          onClick={load}
          className="ml-auto px-3 py-1.5 rounded-lg text-xs bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 hover:bg-indigo-500/15 transition-colors"
        >
          ↻ Refresh
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="mb-4 p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-sm text-red-400">
          {error}
        </div>
      )}

      {/* Table */}
      <div className={`${glass} overflow-hidden`}>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="border-b border-white/[0.06]">
              <tr>
                <SortTh col="rank_in_universe"     label="Rank" />
                <th className="px-3 py-2.5 text-left text-[10px] uppercase tracking-wider text-[#475569] font-medium">Symbol</th>
                <th className="px-3 py-2.5 text-left text-[10px] uppercase tracking-wider text-[#475569] font-medium">Class</th>
                <SortTh col="price"                label="Price" />
                <SortTh col="margin_of_safety_pct" label="MoS %" />
                <SortTh col="value_score"          label="Value" />
                <SortTh col="momentum_score"       label="Momentum" />
                <SortTh col="quality_score"        label="Quality" />
                <SortTh col="composite_score"      label="Composite" />
                <th className="px-3 py-2.5 text-left text-[10px] uppercase tracking-wider text-[#475569] font-medium">Moat</th>
                <th className="px-3 py-2.5 text-left text-[10px] uppercase tracking-wider text-[#475569] font-medium">Fair Value</th>
                <th className="px-3 py-2.5 text-left text-[10px] uppercase tracking-wider text-[#475569] font-medium">Tier</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                Array.from({ length: 8 }).map((_, i) => (
                  <tr key={i} className="border-b border-white/[0.04]">
                    {Array.from({ length: 12 }).map((_, j) => (
                      <td key={j} className="px-3 py-3">
                        <div className="h-3 rounded bg-white/[0.04] animate-pulse" />
                      </td>
                    ))}
                  </tr>
                ))
              ) : filtered.length === 0 ? (
                <tr>
                  <td colSpan={12} className="px-4 py-12 text-center text-[#475569] text-sm">
                    {data.length === 0
                      ? "No valuations found. Run POST /valuation_update to score assets."
                      : "No assets match the current filters."}
                  </td>
                </tr>
              ) : (
                filtered.map((asset) => {
                  const moat = MOAT_CONFIG[asset.moat_rating ?? ""] ?? null;
                  const tier = TIER_CONFIG[asset.tier ?? ""] ?? null;
                  const mos  = asset.margin_of_safety_pct;

                  return (
                    <tr
                      key={asset.asset_id || asset.symbol}
                      className="border-b border-white/[0.04] hover:bg-white/[0.02] cursor-pointer transition-colors"
                      onClick={() => setSelected(asset)}
                    >
                      {/* Rank */}
                      <td className="px-3 py-3 text-xs font-mono text-[#475569]">
                        #{asset.rank_in_universe ?? "—"}
                      </td>
                      {/* Symbol */}
                      <td className="px-3 py-3">
                        <div className="font-mono font-semibold text-sm text-[#f1f5f9]">
                          {asset.symbol}
                        </div>
                        {asset.name && (
                          <div className="text-[10px] text-[#475569] truncate max-w-[120px]">
                            {asset.name}
                          </div>
                        )}
                      </td>
                      {/* Class badge */}
                      <td className="px-3 py-3">
                        <span
                          className="text-[10px] px-1.5 py-0.5 rounded font-medium"
                          style={{
                            color: CLASS_COLORS[asset.asset_class] ?? "#94a3b8",
                            background: `${CLASS_COLORS[asset.asset_class] ?? "#94a3b8"}18`,
                          }}
                        >
                          {asset.asset_class?.replace("_", " ") ?? "—"}
                        </span>
                      </td>
                      {/* Price */}
                      <td className="px-3 py-3 text-xs font-mono text-[#94a3b8]">
                        {fmtUSD(asset.price)}
                      </td>
                      {/* MoS */}
                      <td className="px-3 py-3">
                        {mos != null ? (
                          <span
                            className="text-xs font-mono font-semibold px-1.5 py-0.5 rounded"
                            style={{
                              color: mosColor(mos),
                              background: `${mosColor(mos)}14`,
                            }}
                          >
                            {fmtPct(mos)}
                          </span>
                        ) : (
                          <span className="text-xs text-[#475569]">—</span>
                        )}
                      </td>
                      {/* Factor score bars */}
                      <td className="px-3 py-3"><ScoreBar value={asset.value_score} /></td>
                      <td className="px-3 py-3"><ScoreBar value={asset.momentum_score} /></td>
                      <td className="px-3 py-3"><ScoreBar value={asset.quality_score} /></td>
                      {/* Composite */}
                      <td className="px-3 py-3">
                        <ScoreBar value={asset.composite_score} />
                      </td>
                      {/* Moat */}
                      <td className="px-3 py-3">
                        {moat ? (
                          <span
                            className="text-[10px] px-1.5 py-0.5 rounded font-medium"
                            style={{ color: moat.color, background: moat.bg }}
                          >
                            {moat.label}
                          </span>
                        ) : (
                          <span className="text-xs text-[#2d3748]">—</span>
                        )}
                      </td>
                      {/* Fair value */}
                      <td className="px-3 py-3 text-xs font-mono text-[#94a3b8]">
                        {fmtUSD(asset.fair_value_estimate_dcf)}
                      </td>
                      {/* Tier */}
                      <td className="px-3 py-3">
                        {tier ? (
                          <span
                            className="text-[10px] px-1.5 py-0.5 rounded-full border font-medium"
                            style={{
                              color: tier.color,
                              borderColor: `${tier.color}40`,
                              background: `${tier.color}12`,
                            }}
                          >
                            {tier.label}
                          </span>
                        ) : null}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Footer stats */}
        {!loading && data.length > 0 && (
          <div className="px-4 py-2 border-t border-white/[0.04] flex gap-4 text-[10px] text-[#475569]">
            <span>{filtered.length} assets shown</span>
            <span>·</span>
            <span>{data.filter(a => (a.margin_of_safety_pct ?? 0) > 0).length} with positive MoS</span>
            <span>·</span>
            <span>{data.filter(a => a.tier === "tier_1" || a.tier === "tier_2").length} opportunities</span>
          </div>
        )}
      </div>

      {/* Detail drawer overlay */}
      {selected && (
        <>
          <div
            className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm"
            onClick={() => setSelected(null)}
          />
          <DetailDrawer asset={selected} onClose={() => setSelected(null)} />
        </>
      )}

      {/* Slide-in animation */}
      <style>{`
        @keyframes slideIn {
          from { transform: translateX(100%); }
          to   { transform: translateX(0); }
        }
      `}</style>
    </div>
  );
}
