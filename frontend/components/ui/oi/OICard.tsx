import { cn } from "@/lib/utils";

interface OICardProps {
  children: React.ReactNode;
  className?: string;
  variant?: "default" | "elevated" | "subtle" | "ghost";
  glow?: "emerald" | "violet" | "amber" | "none";
}

export function OICard({ children, className, variant = "default", glow = "none" }: OICardProps) {
  return (
    <div
      className={cn(
        // base
        "rounded-2xl",
        // variant
        variant === "default"  && "glass-card",
        variant === "elevated" && "glass-card bg-surface-container-high/80",
        variant === "subtle"   && "glass-card-subtle",
        variant === "ghost"    && "bg-transparent border border-white/5",
        // glow
        glow === "emerald" && "emerald-glow",
        glow === "violet"  && "violet-glow",
        glow === "amber"   && "amber-glow",
        className
      )}
    >
      {children}
    </div>
  );
}
