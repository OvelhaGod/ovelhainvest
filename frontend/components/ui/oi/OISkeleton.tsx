import { cn } from "@/lib/utils";

interface OISkeletonProps {
  variant?: "line" | "card" | "metric" | "table";
  rows?: number;
  className?: string;
}

export function OISkeleton({ variant = "line", rows = 3, className }: OISkeletonProps) {
  if (variant === "metric") {
    return (
      <div className={cn("glass-card p-5 animate-pulse", className)}>
        <div className="h-3 w-20 bg-white/5 rounded mb-3" />
        <div className="h-8 w-32 bg-white/5 rounded mb-2" />
        <div className="h-3 w-24 bg-white/5 rounded" />
      </div>
    );
  }
  if (variant === "table") {
    return (
      <div className={cn("space-y-2 animate-pulse", className)}>
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} className="h-12 rounded-xl bg-white/[0.03]" />
        ))}
      </div>
    );
  }
  if (variant === "card") {
    return (
      <div className={cn("glass-card p-6 animate-pulse", className)}>
        <div className="h-4 w-1/3 bg-white/5 rounded mb-4" />
        <div className="space-y-2">
          {Array.from({ length: rows }).map((_, i) => (
            <div key={i} className="h-3 bg-white/5 rounded" style={{ width: `${80 - i * 10}%` }} />
          ))}
        </div>
      </div>
    );
  }
  return <div className={cn("h-4 bg-white/5 rounded animate-pulse", className)} />;
}
