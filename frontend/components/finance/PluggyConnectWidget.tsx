"use client";
/**
 * PluggyConnectWidget — Brazilian Open Finance integration.
 * Fetches a connect token from the backend and launches the Pluggy Connect
 * browser widget for OAuth bank/broker authorization.
 *
 * Usage:
 *   <PluggyConnectWidget onSuccess={(itemId) => ...} onClose={() => ...} />
 *
 * Pluggy Connect SDK is loaded from CDN at runtime (no npm package needed).
 * Docs: https://docs.pluggy.ai/docs/pluggy-connect
 */
import { useEffect, useRef, useState } from "react";

interface PluggyConnectWidgetProps {
  onSuccess?: (itemId: string) => void;
  onClose?: () => void;
  onError?: (error: string) => void;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "https://investapi.ovelha.us";
const PLUGGY_SDK_URL = "https://cdn.pluggy.ai/pluggy-connect/v2/pluggy-connect.js";

declare global {
  interface Window {
    PluggyConnect?: new (config: {
      connectToken: string;
      onSuccess?: (data: { item: { id: string } }) => void;
      onError?: (error: string) => void;
      onClose?: () => void;
    }) => { init: () => void };
  }
}

export function PluggyConnectWidget({
  onSuccess,
  onClose,
  onError,
}: PluggyConnectWidgetProps) {
  const [status, setStatus] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const sdkLoaded = useRef(false);

  async function handleConnect() {
    setStatus("loading");
    setErrorMsg(null);

    try {
      // Load Pluggy Connect SDK if not already loaded
      if (!sdkLoaded.current && !window.PluggyConnect) {
        await new Promise<void>((resolve, reject) => {
          const script = document.createElement("script");
          script.src = PLUGGY_SDK_URL;
          script.onload = () => { sdkLoaded.current = true; resolve(); };
          script.onerror = () => reject(new Error("Failed to load Pluggy Connect SDK"));
          document.head.appendChild(script);
        });
      }

      // Get connect token from backend
      const res = await fetch(`${API_BASE}/connections/token`, { method: "POST" });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail ?? `Token fetch failed (HTTP ${res.status})`);
      }
      const { access_token } = await res.json();

      if (!window.PluggyConnect) {
        throw new Error("Pluggy Connect SDK not available");
      }

      setStatus("ready");

      // Launch the widget
      const widget = new window.PluggyConnect({
        connectToken: access_token,
        onSuccess: (data) => {
          const itemId = data?.item?.id;
          if (itemId && onSuccess) onSuccess(itemId);
        },
        onError: (err) => {
          setErrorMsg(err);
          setStatus("error");
          if (onError) onError(err);
        },
        onClose: () => {
          setStatus("idle");
          if (onClose) onClose();
        },
      });

      widget.init();
    } catch (err: any) {
      const msg = err.message ?? "Failed to connect";
      setErrorMsg(msg);
      setStatus("error");
      if (onError) onError(msg);
    }
  }

  return (
    <div className="space-y-3">
      <button
        onClick={handleConnect}
        disabled={status === "loading"}
        className="w-full py-2.5 rounded-lg text-sm font-medium transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
        style={{
          background: "rgba(16,185,129,0.15)",
          border: "1px solid rgba(16,185,129,0.3)",
          color: "#10b981",
        }}
      >
        {status === "loading" ? (
          <>
            <span className="animate-spin text-base">⟳</span>
            Connecting...
          </>
        ) : (
          <>
            <span className="text-base">🇧🇷</span>
            Connect Brazilian Bank / Broker
          </>
        )}
      </button>

      {status === "error" && errorMsg && (
        <div className="rounded-lg px-3 py-2 text-xs" style={{ background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.2)", color: "#f87171" }}>
          {errorMsg.includes("PLUGGY_CLIENT_ID") || errorMsg.includes("not configured")
            ? "Pluggy not configured. Set PLUGGY_CLIENT_ID and PLUGGY_CLIENT_SECRET in backend/.env to enable Open Finance sync."
            : errorMsg}
        </div>
      )}

      <p className="text-[10px] text-white/20 text-center">
        Powered by Pluggy Open Finance · Read-only access · Data stays private
      </p>
    </div>
  );
}
