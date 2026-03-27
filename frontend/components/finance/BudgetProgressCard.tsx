"use client";
/**
 * BudgetProgressCard — displays budget vs actual for one category.
 * Color: green < 80%, amber 80-100%, red > 100%.
 */

interface BudgetProgressCardProps {
  categoryName: string;
  categoryColor?: string;
  amount: number;       // budgeted
  spent: number;        // actual spent
  remaining: number;
  pctUsed: number;      // 0-100+
}

function fmtUSD(n: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(n);
}

function progressColor(pct: number): string {
  if (pct > 100) return "#ef4444";
  if (pct > 80) return "#f59e0b";
  return "#10b981";
}

export function BudgetProgressCard({
  categoryName,
  categoryColor = "#6b7280",
  amount,
  spent,
  remaining,
  pctUsed,
}: BudgetProgressCardProps) {
  const color = progressColor(pctUsed);
  const isOver = pctUsed > 100;

  return (
    <div
      className="glass-card p-5"
      style={{ borderColor: isOver ? "rgba(239,68,68,0.2)" : undefined }}
    >
      <div className="flex items-center gap-2 mb-3">
        <div
          className="w-7 h-7 rounded-full flex items-center justify-center text-xs shrink-0"
          style={{ background: categoryColor + "22", border: `1px solid ${categoryColor}33` }}
        >
          $
        </div>
        <span className="text-xs text-white/70 font-medium truncate">{categoryName}</span>
        {isOver && (
          <span className="text-[10px] px-1 py-0.5 rounded bg-[rgba(239,68,68,0.1)] text-[#ef4444] border border-[rgba(239,68,68,0.2)] ml-auto shrink-0">
            Over
          </span>
        )}
      </div>

      {/* Progress bar */}
      <div className="h-1.5 rounded-full bg-white/[0.06] mb-2 overflow-hidden">
        <div
          className="h-full rounded-full transition-all"
          style={{ width: `${Math.min(pctUsed, 100)}%`, background: color }}
        />
      </div>

      <div className="flex justify-between text-xs">
        <span className="text-white/40">{fmtUSD(spent)} spent</span>
        <span className="font-mono" style={{ color }}>
          {pctUsed.toFixed(0)}%
        </span>
      </div>
      <div className="text-[10px] text-white/25 mt-0.5">
        {remaining >= 0
          ? fmtUSD(remaining) + " remaining"
          : fmtUSD(Math.abs(remaining)) + " over"}{" "}
        of {fmtUSD(amount)}
      </div>
    </div>
  );
}
