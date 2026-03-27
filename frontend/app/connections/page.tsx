"use client";

/**
 * /connections — Open Finance connections via Pluggy (Phase 11+).
 * Current scope: setup instructions + status display.
 * Full implementation in Phase 11 (Personal Finance OS).
 */

import useSWR from "swr";
import { fetcher } from "@/lib/swr-config";
import { PluggyConnectWidget } from "@/components/finance/PluggyConnectWidget";

interface ConnectionStatus {
  connections: Array<{
    item_id: string;
    institution_name: string;
    last_sync: string | null;
    status: string;
  }>;
  message?: string;
  setup_docs?: string;
}

function GlassCard({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <div
      className={`rounded-2xl p-6 ${className}`}
      style={{
        background: "rgba(255,255,255,0.04)",
        backdropFilter: "blur(12px)",
        border: "1px solid rgba(255,255,255,0.08)",
      }}
    >
      {children}
    </div>
  );
}

export default function ConnectionsPage() {
  const { data, isLoading } = useSWR<ConnectionStatus>("/connections/status", fetcher, {
    refreshInterval: 60_000,
  });

  const hasConnections = (data?.connections?.length ?? 0) > 0;

  return (
    <div
      className="min-h-screen p-5 space-y-5"
      style={{
        background:
          "radial-gradient(ellipse 80% 50% at 50% -20%, rgba(99,102,241,0.10) 0%, transparent 60%), #050508",
      }}
    >
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center gap-3">
          <h1 className="text-xl font-bold text-[#f1f5f9]">Connections</h1>
          <span className="text-[10px] px-2 py-0.5 rounded-full font-medium bg-violet-500/10 text-violet-400 border border-violet-500/20">
            Phase 11
          </span>
        </div>
        <p className="text-xs text-[#475569] mt-1">
          Open Finance sync via Pluggy · Brazilian banks + brokers
        </p>
      </div>

      {/* Status banner */}
      {!isLoading && !hasConnections && (
        <GlassCard className="border-l-2 border-l-violet-500/40">
          <div className="flex items-start gap-4">
            <div className="w-10 h-10 rounded-xl bg-violet-500/10 border border-violet-500/20 flex items-center justify-center shrink-0 text-lg">
              🔗
            </div>
            <div className="flex-1">
              <h2 className="text-sm font-semibold text-[#f1f5f9] mb-1">No connections configured</h2>
              <p className="text-xs text-[#475569] leading-relaxed">
                {data?.message ?? "Connect your Brazilian bank and broker accounts to enable automatic transaction sync."}
              </p>
              <div className="mt-4">
                <PluggyConnectWidget
                  onSuccess={() => {
                    window.location.reload();
                  }}
                />
              </div>
              <div className="mt-2">
                <a
                  href="https://pluggy.ai"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs text-violet-400/60 hover:text-violet-400 transition-colors"
                >
                  Pluggy Documentation →
                </a>
              </div>
            </div>
          </div>
        </GlassCard>
      )}

      {/* Active connections list */}
      {hasConnections && (
        <div className="space-y-3">
          <h2 className="text-xs font-semibold text-[#475569] uppercase tracking-wider">
            Connected Institutions
          </h2>
          {data!.connections.map((conn) => (
            <GlassCard key={conn.item_id} className="flex items-center justify-between gap-4">
              <div>
                <p className="text-sm font-semibold text-[#f1f5f9]">{conn.institution_name}</p>
                <p className="text-xs text-[#475569] mt-0.5">
                  Last sync: {conn.last_sync ? new Date(conn.last_sync).toLocaleString() : "Never"}
                </p>
              </div>
              <span
                className={`text-[10px] px-2 py-0.5 rounded-full font-medium border ${
                  conn.status === "active"
                    ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                    : "bg-amber-500/10 text-amber-400 border-amber-500/20"
                }`}
              >
                {conn.status}
              </span>
            </GlassCard>
          ))}
        </div>
      )}

      {/* Setup guide */}
      <GlassCard>
        <h2 className="text-sm font-semibold text-[#f1f5f9] mb-4">Setup Guide</h2>
        <div className="space-y-4">
          {[
            {
              step: "1",
              title: "Get Pluggy credentials",
              desc: "Sign up at pluggy.ai and create a client application to receive your Client ID and Client Secret.",
              code: "PLUGGY_CLIENT_ID=your-client-id\nPLUGGY_CLIENT_SECRET=your-secret",
            },
            {
              step: "2",
              title: "Add to backend environment",
              desc: "Add the credentials to your backend/.env file and restart the server.",
              code: null,
            },
            {
              step: "3",
              title: "Connect your accounts",
              desc: "Once configured, this page will show a Pluggy Connect widget to link your Brazilian bank and broker accounts.",
              code: null,
            },
            {
              step: "4",
              title: "Automatic sync",
              desc: "After connecting, transactions will sync automatically via n8n workflows (Phase 11 full implementation).",
              code: null,
            },
          ].map(({ step, title, desc, code }) => (
            <div key={step} className="flex gap-4">
              <div className="w-6 h-6 rounded-full bg-indigo-500/15 border border-indigo-500/25 flex items-center justify-center text-[10px] font-bold text-indigo-400 shrink-0 mt-0.5">
                {step}
              </div>
              <div className="flex-1">
                <p className="text-xs font-semibold text-[#94a3b8]">{title}</p>
                <p className="text-xs text-[#475569] mt-0.5 leading-relaxed">{desc}</p>
                {code && (
                  <pre className="mt-2 p-2.5 rounded-lg bg-black/30 border border-white/[0.06] text-[10px] font-mono text-[#94a3b8] overflow-x-auto">
                    {code}
                  </pre>
                )}
              </div>
            </div>
          ))}
        </div>
      </GlassCard>

      {/* Supported institutions */}
      <GlassCard>
        <h2 className="text-sm font-semibold text-[#f1f5f9] mb-3">Supported Institutions (via Pluggy)</h2>
        <p className="text-xs text-[#475569] mb-4">
          Pluggy supports 200+ Brazilian financial institutions including:
        </p>
        <div className="grid grid-cols-3 gap-2">
          {[
            "Itaú", "Bradesco", "Nubank", "BTG Pactual", "XP Investimentos",
            "Clear Corretora", "Rico", "Inter", "Santander", "Caixa",
            "Banco do Brasil", "Sicoob",
          ].map((inst) => (
            <div
              key={inst}
              className="text-xs text-[#475569] px-2.5 py-1.5 rounded-lg border border-white/[0.05] bg-white/[0.02]"
            >
              {inst}
            </div>
          ))}
        </div>
      </GlassCard>
    </div>
  );
}
