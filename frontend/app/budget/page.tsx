"use client";
/**
 * /budget — Budget vs Actual
 * Monthly targets per category with progress bars.
 */
import { useState } from "react";
import useSWR from "swr";
import { fetcher, CACHE_TTL } from "@/lib/swr-config";

const glass = "glass-card";
const glassInner = `${glass} p-5`;

function fmtUSD(n: number) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(n);
}

function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse rounded-lg bg-white/[0.06] ${className}`} />;
}

interface BudgetRow {
  id: string;
  amount: number;
  spent: number;
  remaining: number;
  pct_used: number;
  categories?: { id: string; name: string; color: string; icon: string };
}

export default function BudgetPage() {
  const today = new Date();
  const defaultMonth = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}-01`;

  const months: string[] = [];
  for (let i = 0; i < 6; i++) {
    const d = new Date(today.getFullYear(), today.getMonth() - i, 1);
    months.push(`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-01`);
  }

  const [selectedMonth, setSelectedMonth] = useState(defaultMonth);
  const [showSetBudget, setShowSetBudget] = useState(false);

  const { data, isLoading, mutate } = useSWR<{ month: string; budgets: BudgetRow[] }>(
    `/budgets?month=${selectedMonth}`,
    fetcher,
    { refreshInterval: CACHE_TTL.MEDIUM, keepPreviousData: true }
  );

  const { data: categories } = useSWR("/categories", fetcher, { refreshInterval: CACHE_TTL.STATIC });

  const budgets = data?.budgets ?? [];
  const totalBudgeted = budgets.reduce((s, b) => s + b.amount, 0);
  const totalSpent = budgets.reduce((s, b) => s + b.spent, 0);
  const overBudget = budgets.filter((b) => b.pct_used > 100).length;

  function progressColor(pct: number) {
    if (pct > 100) return "#ef4444";
    if (pct > 80) return "#f59e0b";
    return "#10b981";
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-white/90">Budget</h1>
          <p className="text-xs text-white/40 mt-0.5">Monthly spending targets</p>
        </div>
        <div className="flex gap-2 items-center">
          <select
            value={selectedMonth}
            onChange={(e) => setSelectedMonth(e.target.value)}
            className="text-xs text-white/60 px-3 py-1.5 rounded-lg outline-none cursor-pointer"
            style={{ background: "rgba(31,32,33,0.6)", border: "1px solid rgba(255,255,255,0.08)" }}
          >
            {months.map((m) => (
              <option key={m} value={m} style={{ background: "#1f2021" }}>
                {new Date(m).toLocaleDateString("en-US", { month: "long", year: "numeric" })}
              </option>
            ))}
          </select>
          <button
            onClick={() => setShowSetBudget(true)}
            className="text-xs px-3 py-1.5 rounded-lg bg-[rgba(16,185,129,0.15)] border border-[rgba(16,185,129,0.3)] text-[#10b981] hover:bg-[rgba(16,185,129,0.2)] transition-colors"
          >
            Edit Budgets
          </button>
        </div>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: "Total Budgeted", value: fmtUSD(totalBudgeted), color: "#94a3b8" },
          { label: "Total Spent", value: fmtUSD(totalSpent), color: totalSpent > totalBudgeted ? "#ef4444" : "#10b981" },
          { label: "Over Budget", value: `${overBudget} categories`, color: overBudget > 0 ? "#f59e0b" : "#10b981" },
        ].map(({ label, value, color }) => (
          <div key={label} className={glassInner}>
            <p className="text-[10px] text-white/40 uppercase tracking-widest mb-2">{label}</p>
            <p className="text-xl font-bold font-mono" style={{ color }}>{value}</p>
          </div>
        ))}
      </div>

      {/* Budget cards grid */}
      {isLoading ? (
        <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(6)].map((_, i) => <Skeleton key={i} className="h-28" />)}
        </div>
      ) : budgets.length > 0 ? (
        <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
          {budgets.map((b) => {
            const color = progressColor(b.pct_used);
            const catColor = b.categories?.color ?? "#6b7280";
            return (
              <div key={b.id} className={glassInner} style={{ borderColor: b.pct_used > 100 ? "rgba(239,68,68,0.2)" : undefined }}>
                <div className="flex items-center gap-2 mb-3">
                  <div
                    className="w-7 h-7 rounded-full flex items-center justify-center text-xs shrink-0"
                    style={{ background: catColor + "22", border: `1px solid ${catColor}33` }}
                  >
                    $
                  </div>
                  <span className="text-xs text-white/70 font-medium truncate">
                    {b.categories?.name ?? "Budget"}
                  </span>
                  {b.pct_used > 100 && (
                    <span className="text-[10px] px-1 py-0.5 rounded bg-[rgba(239,68,68,0.1)] text-[#ef4444] border border-[rgba(239,68,68,0.2)] ml-auto shrink-0">
                      Over
                    </span>
                  )}
                </div>

                {/* Progress bar */}
                <div className="h-1.5 rounded-full bg-white/[0.06] mb-2 overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all"
                    style={{ width: `${Math.min(b.pct_used, 100)}%`, background: color }}
                  />
                </div>

                <div className="flex justify-between text-xs">
                  <span className="text-white/40">{fmtUSD(b.spent)} spent</span>
                  <span className="font-mono" style={{ color }}>
                    {b.pct_used.toFixed(0)}%
                  </span>
                </div>
                <div className="text-[10px] text-white/25 mt-0.5">
                  {b.remaining >= 0 ? fmtUSD(b.remaining) + " remaining" : fmtUSD(Math.abs(b.remaining)) + " over"} of {fmtUSD(b.amount)}
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className={`${glassInner} py-10 text-center`}>
          <p className="text-sm text-white/30">No budgets set for this month.</p>
          <p className="text-xs text-white/20 mt-1">
            Click "Edit Budgets" to set monthly spending targets per category.
          </p>
          <button
            onClick={() => setShowSetBudget(true)}
            className="mt-4 text-xs px-4 py-2 rounded-lg bg-[rgba(16,185,129,0.15)] border border-[rgba(16,185,129,0.3)] text-[#10b981]"
          >
            Set Your First Budget
          </button>
        </div>
      )}

      {/* Set budget modal */}
      {showSetBudget && (
        <SetBudgetModal
          month={selectedMonth}
          categories={(categories ?? []).filter((c: any) => c.type === "expense")}
          onClose={() => setShowSetBudget(false)}
          onSaved={() => { mutate(); setShowSetBudget(false); }}
        />
      )}
    </div>
  );
}

function SetBudgetModal({
  month, categories, onClose, onSaved
}: {
  month: string;
  categories: any[];
  onClose: () => void;
  onSaved: () => void;
}) {
  const [budgets, setBudgets] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "https://investapi.ovelha.us";

  async function handleSave() {
    setSaving(true);
    try {
      const entries = Object.entries(budgets).filter(([, v]) => v && parseFloat(v) > 0);
      await Promise.all(
        entries.map(([cat_id, amount]) =>
          fetch(`${API_BASE}/budgets`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ category_id: cat_id, month, amount: parseFloat(amount) }),
          })
        )
      );
      onSaved();
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="glass-card p-6 w-full max-w-md max-h-[80vh] flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-white/90">Set Monthly Budgets</h2>
          <button onClick={onClose} className="text-white/30 hover:text-white/60 text-lg leading-none">×</button>
        </div>
        <div className="overflow-y-auto space-y-2 flex-1">
          {categories.map((cat) => (
            <div key={cat.id} className="flex items-center gap-3">
              <div
                className="w-6 h-6 rounded-full flex-shrink-0 flex items-center justify-center text-xs"
                style={{ background: cat.color + "22", border: `1px solid ${cat.color}33` }}
              >
                $
              </div>
              <span className="text-xs text-white/60 flex-1 truncate">{cat.name}</span>
              <input
                type="number" placeholder="0"
                value={budgets[cat.id] ?? ""}
                onChange={(e) => setBudgets((b) => ({ ...b, [cat.id]: e.target.value }))}
                className="w-24 text-xs text-right font-mono text-white/80 px-2 py-1.5 rounded outline-none"
                style={{ background: "rgba(31,32,33,0.8)", border: "1px solid rgba(255,255,255,0.10)" }}
              />
            </div>
          ))}
        </div>
        <button
          onClick={handleSave} disabled={saving}
          className="py-2 rounded-lg text-sm font-medium text-white disabled:opacity-50"
          style={{ background: "rgba(16,185,129,0.2)", border: "1px solid rgba(16,185,129,0.3)" }}
        >
          {saving ? "Saving..." : "Save Budgets"}
        </button>
      </div>
    </div>
  );
}
