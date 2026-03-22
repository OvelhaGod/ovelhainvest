export default function AssetsPage() {
  return (
    <div className="p-6 space-y-4">
      <h1 className="text-base font-semibold text-[hsl(210,40%,98%)]">Assets & Valuations</h1>
      <div className="flex gap-2 text-xs text-[hsl(215,20.2%,65.1%)]">
        {["Asset Class","Region","Tier","Min Margin of Safety","Moat"].map(f => (
          <span key={f} className="px-2 py-1 rounded border border-[hsl(217.2,32.6%,17.5%)]">{f}</span>
        ))}
      </div>
      <div className="border border-[hsl(217.2,32.6%,17.5%)] rounded-lg overflow-hidden">
        <table className="w-full text-xs">
          <thead className="bg-[hsl(217.2,32.6%,10%)]">
            <tr>
              {["Symbol","Class","Price","Margin of Safety","Value Score","Momentum Score","Quality Score","Moat","Fair Value","Buy Target","Rank"].map(h => (
                <th key={h} className="text-left px-3 py-2 text-[hsl(215,20.2%,65.1%)] font-medium">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            <tr><td colSpan={11} className="px-3 py-8 text-center text-[hsl(215,20.2%,45%)]">Phase 3 — valuation engine</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
