/**
 * /tax — Tax lot tracker, HIFO/FIFO, Brazil DARF, loss harvesting.
 * Full spec in CLAUDE.md Section 19 (/tax).
 * Phase 8 stub.
 */
export default function TaxPage() {
  return (
    <div className="p-6 space-y-4">
      <h1 className="text-base font-semibold text-[hsl(210,40%,98%)]">Tax</h1>
      <p className="text-xs text-[hsl(215,20.2%,65.1%)]">
        Phase 8 stub — HIFO/FIFO/Spec ID lot tracking, US tax estimate, Brazil DARF tracker, loss harvesting candidates.
      </p>
      <div className="grid grid-cols-2 gap-4">
        <div className="border border-[hsl(217.2,32.6%,17.5%)] rounded-lg p-4 bg-[hsl(222.2,84%,6%)]">
          <p className="text-xs text-[hsl(215,20.2%,65.1%)] uppercase tracking-wider">US Tax Estimate</p>
          <p className="text-xl font-bold text-[hsl(215,20.2%,45%)] mt-1">—</p>
        </div>
        <div className="border border-[hsl(217.2,32.6%,17.5%)] rounded-lg p-4 bg-[hsl(222.2,84%,6%)]">
          <p className="text-xs text-[hsl(215,20.2%,65.1%)] uppercase tracking-wider">Brazil DARF (MTD)</p>
          <p className="text-xl font-bold text-[hsl(215,20.2%,45%)] mt-1">R$— / R$20,000</p>
        </div>
      </div>
    </div>
  );
}
