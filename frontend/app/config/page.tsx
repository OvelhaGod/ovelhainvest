"use client";

/**
 * /config — Phase 6: Strategy Config viewer + Alert Rules manager.
 * Two tabs: "Strategy" (JSON viewer, version history, allocation comparison)
 *            "Alert Rules" (toggle active/inactive, test button, conditions accordion)
 */

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { AlertRule } from "@/lib/types";

// ── Types ─────────────────────────────────────────────────────────────────────
interface RebalanceTrade {
  sleeve: string;
  action: "buy" | "sell";
  amount_usd: number;
  from_weight: number;
  to_weight: number;
  asset_suggestion: string;
}
interface RebalancePreview {
  total_value_usd: number;
  current_weights: Record<string, number>;
  target_weights: Record<string, number>;
  drifts: Record<string, number>;
  proposed_trades: RebalanceTrade[];
  estimated_tax_usd: number;
  tax_warning: boolean;
  tax_warning_message: string | null;
  total_trades: number;
  total_buy_usd: number;
  total_sell_usd: number;
}

// ── Design tokens ─────────────────────────────────────────────────────────────
const glass     = "glass-card";
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
      let cls = "text-primary"; // number
      if (/^"/.test(match)) {
        cls = /:$/.test(match) ? "text-secondary" : "text-tertiary"; // key vs string
      } else if (/true|false/.test(match)) {
        cls = "text-blue-400";
      } else if (/null/.test(match)) {
        cls = "text-error";
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
  const [tab, setTab]                     = useState<"strategy" | "alerts" | "rebalance">("strategy");
  const [allocModel, setAllocModel]       = useState<AllocModel>("current");
  const [alertRules, setAlertRules]       = useState<AlertRule[]>([]);
  const [loadingRules, setLoadingRules]   = useState(false);
  const [testingId, setTestingId]         = useState<string | null>(null);
  const [expandedId, setExpandedId]       = useState<string | null>(null);
  const [toastMsg, setToastMsg]           = useState<string | null>(null);
  const [rebalPreview, setRebalPreview]   = useState<RebalancePreview | null>(null);
  const [rebalLoading, setRebalLoading]   = useState(false);
  const [rebalError, setRebalError]       = useState<string | null>(null);

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

  async function fetchRebalancePreview() {
    setRebalLoading(true);
    setRebalError(null);
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL ?? "https://investapi.ovelha.us"}/simulation/rebalance_preview`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      if (!res.ok) throw new Error(`API ${res.status}`);
      setRebalPreview(await res.json() as RebalancePreview);
    } catch (e) {
      setRebalError(e instanceof Error ? e.message : "Error");
    } finally {
      setRebalLoading(false);
    }
  }

  const model = ALLOCATION_MODELS[allocModel];

  return (
    <div className="min-h-screen p-5 space-y-4" style={{ background: "#050508" }}>
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
        {([
          { id: "strategy",  label: "⚙️ Strategy Config" },
          { id: "alerts",    label: "🔔 Alert Rules" },
          { id: "rebalance", label: "⚖️ Rebalance Preview" },
        ] as const).map(({ id, label }) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            className={`px-4 py-1.5 rounded-full text-xs font-medium border transition-all ${
              tab === id
                ? "border-violet-500/40 bg-violet-500/10 text-violet-300"
                : "border-white/[0.08] bg-white/[0.02] text-white/40 hover:text-white/60"
            }`}
          >
            {label}
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
              <span className="text-[9px] px-1.5 py-0.5 rounded-full border border-primary/30 text-primary bg-primary/10">
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

      {/* ── Rebalance Preview tab ── */}
      {tab === "rebalance" && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <p className="text-xs text-white/40">Simulates a hard rebalance without executing any trades.</p>
            <button
              onClick={fetchRebalancePreview}
              disabled={rebalLoading}
              className="px-5 py-1.5 rounded-xl text-xs font-semibold transition-all"
              style={{ background: rebalLoading ? "rgba(99,102,241,0.2)" : "linear-gradient(135deg, #6366f1, #8b5cf6)", color: "#fff" }}
            >
              {rebalLoading ? "Loading…" : "Preview Hard Rebalance"}
            </button>
          </div>

          {rebalError && (
            <div className="rounded-xl px-4 py-3 text-xs" style={{ background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.2)", color: "#f87171" }}>
              {rebalError}
            </div>
          )}

          {rebalPreview && (
            <>
              {/* Tax warning */}
              {rebalPreview.tax_warning && (
                <div className="rounded-xl px-4 py-3 flex items-start gap-3" style={{ background: "rgba(245,158,11,0.08)", border: "1px solid rgba(245,158,11,0.25)" }}>
                  <span>⚠️</span>
                  <div>
                    <p className="text-xs font-medium" style={{ color: "#fbbf24" }}>Tax Impact Warning</p>
                    <p className="text-xs mt-0.5" style={{ color: "#94a3b8" }}>{rebalPreview.tax_warning_message}</p>
                    <p className="text-xs mt-0.5 font-mono" style={{ color: "#f59e0b" }}>Estimated tax: ${rebalPreview.estimated_tax_usd.toFixed(0)}</p>
                  </div>
                </div>
              )}

              {/* Summary row */}
              <div className="grid grid-cols-4 gap-3">
                {[
                  { label: "Portfolio Value", value: `$${(rebalPreview.total_value_usd / 1000).toFixed(0)}K` },
                  { label: "Total Trades",    value: String(rebalPreview.total_trades) },
                  { label: "Total Buys",      value: `$${rebalPreview.total_buy_usd.toFixed(0)}`,  color: "#10b981" },
                  { label: "Total Sells",     value: `$${rebalPreview.total_sell_usd.toFixed(0)}`, color: "#ef4444" },
                ].map(({ label, value, color }) => (
                  <div key={label} className={`${glassInner} text-center`}>
                    <p className="text-[10px] text-white/30 uppercase tracking-wider">{label}</p>
                    <p className="text-lg font-bold font-mono mt-1" style={{ color: color ?? "#f1f5f9" }}>{value}</p>
                  </div>
                ))}
              </div>

              {/* Before/after weights */}
              <div className={glassInner}>
                <p className="text-xs text-white/40 uppercase tracking-widest mb-4">Sleeve Weights — Current vs Target</p>
                <div className="space-y-3">
                  {Object.entries(SLEEVE_TARGETS).map(([sleeve, targets]) => {
                    const current = rebalPreview.current_weights[sleeve] ?? 0;
                    const target  = targets.target;
                    const drift   = rebalPreview.drifts[sleeve] ?? 0;
                    const color   = targets.color;
                    return (
                      <div key={sleeve} className="grid grid-cols-12 items-center gap-2 text-xs">
                        <span className="col-span-2 text-white/50 truncate capitalize">{SLEEVE_LABELS[sleeve] ?? sleeve}</span>
                        <div className="col-span-7 relative h-3 rounded-full" style={{ background: "rgba(255,255,255,0.06)" }}>
                          {/* target ghost */}
                          <div className="absolute top-0 h-full rounded-full opacity-20" style={{ width: `${target * 100}%`, background: color }} />
                          {/* current */}
                          <div className="absolute top-0 h-full rounded-full transition-all" style={{ width: `${Math.min(current * 100, 100)}%`, background: color }} />
                          {/* target marker */}
                          <div className="absolute top-0 w-px h-full bg-white/40" style={{ left: `${target * 100}%` }} />
                        </div>
                        <span className="col-span-1 text-right font-mono text-white/60">{(current * 100).toFixed(0)}%</span>
                        <span className={`col-span-2 text-right font-mono text-xs ${Math.abs(drift) > 0.05 ? "text-tertiary" : "text-white/30"}`}>
                          {drift > 0 ? "+" : ""}{(drift * 100).toFixed(1)}%
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Proposed trades */}
              {rebalPreview.proposed_trades.length > 0 && (
                <div className={glassInner}>
                  <p className="text-xs text-white/40 uppercase tracking-widest mb-4">Proposed Trades</p>
                  <div className="space-y-2">
                    {rebalPreview.proposed_trades.map((t, i) => (
                      <div key={i} className="flex items-center justify-between py-2 px-3 rounded-xl" style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.05)" }}>
                        <div className="flex items-center gap-3">
                          <span
                            className="px-2 py-0.5 rounded-full text-xs font-semibold uppercase"
                            style={{
                              background: t.action === "buy" ? "rgba(16,185,129,0.12)" : "rgba(239,68,68,0.12)",
                              color: t.action === "buy" ? "#34d399" : "#f87171",
                              border: `1px solid ${t.action === "buy" ? "rgba(16,185,129,0.25)" : "rgba(239,68,68,0.25)"}`,
                            }}
                          >
                            {t.action}
                          </span>
                          <div>
                            <p className="text-xs font-medium text-white/80">{t.asset_suggestion}</p>
                            <p className="text-[10px] text-white/30 capitalize">{(t.sleeve ?? "").replace("_", " ")} sleeve · {(t.from_weight * 100).toFixed(1)}% → {(t.to_weight * 100).toFixed(1)}%</p>
                          </div>
                        </div>
                        <p className="font-mono text-sm font-bold" style={{ color: t.action === "buy" ? "#10b981" : "#ef4444" }}>
                          ${t.amount_usd.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                        </p>
                      </div>
                    ))}
                  </div>
                  <p className="text-[10px] text-white/20 mt-3 italic">
                    ⚠ Preview only — no trades have been executed. Approve via Telegram or Signals page.
                  </p>
                </div>
              )}
            </>
          )}

          {!rebalPreview && !rebalLoading && !rebalError && (
            <div className={`${glassInner} flex flex-col items-center justify-center py-12 gap-3`}>
              <span className="text-3xl opacity-40">⚖️</span>
              <p className="text-sm text-white/30">Click "Preview Hard Rebalance" to see what a full rebalance would look like.</p>
              <p className="text-xs text-white/20">No trades will be executed — simulation only.</p>
            </div>
          )}
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
              ? "bg-primary/20 border-primary/40"
              : "bg-white/[0.04] border-white/10"
          }`}
        >
          <span
            className={`absolute top-0.5 h-4 w-4 rounded-full border transition-all ${
              rule.is_active
                ? "left-[18px] bg-primary border-primary/80"
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
