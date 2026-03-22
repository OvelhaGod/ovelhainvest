export default function ResearchPage() {
  return (
    <div className="p-6 space-y-4">
      <h1 className="text-base font-semibold text-[hsl(210,40%,98%)]">Research</h1>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <p className="text-xs text-[hsl(215,20.2%,65.1%)] uppercase tracking-wider mb-2">News Feed</p>
          <p className="text-xs text-[hsl(215,20.2%,45%)]">Phase 3 — Finnhub news, sorted by importance</p>
        </div>
        <div>
          <p className="text-xs text-[hsl(215,20.2%,65.1%)] uppercase tracking-wider mb-2">Earnings Calendar</p>
          <p className="text-xs text-[hsl(215,20.2%,45%)]">Phase 3 — next 30 days for positions</p>
        </div>
      </div>
    </div>
  );
}
