/**
 * /journal — Decision log, override accuracy, pattern analysis.
 * Full spec in CLAUDE.md Section 16 & 19 (/journal).
 * Phase 9 stub.
 */
export default function JournalPage() {
  return (
    <div className="p-6 space-y-4">
      <h1 className="text-base font-semibold text-[hsl(210,40%,98%)]">Decision Journal</h1>
      <p className="text-xs text-[hsl(215,20.2%,65.1%)]">
        Phase 9 stub — followed/overrode/deferred log, 30d/90d outcome tracking, override accuracy scorecard.
      </p>
      <div className="grid grid-cols-3 gap-4">
        {["Followed", "Overrode", "Deferred"].map((label) => (
          <div key={label} className="border border-[hsl(217.2,32.6%,17.5%)] rounded-lg p-4 bg-[hsl(222.2,84%,6%)]">
            <p className="text-xs text-[hsl(215,20.2%,65.1%)] uppercase tracking-wider">{label}</p>
            <p className="text-xl font-bold text-[hsl(215,20.2%,45%)] mt-1">—</p>
          </div>
        ))}
      </div>
    </div>
  );
}
