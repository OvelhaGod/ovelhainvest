import { cn } from "@/lib/utils";

type BadgeVariant = "positive" | "negative" | "warning" | "ai" | "neutral" | "blue";

const VARIANT_CLASSES: Record<BadgeVariant, string> = {
  positive: "bg-primary/10 text-primary border border-primary/20",
  negative: "bg-error/10 text-error border border-error/20",
  warning:  "bg-tertiary/10 text-tertiary border border-tertiary/20",
  ai:       "bg-secondary/10 text-secondary border border-secondary/20",
  neutral:  "bg-white/5 text-on-surface-variant border border-white/10",
  blue:     "bg-blue-500/10 text-blue-400 border border-blue-500/20",
};

interface OIBadgeProps {
  children: React.ReactNode;
  variant?: BadgeVariant;
  className?: string;
  size?: "sm" | "md";
}

export function OIBadge({ children, variant = "neutral", className, size = "md" }: OIBadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center font-mono font-semibold uppercase tracking-wider rounded-full",
        size === "md" && "px-2.5 py-0.5 text-[10px]",
        size === "sm" && "px-2 py-0.5 text-[9px]",
        VARIANT_CLASSES[variant],
        className
      )}
    >
      {children}
    </span>
  );
}
