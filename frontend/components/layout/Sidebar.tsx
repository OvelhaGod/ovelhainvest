"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { preload } from "swr";
import { fetcher } from "@/lib/swr-config";
import {
  LayoutDashboard, Activity, TrendingUp, LineChart,
  Package, Globe, Newspaper, Receipt, BookMarked, FileText, Settings,
  ChevronLeft, ChevronRight, User, Link2,
} from "lucide-react";

// Endpoints to prefetch when hovering each nav item
const PREFETCH_MAP: Record<string, string[]> = {
  "/dashboard":    ["/daily_status"],
  "/performance":  ["/performance/summary"],
  "/signals":      ["/signals/runs"],
  "/assets":       ["/assets/list"],
  "/markets":      ["/markets/overview"],
  "/projections":  ["/simulation/dashboard_preview"],
  "/tax":          ["/tax/estimate"],
};

const navItems = [
  {
    group: "Portfolio",
    items: [
      { href: "/dashboard",   label: "Dashboard",   icon: LayoutDashboard },
      { href: "/signals",     label: "Signals",     icon: Activity },
      { href: "/performance", label: "Performance", icon: TrendingUp },
      { href: "/projections", label: "Projections", icon: LineChart },
    ],
  },
  {
    group: "Research",
    items: [
      { href: "/assets",   label: "Assets",   icon: Package },
      { href: "/markets",  label: "Markets",  icon: Globe },
      { href: "/research", label: "Research", icon: Newspaper },
    ],
  },
  {
    group: "Tax & Admin",
    items: [
      { href: "/tax",         label: "Tax",         icon: Receipt },
      { href: "/journal",     label: "Journal",     icon: BookMarked },
      { href: "/reports",     label: "Reports",     icon: FileText },
      { href: "/connections", label: "Connections", icon: Link2 },
      { href: "/config",      label: "Config",      icon: Settings },
    ],
  },
];

const STORAGE_KEY = "oi_sidebar_collapsed";

export function Sidebar() {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);

  // Restore collapse state from localStorage (client-only)
  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === "true") setCollapsed(true);
  }, []);

  const toggle = () => {
    setCollapsed((prev) => {
      const next = !prev;
      localStorage.setItem(STORAGE_KEY, String(next));
      return next;
    });
  };

  const w = collapsed ? "w-[64px]" : "w-[220px]";

  return (
    <aside
      className={`hidden md:flex ${w} flex-none flex-col transition-[width] duration-200 ease-in-out overflow-hidden`}
      style={{
        background: "linear-gradient(180deg, rgba(13,13,20,0.97) 0%, rgba(5,5,8,0.99) 100%)",
        borderRight: "1px solid rgba(255,255,255,0.06)",
      }}
    >
      {/* Logo + collapse toggle */}
      <div
        className="flex items-center justify-between px-3 py-4"
        style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}
      >
        <div className={`flex items-center gap-2 min-w-0 ${collapsed ? "justify-center w-full" : ""}`}>
          <span className="text-[#10b981] shrink-0 text-base leading-none">🐑</span>
          {!collapsed && (
            <span className="text-[#10b981] font-semibold text-sm tracking-tight truncate">OvelhaInvest</span>
          )}
        </div>
        {!collapsed && (
          <button
            onClick={toggle}
            className="shrink-0 text-white/30 hover:text-white/60 transition-colors p-0.5 rounded"
            aria-label="Collapse sidebar"
          >
            <ChevronLeft size={14} />
          </button>
        )}
      </div>

      {/* Nav */}
      <nav className="flex-1 px-2 py-3 space-y-4 overflow-y-auto overflow-x-hidden">
        {navItems.map(({ group, items }) => (
          <div key={group}>
            {!collapsed && (
              <p className="px-2 mb-1.5 text-[10px] font-semibold uppercase tracking-widest text-white/25">
                {group}
              </p>
            )}
            <div className="space-y-0.5">
              {items.map(({ href, label, icon: Icon }) => {
                const active = pathname === href || pathname?.startsWith(href + "/");
                return (
                  <Link
                    key={href}
                    href={href}
                    title={collapsed ? label : undefined}
                    onMouseEnter={() => {
                      const endpoints = PREFETCH_MAP[href];
                      if (endpoints) endpoints.forEach((ep) => preload(ep, fetcher));
                    }}
                    className={`flex items-center gap-2.5 px-2 py-2 rounded-lg text-xs font-medium transition-all duration-150 ${
                      collapsed ? "justify-center" : ""
                    } ${
                      active
                        ? "bg-[rgba(16,185,129,0.08)] text-[#10b981] border-l-2 border-l-[#10b981] border-t-0 border-r-0 border-b-0 pl-[calc(0.5rem-2px)]"
                        : "text-white/45 hover:text-white/80 hover:bg-white/[0.04] border border-transparent"
                    }`}
                  >
                    <Icon size={15} className="shrink-0" strokeWidth={active ? 2.2 : 1.8} />
                    {!collapsed && <span className="truncate">{label}</span>}
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* User profile + version */}
      <div
        className="px-2 py-3 space-y-1"
        style={{ borderTop: "1px solid rgba(255,255,255,0.06)" }}
      >
        {/* Expand button when collapsed */}
        {collapsed && (
          <button
            onClick={toggle}
            className="w-full flex justify-center text-white/30 hover:text-white/60 transition-colors py-1 rounded"
            aria-label="Expand sidebar"
          >
            <ChevronRight size={14} />
          </button>
        )}

        <div className={`flex items-center gap-2 px-1 py-1 rounded-lg ${collapsed ? "justify-center" : ""}`}>
          <div className="w-6 h-6 rounded-full bg-[rgba(16,185,129,0.15)] border border-[rgba(16,185,129,0.25)] flex items-center justify-center shrink-0">
            <User size={11} className="text-[#10b981]" />
          </div>
          {!collapsed && (
            <div className="min-w-0">
              <p className="text-xs font-medium text-white/70 truncate">Thiago</p>
              <p className="text-[10px] text-white/25 truncate">Personal Wealth OS</p>
            </div>
          )}
        </div>

        {!collapsed && (
          <p className="text-[10px] text-white/20 px-1 pt-0.5">v1.5.0 · Phase 10</p>
        )}
      </div>
    </aside>
  );
}
