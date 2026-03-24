"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

const navItems = [
  {
    group: "Portfolio",
    items: [
      { href: "/dashboard", label: "Dashboard" },
      { href: "/signals", label: "Signals" },
      { href: "/performance", label: "Performance" },
      { href: "/projections", label: "Projections" },
    ],
  },
  {
    group: "Research",
    items: [
      { href: "/assets", label: "Assets" },
      { href: "/research", label: "Research" },
    ],
  },
  {
    group: "Tax & Admin",
    items: [
      { href: "/tax", label: "Tax" },
      { href: "/journal", label: "Journal" },
      { href: "/reports", label: "Reports" },
      { href: "/config", label: "Config" },
    ],
  },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="hidden md:flex lg:w-52 w-16 flex-none border-r border-white/[0.06] flex-col transition-all">
      {/* Logo */}
      <div className="px-3 lg:px-4 py-5 border-b border-white/[0.06] flex items-center gap-2 overflow-hidden">
        <span className="text-emerald-400 font-bold tracking-tight text-sm shrink-0">🐑</span>
        <span className="text-emerald-400 font-bold tracking-tight text-sm hidden lg:block truncate">OvelhaInvest</span>
        <p className="text-slate-500 text-xs mt-0.5 hidden lg:block">Wealth OS · v1.0</p>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-1.5 lg:px-2 py-4 space-y-4 overflow-y-auto">
        {navItems.map(({ group, items }) => (
          <div key={group}>
            <p className="px-3 mb-1 text-[10px] font-semibold uppercase tracking-widest text-slate-600 hidden lg:block">
              {group}
            </p>
            {items.map(({ href, label }) => {
              const active =
                pathname === href || pathname?.startsWith(href + "/");
              return (
                <Link
                  key={href}
                  href={href}
                  title={label}
                  className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs transition-all justify-center lg:justify-start ${
                    active
                      ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                      : "text-slate-400 hover:bg-white/[0.04] hover:text-slate-200 border border-transparent"
                  }`}
                >
                  <span className="text-sm shrink-0">{label.charAt(0)}</span>
                  <span className="hidden lg:block">{label}</span>
                </Link>
              );
            })}
          </div>
        ))}
      </nav>

      {/* Footer */}
      <div className="px-3 lg:px-4 py-3 border-t border-white/[0.06]">
        <p className="text-slate-600 text-xs hidden lg:block">Phase 10 · PWA Ready</p>
      </div>
    </aside>
  );
}
