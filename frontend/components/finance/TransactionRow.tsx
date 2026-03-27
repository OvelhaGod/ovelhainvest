"use client";
/**
 * TransactionRow — reusable transaction list item.
 * Used in /finance, /transactions, and dashboard widgets.
 */

interface Category {
  name: string;
  color: string;
  icon?: string;
}

interface Account {
  name: string;
}

export interface TransactionRowProps {
  id: string;
  date: string;
  description: string;
  amount: number;
  type: string;
  currency?: string;
  categories?: Category;
  accounts?: Account;
  notes?: string;
  compact?: boolean;
}

function fmtAmount(amount: number, currency = "USD") {
  if (currency === "BRL") {
    return "R$ " + Math.abs(amount).toLocaleString("pt-BR", { minimumFractionDigits: 2 });
  }
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
  }).format(Math.abs(amount));
}

export function TransactionRow({
  date,
  description,
  amount,
  type,
  currency = "USD",
  categories,
  accounts,
  notes,
  compact = false,
}: TransactionRowProps) {
  const isIncome = type === "income";
  const catColor = categories?.color ?? "#6b7280";
  const d = new Date(date);
  const dateStr = d.toLocaleDateString("en-US", { month: "short", day: "numeric" });

  if (compact) {
    return (
      <div className="flex items-center justify-between py-2 px-2 rounded-lg hover:bg-white/[0.02] transition-colors">
        <div className="flex items-center gap-3 min-w-0">
          <div
            className="w-7 h-7 rounded-full flex items-center justify-center shrink-0 text-xs"
            style={{ background: catColor + "22", border: `1px solid ${catColor}33` }}
          >
            {isIncome ? "↑" : "↓"}
          </div>
          <div className="min-w-0">
            <p className="text-xs text-white/80 truncate">{description}</p>
            <p className="text-[10px] text-white/30">
              {categories?.name ?? "Uncategorized"} · {dateStr}
            </p>
          </div>
        </div>
        <span
          className="font-mono text-sm font-semibold shrink-0 ml-3"
          style={{ color: isIncome ? "#10b981" : "#ef4444" }}
        >
          {isIncome ? "+" : "-"}{fmtAmount(amount, currency)}
        </span>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-12 gap-2 py-2.5 px-1 rounded-lg hover:bg-white/[0.02] transition-colors text-xs group">
      <span className="col-span-2 text-white/40 font-mono">{dateStr}</span>
      <div className="col-span-4 min-w-0">
        <span className="text-white/75 truncate block">{description}</span>
        {notes && <span className="text-[10px] text-white/25 truncate block">{notes}</span>}
      </div>
      <div className="col-span-2 flex items-center gap-1">
        {categories && (
          <span
            className="text-[10px] px-1.5 py-0.5 rounded-full truncate"
            style={{ background: catColor + "22", color: catColor }}
          >
            {categories.name}
          </span>
        )}
      </div>
      <span className="col-span-2 text-white/35 truncate text-[10px]">
        {accounts?.name ?? "—"}
      </span>
      <span
        className="col-span-2 text-right font-mono font-semibold"
        style={{ color: isIncome ? "#10b981" : "#ef4444" }}
      >
        {isIncome ? "+" : "-"}{fmtAmount(amount, currency)}
      </span>
    </div>
  );
}
