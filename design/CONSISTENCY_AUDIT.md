# OvelhaInvest — Design Consistency Audit
Generated: 2026-03-24

## Two Design Systems Found

### Resolution
The Stitch glassmorphism design (design/DESIGN.md) is canonical — it matches all 10 screen
HTML exports and the component designs built during Phases 1-10.

The root DESIGN.md ("Brutalist Quantitative") is an earlier spec that was superseded by Stitch.
It should be archived but not followed.

## Top 10 Inconsistencies Found (Pre-Fix)

1. **Background color**: Pages use `bg-[#050508]` (correct), but also `bg-white/[0.04]` for cards
   instead of the Stitch glass-card pattern (`rgba(31,32,33,0.6)` with `backdrop-blur-20px`).

2. **Positive color**: Pages inconsistently use `text-emerald-400`, `text-green-400`, `text-emerald-500`.
   Stitch canonical: `text-primary` = `#4edea3`.

3. **Negative color**: Pages use `text-rose-400`, `text-red-400`, `text-rose-500`.
   Stitch canonical: `text-error` = `#ffb4ab`.

4. **Warning color**: Mix of `text-amber-400`, `text-yellow-400`.
   Stitch canonical: `text-tertiary` = `#ffb95f`.

5. **Card radius**: Mix of `rounded-2xl`, `rounded-xl`, `rounded-lg`.
   Stitch canonical: `rounded-2xl` (1rem default radius).

6. **Muted text**: Mix of `text-slate-400`, `text-slate-500`, `text-gray-400`.
   Stitch canonical: `text-on-surface-variant` = `#bbcabf`, `text-outline` = `#86948a`.

7. **Badge styles**: Mix of inline Tailwind badge spans and inconsistent colors.
   Fix: All badges → `<OIBadge variant="...">`.

8. **Tab bars**: Different tab styles per page (some glass pills, some underline).
   Fix: All tabs → `<OITabBar>`.

9. **Table headers**: Mix of `text-[10px]`, `text-xs`, different opacity levels.
   Stitch: `text-[11px] font-mono uppercase tracking-widest text-outline`.

10. **Page headers**: Inconsistent sizing (some `text-4xl`, some `text-3xl`, mix of `font-black` vs `font-bold`).
    Stitch: `text-3xl font-bold tracking-tight uppercase font-mono`.

## Stitch Color Token Map

| Old Class | New Class | Hex |
|-----------|-----------|-----|
| `text-emerald-400` | `text-primary` | `#4edea3` |
| `text-emerald-500` | `text-primary-container` | `#10b981` |
| `text-rose-400` / `text-red-400` | `text-error` | `#ffb4ab` |
| `text-amber-400` | `text-tertiary` | `#ffb95f` |
| `text-slate-100`, `text-white` | `text-on-surface` | `#e3e2e3` |
| `text-slate-400` | `text-on-surface-variant` | `#bbcabf` |
| `text-slate-500` | `text-outline` | `#86948a` |
| `bg-white/[0.04]` | `.glass-card` | rgba(31,32,33,0.6) |
| `border-white/[0.08]` | (included in .glass-card) | rgba(255,255,255,0.08) |
| `bg-emerald-500/10` | `bg-primary/10` | — |
| `bg-rose-500/10` | `bg-error/10` | — |
| `bg-amber-500/10` | `bg-tertiary/10` | — |
