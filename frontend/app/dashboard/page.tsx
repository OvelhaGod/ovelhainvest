/**
 * /dashboard — Phase 1 placeholder with hardcoded data.
 * Real data wired in Phase 2 (Supabase + API integration).
 */

import { formatUSD, formatPct } from "@/lib/utils";

// ── Placeholder data ──────────────────────────────────────────────────────────

const PLACEHOLDER = {
  netWorth: 287_430.12,
  dailyChange: 1_842.55,
  dailyChangePct: 0.00644,
  regime: "normal" as const,
  sleeves: [
    { name: "US Equity",    target: 0.45, actual: 0.463, color: "#3b82f6" },
    { name: "Bonds",        target: 0.20, actual: 0.187, color: "#22c55e" },
    { name: "Intl Equity",  target: 0.15, actual: 0.142, color: "#f59e0b" },
    { name: "Brazil Eq.",   target: 0.10, actual: 0.094, color: "#ef4444" },
    { name: "Crypto",       target: 0.07, actual: 0.082, color: "#a855f7" },
    { name: "Cash",         target: 0.03, actual: 0.032, color: "#6b7280" },
  ],
  vaults: [
    { name: "Future Investments", balance: 4_200,  min: 500,   color: "#3b82f6" },
    { name: "Opportunity",        balance: 8_750,  min: 1_000, color: "#f59e0b" },
    { name: "Emergency",          balance: 18_000, min: null,  color: "#22c55e" },
  ],
};

const REGIME_BADGE: Record<string, { label: string; classes: string }> = {
  normal:      { label: "NORMAL",      classes: "bg-green-900/40 text-green-400 border-green-700" },
  high_vol:    { label: "HIGH VOL",    classes: "bg-red-900/40 text-red-400 border-red-700" },
  opportunity: { label: "OPPORTUNITY", classes: "bg-amber-900/40 text-amber-400 border-amber-700" },
};

// ── Component ─────────────────────────────────────────────────────────────────

export default function DashboardPage() {
  const regime = REGIME_BADGE[PLACEHOLDER.regime];
  const isPositive = PLACEHOLDER.dailyChange >= 0;

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-base font-semibold text-[hsl(210,40%,98%)]">Dashboard</h1>
          <p className="text-xs text-[hsl(215,20.2%,65.1%)] mt-0.5">
            Placeholder data — Phase 1 · {new Date().toLocaleDateString("en-US", { dateStyle: "medium" })}
          </p>
        </div>
        <span className={`text-xs font-medium px-2.5 py-1 rounded border ${regime.classes}`}>
          {regime.label}
        </span>
      </div>

      {/* Top row: Net Worth + Vaults */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {/* Net Worth card */}
        <div className="md:col-span-1 border border-[hsl(217.2,32.6%,17.5%)] rounded-lg p-4 bg-[hsl(222.2,84%,6%)]">
          <p className="text-xs text-[hsl(215,20.2%,65.1%)] uppercase tracking-wider">Net Worth</p>
          <p className="text-2xl font-bold text-[hsl(210,40%,98%)] mt-1">
            {formatUSD(PLACEHOLDER.netWorth)}
          </p>
          <p className={`text-xs mt-1 font-medium ${isPositive ? "text-green-400" : "text-red-400"}`}>
            {isPositive ? "+" : ""}
            {formatUSD(PLACEHOLDER.dailyChange)}{" "}
            ({isPositive ? "+" : ""}
            {formatPct(PLACEHOLDER.dailyChangePct)}) today
          </p>
        </div>

        {/* Vault cards */}
        {PLACEHOLDER.vaults.map((vault) => (
          <div
            key={vault.name}
            className="border border-[hsl(217.2,32.6%,17.5%)] rounded-lg p-4 bg-[hsl(222.2,84%,6%)]"
          >
            <p className="text-xs text-[hsl(215,20.2%,65.1%)] uppercase tracking-wider truncate">
              {vault.name}
            </p>
            <p className="text-xl font-bold mt-1" style={{ color: vault.color }}>
              {formatUSD(vault.balance)}
            </p>
            {vault.min !== null && (
              <p className="text-xs text-[hsl(215,20.2%,65.1%)] mt-1">
                Min: {formatUSD(vault.min)}
              </p>
            )}
            {vault.name === "Emergency" && (
              <p className="text-xs text-[hsl(215,20.2%,65.1%)] mt-1">Non-investable</p>
            )}
          </div>
        ))}
      </div>

      {/* Sleeve allocation */}
      <div className="border border-[hsl(217.2,32.6%,17.5%)] rounded-lg p-4 bg-[hsl(222.2,84%,6%)]">
        <p className="text-xs text-[hsl(215,20.2%,65.1%)] uppercase tracking-wider mb-4">
          Sleeve Allocation vs. Targets
        </p>
        <div className="space-y-3">
          {PLACEHOLDER.sleeves.map((sleeve) => {
            const diff = sleeve.actual - sleeve.target;
            const absDiff = Math.abs(diff);
            const drifted = absDiff >= 0.05;

            return (
              <div key={sleeve.name} className="grid grid-cols-12 items-center gap-3 text-xs">
                <span className="col-span-2 text-[hsl(215,20.2%,65.1%)] truncate">{sleeve.name}</span>

                {/* Bar track */}
                <div className="col-span-7 h-2 rounded-full bg-[hsl(217.2,32.6%,17.5%)] relative">
                  {/* Target marker */}
                  <div
                    className="absolute top-0 h-full w-0.5 bg-white/30 rounded"
                    style={{ left: `${sleeve.target * 100}%` }}
                  />
                  {/* Actual fill */}
                  <div
                    className="h-full rounded-full transition-all"
                    style={{
                      width: `${Math.min(sleeve.actual * 100, 100)}%`,
                      backgroundColor: sleeve.color,
                      opacity: drifted ? 1 : 0.7,
                    }}
                  />
                </div>

                <span className="col-span-1 text-right text-[hsl(210,40%,98%)] font-medium">
                  {formatPct(sleeve.actual)}
                </span>
                <span className={`col-span-2 text-right font-medium ${drifted ? "text-amber-400" : "text-[hsl(215,20.2%,65.1%)]"}`}>
                  {diff >= 0 ? "+" : ""}
                  {formatPct(diff)} {drifted ? "⚠" : ""}
                </span>
              </div>
            );
          })}
        </div>
        <p className="text-xs text-[hsl(215,20.2%,65.1%)] mt-4">
          White markers = target · Drift threshold: ±5%
        </p>
      </div>
    </div>
  );
}
