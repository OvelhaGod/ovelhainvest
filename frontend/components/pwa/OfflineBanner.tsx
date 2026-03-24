"use client";
import { useEffect, useState } from "react";

export function OfflineBanner() {
  const [isOnline, setIsOnline] = useState(true);
  const [lastSync, setLastSync] = useState<string | null>(null);
  const [showOnlineFlash, setShowOnlineFlash] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;
    setIsOnline(navigator.onLine);
    const stored = localStorage.getItem("oi_last_sync");
    if (stored) setLastSync(stored);

    const handleOnline = () => {
      setIsOnline(true);
      setShowOnlineFlash(true);
      localStorage.setItem("oi_last_sync", new Date().toISOString());
      setTimeout(() => setShowOnlineFlash(false), 3000);
    };
    const handleOffline = () => setIsOnline(false);

    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);
    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, []);

  if (isOnline && !showOnlineFlash) return null;

  if (showOnlineFlash) {
    return (
      <div className="fixed top-0 left-0 right-0 z-[100] flex items-center justify-center gap-2 bg-emerald-500/90 backdrop-blur-sm text-emerald-950 text-xs font-semibold py-2 px-4">
        ✅ Back online — data refreshing…
      </div>
    );
  }

  const syncTime = lastSync
    ? new Date(lastSync).toLocaleTimeString("en-US", {
        hour: "2-digit",
        minute: "2-digit",
      })
    : "unknown";

  return (
    <div className="fixed top-0 left-0 right-0 z-[100] flex items-center justify-center gap-2 bg-amber-500/90 backdrop-blur-sm text-amber-950 text-xs font-semibold py-2 px-4">
      📴 You&apos;re offline — showing data from last sync at {syncTime}
    </div>
  );
}
