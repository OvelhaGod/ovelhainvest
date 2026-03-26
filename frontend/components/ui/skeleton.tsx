/**
 * Skeleton loading components — shimmer placeholders for async content.
 * Uses .skeleton CSS class (globals.css) for the animated shimmer.
 */

export function SkeletonCard({ lines = 3, className = "" }: { lines?: number; className?: string }) {
  return (
    <div className={`glass-card p-5 ${className}`}>
      <div className="skeleton h-3 rounded w-1/3 mb-4" />
      <div className="skeleton h-8 rounded w-2/3 mb-3" />
      {Array.from({ length: lines - 1 }).map((_, i) => (
        <div
          key={i}
          className={`skeleton h-3 rounded mb-2 ${i % 2 === 0 ? "w-1/2" : "w-2/3"}`}
        />
      ))}
    </div>
  );
}

export function SkeletonChart({ height = 200, className = "" }: { height?: number; className?: string }) {
  return (
    <div className={`glass-card overflow-hidden ${className}`} style={{ height }}>
      <div className="p-4">
        <div className="skeleton h-3 rounded w-1/4 mb-2" />
        <div className="skeleton h-6 rounded w-1/3" />
      </div>
      <div className="px-4 pb-4">
        <div className="flex items-end gap-1" style={{ height: height - 80 }}>
          {[60, 80, 45, 90, 70, 55, 85, 65, 75, 50, 95, 70].map((h, i) => (
            <div
              key={i}
              className="skeleton flex-1 rounded-t"
              style={{ height: `${h}%` }}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

export function SkeletonRow({ className = "" }: { className?: string }) {
  return (
    <div className={`flex items-center gap-4 py-3 px-4 border-b border-white/[0.04] ${className}`}>
      <div className="skeleton w-8 h-8 rounded-full shrink-0" />
      <div className="flex-1 space-y-1">
        <div className="skeleton h-4 rounded w-16" />
        <div className="skeleton h-3 rounded w-32" />
      </div>
      <div className="skeleton h-4 rounded w-20" />
      <div className="skeleton h-4 rounded w-16" />
    </div>
  );
}

export function SkeletonText({ width = "w-full", height = "h-3", className = "" }: { width?: string; height?: string; className?: string }) {
  return <div className={`skeleton ${height} ${width} rounded ${className}`} />;
}
