interface OIEmptyStateProps {
  title?: string;
  description: string;
  icon?: string;
  action?: React.ReactNode;
  compact?: boolean;
}

export function OIEmptyState({ title, description, icon = "✦", action, compact = false }: OIEmptyStateProps) {
  return (
    <div className={`flex flex-col items-center justify-center text-center ${compact ? "py-8" : "py-16"}`}>
      {/* Gradient glow orb behind icon */}
      <div className="relative mb-4">
        <div
          className="absolute inset-0 blur-xl rounded-full opacity-30"
          style={{ background: "radial-gradient(circle, rgba(99,102,241,0.6) 0%, transparent 70%)", width: 64, height: 64 }}
        />
        <div
          className="relative w-12 h-12 rounded-2xl border border-white/[0.08] flex items-center justify-center"
          style={{ background: "rgba(99,102,241,0.08)" }}
        >
          <span className="text-xl text-white/40">{icon}</span>
        </div>
      </div>

      {title && (
        <p className="text-sm font-semibold text-white/70 mb-1">{title}</p>
      )}
      <p className="text-xs text-white/35 max-w-[280px] leading-relaxed">{description}</p>
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}
