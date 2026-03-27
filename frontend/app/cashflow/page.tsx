"use client";
/**
 * /cashflow — Cash Flow Forecast
 * 90-day projected balance, upcoming bills/income timeline.
 */
import useSWR from "swr";
import { fetcher, CACHE_TTL } from "@/lib/swr-config";
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine } from "recharts";

const glass = "glass-card";
const glassInner = `${glass} p-5`;

function fmtUSD(n: number) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(n);
}

function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse rounded-lg bg-white/[0.06] ${className}`} />;
}

interface CashflowDay {
  date: string;
  projected_balance: number;
  events: { name: string; amount: number; type: string }[];
  is_today: boolean;
}

interface CashflowData {
  current_balance: number;
  projection: CashflowDay[];
}

interface RecurringItem {
  id: string;
  name: string;
  amount: number;
  direction: string;
  frequency: string;
  next_date: string;
  category?: string;
}

export default function CashflowPage() {
  const { data, isLoading } = useSWR<CashflowData>(
    "/finance/cashflow",
    fetcher,
    { refreshInterval: CACHE_TTL.MEDIUM, keepPreviousData: true }
  );

  const { data: recurring, isLoading: recurLoading } = useSWR<RecurringItem[]>(
    "/recurring",
    fetcher,
    { refreshInterval: CACHE_TTL.SLOW, keepPreviousData: true }
  );

  const projection = data?.projection ?? [];
  const currentBalance = data?.current_balance ?? 0;

  // Build chart data — sample every 3 days to reduce clutter
  const chartData = projection
    .filter((_, i) => i % 3 === 0 || projection[i]?.is_today)
    .map((d) => ({
      date: new Date(d.date).toLocaleDateString("en-US", { month: "short", day: "numeric" }),
      balance: Math.round(d.projected_balance),
      danger: d.projected_balance < 500,
      is_today: d.is_today,
    }));

  const todayIdx = projection.findIndex((d) => d.is_today);
  const minProjected = Math.min(...projection.map((d) => d.projected_balance));
  const maxProjected = Math.max(...projection.map((d) => d.projected_balance));

  // Upcoming events — next 30 days
  const upcomingEvents = projection
    .slice(0, 30)
    .flatMap((d) =>
      d.events.map((e) => ({
        ...e,
        date: d.date,
        is_today: d.is_today,
      }))
    )
    .filter((e) => e.amount !== 0);

  // Upcoming recurring items sorted by next_date
  const upcomingRecurring = (recurring ?? [])
    .filter((r) => r.next_date)
    .sort((a, b) => new Date(a.next_date).getTime() - new Date(b.next_date).getTime())
    .slice(0, 10);

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const val = payload[0].value;
      return (
        <div className="glass-card p-3 text-xs">
          <p className="text-white/50 mb-1">{label}</p>
          <p className="font-mono font-semibold" style={{ color: val < 500 ? "#ef4444" : "#10b981" }}>
            {fmtUSD(val)}
          </p>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-white/90">Cash Flow</h1>
          <p className="text-xs text-white/40 mt-0.5">90-day balance forecast</p>
        </div>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: "Current Balance", value: isLoading ? null : fmtUSD(currentBalance), color: "#06b6d4" },
          { label: "Min (90 days)", value: isLoading ? null : fmtUSD(minProjected), color: minProjected < 500 ? "#ef4444" : "#f59e0b" },
          { label: "Max (90 days)", value: isLoading ? null : fmtUSD(maxProjected), color: "#10b981" },
        ].map(({ label, value, color }) => (
          <div key={label} className={glassInner}>
            <p className="text-[10px] text-white/40 uppercase tracking-widest mb-2">{label}</p>
            {value === null ? (
              <div className="h-8 w-28 animate-pulse rounded bg-white/[0.06]" />
            ) : (
              <p className="text-xl font-bold font-mono" style={{ color }}>{value}</p>
            )}
          </div>
        ))}
      </div>

      {/* Projection chart */}
      <div className={glassInner}>
        <p className="text-xs text-white/40 uppercase tracking-widest mb-4">90-Day Balance Projection</p>
        {isLoading ? (
          <Skeleton className="h-52" />
        ) : chartData.length > 0 ? (
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={chartData} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="balanceGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.25} />
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0.02} />
                </linearGradient>
                <linearGradient id="dangerGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#ef4444" stopOpacity={0.25} />
                  <stop offset="95%" stopColor="#ef4444" stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <XAxis
                dataKey="date"
                tick={{ fill: "rgba(255,255,255,0.3)", fontSize: 10 }}
                tickLine={false}
                axisLine={false}
                interval={Math.floor(chartData.length / 5)}
              />
              <YAxis
                tick={{ fill: "rgba(255,255,255,0.3)", fontSize: 10 }}
                tickLine={false}
                axisLine={false}
                tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
                width={40}
              />
              <Tooltip content={<CustomTooltip />} />
              <ReferenceLine y={500} stroke="rgba(239,68,68,0.4)" strokeDasharray="4 4" label={{ value: "Danger $500", fill: "rgba(239,68,68,0.5)", fontSize: 9 }} />
              {todayIdx >= 0 && (
                <ReferenceLine
                  x={chartData.find((d) => d.is_today)?.date}
                  stroke="rgba(255,255,255,0.2)"
                  strokeDasharray="3 3"
                  label={{ value: "Today", fill: "rgba(255,255,255,0.3)", fontSize: 9 }}
                />
              )}
              <Area
                type="monotone"
                dataKey="balance"
                stroke="#10b981"
                strokeWidth={2}
                fill="url(#balanceGrad)"
                dot={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        ) : (
          <div className="h-52 flex items-center justify-center text-xs text-white/20">
            No cashflow data. Add recurring items to generate a forecast.
          </div>
        )}
      </div>

      {/* Upcoming events */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Event timeline */}
        <div className={glassInner}>
          <p className="text-xs text-white/40 uppercase tracking-widest mb-4">Upcoming Events (30 days)</p>
          {isLoading ? (
            <div className="space-y-2">
              {[...Array(5)].map((_, i) => <Skeleton key={i} className="h-10" />)}
            </div>
          ) : upcomingEvents.length > 0 ? (
            <div className="space-y-1">
              {upcomingEvents.slice(0, 8).map((e, i) => {
                const isIncome = e.type === "income";
                const d = new Date(e.date);
                return (
                  <div key={i} className="flex items-center justify-between py-2 px-2 rounded-lg hover:bg-white/[0.02] transition-colors">
                    <div className="flex items-center gap-3 min-w-0">
                      <div
                        className="w-7 h-7 rounded-full flex items-center justify-center text-xs shrink-0"
                        style={{
                          background: isIncome ? "rgba(16,185,129,0.15)" : "rgba(239,68,68,0.15)",
                          border: `1px solid ${isIncome ? "rgba(16,185,129,0.3)" : "rgba(239,68,68,0.3)"}`,
                        }}
                      >
                        {isIncome ? "+" : "-"}
                      </div>
                      <div className="min-w-0">
                        <p className="text-xs text-white/80 truncate">{e.name}</p>
                        <p className="text-[10px] text-white/30">
                          {e.is_today ? "Today" : d.toLocaleDateString("en-US", { month: "short", day: "numeric" })}
                        </p>
                      </div>
                    </div>
                    <span
                      className="font-mono text-sm font-semibold shrink-0 ml-3"
                      style={{ color: isIncome ? "#10b981" : "#ef4444" }}
                    >
                      {isIncome ? "+" : "-"}{fmtUSD(Math.abs(e.amount))}
                    </span>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="py-8 text-center text-xs text-white/20">
              No upcoming events. Add recurring items to track bills and income.
            </div>
          )}
        </div>

        {/* Recurring items */}
        <div className={glassInner}>
          <p className="text-xs text-white/40 uppercase tracking-widest mb-4">Recurring Schedule</p>
          {recurLoading ? (
            <div className="space-y-2">
              {[...Array(5)].map((_, i) => <Skeleton key={i} className="h-10" />)}
            </div>
          ) : upcomingRecurring.length > 0 ? (
            <div className="space-y-1">
              {upcomingRecurring.map((r) => {
                const isIncome = r.direction === "income";
                const nextDate = new Date(r.next_date);
                const daysUntil = Math.ceil((nextDate.getTime() - Date.now()) / (1000 * 60 * 60 * 24));
                return (
                  <div key={r.id} className="flex items-center justify-between py-2 px-2 rounded-lg hover:bg-white/[0.02] transition-colors">
                    <div className="flex items-center gap-3 min-w-0">
                      <div
                        className="w-7 h-7 rounded-full flex items-center justify-center text-xs shrink-0 font-mono"
                        style={{
                          background: isIncome ? "rgba(16,185,129,0.15)" : "rgba(239,68,68,0.15)",
                          border: `1px solid ${isIncome ? "rgba(16,185,129,0.3)" : "rgba(239,68,68,0.3)"}`,
                          color: isIncome ? "#10b981" : "#ef4444",
                        }}
                      >
                        {daysUntil <= 0 ? "!" : daysUntil}
                      </div>
                      <div className="min-w-0">
                        <p className="text-xs text-white/80 truncate">{r.name}</p>
                        <p className="text-[10px] text-white/30">
                          {r.frequency} · {nextDate.toLocaleDateString("en-US", { month: "short", day: "numeric" })}
                        </p>
                      </div>
                    </div>
                    <span
                      className="font-mono text-sm font-semibold shrink-0 ml-3"
                      style={{ color: isIncome ? "#10b981" : "#ef4444" }}
                    >
                      {isIncome ? "+" : "-"}{fmtUSD(Math.abs(r.amount))}
                    </span>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="py-8 text-center text-xs text-white/20">
              No recurring items. Add bills and income to forecast your cashflow.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
