# OvelhaInvest — Google Stitch Design Prompts
> Go to stitch.withgoogle.com and run each prompt below to generate the 8 page designs.
> Export DESIGN.md from Stitch, replace the placeholder DESIGN.md in this repo root, then commit.

---

## Page 1 — Dashboard

```
Professional financial portfolio dashboard. Dark theme #0a0a0a background.
Bloomberg terminal aesthetic — data-dense, zero decoration.
Top row: 4 metric cards (Net Worth in USD, Today P&L with % change, YTD TWR vs benchmark delta, Max Drawdown).
Center: Asset allocation donut chart (6 slices: US Equity, Intl, Bonds, Brazil, Crypto, Cash) with target vs actual rings.
Right: 3 vault balance cards (Future Investments, Opportunity, Emergency) with progress bars.
Bottom: Regime status banner (Normal/High-Vol/Opportunity) + recent signals table (5 rows).
Font: Inter. Numbers: JetBrains Mono. Green for positive values, red for negative. shadcn/ui components.
```

---

## Page 2 — Signals

```
Financial signals and activity log page. Dark theme.
Full-width table: timestamp, event type badge, proposed trades summary, AI status badge (OK/Warning/Block), execution status.
Expandable row reveals: full trade list with amounts, AI investment framework check (5 green/amber/red indicators for Swensen/Dalio/Marks/Graham/Bogle), approval button if pending.
Filter bar: status dropdown, event type, date range picker.
Dense, professional, no whitespace waste. shadcn/ui Table component.
```

---

## Page 3 — Assets & Valuations

```
Investment asset screener and valuation table. Dark theme, Bloomberg style.
Sticky header with filter bar: asset class, region, tier, min margin of safety slider.
Sortable table columns: Symbol, Class, Price, Margin of Safety % (color-coded: green >20%, amber 10-20%, red <10%), Value Score, Momentum Score, Quality Score, Moat (wide/narrow/none badge), Fair Value, Buy Target, Rank.
Row click opens right drawer with: DCF assumptions accordion, score breakdown bar charts, linked news feed.
Compact row height, monospace numbers.
```

---

## Page 4 — Performance

```
Portfolio performance analytics page. Dark theme. Institutional-grade.
Top tabs: Summary | Attribution | Rolling | Risk.
Summary tab: return cards row (1mo/3mo/6mo/YTD/1yr/All) showing TWR vs benchmark delta. Below: Sharpe/Sortino/Calmar ratio cards with interpretation badge.
Attribution tab: stacked horizontal bar chart by sleeve (allocation effect + selection effect). Table: top 5 contributors, bottom 5 detractors.
Risk tab: Beta, R2, Max Drawdown timeline chart, VaR gauge.
Color: green for outperformance, red for underperformance.
```

---

## Page 5 — Projections

```
Portfolio projection and scenario analysis page. Dark theme.
4 horizontal tabs: Monte Carlo | Contribution Sim | Stress Test | Retirement.
Monte Carlo tab: input row (monthly contribution, years, model selector). Below: fan chart with 5 shaded percentile bands (5th/25th/50th/75th/95th) from today to horizon. Key stats: median ending value, probability of reaching $X, 4% SWR survival %.
Stress test tab: scenario cards (2008 GFC, 2020 COVID, 2022 Rate Shock, Stagflation, Brazil Crisis) — select one to see waterfall chart of sleeve-level impact.
```

---

## Page 6 — Tax

```
Tax lot tracker and optimization page. Dark theme.
Top: Brazil DARF progress bar (monthly gross sales vs R$20,000 exemption, with projected month-end estimate).
Main: Tax lots table — Symbol, Account, Acquisition Date, Quantity, Cost Basis, Current Value, Unrealized Gain/Loss (green/red), Holding Period (ST/LT badge), Est. Tax if Sold.
Method selector: FIFO / HIFO / Spec ID toggle per account.
Loss harvesting panel: flagged lots with suggested harvest action and wash-sale warning.
```

---

## Page 7 — Journal

```
Investment decision journal page. Dark theme.
Top: Override accuracy scorecard — 2 big numbers: "When you followed the system: +X% avg 90d outcome" vs "When you overrode: +Y% avg 90d outcome".
Main table: Date, Action (Followed/Overrode/Deferred badge), Asset, System Recommendation summary, Your Reasoning (truncated), 30d Outcome, 90d Outcome.
Bottom: Pattern analysis card — AI-generated text block on behavioral tendencies.
```

---

## Page 8 — Config

```
Strategy configuration viewer. Dark theme. Technical, developer-facing.
Left: version history list (active version highlighted).
Right: JSON viewer with syntax highlighting showing active strategy_config. Allocation targets donut chart rendered from config values. Comparison toggle: "vs Swensen" / "vs All-Weather" overlaid on same donut.
Read-only in v1 with prominent "v2: editable" label.
```

---

## After Generating All 8 Designs

1. Export DESIGN.md from Stitch
2. Replace the placeholder `DESIGN.md` in this repo root
3. Commit: `git add DESIGN.md && git commit -m "docs(design): add Stitch DESIGN.md — design system contract"`
4. Push to both remotes
5. Return to Claude Code for Phase 2 using the Phase 2 prompt in CLAUDE_CODE_START.md
