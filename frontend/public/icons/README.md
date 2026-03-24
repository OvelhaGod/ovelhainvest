# PWA Icons

The PNG icons (192, 512, 512-maskable) must be generated from `icon.svg`.

## Generate icons

From the `frontend/` directory:

```bash
npm install canvas          # or: pnpm add canvas
node scripts/generate-pwa-icons.mjs
```

This produces:
- `icon-192.png`
- `icon-512.png`
- `icon-512-maskable.png`

## Placeholder icons

Placeholder 1×1 PNG files are committed so the manifest doesn't 404 in development.
Run the generate script before deploying to production.
