"use client";

/**
 * Asset logo utilities using TradingView's public symbol logo CDN.
 * Falls back to a colored initial circle when the image fails to load.
 */

import { useState } from "react";

// Explicit logo map for known edge cases
const LOGO_MAP: Record<string, string> = {
  BTC:   "https://s3-symbol-logo.tradingview.com/crypto/XTVCBTC--big.svg",
  ETH:   "https://s3-symbol-logo.tradingview.com/crypto/XTVCETH--big.svg",
  SOL:   "https://s3-symbol-logo.tradingview.com/crypto/XTVCSOL--big.svg",
  LINK:  "https://s3-symbol-logo.tradingview.com/crypto/XTVCLINK--big.svg",
  PETR4: "https://s3-symbol-logo.tradingview.com/petrobras--big.svg",
  VALE3: "https://s3-symbol-logo.tradingview.com/vale--big.svg",
  ITUB4: "https://s3-symbol-logo.tradingview.com/itau-unibanco--big.svg",
  VTI:   "https://s3-symbol-logo.tradingview.com/vanguard--big.svg",
  VXUS:  "https://s3-symbol-logo.tradingview.com/vanguard--big.svg",
  BND:   "https://s3-symbol-logo.tradingview.com/vanguard--big.svg",
  BNDX:  "https://s3-symbol-logo.tradingview.com/vanguard--big.svg",
  VNQ:   "https://s3-symbol-logo.tradingview.com/vanguard--big.svg",
  VOO:   "https://s3-symbol-logo.tradingview.com/vanguard--big.svg",
  SPY:   "https://s3-symbol-logo.tradingview.com/state-street--big.svg",
  GLD:   "https://s3-symbol-logo.tradingview.com/state-street--big.svg",
  QQQ:   "https://s3-symbol-logo.tradingview.com/invesco--big.svg",
  TIP:   "https://s3-symbol-logo.tradingview.com/ishares--big.svg",
  AGG:   "https://s3-symbol-logo.tradingview.com/ishares--big.svg",
  ACWI:  "https://s3-symbol-logo.tradingview.com/ishares--big.svg",
  IWM:   "https://s3-symbol-logo.tradingview.com/ishares--big.svg",
  TLT:   "https://s3-symbol-logo.tradingview.com/ishares--big.svg",
  GOOG:  "https://s3-symbol-logo.tradingview.com/alphabet--big.svg",
  MSFT:  "https://s3-symbol-logo.tradingview.com/microsoft--big.svg",
  NVDA:  "https://s3-symbol-logo.tradingview.com/nvidia--big.svg",
  AAPL:  "https://s3-symbol-logo.tradingview.com/apple--big.svg",
  AMZN:  "https://s3-symbol-logo.tradingview.com/amazon--big.svg",
  META:  "https://s3-symbol-logo.tradingview.com/meta-platforms--big.svg",
  CRM:   "https://s3-symbol-logo.tradingview.com/salesforce--big.svg",
  PLTR:  "https://s3-symbol-logo.tradingview.com/palantir-technologies--big.svg",
  ARM:   "https://s3-symbol-logo.tradingview.com/arm-holdings--big.svg",
};

// Deterministic color for fallback circle based on symbol
function symbolColor(symbol: string): string {
  const colors = [
    "#6366f1", "#8b5cf6", "#06b6d4", "#10b981",
    "#f59e0b", "#f43f5e", "#3b82f6", "#84cc16",
  ];
  let hash = 0;
  for (const ch of symbol) hash = (hash * 31 + ch.charCodeAt(0)) & 0xffff;
  return colors[hash % colors.length];
}

export function getAssetLogo(symbol: string): string {
  return LOGO_MAP[symbol] ?? `https://s3-symbol-logo.tradingview.com/${symbol.toLowerCase()}--big.svg`;
}

/**
 * Asset logo image with automatic fallback to colored initial circle.
 * Usage: <AssetLogo symbol="NVDA" size={32} />
 */
export function AssetLogo({ symbol, size = 32, className = "" }: {
  symbol: string;
  size?: number;
  className?: string;
}) {
  const [failed, setFailed] = useState(false);
  const bg = symbolColor(symbol);

  if (failed) {
    return (
      <div
        className={`rounded-full flex items-center justify-center shrink-0 font-mono font-bold ${className}`}
        style={{ width: size, height: size, background: bg, fontSize: size * 0.4 }}
      >
        <span className="text-white select-none">{symbol.charAt(0)}</span>
      </div>
    );
  }

  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={getAssetLogo(symbol)}
      alt={symbol}
      width={size}
      height={size}
      loading="lazy"
      className={`rounded-full object-contain shrink-0 ${className}`}
      style={{ width: size, height: size, background: "rgba(255,255,255,0.05)" }}
      onError={() => setFailed(true)}
    />
  );
}
