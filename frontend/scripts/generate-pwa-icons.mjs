/**
 * Generate PWA icon PNGs from the SVG template.
 * Run from the frontend/ directory:
 *   node scripts/generate-pwa-icons.mjs
 *
 * Requires: npm install canvas
 *   OR use sharp: npm install sharp
 */
import { createCanvas } from 'canvas';
import { writeFileSync, mkdirSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const iconsDir = resolve(__dirname, '../public/icons');
mkdirSync(iconsDir, { recursive: true });

const sizes = [192, 512];

for (const size of sizes) {
  const canvas = createCanvas(size, size);
  const ctx = canvas.getContext('2d');

  // Background rounded rect
  const radius = size * 0.15;
  ctx.fillStyle = '#050508';
  ctx.beginPath();
  ctx.moveTo(radius, 0);
  ctx.lineTo(size - radius, 0);
  ctx.quadraticCurveTo(size, 0, size, radius);
  ctx.lineTo(size, size - radius);
  ctx.quadraticCurveTo(size, size, size - radius, size);
  ctx.lineTo(radius, size);
  ctx.quadraticCurveTo(0, size, 0, size - radius);
  ctx.lineTo(0, radius);
  ctx.quadraticCurveTo(0, 0, radius, 0);
  ctx.closePath();
  ctx.fill();

  // Green accent bar at bottom
  ctx.fillStyle = '#22c55e';
  ctx.globalAlpha = 0.85;
  ctx.fillRect(0, size * 0.86, size, size * 0.14);
  ctx.globalAlpha = 1.0;

  // "OI" text
  ctx.fillStyle = '#f8fafc';
  ctx.font = `bold ${size * 0.42}px system-ui, sans-serif`;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText('OI', size / 2, size * 0.46);

  const outPath = `${iconsDir}/icon-${size}.png`;
  writeFileSync(outPath, canvas.toBuffer('image/png'));
  console.log(`Generated ${outPath}`);
}

// Also generate maskable (same design, no rounded corners for bleed safety)
const maskSize = 512;
const canvas = createCanvas(maskSize, maskSize);
const ctx = canvas.getContext('2d');
ctx.fillStyle = '#050508';
ctx.fillRect(0, 0, maskSize, maskSize);
ctx.fillStyle = '#22c55e';
ctx.globalAlpha = 0.85;
ctx.fillRect(0, maskSize * 0.86, maskSize, maskSize * 0.14);
ctx.globalAlpha = 1.0;
ctx.fillStyle = '#f8fafc';
ctx.font = `bold ${maskSize * 0.42}px system-ui, sans-serif`;
ctx.textAlign = 'center';
ctx.textBaseline = 'middle';
ctx.fillText('OI', maskSize / 2, maskSize * 0.46);
writeFileSync(`${iconsDir}/icon-512-maskable.png`, canvas.toBuffer('image/png'));
console.log(`Generated icon-512-maskable.png`);
