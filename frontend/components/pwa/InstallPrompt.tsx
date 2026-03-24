"use client";
import { useEffect, useState } from "react";

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

export function InstallPrompt() {
  const [deferredPrompt, setDeferredPrompt] =
    useState<BeforeInstallPromptEvent | null>(null);
  const [show, setShow] = useState(false);
  const [isIOS, setIsIOS] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;

    // Don't show if already dismissed
    if (localStorage.getItem("oi_install_dismissed")) return;

    // iOS detection
    const ios =
      /iphone|ipad|ipod/i.test(navigator.userAgent) &&
      !(window as unknown as { MSStream: unknown }).MSStream;
    setIsIOS(ios);

    if (ios) {
      const timer = setTimeout(() => setShow(true), 30_000);
      return () => clearTimeout(timer);
    }

    const handler = (e: Event) => {
      e.preventDefault();
      setDeferredPrompt(e as BeforeInstallPromptEvent);
      setTimeout(() => setShow(true), 30_000);
    };

    window.addEventListener("beforeinstallprompt", handler);
    return () => window.removeEventListener("beforeinstallprompt", handler);
  }, []);

  const handleInstall = async () => {
    if (deferredPrompt) {
      await deferredPrompt.prompt();
      const choice = await deferredPrompt.userChoice;
      if (choice.outcome === "accepted") {
        setShow(false);
      }
    }
  };

  const handleDismiss = () => {
    setShow(false);
    localStorage.setItem("oi_install_dismissed", "1");
  };

  if (!show) return null;

  return (
    <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-[99] max-w-sm w-full px-4">
      <div className="rounded-2xl border border-white/[0.12] bg-[#0d0d14]/95 backdrop-blur-xl p-4 shadow-[0_20px_60px_rgba(0,0,0,0.6)]">
        <div className="flex items-start gap-3">
          <div className="text-2xl">📱</div>
          <div className="flex-1">
            <p className="text-sm font-semibold text-slate-100">
              Add OvelhaInvest to your home screen
            </p>
            {isIOS ? (
              <p className="text-xs text-slate-400 mt-1">
                Tap the{" "}
                <span className="font-mono">⎙</span> Share button, then &quot;Add
                to Home Screen&quot;
              </p>
            ) : (
              <p className="text-xs text-slate-400 mt-1">
                Install for quick access to your portfolio at a glance.
              </p>
            )}
          </div>
        </div>
        {!isIOS && (
          <div className="flex gap-2 mt-3">
            <button
              onClick={handleDismiss}
              className="flex-1 py-1.5 rounded-lg border border-white/[0.08] text-xs text-slate-400 hover:bg-white/[0.05] transition-all"
            >
              Not now
            </button>
            <button
              onClick={handleInstall}
              className="flex-1 py-1.5 rounded-lg bg-emerald-500 text-emerald-950 text-xs font-semibold hover:bg-emerald-400 transition-all"
            >
              Install
            </button>
          </div>
        )}
        {isIOS && (
          <button
            onClick={handleDismiss}
            className="mt-2 text-xs text-slate-500 hover:text-slate-300 transition-colors"
          >
            Dismiss
          </button>
        )}
      </div>
    </div>
  );
}
