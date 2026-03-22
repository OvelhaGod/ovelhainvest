export default function SignalsPage() {
  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-base font-semibold text-[hsl(210,40%,98%)]">Signals</h1>
        <div className="flex gap-2 text-xs text-[hsl(215,20.2%,65.1%)]">
          <span className="px-2 py-1 rounded border border-[hsl(217.2,32.6%,17.5%)]">All status</span>
          <span className="px-2 py-1 rounded border border-[hsl(217.2,32.6%,17.5%)]">All types</span>
          <span className="px-2 py-1 rounded border border-[hsl(217.2,32.6%,17.5%)]">Date range</span>
        </div>
      </div>
      <div className="border border-[hsl(217.2,32.6%,17.5%)] rounded-lg overflow-hidden">
        <table className="w-full text-xs">
          <thead className="bg-[hsl(217.2,32.6%,10%)]">
            <tr>
              {["Timestamp","Event Type","Proposed Trades","AI Status","Status","Action"].map(h => (
                <th key={h} className="text-left px-3 py-2 text-[hsl(215,20.2%,65.1%)] font-medium">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            <tr><td colSpan={6} className="px-3 py-8 text-center text-[hsl(215,20.2%,45%)]">Phase 2 — wired to signals_runs</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
