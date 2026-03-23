"use client";

/**
 * /config — Phase 6: Strategy Config viewer + Alert Rules manager.
 * Two tabs: "Strategy" (JSON viewer, version history, allocation comparison)
 *            "Alert Rules" (toggle active/inactive, test button, conditions accordion)
 */

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { AlertRule } from "@/lib/types";

// ── Design tokens ─────────────────────────────────────────────────────────────
const glass     = "rounded-2xl border border-white/[0.08] bg-white/[0.03] backdrop-blur-sm";
const glassInner = `${glass} p-5`;

const SLEEVE_TARGETS: Record<string, { target: number; min: number; max: number; color: string }> = {
  us_equity:     { target: 0.45, min: 0.40, max: 0.50, color: "#10b981" },
  intl_equity:   { target: 0.15, min: 0.10, max: 0.20, color: "#06b6d4" },
  bonds:         { target: 0.20, min: 0.10, max: 0.30, color: "#3b82f6" },
  brazil_equity: { target: 0.10, min: 0.05, max: 0.15, color: "#22c55e" },
  crypto:        { target: 0.07, min: 0.05, max: 0.10, color: "#8b5cf6" },
  cash:          { target: 0.03, min: 0.02, max: 0.10, color: "#64748b" },
};

const SLEEVE_LABELS: Record<string, string> = {
  us_equity: "US Equity", intl_equity: "Intl Equity", bonds: "Bonds",
  brazil_equity: "Brazil Eq.", crypto: "Crypto", cash: "Cash",
};

const RULE_TYPE_ICONS: Record<string, string> = {
  drawdown: "📉", drift: "⚖️", opportunity: "🚨", sell_target: "🎯",
  earnings: "📅", brazil_darf: "🇧🇷", fx_move: "💱", correlation: "🔗", deposit: "💰",
};

// ── Helper: JSON syntax highlight ─────────────────────────────────────────────
function JsonHighlight({ obj }: { obj: unknown }) {
  const raw = JSON.stringify(obj, null, 2);
  const html = raw
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+-]?\d+)?)/g, (match) => {
      let cls = "text-emerald-400"; // number
      if (/^"/.test(match)) {
        cls = /:$/.test(match) ? "text-violet-400" : "text-amber-300"; // key vs string
      } else if (/true|false/.test(match)) {
        cls = "text-blue-400";
      } else if (/null/.test(match)) {
        cls = "text-rose-400";
      }
      return `<span class="${cls}">${match}</span>`;
    });
  return (
    <pre
      className="text-xs font-mono text-white/70 overflow-auto max-h-[480px] leading-relaxed"
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}

// ── Strategy Config static data (from CLAUDE.md Section 5) ───────────────────
const STRATEGY_CONFIG_V1 = {
  version: "1.0.0",
  sleeve_targets: SLEEVE_TARGETS,
  drift_threshold: 0.05,
  hard_rebalance_cooldown_days: 30,
  min_trade_usd: 50,
  max_single_trade_pct: 0.05,
  volatility_regime: {
    vix_threshold: 30,
    equity_daily_move_pct: 0.03,
    crypto_daily_move_pct: 0.10,
    defer_dca_days: [1, 3],
  },
  drawdown_thresholds: {
    alert: 0.25,
    pause_automation: 0.40,
    behavioral_max: 0.35,
  },
  opportunity_rules: {
    max_events_per_year: 5,
    required_min_margin_of_safety: 0.15,
    tier_1: { drawdown_from_high: 0.30, deploy_vault_fraction: 0.20 },
    tier_2: { drawdown_from_high: 0.50, deploy_vault_fraction: 0.30 },
  },
};

// ── Allocation comparison models ──────────────────────────────────────────────
const ALLOCATION_MODELS = {
  current: SLEEVE_TARGETS,
  swensen: {
    us_equity:     { target: 0.30, min: 0.25, max: 0.35, color: "#10b981" },
    intl_equity:   { target: 0.30, min: 0.25, max: 0.35, color: "#06b6d4" },
    bonds:         { target: 0.15, min: 0.10, max: 0.20, color: "#3b82f6" },
    brazil_equity: { target: 0.05, min: 0.00, max: 0.10, color: "#22c55e" },
    crypto:        { target: 0.00, min: 0.00, max: 0.00, color: "#8b5cf6" },
    cash:          { target: 0.20, min: 0.15, max: 0.25, color: "#64748b" },
  },
  all_weather: {
    us_equity:     { target: 0.30, min: 0.25, max: 0.35, color: "#10b981" },
    intl_equity:   { target: 0.00, min: 0.00, max: 0.00, color: "#06b6d4" },
    bonds:         { target: 0.55, min: 0.50, max: 0.60, color: "#3b82f6" },
    brazil_equity: { target: 0.00, min: 0.00, max: 0.00, color: "#22c55e" },
    crypto:        { target: 0.00, min: 0.00, max: 0.00, color: "#8b5cf6" },
    cash:          { target: 0.15, min: 0.10, max: 0.20, color: "#64748b" },
  },
};

type AllocModel = keyof typeof ALLOCATION_MODELS;

// ── Main ──────────────────────────────────────────────────────────────────────
export default function ConfigPage() {
  const [tab, setTab]                     = useState<"strategy" | "alerts">("strategy");
  const [allocModel, setAllocModel]       = useState<AllocModel>("current");
  const [alertRules, setAlertRules]       = useState<AlertRule[]>([]);
  const [loadingRules, setLoadingRules]   = useState(false);
  const [testingId, setTestingId]         = useState<string | null>(null);
  const [expandedId, setExpandedId]       = useState<string | null>(null);
  const [toastMsg, setToastMsg]           = useState<string | null>(null);

  useEffect(() => {
    if (tab === "alerts" && alertRules.length === 0) {
      setLoadingRules(true);
      api.listAlertRules({ include_inactive: true })
        .then(setAlertRules)
        .catch(() => null)
        .finally(() => setLoadingRules(false));
    }
  }, [tab, alertRules.length]);

  function showToast(msg: string) {
    setToastMsg(msg);
    setTimeout(() => setToastMsg(null), 3000);
  }

  async function handleToggle(rule: AlertRule) {
    const prev = [...alertRules];
    setAlertRules((rs) => rs.map((r) => r.id === rule.id ? { ...r, is_active: !r.is_active } : r));
    try {
      await api.toggleAlertRule(rule.id);
      showToast(`${rule.rule_name} ${rule.is_active ? "disabled" : "enabled"}`);
    } catch {
      setAlertRules(prev);
      showToast("Failed to update rule");
    }
  }

  async function handleTest(rule: AlertRule) {
    setTestingId(rule.id);
    try {
      const res = await api.testAlertRule(rule.id);
      showToast(res.sent ? `✅ Test sent for ${res.rule_name}` : "❌ Telegram not configured");
    } catch {
      showToast("Failed to send test");
    } finally {
      setTestingId(null);
    }
  }

  const model = ALLOCATION_MODELS[allocModel];

  return (
    <div className="min-h-screen p-6 space-y-5" style={{ background: "#050508" }}>
      {/* Toast */}
      {toastMsg && (
        <div className="fixed bottom-6 right-6 z-50 rounded-xl border border-white/10 bg-white/[0.06] backdrop-blur-md px-4 py-2.5 text-sm text-white/90 shadow-xl">
          {toastMsg}
        </div>
      )}

      {/* Header */}
      <div>
        <h1 className="text-xl font-semibold text-white/95 tracking-tight">Config</h1>
        <p className="text-xs text-white/40 mt-0.5">Strategy configuration &amp; alert rule management</p>
      </div>

      {/* Tab bar */}
      <div className="flex gap-2">
        {(["strategy", "alerts"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-1.5 rounded-full text-xs font-medium border transition-all ${
              tab === t
                ? "border-violet-500/40 bg-violet-500/10 text-violet-300"
                : "border-white/[0.08] bg-white/[0.02] text-white/40 hover:text-white/60"
            }`}
          >
            {t === "strategy" ? "⚙️ Strategy Config" : "🔔 Alert Rules"}
          </button>
        ))}
      </div>

      {/* ── Strategy tab ── */}
      {tab === "strategy" && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Left: version history */}
          <div className={`${glassInner} flex flex-col gap-3`}>
            <p className="text-xs text-white/40 uppercase tracking-widest">Version History</p>
            <div
              className="flex items-center justify-between px-3 py-2 rounded-lg border"
              style={{ borderColor: "rgba(139,92,246,0.3)", background: "rgba(139,92,246,0.06)" }}
            >
              <div>
                <p className="text-xs font-mono text-violet-300 font-semibold">v1.0.0</p>
                <p className="text-[10px] text-white/30">Active · {new Date().toLocaleDateString()}</p>
              </div>
              <span className="text-[9px] px-1.5 py-0.5 rounded-full border border-emerald-500/30 text-emerald-400 bg-emerald-500/8">
                ACTIVE
              </span>
            </div>
            <p className="text-[10px] text-white/20 mt-auto">
              New versions created automatically when strategy config changes.
            </p>
          </div>

          {/* Right: allocation comparison + JSON viewer */}
          <div className="lg:col-span-2 space-y-4">
            {/* Allocation model comparison */}
            <div className={glassInner}>
              <div className="flex items-center justify-between mb-4">
                <p className="text-xs text-white/40 uppercase tracking-widest">Allocation Targets</p>
                <div className="flex gap-1">
                  {(Object.keys(ALLOCATION_MODELS) as AllocModel[]).map((m) => (
                    <button
                      key={m}
                      onClick={() => setAllocModel(m)}
                      className={`px-2.5 py-1 rounded-full text-[10px] font-medium border transition-all ${
                        allocModel === m
                          ? "border-white/20 bg-white/[0.08] text-white/80"
                          : "border-white/[0.06] text-white/30 hover:text-white/50"
                      }`}
                    >
                      {m === "current" ? "Current" : m === "swensen" ? "Swensen" : "All-Weather"}
                    </button>
                  ))}
                </div>
              </div>
              <div className="space-y-2.5">
                {Object.entries(model).map(([sleeve, cfg]) => {
                  if (cfg.target === 0) return null;
                  return (
                    <div key={sleeve} className="grid grid-cols-12 items-center gap-2 text-xs">
                      <span className="col-span-3 text-white/50 truncate">{SLEEVE_LABELS[sleeve] ?? sleeve}</span>
                      <div className="col-span-7 h-1.5 rounded-full bg-white/[0.06] relative">
                        <div
                          className="absolute top-0 h-full rounded-full transition-all duration-500"
                          style={{ width: `${cfg.target * 100}%`, background: cfg.color, opacity: 0.75 }}
                        />
                        {allocModel !== "current" && SLEEVE_TARGETS[sleeve] && (
                          <div
                            className="absolute top-0 h-full rounded-full opacity-30 border-r-2"
                            style={{ width: `${SLEEVE_TARGETS[sleeve].target * 100}%`, borderColor: SLEEVE_TARGETS[sleeve].color }}
                          />
                        )}
                      </div>
                      <span className="col-span-2 text-right font-mono text-white/60">
                        {(cfg.target * 100).toFixed(0)}%
                        <span className="text-white/25 text-[9px] ml-1">
                          ({(cfg.min * 100).toFixed(0)}–{(cfg.max * 100).toFixed(0)})
                        </span>
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* JSON config viewer */}
            <div className={`${glass} p-5`}>
              <div className="flex items-center justify-between mb-3">
                <p className="text-xs text-white/40 uppercase tracking-widest">Strategy Config JSON</p>
                <span className="text-[10px] text-white/25 border border-white/10 rounded px-2 py-0.5 font-mono">
                  v1.0.0 · Read Only
                </span>
              </div>
              <div className="rounded-xl bg-white/[0.02] p-4 border border-white/[0.05]">
                <JsonHighlight obj={STRATEGY_CONFIG_V1} />
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Alert Rules tab ── */}
      {tab === "alerts" && (
        <div className={glassInner}>
          <div className="flex items-center justify-between mb-4">
            <p className="text-xs text-white/40 uppercase tracking-widest">Alert Rules</p>
            <span className="text-[10px] text-white/25">
              {alertRules.filter((r) => r.is_active).length} active / {alertRules.length} total
            </span>
          </div>

          {loadingRules ? (
            <div className="space-y-2">
              {Array.from({ length: 6 }).map((_, i) => (
                <div key={i} className="h-12 rounded-xl bg-white/[0.04] animate-pulse" />
              ))}
            </div>
          ) : alertRules.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-white/30 text-sm">No alert rules found.</p>
              <p className="text-white/20 text-xs mt-1">Run POST /admin/seed to insert built-in rules.</p>
            </div>
          ) : (
            <div className="space-y-2">
              {alertRules.map((rule) => (
                <AlertRuleRow
                  key={rule.id}
                  rule={rule}
                  expanded={expandedId === rule.id}
                  testing={testingId === rule.id}
                  onToggle={() => handleToggle(rule)}
                  onTest={() => handleTest(rule)}
                  onExpand={() => setExpandedId(expandedId === rule.id ? null : rule.id)}
                />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── AlertRuleRow ──────────────────────────────────────────────────────────────
function AlertRuleRow({
  rule, expanded, testing, onToggle, onTest, onExpand,
}: {
  rule: AlertRule;
  expanded: boolean;
  testing: boolean;
  onToggle: () => void;
  onTest: () => void;
  onExpand: () => void;
}) {
  const icon = RULE_TYPE_ICONS[rule.rule_type] ?? "🔔";

  return (
    <div
      className={`rounded-xl border transition-all ${
        rule.is_active
          ? "border-white/[0.08] bg-white/[0.02]"
          : "border-white/[0.04] bg-white/[0.01] opacity-60"
      }`}
    >
      <div className="flex items-center gap-3 p-3">
        {/* Icon + name */}
        <span className="text-base w-6 text-center shrink-0">{icon}</span>
        <button
          onClick={onExpand}
          className="flex-1 flex items-center gap-2 text-left"
        >
          <span className="text-sm text-white/80 font-medium">{rule.rule_name}</span>
          <span className="text-[10px] text-white/30 font-mono border border-white/[0.06] rounded px-1.5 py-0.5">
            {rule.rule_type}
          </span>
          {rule.source === "builtin" && (
            <span className="text-[9px] text-violet-400/60 border border-violet-400/20 rounded px-1 py-0.5">
              built-in
            </span>
          )}
          <span className="ml-auto text-white/20 text-xs">{expanded ? "▲" : "▼"}</span>
        </button>

        {/* Last triggered */}
        {rule.last_triggered && (
          <span className="text-[10px] text-white/25 font-mono shrink-0 hidden md:block">
            {new Date(rule.last_triggered).toLocaleDateString()}
          </span>
        )}

        {/* Test button */}
        <button
          onClick={onTest}
          disabled={testing}
          className={`text-[10px] px-2 py-1 rounded border transition-all shrink-0 ${
            testing
              ? "border-white/10 text-white/20"
              : "border-white/[0.08] text-white/40 hover:text-white/70 hover:border-white/20"
          }`}
        >
          {testing ? "..." : "Test"}
        </button>

        {/* Toggle switch */}
        <button
          onClick={onToggle}
          className={`relative w-9 h-5 rounded-full border transition-all shrink-0 ${
            rule.is_active
              ? "bg-emerald-500/20 border-emerald-500/40"
              : "bg-white/[0.04] border-white/10"
          }`}
        >
          <span
            className={`absolute top-0.5 h-4 w-4 rounded-full border transition-all ${
              rule.is_active
                ? "left-[18px] bg-emerald-400 border-emerald-300"
                : "left-0.5 bg-white/20 border-white/10"
            }`}
          />
        </button>
      </div>

      {/* Expanded: conditions JSON */}
      {expanded && (
        <div className="px-3 pb-3 border-t border-white/[0.05] mt-0 pt-3">
          <p className="text-[10px] text-white/30 uppercase tracking-widest mb-2">Conditions</p>
          <div className="rounded-lg bg-white/[0.02] p-3 border border-white/[0.04]">
            <pre className="text-[11px] font-mono text-white/50 overflow-auto max-h-32">
              {JSON.stringify(rule.conditions, null, 2)}
            </pre>
          </div>
          {rule.last_triggered && (
            <p className="text-[10px] text-white/25 mt-2 font-mono">
              Last triggered: {new Date(rule.last_triggered).toLocaleString()}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
