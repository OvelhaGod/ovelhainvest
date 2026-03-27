"use client";
/**
 * /net-worth — Net Worth Overview
 * Hero net worth, assets vs liabilities breakdown, trend chart, account list, Connect Account.
 */
import { useState } from "react";
import useSWR from "swr";
import { fetcher, CACHE_TTL } from "@/lib/swr-config";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { PluggyConnectWidget } from "@/components/finance/PluggyConnectWidget";

const glass = "glass-card";
const glassInner = `${glass} p-5`;

function fmtUSD(n: number) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(n);
}

function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse rounded-lg bg-white/[0.06] ${className}`} />;
}

interface NetWorthData {
  net_worth_usd: number;
  total_assets_usd: number;
  total_liabilities_usd: number;
  cash_usd: number;
  breakdown: {
    investment: number;
    cash: number;
    other: number;
    liabilities: number;
  };
}

interface Account {
  id: string;
  name: string;
  institution: string;
  account_type: string;
  current_balance: number;
  currency: string;
  is_liability: boolean;
  last_synced_at?: string;
}

interface NetWorthHistory {
  history: { date: string; net_worth_usd: number }[];
}

export default function NetWorthPage() {
  const [showConnect, setShowConnect] = useState(false);

  const { data: netWorth, isLoading: nwLoading } = useSWR<NetWorthData>(
    "/finance/net_worth",
    fetcher,
    { refreshInterval: CACHE_TTL.MEDIUM, keepPreviousData: true }
  );

  const { data: historyData, isLoading: histLoading } = useSWR<NetWorthHistory>(
    "/finance/net_worth/history",
    fetcher,
    { refreshInterval: CACHE_TTL.SLOW, keepPreviousData: true }
  );

  const { data: accounts, isLoading: acctLoading } = useSWR<Account[]>(
    "/accounts",
    fetcher,
    { refreshInterval: CACHE_TTL.SLOW, keepPreviousData: true }
  );

  const assets = (accounts ?? []).filter((a) => !a.is_liability);
  const liabilities = (accounts ?? []).filter((a) => a.is_liability);

  const history = (historyData?.history ?? []).map((h) => ({
    date: new Date(h.date).toLocaleDateString("en-US", { month: "short", day: "numeric" }),
    value: Math.round(h.net_worth_usd),
  }));

  const prevNetWorth = history.length >= 2 ? history[history.length - 2]?.value : null;
  const netWorthChange = prevNetWorth && netWorth ? netWorth.net_worth_usd - prevNetWorth : null;
  const netWorthChangePct = prevNetWorth && netWorthChange ? (netWorthChange / prevNetWorth) * 100 : null;

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="glass-card p-3 text-xs">
          <p className="text-white/50 mb-1">{label}</p>
          <p className="font-mono font-semibold text-white/90">{fmtUSD(payload[0].value)}</p>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-white/90">Net Worth</h1>
          <p className="text-xs text-white/40 mt-0.5">Assets minus liabilities</p>
        </div>
        <button
          onClick={() => setShowConnect(true)}
          className="text-xs px-3 py-1.5 rounded-lg bg-[rgba(16,185,129,0.15)] border border-[rgba(16,185,129,0.3)] text-[#10b981] hover:bg-[rgba(16,185,129,0.2)] transition-colors"
        >
          + Connect Account
        </button>
      </div>

      {/* Hero net worth */}
      <div className={`${glassInner} relative overflow-hidden`}>
        <div
          className="absolute inset-0 opacity-10"
          style={{ background: "radial-gradient(ellipse at top left, #10b981, transparent 60%)" }}
        />
        <p className="text-[10px] text-white/40 uppercase tracking-widest mb-1 relative">Net Worth</p>
        {nwLoading ? (
          <Skeleton className="h-12 w-48 mb-2" />
        ) : (
          <>
            <p className="text-5xl font-bold font-mono text-white/95 relative">
              {fmtUSD(netWorth?.net_worth_usd ?? 0)}
            </p>
            {netWorthChange !== null && (
              <p className="text-sm font-mono mt-1 relative" style={{ color: netWorthChange >= 0 ? "#10b981" : "#ef4444" }}>
                {netWorthChange >= 0 ? "+" : ""}{fmtUSD(netWorthChange)}{" "}
                <span className="text-xs opacity-70">
                  ({netWorthChangePct !== null ? (netWorthChangePct >= 0 ? "+" : "") + netWorthChangePct.toFixed(2) + "%" : ""} from last snapshot)
                </span>
              </p>
            )}
          </>
        )}
      </div>

      {/* Assets vs Liabilities summary */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: "Total Assets", value: nwLoading ? null : fmtUSD(netWorth?.total_assets_usd ?? 0), color: "#10b981" },
          { label: "Total Liabilities", value: nwLoading ? null : fmtUSD(netWorth?.total_liabilities_usd ?? 0), color: "#ef4444" },
          { label: "Cash & Bank", value: nwLoading ? null : fmtUSD(netWorth?.cash_usd ?? 0), color: "#06b6d4" },
        ].map(({ label, value, color }) => (
          <div key={label} className={glassInner}>
            <p className="text-[10px] text-white/40 uppercase tracking-widest mb-2">{label}</p>
            {value === null ? (
              <Skeleton className="h-8 w-28" />
            ) : (
              <p className="text-xl font-bold font-mono" style={{ color }}>{value}</p>
            )}
          </div>
        ))}
      </div>

      {/* Net worth trend + breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Trend chart */}
        <div className={`${glassInner} lg:col-span-2`}>
          <p className="text-xs text-white/40 uppercase tracking-widest mb-4">Net Worth Trend</p>
          {histLoading ? (
            <Skeleton className="h-44" />
          ) : history.length > 1 ? (
            <ResponsiveContainer width="100%" height={176}>
              <LineChart data={history} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
                <XAxis
                  dataKey="date"
                  tick={{ fill: "rgba(255,255,255,0.3)", fontSize: 10 }}
                  tickLine={false}
                  axisLine={false}
                  interval={Math.floor(history.length / 6)}
                />
                <YAxis
                  tick={{ fill: "rgba(255,255,255,0.3)", fontSize: 10 }}
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
                  width={40}
                />
                <Tooltip content={<CustomTooltip />} />
                <Line
                  type="monotone"
                  dataKey="value"
                  stroke="#10b981"
                  strokeWidth={2}
                  dot={false}
                  activeDot={{ r: 4, fill: "#10b981" }}
                />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-44 flex items-center justify-center text-xs text-white/20">
              Not enough history to show trend.
            </div>
          )}
        </div>

        {/* Breakdown */}
        <div className={glassInner}>
          <p className="text-xs text-white/40 uppercase tracking-widest mb-4">Breakdown</p>
          {nwLoading ? (
            <div className="space-y-3">
              {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-8" />)}
            </div>
          ) : netWorth ? (
            <div className="space-y-3">
              {[
                { label: "Investments", value: netWorth.breakdown.investment, color: "#8b5cf6" },
                { label: "Cash", value: netWorth.breakdown.cash, color: "#06b6d4" },
                { label: "Other Assets", value: netWorth.breakdown.other, color: "#6b7280" },
                { label: "Liabilities", value: -netWorth.breakdown.liabilities, color: "#ef4444" },
              ].map(({ label, value, color }) => {
                const total = netWorth.total_assets_usd || 1;
                const pct = Math.abs(value) / total * 100;
                return (
                  <div key={label}>
                    <div className="flex justify-between text-xs mb-1">
                      <span className="text-white/50">{label}</span>
                      <span className="font-mono" style={{ color }}>{value >= 0 ? "" : "-"}{fmtUSD(Math.abs(value))}</span>
                    </div>
                    <div className="h-1 rounded-full bg-white/[0.06]">
                      <div className="h-full rounded-full" style={{ width: `${Math.min(pct, 100)}%`, background: color }} />
                    </div>
                  </div>
                );
              })}
            </div>
          ) : null}
        </div>
      </div>

      {/* Accounts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Asset accounts */}
        <div className={glassInner}>
          <p className="text-xs text-white/40 uppercase tracking-widest mb-4">Accounts</p>
          {acctLoading ? (
            <div className="space-y-2">{[...Array(4)].map((_, i) => <Skeleton key={i} className="h-12" />)}</div>
          ) : assets.length > 0 ? (
            <div className="space-y-1">
              {assets.map((a) => (
                <div key={a.id} className="flex items-center justify-between py-2.5 px-2 rounded-lg hover:bg-white/[0.02] transition-colors">
                  <div className="min-w-0">
                    <p className="text-xs text-white/80 truncate">{a.name}</p>
                    <p className="text-[10px] text-white/30">{a.institution ?? a.account_type}</p>
                  </div>
                  <div className="text-right shrink-0 ml-3">
                    <p className="font-mono text-sm text-white/80">{fmtUSD(a.current_balance ?? 0)}</p>
                    {a.last_synced_at && (
                      <p className="text-[10px] text-white/20">
                        synced {new Date(a.last_synced_at).toLocaleDateString("en-US", { month: "short", day: "numeric" })}
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="py-8 text-center text-xs text-white/20">
              No accounts yet.{" "}
              <button onClick={() => setShowConnect(true)} className="text-[#10b981]/60 hover:text-[#10b981]">
                Connect one →
              </button>
            </div>
          )}
        </div>

        {/* Liabilities */}
        <div className={glassInner}>
          <p className="text-xs text-white/40 uppercase tracking-widest mb-4">Liabilities</p>
          {acctLoading ? (
            <div className="space-y-2">{[...Array(2)].map((_, i) => <Skeleton key={i} className="h-12" />)}</div>
          ) : liabilities.length > 0 ? (
            <div className="space-y-1">
              {liabilities.map((a) => (
                <div key={a.id} className="flex items-center justify-between py-2.5 px-2 rounded-lg hover:bg-white/[0.02] transition-colors">
                  <div className="min-w-0">
                    <p className="text-xs text-white/80 truncate">{a.name}</p>
                    <p className="text-[10px] text-white/30">{a.institution ?? a.account_type}</p>
                  </div>
                  <p className="font-mono text-sm text-[#ef4444] shrink-0 ml-3">
                    -{fmtUSD(Math.abs(a.current_balance ?? 0))}
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <div className="py-8 text-center text-xs text-white/20">No liabilities tracked.</div>
          )}
        </div>
      </div>

      {/* Connect Account modal stub */}
      {showConnect && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="glass-card p-6 w-full max-w-sm space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-white/90">Connect Account</h2>
              <button onClick={() => setShowConnect(false)} className="text-white/30 hover:text-white/60 text-lg leading-none">×</button>
            </div>
            <p className="text-xs text-white/50">
              Connect your Brazilian bank or broker via Pluggy Open Finance to automatically sync account balances and transactions.
            </p>
            <PluggyConnectWidget
              onSuccess={(itemId) => {
                // After successful connection, trigger sync then close
                const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "https://investapi.ovelha.us";
                fetch(`${API_BASE}/connections/sync/${itemId}`, { method: "POST" })
                  .then(() => setShowConnect(false))
                  .catch(() => setShowConnect(false));
              }}
              onClose={() => setShowConnect(false)}
            />
          </div>
        </div>
      )}
    </div>
  );
}
