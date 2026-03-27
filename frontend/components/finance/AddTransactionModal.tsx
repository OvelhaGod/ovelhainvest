"use client";
/**
 * AddTransactionModal — standalone modal for adding a spending transaction.
 * Can be imported anywhere in the finance section.
 */
import { useState } from "react";

interface Category {
  id: string;
  name: string;
  type: string;
  color?: string;
}

interface Account {
  id: string;
  name: string;
}

interface AddTransactionModalProps {
  categories: Category[];
  accounts: Account[];
  onClose: () => void;
  onSaved: () => void;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "https://investapi.ovelha.us";

const inputStyle = {
  background: "rgba(31,32,33,0.8)",
  border: "1px solid rgba(255,255,255,0.10)",
};

export function AddTransactionModal({
  categories,
  accounts,
  onClose,
  onSaved,
}: AddTransactionModalProps) {
  const [form, setForm] = useState({
    date: new Date().toISOString().slice(0, 10),
    description: "",
    amount: "",
    type: "expense",
    category_id: "",
    account_id: "",
    notes: "",
    currency: "USD",
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const filteredCategories = categories.filter((c) =>
    form.type === "expense" ? c.type === "expense" : c.type === "income"
  );

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (!form.description.trim()) { setError("Description required"); return; }
    const amt = parseFloat(form.amount);
    if (!amt || amt <= 0) { setError("Enter a valid amount > 0"); return; }

    setSaving(true);
    try {
      const res = await fetch(`${API_BASE}/transactions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          date: form.date,
          description: form.description.trim(),
          amount: form.type === "expense" ? -Math.abs(amt) : Math.abs(amt),
          type: form.type,
          category_id: form.category_id || null,
          account_id: form.account_id || null,
          notes: form.notes || null,
          currency: form.currency,
        }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail ?? `HTTP ${res.status}`);
      }
      onSaved();
    } catch (err: any) {
      setError(err.message ?? "Save failed");
    } finally {
      setSaving(false);
    }
  }

  function setField(key: string, value: string) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="glass-card p-6 w-full max-w-md space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-white/90">Add Transaction</h2>
          <button onClick={onClose} className="text-white/30 hover:text-white/60 text-lg leading-none">×</button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-3">
          {/* Type toggle */}
          <div className="flex rounded-lg overflow-hidden border border-white/10">
            {["expense", "income", "transfer"].map((t) => (
              <button
                key={t}
                type="button"
                onClick={() => setField("type", t)}
                className="flex-1 py-1.5 text-xs font-medium transition-colors capitalize"
                style={{
                  background: form.type === t
                    ? t === "income" ? "rgba(16,185,129,0.2)" : "rgba(239,68,68,0.2)"
                    : "transparent",
                  color: form.type === t
                    ? t === "income" ? "#10b981" : "#ef4444"
                    : "rgba(255,255,255,0.4)",
                }}
              >
                {t}
              </button>
            ))}
          </div>

          {/* Date + Description */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-[10px] text-white/40 uppercase tracking-widest block mb-1">Date</label>
              <input
                type="date"
                required
                value={form.date}
                onChange={(e) => setField("date", e.target.value)}
                className="w-full text-sm text-white/80 px-3 py-2 rounded-lg outline-none"
                style={inputStyle}
              />
            </div>
            <div>
              <label className="text-[10px] text-white/40 uppercase tracking-widest block mb-1">Currency</label>
              <select
                value={form.currency}
                onChange={(e) => setField("currency", e.target.value)}
                className="w-full text-sm text-white/80 px-3 py-2 rounded-lg outline-none"
                style={inputStyle}
              >
                <option value="USD">USD</option>
                <option value="BRL">BRL</option>
              </select>
            </div>
          </div>

          <div>
            <label className="text-[10px] text-white/40 uppercase tracking-widest block mb-1">Description</label>
            <input
              type="text"
              required
              placeholder="e.g. Grocery run"
              value={form.description}
              onChange={(e) => setField("description", e.target.value)}
              className="w-full text-sm text-white/80 px-3 py-2 rounded-lg outline-none placeholder:text-white/20"
              style={inputStyle}
            />
          </div>

          <div>
            <label className="text-[10px] text-white/40 uppercase tracking-widest block mb-1">Amount</label>
            <input
              type="number"
              required
              placeholder="0.00"
              min="0.01"
              step="0.01"
              value={form.amount}
              onChange={(e) => setField("amount", e.target.value)}
              className="w-full text-sm text-white/80 px-3 py-2 rounded-lg outline-none placeholder:text-white/20"
              style={inputStyle}
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-[10px] text-white/40 uppercase tracking-widest block mb-1">Category</label>
              <select
                value={form.category_id}
                onChange={(e) => setField("category_id", e.target.value)}
                className="w-full text-sm text-white/80 px-3 py-2 rounded-lg outline-none"
                style={inputStyle}
              >
                <option value="">— Category —</option>
                {filteredCategories.map((c) => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-[10px] text-white/40 uppercase tracking-widest block mb-1">Account</label>
              <select
                value={form.account_id}
                onChange={(e) => setField("account_id", e.target.value)}
                className="w-full text-sm text-white/80 px-3 py-2 rounded-lg outline-none"
                style={inputStyle}
              >
                <option value="">— Account —</option>
                {accounts.map((a) => (
                  <option key={a.id} value={a.id}>{a.name}</option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label className="text-[10px] text-white/40 uppercase tracking-widest block mb-1">Notes (optional)</label>
            <input
              type="text"
              placeholder="Optional note..."
              value={form.notes}
              onChange={(e) => setField("notes", e.target.value)}
              className="w-full text-sm text-white/80 px-3 py-2 rounded-lg outline-none placeholder:text-white/20"
              style={inputStyle}
            />
          </div>

          {error && (
            <p className="text-xs text-[#ef4444] bg-[rgba(239,68,68,0.08)] border border-[rgba(239,68,68,0.2)] rounded px-3 py-2">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={saving}
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
