"use client";
import { cn } from "@/lib/utils";
import { OIBadge } from "./OIBadge";

interface OIMetricCardProps {
  label: string;
  value: string;
  subLabel?: string;
  delta?: string;
  deltaType?: "positive" | "negative" | "neutral" | "warning";
  className?: string;
  glow?: "emerald" | "violet" | "amber" | "none";
  accentLine?: boolean;
}

export function OIMetricCard({
  label,
  value,
  subLabel,
  delta,
  deltaType = "neutral",
  className,
  glow = "none",
  accentLine = false,
}: OIMetricCardProps) {
  return (
    <div
      className={cn(
        "glass-card p-5 relative overflow-hidden",
        glow === "emerald" && "emerald-glow",
        glow === "violet"  && "violet-glow",
        glow === "amber"   && "amber-glow",
        className
      )}
    >
      {accentLine && (
        <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-primary/60 to-transparent" />
      )}
      <p className="text-[10px] font-mono uppercase tracking-widest text-outline mb-2">{label}</p>
      <p className="text-3xl font-mono font-bold text-on-surface leading-none mb-1">{value}</p>
      {(delta || subLabel) && (
        <div className="flex items-center gap-2 mt-2">
          {delta && <OIBadge variant={deltaType === "neutral" ? "neutral" : deltaType}>{delta}</OIBadge>}
          {subLabel && <span className="text-xs text-on-surface-variant font-mono">{subLabel}</span>}
        </div>
      )}
    </div>
  );
}
