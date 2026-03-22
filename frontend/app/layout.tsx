import type { Metadata } from "next";
import { Geist_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "OvelhaInvest",
  description: "Thiago Wealth OS — personal portfolio operating system",
};

const navItems = [
  { group: "Portfolio",   items: [
    { href: "/dashboard",    label: "Dashboard" },
    { href: "/signals",      label: "Signals" },
    { href: "/performance",  label: "Performance" },
    { href: "/projections",  label: "Projections" },
  ]},
  { group: "Research",    items: [
    { href: "/assets",       label: "Assets" },
    { href: "/research",     label: "Research" },
  ]},
  { group: "Tax & Admin", items: [
    { href: "/tax",          label: "Tax" },
    { href: "/journal",      label: "Journal" },
    { href: "/config",       label: "Config" },
  ]},
];

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${geistMono.variable} h-full dark`}>
      <body className="min-h-full flex bg-[hsl(222.2,84%,4.9%)] text-[hsl(210,40%,98%)]">
        {/* ── Sidebar ── */}
        <aside className="w-52 flex-none border-r border-[hsl(217.2,32.6%,17.5%)] flex flex-col">
          {/* Logo */}
          <div className="px-4 py-5 border-b border-[hsl(217.2,32.6%,17.5%)]">
            <span className="text-[hsl(217.2,91.2%,59.8%)] font-bold tracking-tight text-sm">
              OvelhaInvest
            </span>
            <p className="text-[hsl(215,20.2%,65.1%)] text-xs mt-0.5">Wealth OS</p>
          </div>

          {/* Nav */}
          <nav className="flex-1 px-2 py-4 space-y-4 overflow-y-auto">
            {navItems.map(({ group, items }) => (
              <div key={group}>
                <p className="px-3 mb-1 text-[10px] font-semibold uppercase tracking-widest text-[hsl(215,20.2%,45%)]">
                  {group}
                </p>
                {items.map(({ href, label }) => (
                  <Link
                    key={href}
                    href={href}
                    className="block px-3 py-1.5 rounded text-xs text-[hsl(215,20.2%,65.1%)] hover:bg-[hsl(217.2,32.6%,17.5%)] hover:text-[hsl(210,40%,98%)] transition-colors"
                  >
                    {label}
                  </Link>
                ))}
              </div>
            ))}
          </nav>

          {/* Footer */}
          <div className="px-4 py-3 border-t border-[hsl(217.2,32.6%,17.5%)]">
            <p className="text-[hsl(215,20.2%,65.1%)] text-xs">v2.0.0 · Phase 1</p>
          </div>
        </aside>

        {/* ── Main content ── */}
        <main className="flex-1 overflow-auto">{children}</main>
      </body>
    </html>
  );
}
