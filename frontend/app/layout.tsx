import type { Metadata } from "next";
import { Geist_Mono } from "next/font/google";
import "./globals.css";
import { Sidebar } from "@/components/layout/Sidebar";
import { PWAInit } from "@/components/pwa/PWAInit";
import { OfflineBanner } from "@/components/pwa/OfflineBanner";
import { InstallPrompt } from "@/components/pwa/InstallPrompt";

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
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
    <html lang="en" className={`${geistMono.variable} h-full dark`}>
      <head>
        <meta name="theme-color" content="#050508" />
        <meta name="mobile-web-app-capable" content="yes" />
      </head>
      <body className="min-h-full flex bg-[hsl(222.2,84%,4.9%)] text-[hsl(210,40%,98%)]">
        <PWAInit />
        <OfflineBanner />
        <InstallPrompt />
        <Sidebar />
        <main className="flex-1 overflow-auto">{children}</main>
      </body>
    </html>
  );
}
