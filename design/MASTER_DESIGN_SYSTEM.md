# OvelhaInvest — Master Design System
Source: Stitch project 11580419759191253062 (canonical)
Date: 2026-03-24

## Color Tokens

| Token | Hex | CSS Variable | Tailwind Class |
|-------|-----|--------------|----------------|
| primary | #4edea3 | --color-primary | text-primary, bg-primary |
| primary-container | #10b981 | --color-primary-container | text-primary-container |
| secondary | #d0bcff | --color-secondary | text-secondary |
| tertiary | #ffb95f | --color-tertiary | text-tertiary |
| error | #ffb4ab | --color-error | text-error |
| background (page) | #050508 | --color-background | bg-[#050508] |
| surface | #121315 | --color-surface | bg-surface |
| surface-container | #1f2021 | --color-surface-container | bg-surface-container |
| surface-container-high | #292a2b | --color-surface-container-high | bg-surface-container-high |
| on-surface | #e3e2e3 | --color-on-surface | text-on-surface |
| on-surface-variant | #bbcabf | --color-on-surface-variant | text-on-surface-variant |
| outline | #86948a | --color-outline | text-outline |
| outline-variant | #3c4a42 | --color-outline-variant | border-outline-variant |

## Typography

- Numbers/tickers: `font-mono` (JetBrains Mono)
- Page titles: `text-3xl font-bold tracking-tight uppercase font-mono`
- Section labels: `text-[10px] font-mono uppercase tracking-widest text-outline`
- Body text: Inter 400-500
- All monetary values: font-mono, sign prefix (+ or –)

## Glassmorphism Pattern

```css
.glass-card {
  background: rgba(31, 32, 33, 0.6);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 1rem;
}
```

## Spacing

- Page padding: `p-8` (2rem) or `p-10` (2.5rem)
- Card padding: `p-6` (1.5rem)
- Between sections: `space-y-8`
- Grid gap: `gap-6`

## Components

See `components/ui/oi/` for all shared OI components.
