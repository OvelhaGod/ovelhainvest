"use client";

/**
 * /tax — Tax lot tracker, HIFO/FIFO/Spec ID, Brazil DARF, loss harvesting.
 * Phase 8 — full implementation.
 * Design: CLAUDE.md Section 35 glassmorphism + Stitch screen 6 reference.
 */

import { useEffect, useState, useCallback } from "react";
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis, ReferenceLine } from "recharts";

// ── Types ─────────────────────────────────────────────────────────────────────

interface TaxLot {
  id: string;
  symbol: string;
  account_name: string;
  tax_treatment: string;
  acquisition_date: string;
  quantity: number;
  cost_basis_per_unit: number;
  current_price?: number;
  current_value?: number;
  cost_basis_total_computed?: number;
  unrealized_gain?: number;
  unrealized_pct?: number;
  holding_period?: string;
  days_held?: number;
  days_to_long_term?: number;
  estimated_tax_if_sold?: number;
  after_tax_proceeds?: number;
  wait_for_lt_savings?: number;
}

interface LotsResponse {
  lots: TaxLot[];
  total_lots: number;
  lot_method: string;
  total_unrealized_gain: number;
  total_estimated_tax: number;
}

interface HarvestCandidate {
  symbol: string;
  lot_id: string;
  account_name: string;
  acquisition_date: string;
  quantity: number;
  unrealized_loss_usd: number;
  unrealized_loss_pct: number;
  estimated_tax_savings: number;
  wash_sale_warning: boolean;
  suggested_replacement: string | null;
  holding_period: string;
}

interface TaxEstimate {
  realized_ytd: {
    year: number;
    net_st: number;
    net_lt: number;
    total_st_gains: number;
    total_lt_gains: number;
    total_st_losses: number;
    total_lt_losses: number;
    estimated_tax_st: number;
    estimated_tax_lt: number;
    total_estimated_tax: number;
  };
  unrealized: {
    total_unrealized_gain: number;
    unrealized_lt_gain: number;
    unrealized_st_gain: number;
    open_positions: number;
  };
  estimated_tax: {
    on_realized_gains: number;
  };
  worst_case: { if_close_everything_today: number };
  harvest_savings: { potential_savings_usd: number };
  net_estimated_tax: number;
}

interface DARFStatus {
  year: number;
  month: number;
  gross_sales_brl: number;
  exemption_limit: number;
  remaining_before_trigger: number;
  exemption_pct_used: number;
  darf_due: number;
  is_triggered: boolean;
  realized_gain_brl: number;
  projected_month_end: number | null;
  recommendation: string;
  history: { year: number; month: number; gross_sales_brl: number; darf_due: number; exemption_used: boolean }[];
}

// ── API helpers ───────────────────────────────────────────────────────────────

const API = process.env.NEXT_PUBLIC_API_URL ?? "https://investapi.ovelha.us";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API}${path}`, { headers: { "Content-Type": "application/json" }, ...init });
  if (!res.ok) throw new Error(`API ${res.status}: ${path}`);
  return res.json() as Promise<T>;
}

// ── Design helpers ────────────────────────────────────────────────────────────

const glass = "glass-card";

function fmtUSD(n: number) {
  const abs = Math.abs(n);
  const prefix = n < 0 ? "-$" : "$";
  if (abs >= 1_000_000) return `${prefix}${(abs / 1_000_000).toFixed(2)}M`;
  if (abs >= 1_000) return `${prefix}${(abs / 1_000).toFixed(1)}K`;
  return `${prefix}${abs.toFixed(0)}`;
}
function fmtBRL(n: number) { return `R$${n.toLocaleString("pt-BR", { maximumFractionDigits: 0 })}`; }
function fmtPct(n: number, signed = true) {
  const s = (n * 100).toFixed(1) + "%";
  return signed && n > 0 ? "+" + s : s;
}
function fmtDate(s: string) {
  try { return new Date(s).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "2-digit" }); }
  catch { return s; }
}

const MONTH_NAMES = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];

// ── Skeleton ──────────────────────────────────────────────────────────────────
function Sk({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse rounded bg-white/[0.06] ${className}`} />;
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function TaxPage() {
  const [lots, setLots]                   = useState<LotsResponse | null>(null);
  const [darf, setDarf]                   = useState<DARFStatus | null>(null);
  const [estimate, setEstimate]           = useState<TaxEstimate | null>(null);
  const [candidates, setCandidates]       = useState<HarvestCandidate[] | null>(null);
  const [loadingLots, setLoadingLots]     = useState(true);
  const [lotsError, setLotsError]         = useState<string | null>(null);
  const [loadingCandidates, setLoadingCandidates] = useState(false);
  const [lotMethod, setLotMethod]         = useState<"hifo" | "fifo" | "spec_id">("hifo");
  const [hpFilter, setHpFilter]           = useState<"all" | "short_term" | "long_term">("all");
  const [symbolFilter, setSymbolFilter]   = useState("");

  const fetchLots = useCallback(async (method: string) => {
    setLoadingLots(true);
    setLotsError(null);
    try {
      const data = await apiFetch<LotsResponse>(`/tax/lots?lot_method=${method}`);
      setLots(data);
    } catch (e) {
      setLotsError(e instanceof Error ? e.message : "Failed to load tax lots");
    }
    finally { setLoadingLots(false); }
  }, []);

  useEffect(() => {
    fetchLots(lotMethod);
    apiFetch<DARFStatus>("/tax/brazil_darf").then(setDarf).catch(() => null);
    apiFetch<TaxEstimate>("/tax/estimate").then(setEstimate).catch(() => null);
  }, [fetchLots, lotMethod]);

  const fetchCandidates = async () => {
    setLoadingCandidates(true);
    setCandidates(null);
    try {
      const data = await apiFetch<{ candidates: HarvestCandidate[]; total_estimated_savings_usd: number }>(
        "/tax/harvest_candidates", { method: "POST", body: JSON.stringify({ min_loss_pct: 0.10 }) }
      );
      setCandidates(data.candidates);
    } catch { setCandidates([]); }
    finally { setLoadingCandidates(false); }
  };

  // Filter lots
  const visibleLots = (lots?.lots ?? []).filter((l) => {
    if (hpFilter !== "all" && l.holding_period !== hpFilter) return false;
    if (symbolFilter && !l.symbol.toUpperCase().includes(symbolFilter.toUpperCase())) return false;
    return true;
  });

  const darfPct = darf ? Math.min(darf.exemption_pct_used * 100, 100) : 0;
  const darfColor = darfPct >= 90 ? "#ef4444" : darfPct >= 60 ? "#f59e0b" : "#10b981";

  return (
    <div className="p-6 space-y-5 min-h-screen" style={{ background: "radial-gradient(ellipse 80% 50% at 50% -20%, rgba(16,185,129,0.06) 0%, transparent 60%), #050508" }}>

      {/* ── Header ── */}
      <div>
        <h1 className="text-xl font-semibold" style={{ color: "#f1f5f9" }}>Tax Optimization</h1>
        <p className="text-xs mt-0.5" style={{ color: "#475569" }}>Lot tracking · DARF · Loss harvesting</p>
      </div>

      {/* ── Brazil DARF Tracker ── */}
      <div className={`${glass} p-5`} style={{ borderColor: `${darfColor}25` }}>
        <div className="flex items-start justify-between mb-4">
          <div>
            <p className="text-xs uppercase tracking-widest" style={{ color: "#475569" }}>Brazil Monthly Exemption</p>
            <p className="text-2xl font-bold font-mono mt-1" style={{ color: darfColor }}>
              {darf ? fmtBRL(darf.gross_sales_brl) : <Sk className="h-7 w-32 inline-block" />}
              <span className="text-sm font-normal ml-2" style={{ color: "#475569" }}>/ R$20,000</span>
            </p>
          </div>
          {darf && (
            <div className="text-right">
              {darf.is_triggered ? (
                <span className="px-3 py-1 rounded-full text-xs font-semibold" style={{ background: "rgba(239,68,68,0.12)", color: "#f87171", border: "1px solid rgba(239,68,68,0.25)" }}>
                  ⚠ DARF Triggered
                </span>
              ) : (
                <span className="px-3 py-1 rounded-full text-xs font-semibold" style={{ background: "rgba(16,185,129,0.10)", color: "#34d399", border: "1px solid rgba(16,185,129,0.2)" }}>
                  ✓ Exempt
                </span>
              )}
              {darf.projected_month_end != null && (
                <p className="text-[10px] mt-1" style={{ color: "#475569" }}>
                  Proj. month-end: {fmtBRL(darf.projected_month_end)}
                </p>
              )}
            </div>
          )}
        </div>

        {/* Progress bar */}
        <div className="relative h-3 rounded-full mb-2" style={{ background: "rgba(255,255,255,0.07)" }}>
          <div className="absolute top-0 h-full rounded-full transition-all duration-700" style={{ width: `${darfPct}%`, background: `linear-gradient(90deg, ${darfColor}88, ${darfColor})` }} />
          {/* Projection overlay */}
          {darf?.projected_month_end != null && (
            <div
              className="absolute top-0 h-full rounded-full opacity-30"
              style={{ width: `${Math.min((darf.projected_month_end / 20000) * 100, 100)}%`, background: darfColor }}
            />
          )}
        </div>
        <div className="flex justify-between text-[10px]" style={{ color: "#475569" }}>
          <span>{darf ? fmtBRL(darf.gross_sales_brl) + " used" : "—"}</span>
          <span>{darf ? fmtBRL(darf.remaining_before_trigger) + " remaining" : "—"}</span>
        </div>

        {darf?.darf_due != null && darf.darf_due > 0 && (
          <div className="mt-3 rounded-xl px-3 py-2 flex items-center gap-2" style={{ background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.2)" }}>
            <span className="text-sm">⚠️</span>
            <p className="text-xs" style={{ color: "#f87171" }}>
              DARF due: <span className="font-mono font-bold">{fmtBRL(darf.darf_due)}</span>
              {" — "}{darf.recommendation}
            </p>
          </div>
        )}
        {darf && !darf.is_triggered && (
          <p className="text-xs mt-2" style={{ color: "#64748b" }}>{darf.recommendation}</p>
        )}

        {/* 12-month history bar chart */}
        {darf && darf.history.length > 0 && (
          <div className="mt-4">
            <p className="text-[10px] uppercase tracking-widest mb-2" style={{ color: "#475569" }}>12-Month Sales History</p>
            <ResponsiveContainer width="100%" height={60}>
              <BarChart data={[...darf.history].reverse().map(h => ({ name: MONTH_NAMES[h.month - 1], sales: h.gross_sales_brl, darf: h.darf_due }))} margin={{ top: 0, right: 0, bottom: 0, left: 0 }}>
                <XAxis dataKey="name" tick={{ fill: "#334155", fontSize: 9 }} axisLine={false} tickLine={false} />
                <Tooltip formatter={(v: number, n: string) => [fmtBRL(v), n === "sales" ? "Sales" : "DARF"]} contentStyle={{ background: "rgba(13,13,20,0.95)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8, fontSize: 11 }} />
                <ReferenceLine y={20000} stroke="rgba(255,255,255,0.15)" strokeDasharray="3 3" />
                <Bar dataKey="sales" radius={[2, 2, 0, 0]}>
                  {[...darf.history].reverse().map((h, i) => (
                    <Cell key={i} fill={h.exemption_used ? "#ef4444" : h.gross_sales_brl > 15000 ? "#f59e0b" : "#10b981"} fillOpacity={0.7} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {/* ── Summary cards row ── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: "Total Unrealized", value: lots ? fmtUSD(lots.total_unrealized_gain) : null, color: lots && lots.total_unrealized_gain >= 0 ? "#10b981" : "#ef4444" },
          { label: "Est. Tax if Sold", value: lots ? fmtUSD(lots.total_estimated_tax) : null, color: "#f59e0b" },
          { label: "Realized YTD Tax", value: estimate ? fmtUSD(estimate.estimated_tax.on_realized_gains) : null, color: "#94a3b8" },
          { label: "Harvest Savings Available", value: estimate ? fmtUSD(estimate.harvest_savings.potential_savings_usd) : null, color: "#10b981" },
        ].map(({ label, value, color }) => (
          <div key={label} className={`${glass} p-4`}>
            <p className="text-[10px] uppercase tracking-widest" style={{ color: "#475569" }}>{label}</p>
            {value == null ? <Sk className="h-7 w-20 mt-1" /> : (
              <p className="text-xl font-bold font-mono mt-1" style={{ color }}>{value}</p>
            )}
          </div>
        ))}
      </div>

      {/* ── Lots Error ── */}
      {lotsError && (
        <div className="rounded-xl border border-error/20 bg-error/10 px-4 py-3 text-error text-sm flex items-center justify-between">
          <span>{lotsError}</span>
          <button onClick={() => fetchLots(lotMethod)} className="text-error/70 hover:text-error underline text-xs">Retry</button>
        </div>
      )}

      {/* ── Tax Lots Table ── */}
      <div className={glass}>
        {/* Filter row */}
        <div className="flex flex-wrap items-center gap-3 p-4 border-b" style={{ borderColor: "rgba(255,255,255,0.06)" }}>
          <p className="text-xs font-semibold" style={{ color: "#f1f5f9" }}>Tax Lots</p>

          {/* Lot method selector */}
          <div className="flex gap-1 ml-auto">
            {(["hifo", "fifo", "spec_id"] as const).map((m) => (
              <button
                key={m}
                onClick={() => setLotMethod(m)}
                className={`px-3 py-1 rounded-lg text-xs font-medium transition-all ${
                  lotMethod === m
                    ? "bg-primary/10 text-primary border border-primary/30"
                    : "bg-transparent text-outline border border-white/[0.06]"
                }`}
              >
                {m.toUpperCase()}
              </button>
            ))}
          </div>

          {/* Holding period filter */}
          <div className="flex gap-1">
            {([["all", "All"], ["short_term", "ST"], ["long_term", "LT"]] as const).map(([val, lbl]) => (
              <button
                key={val}
                onClick={() => setHpFilter(val)}
                className="px-3 py-1 rounded-lg text-xs transition-all"
                style={
                  hpFilter === val
                    ? { background: "rgba(99,102,241,0.15)", color: "#a78bfa", border: "1px solid rgba(99,102,241,0.25)" }
                    : { color: "#475569", border: "1px solid rgba(255,255,255,0.06)" }
                }
              >
                {lbl}
              </button>
            ))}
          </div>

          {/* Symbol search */}
          <input
            value={symbolFilter}
            onChange={(e) => setSymbolFilter(e.target.value)}
            placeholder="Filter symbol…"
            className="px-3 py-1 rounded-lg text-xs outline-none w-28"
            style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)", color: "#f1f5f9" }}
          />
        </div>

        {/* Table */}
        <div className="overflow-x-auto">
          <table className="w-full min-w-[640px] text-xs">
            <thead>
              <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
                {["Symbol", "Account", "Acquired", "Qty", "Cost/Unit", "Price", "Unrlz G/L", "Holding", "Est. Tax", "Wait LT?"].map((h) => (
                  <th key={h} className="py-2.5 px-3 text-left font-medium uppercase tracking-wider" style={{ color: "#475569", fontSize: 10 }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {loadingLots ? (
                Array.from({ length: 6 }).map((_, i) => (
                  <tr key={i}>
                    {Array.from({ length: 10 }).map((_, j) => (
                      <td key={j} className="py-2.5 px-3"><Sk className="h-3.5 w-full" /></td>
                    ))}
                  </tr>
                ))
              ) : visibleLots.length === 0 ? (
                <tr>
                  <td colSpan={10} className="py-12 text-center text-sm" style={{ color: "#475569" }}>
                    No lots found. Run POST /tax/lots/sync to import from transaction history.
                  </td>
                </tr>
              ) : visibleLots.map((lot) => {
                const gain = lot.unrealized_gain ?? 0;
                const gainPct = lot.unrealized_pct ?? 0;
                const isLoss = gain < -0.01;
                const isAmbiguous = (lot.days_to_long_term ?? 365) <= 30 && (lot.days_to_long_term ?? 365) > 0;
                const rowBg = isLoss && Math.abs(gainPct) > 0.10
                  ? "rgba(239,68,68,0.04)"
                  : isAmbiguous
                  ? "rgba(245,158,11,0.03)"
                  : gain > lot.quantity * (lot.cost_basis_per_unit ?? 0) * 0.2
                  ? "rgba(16,185,129,0.03)"
                  : "transparent";

                return (
                  <tr
                    key={lot.id}
                    className="border-b hover:bg-white/[0.015] transition-colors"
                    style={{ borderColor: "rgba(255,255,255,0.04)", background: rowBg }}
                  >
                    <td className="py-2 px-3 font-mono font-semibold" style={{ color: "#f1f5f9" }}>{lot.symbol}</td>
                    <td className="py-2 px-3 max-w-[100px] truncate" style={{ color: "#94a3b8" }}>{lot.account_name}</td>
                    <td className="py-2 px-3 font-mono" style={{ color: "#64748b" }}>{fmtDate(lot.acquisition_date)}</td>
                    <td className="py-2 px-3 font-mono text-right" style={{ color: "#94a3b8" }}>{Number(lot.quantity).toFixed(4)}</td>
                    <td className="py-2 px-3 font-mono text-right" style={{ color: "#64748b" }}>${lot.cost_basis_per_unit.toFixed(2)}</td>
                    <td className="py-2 px-3 font-mono text-right" style={{ color: lot.current_price ? "#f1f5f9" : "#334155" }}>
                      {lot.current_price ? `$${lot.current_price.toFixed(2)}` : "—"}
                    </td>
                    <td className="py-2 px-3 font-mono text-right">
                      {lot.unrealized_gain != null ? (
                        <span style={{ color: gain >= 0 ? "#10b981" : "#ef4444" }}>
                          {gain >= 0 ? "+" : ""}{fmtUSD(gain)}
                          <span className="text-[10px] ml-1" style={{ color: gain >= 0 ? "#34d399" : "#f87171" }}>
                            ({gain >= 0 ? "+" : ""}{fmtPct(gainPct, false)})
                          </span>
                        </span>
                      ) : "—"}
                    </td>
                    <td className="py-2 px-3">
                      {lot.holding_period ? (
                        <span
                          className={`px-2.5 py-0.5 rounded-full text-[10px] font-mono font-semibold uppercase border ${
                            lot.holding_period === "long_term"
                              ? "bg-primary/10 text-primary border-primary/20"
                              : "bg-tertiary/10 text-tertiary border-tertiary/20"
                          }`}
                        >
                          {lot.holding_period === "long_term" ? "LT" : `ST · ${lot.days_held}d`}
                        </span>
                      ) : "—"}
                    </td>
                    <td className="py-2 px-3 font-mono text-right" style={{ color: "#f59e0b" }}>
                      {lot.estimated_tax_if_sold != null ? fmtUSD(lot.estimated_tax_if_sold) : "—"}
                    </td>
                    <td className="py-2 px-3 text-right">
                      {lot.wait_for_lt_savings != null && lot.wait_for_lt_savings > 0 ? (
                        <span className="text-[10px]" style={{ color: "#f59e0b" }}>
                          Wait {lot.days_to_long_term}d → save {fmtUSD(lot.wait_for_lt_savings)}
                        </span>
                      ) : lot.holding_period === "long_term" ? (
                        <span className="text-[10px]" style={{ color: "#34d399" }}>✓ LT</span>
                      ) : "—"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {lots && (
          <div className="px-4 py-2 flex items-center gap-4 text-[10px]" style={{ borderTop: "1px solid rgba(255,255,255,0.05)", color: "#334155" }}>
            <div className="w-2 h-2 rounded" style={{ background: "rgba(16,185,129,0.2)" }} /><span>Gain &gt;20%</span>
            <div className="w-2 h-2 rounded" style={{ background: "rgba(239,68,68,0.2)" }} /><span>Loss &gt;10% (harvest?)</span>
            <div className="w-2 h-2 rounded" style={{ background: "rgba(245,158,11,0.2)" }} /><span>≤30 days to LT treatment</span>
          </div>
        )}
      </div>

      {/* ── Annual Tax Estimate ── */}
      {estimate && (
        <div className={`${glass} p-5`}>
          <p className="text-xs uppercase tracking-widest mb-4" style={{ color: "#475569" }}>
            {estimate.realized_ytd.year} Tax Estimate
          </p>
          <div className="grid grid-cols-2 lg:grid-cols-5 gap-4 text-sm">
            {[
              { label: "Realized YTD Tax",     value: estimate.estimated_tax.on_realized_gains, color: "#94a3b8" },
              { label: "Worst Case (close all)", value: estimate.worst_case.if_close_everything_today, color: "#ef4444" },
              { label: "Harvest Savings",      value: -estimate.harvest_savings.potential_savings_usd, color: "#10b981" },
              { label: "Net Estimated",        value: estimate.net_estimated_tax, color: "#f1f5f9" },
              { label: "Open Positions",       value: estimate.unrealized.open_positions, color: "#a78bfa", isCount: true },
            ].map(({ label, value, color, isCount }) => (
              <div key={label} className="rounded-xl p-3" style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.05)" }}>
                <p className="text-[10px] uppercase tracking-wider" style={{ color: "#475569" }}>{label}</p>
                <p className="text-lg font-bold font-mono mt-1" style={{ color }}>
                  {isCount ? value : `${value < 0 ? "-" : ""}$${Math.abs(Number(value)).toFixed(0)}`}
                </p>
              </div>
            ))}
          </div>
          {estimate.realized_ytd.total_st_gains > 0 || estimate.realized_ytd.total_lt_gains > 0 ? (
            <div className="grid grid-cols-4 gap-3 mt-4 text-xs">
              {[
                { label: "ST Gains", value: estimate.realized_ytd.total_st_gains, color: "#f59e0b" },
                { label: "ST Losses", value: -estimate.realized_ytd.total_st_losses, color: "#10b981" },
                { label: "LT Gains", value: estimate.realized_ytd.total_lt_gains, color: "#f59e0b" },
                { label: "LT Losses", value: -estimate.realized_ytd.total_lt_losses, color: "#10b981" },
              ].map(({ label, value, color }) => (
                <div key={label} className="text-center">
                  <p style={{ color: "#475569" }}>{label}</p>
                  <p className="font-mono font-semibold" style={{ color }}>
                    {value < 0 ? "-" : ""}${Math.abs(value).toFixed(0)}
                  </p>
                </div>
              ))}
            </div>
          ) : null}
        </div>
      )}

      {/* ── Loss Harvest Candidates ── */}
      <div className={`${glass} border-l-2 border-tertiary`}>
        <div className="flex items-center justify-between p-4" style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
          <div>
            <p className="text-sm font-semibold" style={{ color: "#f1f5f9" }}>Loss Harvest Candidates</p>
            <p className="text-xs mt-0.5" style={{ color: "#475569" }}>
              Lots with &gt;10% unrealized loss eligible for tax-loss harvesting
            </p>
          </div>
          <button
            onClick={fetchCandidates}
            disabled={loadingCandidates}
            className="px-4 py-1.5 rounded-xl text-xs font-semibold transition-all"
            style={{ background: "linear-gradient(135deg, #10b981, #059669)", color: "#fff", opacity: loadingCandidates ? 0.5 : 1 }}
          >
            {loadingCandidates ? "Scanning…" : "Find Candidates"}
          </button>
        </div>

        {candidates === null && (
          <div className="py-10 text-center">
            <p className="text-xs" style={{ color: "#334155" }}>Click "Find Candidates" to scan for loss harvesting opportunities.</p>
          </div>
        )}

        {candidates !== null && candidates.length === 0 && (
          <div className="py-10 text-center">
            <span className="text-2xl">✓</span>
            <p className="text-xs mt-2" style={{ color: "#475569" }}>No lots with &gt;10% unrealized loss. Portfolio is in good shape.</p>
          </div>
        )}

        {candidates && candidates.length > 0 && (
          <div className="p-4 space-y-3">
            {candidates.map((c, i) => (
              <div
                key={i}
                className="rounded-xl p-4"
                style={{
                  background: "rgba(239,68,68,0.04)",
                  border: c.wash_sale_warning ? "1px solid rgba(245,158,11,0.25)" : "1px solid rgba(239,68,68,0.15)",
                }}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className="font-mono font-bold text-sm" style={{ color: "#f1f5f9" }}>{c.symbol}</span>
                    <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-error/10 text-error border border-error/20">
                      {c.unrealized_loss_pct.toFixed(1)}% loss
                    </span>
                    {c.wash_sale_warning && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-tertiary/10 text-tertiary border border-tertiary/20">
                        ⚠ Wash Sale Risk
                      </span>
                    )}
                    <span className={`text-[10px] px-1.5 py-0.5 rounded-full border ${c.holding_period === "long_term" ? "bg-primary/10 text-primary border-primary/20" : "bg-tertiary/10 text-tertiary border-tertiary/20"}`}>
                      {c.holding_period === "long_term" ? "LT" : "ST"}
                    </span>
                  </div>
                  <div className="text-right">
                    <p className="text-xs font-mono font-bold" style={{ color: "#10b981" }}>
                      Save {fmtUSD(c.estimated_tax_savings)}
                    </p>
                    <p className="text-[10px]" style={{ color: "#475569" }}>est. tax savings</p>
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-3 text-xs">
                  <div>
                    <p style={{ color: "#475569" }}>Unrealized Loss</p>
                    <p className="font-mono font-semibold" style={{ color: "#ef4444" }}>{fmtUSD(c.unrealized_loss_usd)}</p>
                  </div>
                  <div>
                    <p style={{ color: "#475569" }}>Account</p>
                    <p className="truncate" style={{ color: "#94a3b8" }}>{c.account_name}</p>
                  </div>
                  <div>
                    <p style={{ color: "#475569" }}>Acquired</p>
                    <p className="font-mono" style={{ color: "#64748b" }}>{fmtDate(c.acquisition_date)}</p>
                  </div>
                </div>

                {c.suggested_replacement && (
                  <div className="mt-2 flex items-center gap-2">
                    <p className="text-[10px]" style={{ color: "#475569" }}>
                      Replace with <span className="font-mono font-semibold" style={{ color: "#a78bfa" }}>{c.suggested_replacement}</span>
                      {" "}to maintain market exposure while avoiding wash sale.
                    </p>
                  </div>
                )}

                {c.wash_sale_warning && (
                  <p className="text-[10px] mt-2" style={{ color: "#fbbf24" }}>
                    ⚠ You recently purchased {c.symbol}. Wait 30 days from last purchase before harvesting to avoid wash sale disallowance.
                  </p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

    </div>
  );
}
