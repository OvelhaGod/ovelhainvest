"use client";
/**
 * /transactions — Full transaction history with filtering, pagination, add/edit.
 */
import { useState } from "react";
import useSWR from "swr";
import { fetcher, CACHE_TTL } from "@/lib/swr-config";
import Link from "next/link";

const glass = "glass-card";
const glassInner = `${glass} p-5`;

function fmtUSD(n: number, currency = "USD") {
  if (currency === "BRL") return "R$ " + Math.abs(n).toLocaleString("pt-BR", { minimumFractionDigits: 2 });
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 2 }).format(Math.abs(n));
}

function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse rounded-lg bg-white/[0.06] ${className}`} />;
}

function MonthPicker({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  const months: string[] = [];
  const now = new Date();
  for (let i = 0; i < 12; i++) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
    months.push(`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`);
  }
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="glass-card text-xs text-white/70 px-3 py-1.5 rounded-lg bg-transparent border-0 outline-none cursor-pointer"
      style={{ background: "rgba(31,32,33,0.6)" }}
    >
      {months.map((m) => (
        <option key={m} value={m} style={{ background: "#1f2021" }}>
          {new Date(m + "-01").toLocaleDateString("en-US", { month: "long", year: "numeric" })}
        </option>
      ))}
    </select>
  );
}

interface Category { id: string; name: string; color: string; icon: string; type: string; }
interface Account { id: string; name: string; institution: string; }
interface Transaction {
  id: string; date: string; description: string; amount: number; type: string;
  currency: string; categories?: Category; accounts?: Account; notes?: string;
}

export default function TransactionsPage() {
  const today = new Date();
  const defaultMonth = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}`;

  const [selectedMonth, setSelectedMonth] = useState(defaultMonth);
  const [selectedAccount, setSelectedAccount] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("");
  const [search, setSearch] = useState("");
  const [offset, setOffset] = useState(0);
  const [showAddModal, setShowAddModal] = useState(false);
  const LIMIT = 50;

  const params = new URLSearchParams({
    month: selectedMonth,
    limit: String(LIMIT),
    offset: String(offset),
  });
  if (selectedAccount) params.set("account_id", selectedAccount);
  if (selectedCategory) params.set("category_id", selectedCategory);

  const { data: txnData, isLoading, mutate } = useSWR<{ transactions: Transaction[] }>(
    `/transactions?${params}`,
    fetcher,
    { refreshInterval: CACHE_TTL.MEDIUM, keepPreviousData: true }
  );
  const { data: categories } = useSWR<Category[]>("/categories", fetcher, { refreshInterval: CACHE_TTL.STATIC });
  const { data: accounts } = useSWR<Account[]>("/accounts", fetcher, { refreshInterval: CACHE_TTL.SLOW });

  const transactions = txnData?.transactions ?? [];
  const filtered = search
    ? transactions.filter((t) => t.description.toLowerCase().includes(search.toLowerCase()))
    : transactions;

  const totalIn  = filtered.filter((t) => t.type === "income").reduce((s, t) => s + t.amount, 0);
  const totalOut = filtered.filter((t) => t.type !== "income").reduce((s, t) => s + Math.abs(t.amount), 0);
  const net = totalIn - totalOut;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-white/90">Transactions</h1>
          <p className="text-xs text-white/40 mt-0.5">Spending history</p>
        </div>
        <div className="flex gap-2">
          <Link
            href="/import"
            className="text-xs px-3 py-1.5 rounded-lg border border-white/10 text-white/50 hover:text-white/70 hover:border-white/20 transition-colors"
          >
            Import CSV
          </Link>
          <button
            onClick={() => setShowAddModal(true)}
            className="text-xs px-3 py-1.5 rounded-lg bg-[rgba(16,185,129,0.15)] border border-[rgba(16,185,129,0.3)] text-[#10b981] hover:bg-[rgba(16,185,129,0.2)] transition-colors"
          >
            + Add
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className={`${glass} p-3 flex flex-wrap gap-3 items-center`}>
        <MonthPicker value={selectedMonth} onChange={(v) => { setSelectedMonth(v); setOffset(0); }} />
        <select
          value={selectedAccount}
          onChange={(e) => { setSelectedAccount(e.target.value); setOffset(0); }}
          className="text-xs text-white/60 px-3 py-1.5 rounded-lg bg-transparent outline-none cursor-pointer"
          style={{ background: "rgba(31,32,33,0.6)", border: "1px solid rgba(255,255,255,0.08)" }}
        >
          <option value="" style={{ background: "#1f2021" }}>All accounts</option>
          {(accounts ?? []).map((a: any) => (
            <option key={a.id} value={a.id} style={{ background: "#1f2021" }}>{a.name}</option>
          ))}
        </select>
        <select
          value={selectedCategory}
          onChange={(e) => { setSelectedCategory(e.target.value); setOffset(0); }}
          className="text-xs text-white/60 px-3 py-1.5 rounded-lg outline-none cursor-pointer"
          style={{ background: "rgba(31,32,33,0.6)", border: "1px solid rgba(255,255,255,0.08)" }}
        >
          <option value="" style={{ background: "#1f2021" }}>All categories</option>
          {(categories ?? []).map((c: any) => (
            <option key={c.id} value={c.id} style={{ background: "#1f2021" }}>{c.name}</option>
          ))}
        </select>
        <input
          type="text"
          placeholder="Search..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="text-xs text-white/70 px-3 py-1.5 rounded-lg outline-none bg-transparent placeholder:text-white/25"
          style={{ border: "1px solid rgba(255,255,255,0.08)", background: "rgba(31,32,33,0.6)" }}
        />
      </div>

      {/* Table */}
      <div className={glassInner}>
        {isLoading ? (
          <div className="space-y-2">
            {[...Array(8)].map((_, i) => <Skeleton key={i} className="h-12" />)}
          </div>
        ) : filtered.length > 0 ? (
          <>
            {/* Header */}
            <div className="grid grid-cols-12 gap-2 text-[10px] text-white/25 uppercase tracking-widest pb-2 border-b border-white/[0.05] mb-1">
              <span className="col-span-2">Date</span>
              <span className="col-span-4">Description</span>
              <span className="col-span-2">Category</span>
              <span className="col-span-2">Account</span>
              <span className="col-span-2 text-right">Amount</span>
            </div>
            <div className="space-y-0.5">
              {filtered.map((txn) => {
                const isIncome = txn.type === "income";
                const catColor = txn.categories?.color ?? "#6b7280";
                const d = new Date(txn.date);
                return (
                  <div
                    key={txn.id}
                    className="grid grid-cols-12 gap-2 py-2.5 px-1 rounded-lg hover:bg-white/[0.02] transition-colors text-xs group"
                  >
                    <span className="col-span-2 text-white/40 font-mono">
                      {d.toLocaleDateString("en-US", { month: "short", day: "numeric" })}
                    </span>
                    <div className="col-span-4 min-w-0">
                      <span className="text-white/75 truncate block">{txn.description}</span>
                      {txn.notes && <span className="text-[10px] text-white/25 truncate block">{txn.notes}</span>}
                    </div>
                    <div className="col-span-2 flex items-center gap-1">
                      <span
                        className="text-[10px] px-1.5 py-0.5 rounded-full truncate"
                        style={{ background: catColor + "22", color: catColor }}
                      >
                        {txn.categories?.name ?? "—"}
                      </span>
                    </div>
                    <span className="col-span-2 text-white/35 truncate text-[10px]">
                      {txn.accounts?.name ?? "—"}
                    </span>
                    <span
                      className="col-span-2 text-right font-mono font-semibold"
                      style={{ color: isIncome ? "#10b981" : "#ef4444" }}
                    >
                      {isIncome ? "+" : "-"}{fmtUSD(Math.abs(txn.amount), txn.currency)}
                    </span>
                  </div>
                );
              })}
            </div>
          </>
        ) : (
          <div className="py-10 text-center text-xs text-white/20">
            No transactions for this period.{" "}
            <button onClick={() => setShowAddModal(true)} className="text-primary/60 hover:text-primary">
              Add one →
            </button>
          </div>
        )}

        {/* Footer totals */}
        {filtered.length > 0 && (
          <div className="mt-4 pt-3 border-t border-white/[0.05] grid grid-cols-3 gap-4 text-xs">
            <div>
              <span className="text-white/30">Total In</span>
              <span className="ml-2 font-mono text-[#10b981]">+{fmtUSD(totalIn)}</span>
            </div>
            <div>
              <span className="text-white/30">Total Out</span>
              <span className="ml-2 font-mono text-[#ef4444]">-{fmtUSD(totalOut)}</span>
            </div>
            <div>
              <span className="text-white/30">Net</span>
              <span className="ml-2 font-mono" style={{ color: net >= 0 ? "#10b981" : "#ef4444" }}>
                {net >= 0 ? "+" : ""}{fmtUSD(Math.abs(net))}
              </span>
            </div>
          </div>
        )}

        {/* Pagination */}
        {filtered.length === LIMIT && (
          <div className="mt-3 flex gap-2 justify-end">
            {offset > 0 && (
              <button onClick={() => setOffset(Math.max(0, offset - LIMIT))}
                className="text-xs px-3 py-1 rounded glass-card text-white/50 hover:text-white/70">
                ← Prev
              </button>
            )}
            <button onClick={() => setOffset(offset + LIMIT)}
              className="text-xs px-3 py-1 rounded glass-card text-white/50 hover:text-white/70">
              Next →
            </button>
          </div>
        )}
      </div>

      {/* Add transaction modal (minimal) */}
      {showAddModal && (
        <AddTransactionModal
          categories={categories ?? []}
          accounts={accounts ?? []}
          onClose={() => setShowAddModal(false)}
          onSaved={() => { mutate(); setShowAddModal(false); }}
        />
      )}
    </div>
  );
}

function AddTransactionModal({
  categories, accounts, onClose, onSaved
}: {
  categories: Category[];
  accounts: Account[];
  onClose: () => void;
  onSaved: () => void;
}) {
  const [form, setForm] = useState({
    date: new Date().toISOString().slice(0, 10),
    description: "",
    amount: "",
    type: "expense",
    category_id: "",
    account_id: "",
    notes: "",
  });
  const [saving, setSaving] = useState(false);

  const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "https://investapi.ovelha.us";

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    try {
      const amt = parseFloat(form.amount);
      await fetch(`${API_BASE}/transactions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...form,
          amount: form.type === "expense" ? -Math.abs(amt) : Math.abs(amt),
          category_id: form.category_id || null,
          account_id: form.account_id || null,
        }),
      });
      onSaved();
    } catch (err) {
      console.error(err);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="glass-card p-6 w-full max-w-md space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-white/90">Add Transaction</h2>
          <button onClick={onClose} className="text-white/30 hover:text-white/60 text-lg leading-none">×</button>
        </div>
        <form onSubmit={handleSubmit} className="space-y-3">
          {[
            { label: "Date", key: "date", type: "date" },
            { label: "Description", key: "description", type: "text", placeholder: "e.g. Grocery run" },
            { label: "Amount", key: "amount", type: "number", placeholder: "0.00" },
          ].map(({ label, key, type, placeholder }) => (
            <div key={key}>
              <label className="text-[10px] text-white/40 uppercase tracking-widest block mb-1">{label}</label>
              <input
                required type={type} placeholder={placeholder}
                value={(form as any)[key]}
                onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))}
                className="w-full text-sm text-white/80 px-3 py-2 rounded-lg outline-none"
                style={{ background: "rgba(31,32,33,0.8)", border: "1px solid rgba(255,255,255,0.10)" }}
              />
            </div>
          ))}

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-[10px] text-white/40 uppercase tracking-widest block mb-1">Type</label>
              <select
                value={form.type}
                onChange={(e) => setForm((f) => ({ ...f, type: e.target.value }))}
                className="w-full text-sm text-white/80 px-3 py-2 rounded-lg outline-none"
                style={{ background: "rgba(31,32,33,0.8)", border: "1px solid rgba(255,255,255,0.10)" }}
              >
                <option value="expense">Expense</option>
                <option value="income">Income</option>
                <option value="transfer">Transfer</option>
                <option value="investment">Investment</option>
              </select>
            </div>
            <div>
              <label className="text-[10px] text-white/40 uppercase tracking-widest block mb-1">Category</label>
              <select
                value={form.category_id}
                onChange={(e) => setForm((f) => ({ ...f, category_id: e.target.value }))}
                className="w-full text-sm text-white/80 px-3 py-2 rounded-lg outline-none"
                style={{ background: "rgba(31,32,33,0.8)", border: "1px solid rgba(255,255,255,0.10)" }}
              >
                <option value="">— Category —</option>
                {categories.filter((c) => c.type === form.type || form.type === "expense" ? c.type === "expense" : c.type === "income").map((c) => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
            </div>
          </div>

          <button
            type="submit" disabled={saving}
            className="w-full py-2 rounded-lg text-sm font-medium text-white transition-colors disabled:opacity-50"
            style={{ background: "rgba(16,185,129,0.2)", border: "1px solid rgba(16,185,129,0.3)" }}
          >
            {saving ? "Saving..." : "Save Transaction"}
          </button>
        </form>
      </div>
    </div>
  );
}
