export default function ConfigPage() {
  return (
    <div className="p-6 space-y-4">
      <h1 className="text-base font-semibold text-[hsl(210,40%,98%)]">Config</h1>
      <div className="grid grid-cols-3 gap-4">
        <div className="border border-[hsl(217.2,32.6%,17.5%)] rounded-lg p-4 bg-[hsl(222.2,84%,6%)]">
          <p className="text-xs text-[hsl(215,20.2%,65.1%)] uppercase tracking-wider mb-2">Version History</p>
          <p className="text-xs text-[hsl(215,20.2%,45%)]">Phase 2 — version list</p>
        </div>
        <div className="col-span-2 border border-[hsl(217.2,32.6%,17.5%)] rounded-lg p-4 bg-[hsl(222.2,84%,6%)] font-mono">
          <p className="text-xs text-[hsl(215,20.2%,65.1%)] uppercase tracking-wider mb-2">Active Config (read-only)</p>
          <p className="text-xs text-[hsl(215,20.2%,45%)]">Phase 2 — JSON viewer + Swensen/All-Weather comparison</p>
        </div>
      </div>
    </div>
  );
}
