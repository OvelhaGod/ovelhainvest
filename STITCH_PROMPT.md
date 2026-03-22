# OvelhaInvest — Stitch Design Prompts
> Use at https://stitch.withgoogle.com
> Create ONE new Stitch project. Paste the GLOBAL STYLE BLOCK as the project
> description first, then generate each screen inside the same project.
> After all 8 screens: export DESIGN.md, commit to repo root, then start Phase 2.

---

## STEP 1 — PROJECT DESCRIPTION (paste when creating new Stitch project)

OvelhaInvest — premium AI-powered personal wealth management app. 2026 glassmorphism aesthetic.

Visual DNA: Inspired by Linear.app, Vercel dashboard, and Raycast. NOT corporate fintech. NOT boxy.
Dark mode only. Background #050508 deep space with faint radial glow behind hero elements.
Cards: frosted glass — semi-transparent, backdrop-blur, 1px border at 8% white opacity, rounded-2xl.
Typography: Geist Sans headings, Inter body copy, JetBrains Mono for ALL numbers/tickers/prices.
Colors: emerald #10b981 = positive/gains, rose #f43f5e = negative/losses, amber #f59e0b = warning, violet #8b5cf6 = AI features.
Charts: glowing colored line strokes with translucent gradient area fills beneath. No flat bars for financial data.
Badges: pill-shaped with soft colored fill at 12% opacity and border glow. Never rectangular chips.
Sidebar: fixed left 240px, glassmorphic blurred background, active item has emerald left-border glow.
Buttons: primary = emerald gradient with glow shadow. No flat, no squared.
No pure black or pure white. Everything lives in the dark glass world.

---

## SCREEN 1 — Dashboard

OvelhaInvest Dashboard. Use the project design system.

Fixed sidebar (240px): 🐑 OvelhaInvest logo top. Nav: Dashboard (active — emerald left-border glow), Signals, Assets, Performance, Projections, Tax, Journal, Config. User avatar + name at bottom.

Main content:
Page header: "Dashboard" large Geist Sans + "Sunday, March 22 · Normal Market Regime" muted subtitle.

TOP ROW — 4 equal glass metric cards:
Card 1 "Net Worth": "$284,420" 36px JetBrains Mono white. "↑ $1,240 today +0.44%" emerald below. "R$ 1.42M" muted. Faint emerald glow bottom border.
Card 2 "Today P&L": "+$1,240" large emerald JetBrains Mono. "+0.44%" emerald pill badge. 7-day sparkline in emerald below (glowing stroke, no axes).
Card 3 "YTD Return": "+18.4%" large emerald. "vs benchmark +14.2%" muted below. "+4.2% alpha" emerald pill.
Card 4 "Max Drawdown": "-8.3%" large amber JetBrains Mono. "From peak · Mar 2024" muted. Amber glow border.

MIDDLE ROW — 60/40 split:
Left (60%) "Asset Allocation" glass card: Donut chart with 6 glowing arc segments: US Equity emerald, Intl cyan, Bonds blue, Brazil green, Crypto violet, Cash slate. Center: "45% US Equity" with emerald dot. Outer ghost ring = target allocations. Color legend pills below.
Right (40%) 3 vault cards stacked: "Future Investments" $8,400 emerald progress bar 68%. "Opportunity" $2,800 amber bar 22% with 🔒 icon. "Emergency" $15,000 slate bar 100% locked.

BOTTOM ROW — 50/50:
Left "Recent Signals" glass card: mini-table 3 rows — timestamp, type badge, summary, status. "View all →" emerald link.
Right "Quick Stats" glass card: 4 metrics — Sharpe 1.42, Sortino 1.89, Calmar 0.87, Beta 0.73. JetBrains Mono numbers, color-coded.

---

## SCREEN 2 — Signals & Activity

OvelhaInvest Signals page. Use the project design system.

Header "Signals & Activity". Filter bar glass card: Status dropdown, Event Type dropdown, Date range picker — all glass selects with chevrons.

Main glass card — table:
Headers (muted small-caps): Timestamp | Event Type | Proposed Trades | AI Status | Execution | Actions

Row 1 EXPANDED (subtle emerald bg tint):
- "Today 09:14" JetBrains Mono | "DAILY CHECK" emerald pill | "Buy VTI $600 · Buy BTC $300" | "✓ OK" emerald badge | "Needs Approval" amber badge | "Approve" emerald gradient button + "Reject" ghost button
Expanded detail panel (inset glass): 5 framework pills [Swensen ✓] [Dalio ✓] [Marks ⚠] [Graham ✓] [Bogle ✓] in emerald/amber. Trade details below. AI summary sub-card with violet left glow. Action buttons row.

Row 2: Yesterday | DAILY CHECK | Buy VXUS $400 | ✓ OK | "Executed" slate | "View →"
Row 3: Mar 18 | "OPPORTUNITY" violet pill | Buy BTC $1,500 Tier-1 | ✓ OK | "Approved" emerald | "View →"

---

## SCREEN 3 — Assets & Valuations

OvelhaInvest Assets page. Use the project design system.

Header "Assets & Valuations". Filter bar: asset class pill toggles (All/Equity/Bonds/Crypto/Brazil), MoS slider at 15%, Moat dropdown, Tier dropdown.

Sortable table in large glass card:
Headers: Symbol | Class | Price | MoS% | Value | Momentum | Quality | Moat | Fair Value | Buy Target | Rank

NVDA row: "NVDA" white bold + violet "Stock" pill | $124.80 | "+28%" emerald pill with glow | 3 mini progress bars (0.58 amber / 0.89 emerald / 0.76 emerald) | "Narrow" amber pill | $173 | $147 emerald | #1 large emerald bold
VTI row: blue "ETF" pill | $218.40 | "+12%" amber pill | bars (0.62/0.71/0.83) | "—" | $247 | $197 | #3
BTC row: amber "Crypto" pill | $82,400 | "+31%" emerald pill | bars (0.71/0.83/N/A) | "—" | $115k | $92k | #2
PLTR row: violet "Stock" pill | $24.10 | "-8%" ROSE pill (overvalued) | bars (0.31/0.77/0.54) | "Narrow" | $22 | $18 | #8

Right side drawer OPEN for NVDA (380px glass panel):
"NVDA Detail" header + X close. Fair value semicircle gauge pointing "Undervalued" in emerald. "+28% Margin of Safety" large emerald badge. Factor score bars labeled (Value/Momentum/Quality). DCF collapsible. News feed 3 rows.

---

## SCREEN 4 — Performance Analytics

OvelhaInvest Performance page. Use the project design system.

Glass pill tabs: [Summary active] [Attribution] [Rolling] [Risk] — active has emerald underline glow.

SUMMARY TAB:
Period cards row (6 equal glass cards): 1mo +2.1% / 3mo +8.4% / 6mo +12.1% / YTD +18.4% (emerald glow highlighted) / 1yr +22.3% / All +67.4%. Each: big JetBrains Mono % + benchmark delta below.

Risk ratios row (3 large glass cards):
Sharpe 1.42 large emerald + "Good" emerald pill + "Risk-adjusted return" muted.
Sortino 1.89 large emerald + "Excellent" emerald glow pill.
Calmar 0.87 large amber + "Fair" amber pill.

Portfolio vs Benchmark chart (full width glass card):
Dark canvas. Portfolio: 2px emerald stroke with emerald gradient area fill below. Benchmark: 1.5px dashed slate stroke. 12-month X-axis. Hover: glass tooltip card.

---

## SCREEN 5 — Projections

OvelhaInvest Projections page. Use the project design system.

Glass pill tabs: [Monte Carlo active] [Contribution Sim] [Stress Test] [Retirement]

Input glass card (single row): Monthly Contribution $2,000 input | Years slider at 20 | Model dropdown "Current" | "Run Simulation" emerald gradient button with glow.

Monte Carlo fan chart (large glass card — dominant element):
Dark canvas. Starting from $284k today, 5 fan bands over 20 years:
- 5th percentile: thin, rose-tinted translucent fill, nearly flat line
- 25th: wider, amber-tinted
- 50th MEDIAN: bright emerald 2.5px stroke, emerald fill, ends labeled "$892,000"
- 75th: wider emerald lighter
- 95th: widest, light emerald translucent ~$2.1M
Subtle dashed $1M milestone line. Muted Y-axis: $0/$500k/$1M/$1.5M/$2M. Years 0-20 X-axis.

Stats row (3 glass cards): "Median Year 20" $892k emerald | "Reach $1M" 61% amber | "4% Survival" 94% emerald + "Safe" badge.

---

## SCREEN 6 — Tax Optimization

OvelhaInvest Tax page. Use the project design system.

Brazil DARF glass card: "🇧🇷 Brazil Monthly Exemption" header. Amber progress bar 34% — "R$6,800 of R$20,000". Right: "Projected: R$11,200 — Safe ✓" emerald. "9 days remaining" muted. 80% alert threshold marker on bar.

Method toggle: "FIFO | HIFO ✓ | Spec ID" — HIFO active with emerald glow border.

Tax lots table glass card: Symbol | Account | Acquired | Qty | Cost Basis | Current Value | G/L | Period | Est. Tax
NVDA: M1 Taxable / Jun 2022 / 50sh / $4,200 / $6,240 / +$2,040 emerald / "Long-Term" green / $306
BTC: Binance / Jan 2023 / 0.12 / $3,600 / $9,888 / +$6,288 emerald / "Long-Term" green / $943
PLTR: M1 Taxable / Nov 2024 / 100sh / $2,100 / $2,410 / +$310 emerald / "Short-Term" AMBER / $99
VTI: M1 Roth / various / 120sh / $18,400 / $26,208 / +$7,808 / "Tax-Free" slate pill / $0

Harvest panel (amber left glow glass card): "⚡ 2 Harvest Opportunities". BNDX -$420 row + PETR4 R$890 row, each with Review button.

---

## SCREEN 7 — Decision Journal

OvelhaInvest Journal page. Use the project design system.

Override Accuracy (2 large glass cards side by side):
Left (emerald glow): "When You Followed the System" — "+12.4%" 52px JetBrains Mono emerald. "Avg 90-day outcome". "47 decisions" muted. Large faint emerald checkmark background icon.
Right (amber glow): "When You Overrode" — "+7.1%" 52px amber. "12 overrides". "System outperformed by 5.3%" rose small text + warning icon.

Journal table glass card: Date | Action | Asset | System Rec | Reasoning | 30d | 90d
Mar 15: "Followed" emerald pill / BTC / Buy $300 Tier-1 / Agreed with drawdown / +8.2% emerald / +22.1% emerald large
Mar 10: "Overrode" rose pill / NVDA / Hold signal / Felt strong momentum / +4.1% amber / +11.2% amber
Feb 28: "Deferred" amber pill / VTI / Buy $600 DCA / Waited for entry / -1.2% rose / +3.8% emerald

AI Insights glass card (violet left glow): "✦ AI Behavioral Insights" violet heading. 2-line analysis text. "Updated weekly" muted bottom-right.

---

## SCREEN 8 — Config

OvelhaInvest Config page. Use the project design system.

Two columns (35/65):

LEFT — Version History glass card: "Config Versions" small-caps. v1.0.0 row active (emerald left glow, white bold, "Active" emerald pill). v0.9.1 muted. v0.9.0 muted. "+ Create New Version" dashed ghost button.

RIGHT — Two stacked glass cards:
Top: Allocation donut (6 glowing segments, same as dashboard, smaller). Toggle pills: [Current ✓] [Swensen] [All-Weather] — Swensen shows ghost overlay ring for comparison.
Bottom: JSON viewer — dark code area, syntax highlighted (violet keys, emerald strings/values, amber booleans). "v1.0.0 · Read Only" slate badge top-right. Scrollable 12 lines. Monospace font.

---

## AFTER ALL 8 SCREENS

1. Review — any screen that looks boxy or unstyled: regenerate it with "Apply the glassmorphism design system to this screen. Use Geist Sans, JetBrains Mono for numbers, frosted glass cards, dark #050508 background."
2. Export DESIGN.md from Stitch
3. Commit: git add DESIGN.md && git commit -m "docs(design): Stitch glassmorphism v1" && git push origin dev
4. Return to Claude Code and paste the Phase 2 prompt
