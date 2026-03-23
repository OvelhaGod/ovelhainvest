# OvelhaInvest — Stitch Design Reference

**Stitch Project ID:** `11580419759191253062`
**Project URL:** https://stitch.withgoogle.com/u/1/projects/11580419759191253062
**Generated:** 2026-03-22
**Screens analyzed:** 10 (all visible screens)
**Design aesthetic:** Glassmorphism 2026 — "The Obsidian Ledger"

---

## Screen Index

| # | Slug | Stitch Title | Route | Screen ID |
|---|------|-------------|-------|-----------|
| 1 | `dashboard` | Final Dashboard — Obsidian Ledger | `/dashboard` | `2277c47567854717a7fa3e00e92fb99b` |
| 2 | `signals` | Final Signals & Activity | `/signals` | `4b0ba5c1aad34fe686727fb31e538cbc` |
| 3 | `assets` | Final Assets & Valuations | `/assets` | `e21d3b24395041269140399b703abf6a` |
| 4 | `performance` | Final Performance Analytics | `/performance` | `290fff9636ba460287367a74a5b5ebfa` |
| 5 | `projections` | Final Projections — Monte Carlo | `/projections` | `fa14630e602942fc88b00a661d607752` |
| 6 | `tax` | Final Tax Optimization | `/tax` | `bee56bf51ced4454a69aee8033e8addc` |
| 7 | `journal` | Final Decision Journal | `/journal` | `c2e71169585c46f3b664929c4d91dc85` |
| 8 | `config` | Final Portfolio Configuration | `/config` | `cfa6eb76b5444f32a9b01ed8d3baec1d` |
| 9 | `watchlist` | Market Watchlist | `/watchlist` | `ca527bbea2df4c4c9de26919580809b7` |
| 10 | `ai_insights` | AI Insights | `/ai_insights` | `c3041f17e9e1418fb8ad3ef936c78486` |

---

## Design System

### Color Palette

| Token | Hex | Usage |
|---|---|---|
| `primary` | `#4edea3` | Gains, success, positive values |
| `primary-container` | `#10b981` | Primary hover/active states |
| `secondary` | `#d0bcff` | AI/automation features |
| `secondary-container` | `#571bc1` | Violet accents |
| `tertiary` | `#ffb95f` | Warnings, volatility, amber alerts |
| `error` | `#ffb4ab` | Losses, drawdowns, risk |
| `background` | `#050508` | Page background (deepest) |
| `surface` | `#121315` | Main surface |
| `surface-container` | `#1f2021` | Cards and widgets |
| `surface-container-low` | `#1b1c1d` | Subtle containers |
| `surface-container-high` | `#292a2b` | Elevated surfaces |
| `on-surface` | `#e3e2e3` | Primary text |
| `on-surface-variant` | `#bbcabf` | Secondary text |
| `outline` | `#86948a` | Borders and dividers |
| `outline-variant` | `#3c4a42` | Ghost borders (8–12% opacity) |

### Typography

| Role | Font | Usage |
|---|---|---|
| **Headlines** | Geist Sans (700–900) | Page titles, section headers, card titles |
| **Body** | Inter (400–600) | Labels, descriptions, body copy |
| **Data/Numbers** | JetBrains Mono (400–700) | ALL numeric values, timestamps, tickers |

**Rules:**
- JetBrains Mono is mandatory for every number — no exceptions
- `tracking-tighter` (–0.05em) on Geist headlines
- `uppercase tracking-widest` on 10px label text (Inter or Mono)
- `display-lg` (3.5rem) for portfolio totals only

### Glassmorphism Base

```css
.glass-card {
  background: rgba(31, 32, 33, 0.4);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 1rem; /* rounded-2xl */
}
```

**Glow classes:**
```css
.emerald-glow { box-shadow: 0 0 20px rgba(16, 185, 129, 0.05); }
.violet-glow  { box-shadow: 0 0 20px rgba(139, 92, 246, 0.10); }
.amber-glow   { box-shadow: 0 0 20px rgba(245, 158, 11, 0.15); }
```

**Radial background glows (fixed, –z-10, pointer-events-none):**
```html
<div class="fixed top-[-10%] right-[-10%] w-[800px] h-[800px]
            bg-primary/5 blur-[120px] rounded-full -z-10 pointer-events-none" />
```

**Active nav indicator:**
```css
.active-nav-glow::before {
  content: '';
  position: absolute; left: 0;
  width: 2px; height: 24px;
  background: #10b981;
  box-shadow: 0 0 10px #10b981;
}
```

### Layout

- **Sidebar:** Fixed, 240px wide, `backdrop-blur-2xl bg-surface-container-lowest/40`
- **Main content:** `ml-[240px] overflow-y-auto`, padding `p-12` or `px-12 pb-12 pt-24`
- **Grid system:** 4-col (`grid-cols-4 gap-6`), 3-col (`grid-cols-3 gap-8`), 2-col (`grid-cols-2 gap-8`)

### Icons

Google Material Symbols Outlined, loaded via Google Fonts CDN:
```html
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined" rel="stylesheet" />
```
Usage: `<span class="material-symbols-outlined">dashboard</span>`

---

## Screen Specifications

### 1. Dashboard — `design/screens/dashboard.html`

**Layout:** Sidebar + content with FAB (floating action button)

**Sections (top → bottom):**
1. 4-card bento row: Net Worth, Today P&L, YTD Return, Max Drawdown
2. 60/40 split: SVG portfolio timeline chart + 3 vault progress cards
3. 60/40 split: Recent signals table + risk analytics grid
4. FAB: `bg-gradient-to-r from-primary to-primary-container rounded-full`

**Key patterns:**
- Metric cards: uppercase label (10px mono) + large value (Mono bold) + delta chip
- Chart SVG: gradient area fill + dashed benchmark line
- Vault cards: color-coded left border (primary/secondary/tertiary) + progress bar
- Signal row: pulse dot + event type + status badge

---

### 2. Signals — `design/screens/signals.html`

**Layout:** Full-width expanded signal detail + historical table

**Sections:**
1. Radial glow background (emerald top-right, violet bottom-left)
2. Expanded signal header: event name, live recommendation label, "Execute Batch" CTA
3. Signal logic chain: 3 cards (Momentum / Volatility / Correlation) with progress bars
4. AI Synthesis sidebar (right): `bg-secondary/5 border-secondary/10 violet-glow`
5. Historical activity table: 6 columns with status badges

**Key patterns:**
- Logic bars: primary (momentum), tertiary (volatility), secondary (correlation)
- Status badges: `px-3 py-1 rounded-full bg-primary/10 border border-primary/20 text-primary`
- AI quote: italic, leading-relaxed, `text-slate-300`
- Execute button: primary gradient + `shadow-[0_0_15px_rgba(16,185,129,0.3)]`

---

### 3. Assets — `design/screens/assets.html`

**Layout:** Table (calc 100% – 400px) + sticky right drawer (400px)

**Sections:**
1. Sortable asset table: symbol, class, price, margin-of-safety, factor analysis mini-bars
2. Right drawer: asset detail with large MOS badge, semicircle gauge SVG, quick metrics 2×2, news feed

**Key patterns:**
- Factor bars: VALUE (primary/opacity), MOM (primary/glow), QUAL (secondary)
- Selected row: `bg-primary/5`
- MOS badge: Geist 48px bold, text-primary, `.text-glow` class
- News items: `p-4 rounded-xl bg-white/[0.02] hover:bg-white/[0.05]`
- Asset class badge colors: custom per class (US_equity green, Brazil amber, Crypto violet, etc.)

---

### 4. Performance — `design/screens/performance.html`

**Layout:** Tab bar + 3 rows (period cards / ratio cards / chart)

**Sections:**
1. Glass pill tabs: Summary / Risk Metrics / Benchmarks / Attribution
2. 6 period return cards (1mo, 3mo, 6mo, YTD, 1yr, All-time) with progress bars
3. 3 large ratio cards: Sharpe (emerald-glow), Sortino (emerald-glow), Calmar (amber-glow)
4. SVG delta chart with portfolio vs benchmark vs alpha tooltip overlay

**Key patterns:**
- Ratio values: `text-6xl font-mono font-bold text-primary`
- Active tab: `bg-primary/10 text-primary rounded-full`
- Tooltip: `absolute left-[70%] top-0 glass-card`

---

### 5. Projections — `design/screens/projections.html`

**Layout:** Control panel + fan chart + 3 stat cards

**Sections:**
1. Simulation controls: Monthly contribution, Years, Market Model, Run button (glass-panel)
2. Probability envelope SVG: 5 percentile bands (5% / 25% / 50% / 75% / 95%)
3. 3 stat cards: Median End Balance, Time to $1M, 4% Survival Rate

**Key patterns:**
- Fan chart bands: gradient fills from `error/5` (pessimistic) to `primary/95` (optimistic)
- Median line: `stroke="#4edea3"` + `filter: drop-shadow(0 0 8px rgba(78,222,163,0.5))`
- Control inputs: `bg-transparent border-none font-mono` inside glass-panel
- Stat card icons: `bg-primary/10` / `bg-secondary/10` / `bg-tertiary/10` with border

---

### 6. Tax — `design/screens/tax.html`

**Layout:** Brazil exemption tracker + active lots table + harvesting opportunities

**Sections:**
1. Brazil R$20k monthly exemption progress bar with 80% threshold marker
2. Active tax lots table: symbol, cost basis, G/L, period (LT/ST), estimated tax
3. 2/3 – 1/3 split: harvesting opportunities + estimated savings

**Key patterns:**
- Progress bar: `from-tertiary/40 to-tertiary` gradient + glow
- Threshold at 80%: `absolute left-[80%] w-[2px] bg-error/60`
- LT badge: `bg-primary/10`, ST badge: `bg-secondary/10`
- "REVIEW" button: `bg-tertiary text-on-tertiary font-mono text-xs font-bold uppercase`

---

### 7. Journal — `design/screens/journal.html`

**Layout:** 2-card comparison + execution ledger + AI behavioral insight

**Sections:**
1. Two-card grid: "Followed System" (primary left border) vs "Overrode System" (amber left border)
2. Execution ledger table: ticker, class, 30D/90D returns, strategy note
3. AI Behavioral Insight block: violet-left-glow, bias detected, consistency score, recommendations

**Key patterns:**
- Fidelity percentage: `text-6xl font-mono font-bold tracking-tighter`
- Card left border: `border-l-4 border-l-[#10b981]` or `border-l-[#ffb95f]`
- `.violet-left-glow::before`: 3px left border, `box-shadow: 0 0 15px rgba(139,92,246,0.3)`
- Execution class badges: mono 10px font-bold uppercase tracking-wider

---

### 8. Config — `design/screens/config.html`

**Layout:** 35/65 split — version history sidebar + simulation + JSON editor

**Sections:**
1. Left: version list (active = `bg-primary/5 border-primary/20`) + AI insight box
2. Right top: allocation donut SVG + strategy comparison tabs + quick metrics
3. Right bottom: JSON syntax-highlighted config editor + "Deploy Changes" button

**Key patterns:**
- Syntax highlighting: keyword=`#d0bcff` (secondary), string=`#4edea3` (primary), number=`#ffb95f` (tertiary)
- Donut chart: SVG circles with `stroke-dasharray` for segments
- Active version: `border-l-2 border-primary` left accent
- Deploy button: primary gradient, 10px font-bold uppercase

---

### 9. Watchlist — `design/screens/watchlist.html`

**Layout:** Hero + asset table + 3-card bottom bento

**Sections:**
1. Hero with gradient line and "Market Intelligence" label
2. Asset table: icon, name/symbol, price, 24h change, sparkline SVG, action menu
3. Bottom 3 cards: VIX gauge, AI Sentiment bars, Top Momentum ticker

**Key patterns:**
- Asset icons: color-coded `bg-orange-500/10` (BTC), `bg-indigo-500/10` (ETH), `bg-cyan-500/10` (SOL)
- Sparklines: inline SVG with `filter: drop-shadow(0 0 4px currentColor)`
- Row hover: `hover:bg-[#4edea3]/[0.02]`
- Trend badge: `rounded-full px-2.5 py-1 bg-primary/10` or `bg-error/10`

---

### 10. AI Insights — `design/screens/ai_insights.html`

**Layout:** 8-col main + 4-col assistant sidebar

**Sections:**
1. Portfolio forecast hero: confidence score (mono 24px, text-secondary) + SVG line chart
2. 2-card grid: Sentiment analysis + Dividend alerts
3. 3-col optimization suggestions: REBALANCE/DIVERSIFY/RISK MITIGATION
4. Right sidebar: AI Strategy Assistant chat (bubbles + typing animation + quick-action pills)

**Key patterns:**
- `.ai-violet-glow`: `radial-gradient(circle, rgba(139,92,246,0.08), transparent 70%)`
- AI message: `bg-[#8b5cf6]/5 border-[#8b5cf6]/20 rounded-2xl rounded-tl-none`
- User message: `bg-white/10 border-white/10 rounded-2xl rounded-tr-none`
- Typing dots: 3 spans with `animate-bounce` + staggered `animation-delay`
- Quick-action pills: `px-3 py-1.5 rounded-full bg-white/5 border border-white/10 text-xs font-mono`

---

## Reusable Component Cheatsheet

### Badge / Status Pill
```tsx
<span className="px-3 py-1 rounded-full bg-primary/10 border border-primary/20
                 text-primary text-[10px] font-bold uppercase tracking-widest">
  auto_ok
</span>
```

### Glass Card
```tsx
<div className="rounded-2xl p-6 border border-white/[0.08]
                bg-white/[0.03] backdrop-blur-sm">
  {children}
</div>
```

### Metric Label + Value
```tsx
<p className="text-[10px] font-mono uppercase tracking-widest text-slate-500">Net Worth</p>
<p className="text-3xl font-mono font-bold text-on-surface">$284,420</p>
```

### Table Header Row
```tsx
<th className="py-4 px-6 text-left text-[10px] font-mono font-bold
               uppercase tracking-widest text-slate-500">
  Symbol
</th>
```

### Primary CTA Button
```tsx
<button className="px-6 py-2.5 rounded-full
                   bg-gradient-to-r from-primary to-primary-container
                   text-on-primary text-[10px] font-bold uppercase tracking-widest
                   shadow-[0_0_15px_rgba(16,185,129,0.3)]
                   hover:scale-105 transition-transform">
  Run Allocation
</button>
```

### Progress Bar
```tsx
<div className="h-1.5 w-full rounded-full bg-white/5">
  <div className="h-full rounded-full bg-primary shadow-[0_0_8px_rgba(78,222,163,0.4)]"
       style={{ width: '72%' }} />
</div>
```

---

## Tailwind Config Extensions

```js
// tailwind.config.ts additions
{
  colors: {
    primary:             '#4edea3',
    'primary-container': '#10b981',
    secondary:           '#d0bcff',
    'secondary-container': '#571bc1',
    tertiary:            '#ffb95f',
    'tertiary-container': '#e29100',
    'on-primary':        '#003824',
    background:          '#050508',
    surface:             '#121315',
    'surface-container': '#1f2021',
    'on-surface':        '#e3e2e3',
    'on-surface-variant': '#bbcabf',
    outline:             '#86948a',
    'outline-variant':   '#3c4a42',
  },
  fontFamily: {
    geist: ['Geist Sans', 'sans-serif'],
    body:  ['Inter', 'sans-serif'],
    mono:  ['JetBrains Mono', 'monospace'],
  },
  boxShadow: {
    'glow-emerald': '0 0 20px rgba(16, 185, 129, 0.15)',
    'glow-violet':  '0 0 20px rgba(139, 92, 246, 0.15)',
    'glow-amber':   '0 0 20px rgba(245, 158, 11, 0.15)',
    'glow-rose':    '0 0 20px rgba(244, 63, 94, 0.15)',
  },
}
```

---

## Additional Screens (Stitch project, hidden/draft)

The following screen IDs exist in the project but were hidden at export time. They may contain earlier iterations or component explorations:

`088c9d78`, `2385749e`, `39f43d0e`, `60b636a9`, `67c14e8a`, `68158490`,
`6fb4ffa0`, `75a745c1`, `761e922e`, `7764b940`, `80dc2c33`, `83f8220d`,
`8e464085`, `aad423d5`, `b1d1bd7e`, `e50433e4`, `e891cd80`
