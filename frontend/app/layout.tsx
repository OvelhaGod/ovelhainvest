import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Sidebar } from "@/components/layout/Sidebar";
import { MobileNav } from "@/components/layout/MobileNav";
import { PWAInit } from "@/components/pwa/PWAInit";
import { OfflineBanner } from "@/components/pwa/OfflineBanner";
import { InstallPrompt } from "@/components/pwa/InstallPrompt";
import { SWRProvider } from "@/lib/swr-config";
import { SnapshotInit } from "@/components/pwa/SnapshotInit";
import { UserProvider } from "@/lib/user-context";

const geist = Geist({
  variable: "--font-geist",
  subsets: ["latin"],
  display: "swap",
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "OvelhaInvest",
  description: "Thiago Wealth OS — personal portfolio operating system",
  manifest: "/manifest.json",
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "OvelhaInvest",
  },
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${geist.variable} ${geistMono.variable} h-full dark`}>
      <head>
        <meta name="theme-color" content="#050508" />
        <meta name="mobile-web-app-capable" content="yes" />
      </head>
      <body className="min-h-full flex bg-[hsl(222.2,84%,4.9%)] text-[hsl(210,40%,98%)] font-sans">
        <PWAInit />
        <SnapshotInit />
        <OfflineBanner />
        <InstallPrompt />
        <MobileNav />
        <Sidebar />
        <SWRProvider>
          <UserProvider>
            <main className="flex-1 overflow-auto pb-16 md:pb-0">{children}</main>
          </UserProvider>
        </SWRProvider>
      </body>
    </html>
  );
}
