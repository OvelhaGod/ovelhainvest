"use client";
/**
 * /finance — Personal Finance Dashboard
 * Monthly summary, income vs expenses, category breakdown, recent transactions.
 */
import useSWR from "swr";
import { fetcher, CACHE_TTL } from "@/lib/swr-config";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from "recharts";
import Link from "next/link";

const glass = "glass-card";
const glassInner = `${glass} p-5`;

function fmtUSD(n: number) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(n);
}
function fmtPct(n: number) {
  return (n >= 0 ? "+" : "") + n.toFixed(1) + "%";
}

function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse rounded-lg bg-white/[0.06] ${className}`} />;
}

interface MonthlySummary {
  month: string;
  total_income: number;
  total_expenses: number;
  savings: number;
  savings_rate: number;
  by_category: Record<string, number>;
}

interface Transaction {
  id: string;
  date: string;
  description: string;
  amount: number;
  type: string;
  categories?: { name: string; color: string; icon: string };
}

const CAT_COLORS = [
  "#10b981","#06b6d4","#8b5cf6","#f59e0b","#ef4444","#3b82f6",
  "#ec4899","#f97316","#a78bfa","#34d399","#fb923c","#60a5fa",
];

export default function FinancePage() {
  const today = new Date();
  const monthStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}`;

  const { data: summary, isLoading: sumLoading } = useSWR<MonthlySummary>(
    `/finance/summary?month=${monthStr}`,
    fetcher,
    { refreshInterval: CACHE_TTL.MEDIUM, keepPreviousData: true }
  );

  const { data: txnsData, isLoading: txnLoading } = useSWR<{ transactions: Transaction[] }>(
    `/transactions?month=${monthStr}&limit=10`,
    fetcher,
    { refreshInterval: CACHE_TTL.MEDIUM, keepPreviousData: true }
  );

  const { data: accounts } = useSWR("/accounts", fetcher, {
    refreshInterval: CACHE_TTL.SLOW,
    keepPreviousData: true,
  });

  // Build bar chart data — last 6 months (use summary for current month + placeholder for past)
  const barData = summary ? [{ month: "This month", income: summary.total_income, expenses: summary.total_expenses }] : [];

  // Pie chart data from by_category
  const pieData = summary?.by_category
    ? Object.entries(summary.by_category)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 8)
        .map(([name, value]) => ({ name, value: Math.round(value) }))
    : [];

  const cashBalance = Array.isArray(accounts)
    ? accounts
        .filter((a: any) => a.account_type === "checking" || a.account_type === "savings")
        .reduce((sum: number, a: any) => sum + (a.current_balance || 0), 0)
    : null;

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-white/90">Personal Finance</h1>
          <p className="text-xs text-white/40 mt-0.5">
            {today.toLocaleDateString("en-US", { month: "long", year: "numeric" })}
          </p>
        </div>
        <div className="flex gap-2">
          <Link href="/transactions" className="text-xs px-3 py-1.5 rounded-lg bg-white/[0.06] text-white/60 hover:bg-white/[0.09] hover:text-white/80 transition-colors">
            Add Transaction
          </Link>
          <Link href="/budget" className="text-xs px-3 py-1.5 rounded-lg bg-white/[0.06] text-white/60 hover:bg-white/[0.09] hover:text-white/80 transition-colors">
            Set Budget
          </Link>
        </div>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          {
            label: "Monthly Income",
            value: sumLoading ? null : fmtUSD(summary?.total_income ?? 0),
            color: "#10b981",
          },
          {
            label: "Monthly Expenses",
            value: sumLoading ? null : fmtUSD(summary?.total_expenses ?? 0),
            color: "#ef4444",
          },
          {
            label: "Savings Rate",
            value: sumLoading ? null : fmtPct(summary?.savings_rate ?? 0),
            color: (summary?.savings_rate ?? 0) >= 20 ? "#10b981" : (summary?.savings_rate ?? 0) >= 10 ? "#f59e0b" : "#ef4444",
          },
          {
            label: "Cash Balance",
            value: cashBalance !== null ? fmtUSD(cashBalance) : "—",
            color: "#06b6d4",
          },
        ].map(({ label, value, color }) => (
          <div key={label} className={glassInner}>
            <p className="text-[10px] text-white/40 uppercase tracking-widest mb-2">{label}</p>
            {value === null ? (
              <Skeleton className="h-8 w-28" />
            ) : (
              <p className="text-2xl font-bold font-mono" style={{ color }}>
                {value}
              </p>
            )}
          </div>
        ))}
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Income vs Expenses bar */}
        <div className={`${glassInner} lg:col-span-2`}>
          <p className="text-xs text-white/40 uppercase tracking-widest mb-4">Income vs Expenses</p>
          {sumLoading ? (
            <Skeleton className="h-40" />
          ) : summary ? (
            <div className="space-y-4">
              {/* Current month summary bars */}
              <div className="space-y-2">
                <div className="flex justify-between text-xs text-white/50 mb-1">
                  <span>Income</span>
                  <span className="font-mono text-[#10b981]">{fmtUSD(summary.total_income)}</span>
                </div>
                <div className="h-2 rounded-full bg-white/[0.06]">
                  <div className="h-full rounded-full bg-[#10b981]" style={{ width: "100%" }} />
                </div>

                <div className="flex justify-between text-xs text-white/50 mb-1 mt-3">
                  <span>Expenses</span>
                  <span className="font-mono text-[#ef4444]">{fmtUSD(summary.total_expenses)}</span>
                </div>
                <div className="h-2 rounded-full bg-white/[0.06]">
                  <div
                    className="h-full rounded-full bg-[#ef4444]"
                    style={{
                      width: summary.total_income > 0
                        ? `${Math.min((summary.total_expenses / summary.total_income) * 100, 100)}%`
                        : "0%",
                    }}
                  />
                </div>

                <div className="flex justify-between text-xs text-white/50 mt-3">
                  <span>Net Savings</span>
                  <span
                    className="font-mono font-semibold"
                    style={{ color: summary.savings >= 0 ? "#10b981" : "#ef4444" }}
                  >
                    {fmtUSD(summary.savings)}
                  </span>
                </div>
              </div>
            </div>
          ) : (
            <div className="h-40 flex items-center justify-center text-xs text-white/20">
              No transactions this month. <Link href="/transactions" className="ml-1 text-primary/60 hover:text-primary">Add one →</Link>
            </div>
          )}
        </div>

        {/* Category donut */}
        <div className={glassInner}>
          <p className="text-xs text-white/40 uppercase tracking-widest mb-4">Expenses by Category</p>
          {sumLoading ? (
            <Skeleton className="h-40" />
          ) : pieData.length > 0 ? (
            <div>
              <ResponsiveContainer width="100%" height={120}>
                <PieChart>
                  <Pie data={pieData} cx="50%" cy="50%" innerRadius={35} outerRadius={55} dataKey="value" strokeWidth={0}>
                    {pieData.map((_, i) => (
                      <Cell key={i} fill={CAT_COLORS[i % CAT_COLORS.length]} />
                    ))}
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
              <div className="space-y-1 mt-2">
                {pieData.slice(0, 5).map((item, i) => (
                  <div key={item.name} className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-1.5">
                      <div className="w-2 h-2 rounded-full shrink-0" style={{ background: CAT_COLORS[i % CAT_COLORS.length] }} />
                      <span className="text-white/60 truncate max-w-[100px]">{item.name}</span>
                    </div>
                    <span className="font-mono text-white/50">{fmtUSD(item.value)}</span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="h-40 flex items-center justify-center text-xs text-white/20">No expenses yet</div>
          )}
        </div>
      </div>

      {/* Recent transactions */}
      <div className={glassInner}>
        <div className="flex items-center justify-between mb-4">
          <p className="text-xs text-white/40 uppercase tracking-widest">Recent Transactions</p>
          <Link href="/transactions" className="text-xs text-white/30 hover:text-white/50 transition-colors">
            View all →
          </Link>
        </div>
        {txnLoading ? (
          <div className="space-y-2">
            {[...Array(5)].map((_, i) => <Skeleton key={i} className="h-10" />)}
          </div>
        ) : (txnsData?.transactions?.length ?? 0) > 0 ? (
          <div className="space-y-1">
            {(txnsData?.transactions ?? []).map((txn) => {
              const isIncome = txn.type === "income";
              const catColor = txn.categories?.color ?? "#6b7280";
              const d = new Date(txn.date);
              const dateStr = d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
              return (
                <div key={txn.id} className="flex items-center justify-between py-2 px-2 rounded-lg hover:bg-white/[0.02] transition-colors">
                  <div className="flex items-center gap-3 min-w-0">
                    <div
                      className="w-7 h-7 rounded-full flex items-center justify-center shrink-0 text-xs"
                      style={{ background: catColor + "22", border: `1px solid ${catColor}33` }}
                    >
                      {isIncome ? "↑" : "↓"}
                    </div>
                    <div className="min-w-0">
                      <p className="text-xs text-white/80 truncate">{txn.description}</p>
                      <p className="text-[10px] text-white/30">{txn.categories?.name ?? "Uncategorized"} · {dateStr}</p>
                    </div>
                  </div>
                  <span
                    className="font-mono text-sm font-semibold shrink-0 ml-3"
                    style={{ color: isIncome ? "#10b981" : "#ef4444" }}
                  >
                    {isIncome ? "+" : "-"}{fmtUSD(Math.abs(txn.amount))}
                  </span>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="py-8 text-center text-xs text-white/20">
            No transactions yet.{" "}
            <Link href="/transactions" className="text-primary/60 hover:text-primary">Add your first →</Link>
          </div>
        )}
      </div>
    </div>
  );
}
