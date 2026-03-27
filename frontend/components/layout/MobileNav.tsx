"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV = [
  { href: "/dashboard",    label: "Home",     icon: "⌂" },
  { href: "/finance",      label: "Finance",  icon: "💰" },
  { href: "/assets",       label: "Assets",   icon: "◈" },
  { href: "/performance",  label: "Perf",     icon: "↗" },
  { href: "/budget",       label: "Budget",   icon: "🎯" },
];

export function MobileNav() {
  const pathname = usePathname();
  return (
    <nav className="fixed bottom-0 left-0 right-0 z-50 md:hidden border-t border-white/[0.08] bg-[#050508]/95 backdrop-blur-xl">
      <div className="flex items-center justify-around px-2 py-2 pb-safe">
        {NAV.map((item) => {
          const active = pathname === item.href || pathname.startsWith(item.href + "/");
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex flex-col items-center gap-0.5 px-3 py-1.5 rounded-xl transition-all text-center min-w-0 ${
                active
                  ? "text-emerald-400 bg-emerald-500/10"
                  : "text-slate-500 hover:text-slate-300"
              }`}
            >
              <span className="text-lg leading-none">{item.icon}</span>
              <span className="text-[10px] font-medium tracking-wide leading-none">{item.label}</span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
