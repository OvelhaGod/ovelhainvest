"use client";

import React, { useState } from "react";

interface CorrelationHeatmapProps {
  matrix: Record<string, Record<string, number>>;
  sleeves: string[];
}

const SLEEVE_SHORT: Record<string, string> = {
  us_equity: "US Eq",
  intl_equity: "Intl",
  bonds: "Bonds",
  brazil_equity: "Brazil",
  crypto: "Crypto",
  cash: "Cash",
};

function getCellBg(val: number, isDiag: boolean): string {
  if (isDiag) return "rgba(208,188,255,0.15)"; // secondary/AI accent for diagonal
  const abs = Math.abs(val);
  if (val > 0) return `rgba(255,180,171,${abs * 0.6})`; // var(--color-error)
  return `rgba(78,222,163,${abs * 0.6})`;              // var(--color-primary)
}

function getInterpretation(val: number, isDiag: boolean): string {
  if (isDiag) return "Same asset";
  if (val > 0.85) return "⚠️ Very high — limited diversification";
  if (val > 0.7) return "⚠️ High — some diversification loss";
  if (val > 0.3) return "Moderate — acceptable correlation";
  if (val >= 0) return "✅ Low — good diversification";
  return "✅ Negative — active diversification";
}

export const CorrelationHeatmap = React.memo(function CorrelationHeatmap({ matrix, sleeves }: CorrelationHeatmapProps) {
  const [tooltip, setTooltip] = useState<{
    a: string;
    b: string;
    val: number;
    x: number;
    y: number;
  } | null>(null);

  const highCorrPairs = sleeves.flatMap((a, i) =>
    sleeves
      .slice(i + 1)
      .filter((b) => (matrix[a]?.[b] ?? 0) > 0.85)
      .map((b) => `${SLEEVE_SHORT[a] ?? a}↔${SLEEVE_SHORT[b] ?? b}`)
  );

  return (
    <div className="relative">
      {highCorrPairs.length > 0 && (
        <div className="mb-3 px-3 py-2 rounded-xl bg-tertiary/10 border border-tertiary/20 text-xs text-tertiary">
          ⚠️ {highCorrPairs.length} high-correlation pair
          {highCorrPairs.length > 1 ? "s" : ""} detected:{" "}
          {highCorrPairs.join(", ")}
        </div>
      )}

      <div className="overflow-x-auto">
        <div
          style={{
            display: "grid",
            gridTemplateColumns: `80px repeat(${sleeves.length}, 1fr)`,
            gap: 2,
          }}
        >
          {/* Header row */}
          <div />
          {sleeves.map((s) => (
            <div
              key={s}
              className="text-[10px] text-outline font-mono text-center py-1 truncate"
            >
              {SLEEVE_SHORT[s] ?? s}
            </div>
          ))}

          {/* Data rows */}
          {sleeves.map((row) => (
            <>
              <div
                key={`lbl-${row}`}
                className="text-[10px] text-on-surface-variant font-mono flex items-center pr-2 truncate"
              >
                {SLEEVE_SHORT[row] ?? row}
              </div>
              {sleeves.map((col) => {
                const val = matrix[row]?.[col] ?? 0;
                const isDiag = row === col;
                const bg = getCellBg(val, isDiag);
                return (
                  <div
                    key={`${row}-${col}`}
                    className="relative rounded cursor-pointer transition-all hover:scale-110 hover:z-10"
                    style={{
                      background: bg,
                      aspectRatio: "1",
                      minWidth: 36,
                      minHeight: 36,
                    }}
                    onMouseEnter={(e) => {
                      const rect = e.currentTarget.getBoundingClientRect();
                      setTooltip({ a: row, b: col, val, x: rect.left, y: rect.top });
                    }}
                    onMouseLeave={() => setTooltip(null)}
                  >
                    <div
                      className="absolute inset-0 flex items-center justify-center text-[10px] font-mono font-bold"
                      style={{ color: isDiag ? "var(--color-secondary, #d0bcff)" : "var(--color-on-surface, #e3e2e3)", fontFamily: "JetBrains Mono, monospace" }}
                    >
                      {val.toFixed(2)}
                    </div>
                  </div>
                );
              })}
            </>
          ))}
        </div>
      </div>

      {/* Color scale legend */}
      <div className="mt-3 flex items-center gap-2 text-[10px] text-outline">
        <div
          style={{
            background: "rgba(78,222,163,0.6)",
            width: 16,
            height: 10,
            borderRadius: 2,
          }}
        />
        <span>Negative corr</span>
        <div
          style={{
            background: "rgba(255,255,255,0.1)",
            width: 16,
            height: 10,
            borderRadius: 2,
          }}
        />
        <span>Zero</span>
        <div
          style={{
            background: "rgba(255,180,171,0.6)",
            width: 16,
            height: 10,
            borderRadius: 2,
          }}
        />
        <span>High positive</span>
      </div>

      {/* Tooltip */}
      {tooltip && (
        <div
          className="fixed z-50 rounded-xl border border-white/10 bg-[#0d0d14]/95 backdrop-blur-sm p-3 text-xs shadow-xl pointer-events-none"
          style={{ top: tooltip.y - 80, left: tooltip.x }}
        >
          <div className="font-semibold text-on-surface mb-1" style={{ fontFamily: "JetBrains Mono, monospace" }}>
            {SLEEVE_SHORT[tooltip.a] ?? tooltip.a} ↔{" "}
            {SLEEVE_SHORT[tooltip.b] ?? tooltip.b}
          </div>
          <div className="font-mono text-on-surface" style={{ fontFamily: "JetBrains Mono, monospace" }}>{tooltip.val.toFixed(3)}</div>
          <div className="text-on-surface-variant mt-1 max-w-[200px]" style={{ fontFamily: "JetBrains Mono, monospace" }}>
            {getInterpretation(tooltip.val, tooltip.a === tooltip.b)}
          </div>
        </div>
      )}
    </div>
  );
});

export default CorrelationHeatmap;
