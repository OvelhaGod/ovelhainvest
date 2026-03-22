/**
 * /performance — TWR/MWR, Sharpe/Sortino/Calmar, attribution.
 * Full spec in CLAUDE.md Section 17.
 * Phase 4 stub.
 */
export default function PerformancePage() {
  return (
    <div className="p-6 space-y-4">
      <h1 className="text-base font-semibold text-[hsl(210,40%,98%)]">Performance</h1>
      <p className="text-xs text-[hsl(215,20.2%,65.1%)]">
        Phase 4 stub — TWR, MWR, Sharpe, Sortino, Calmar, Brinson-Hood-Beebower attribution.
      </p>
      <div className="grid grid-cols-3 gap-4">
        {["TWR YTD", "Sharpe", "Max Drawdown"].map((label) => (
          <div key={label} className="border border-[hsl(217.2,32.6%,17.5%)] rounded-lg p-4 bg-[hsl(222.2,84%,6%)]">
            <p className="text-xs text-[hsl(215,20.2%,65.1%)] uppercase tracking-wider">{label}</p>
            <p className="text-xl font-bold text-[hsl(215,20.2%,45%)] mt-1">—</p>
          </div>
        ))}
      </div>
    </div>
  );
}
