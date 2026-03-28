"""
Rebuilds ALL portfolio snapshots from scratch:
  1. Deletes every existing snapshot for the user
  2. Regenerates 90 calendar days using current holdings × historical prices
  3. Forward-fills prices across weekends/holidays
  4. Skips days where < 80% of portfolio value has valid prices

Run from backend/ directory:
    python scripts/rebuild_snapshots.py
"""
import os
import sys
import math
from datetime import date, timedelta

from dotenv import load_dotenv
import yfinance as yf
import pandas as pd
import requests

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
DEFAULT_USER_ID = os.getenv("DEFAULT_USER_ID", "df6f002d-c8c0-4d03-9298-1e58e8025a35")

HISTORY_DAYS = 90
MIN_COVERAGE = 0.80

if not SUPABASE_URL or not SUPABASE_KEY:
    print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in .env")
    sys.exit(1)

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal",
}

YF_MAP = {
    "BTC":   "BTC-USD",
    "ETH":   "ETH-USD",
    "SOL":   "SOL-USD",
    "LINK":  "LINK-USD",
    "PETR4": "PETR4.SA",
    "VALE3": "VALE3.SA",
    "ITUB4": "ITUB4.SA",
}


def delete_all_snapshots():
    print(f"Deleting all snapshots for user {DEFAULT_USER_ID}...")
    r = requests.delete(
        f"{SUPABASE_URL}/rest/v1/portfolio_snapshots?user_id=eq.{DEFAULT_USER_ID}",
        headers={**headers, "Prefer": "return=representation"},
    )
    if r.status_code in (200, 204):
        try:
            deleted = r.json()
            print(f"  Deleted {len(deleted)} snapshots")
        except Exception:
            print(f"  Deleted (HTTP {r.status_code})")
    else:
        print(f"  ERROR deleting: HTTP {r.status_code} — {r.text[:300]}")
        sys.exit(1)


def get_holdings():
    r = requests.get(
        f"{SUPABASE_URL}/rest/v1/holdings?select=*,assets(symbol,asset_class,currency)",
        headers=headers,
    )
    r.raise_for_status()
    return r.json()


def get_usd_brl_history(start: str, end: str) -> dict:
    ticker = yf.Ticker("BRL=X")
    hist = ticker.history(start=start, end=end)
    return {str(d.date()): float(r["Close"]) for d, r in hist.iterrows()}


def rebuild():
    # ── Step 1: delete ──────────────────────────────────────────────────────
    delete_all_snapshots()

    # ── Step 2: load holdings ───────────────────────────────────────────────
    holdings = get_holdings()
    if not holdings:
        print("No holdings found — aborting")
        return

    symbol_qty: dict[str, float] = {}
    asset_class_map: dict[str, str] = {}
    brl_symbols: set[str] = set()

    for h in holdings:
        asset = h.get("assets") or {}
        symbol = asset.get("symbol")
        asset_class = asset.get("asset_class", "")
        currency = asset.get("currency", "USD")
        qty = float(h.get("quantity", 0))
        if not symbol or qty <= 0:
            continue
        symbol_qty[symbol] = symbol_qty.get(symbol, 0.0) + qty
        asset_class_map[symbol] = asset_class.lower().replace(" ", "_")
        if currency == "BRL" or "brazil" in asset_class.lower():
            brl_symbols.add(symbol)

    if not symbol_qty:
        print("No valid holdings (qty > 0) — aborting")
        return

    print(f"\nHoldings: {len(symbol_qty)} symbols — {', '.join(sorted(symbol_qty))}")
    print(f"BRL-denominated: {sorted(brl_symbols)}")

    # ── Step 3: download prices ─────────────────────────────────────────────
    all_symbols = list(symbol_qty.keys())
    sym_to_yf = {s: YF_MAP.get(s, s) for s in all_symbols}
    all_yf = list(sym_to_yf.values())

    end_date = date.today()
    start_date = end_date - timedelta(days=HISTORY_DAYS + 35)  # extra buffer
    start_str = str(start_date)
    end_str = str(end_date)

    print(f"\nDownloading prices {start_str} to {end_str} for {len(all_yf)} symbols...")

    if len(all_yf) == 1:
        raw = yf.download(all_yf[0], start=start_str, end=end_str,
                          auto_adjust=True, progress=False)
        prices_raw = raw[["Close"]].rename(columns={"Close": all_yf[0]})
    else:
        raw = yf.download(all_yf, start=start_str, end=end_str,
                          auto_adjust=True, progress=False)
        if isinstance(raw.columns, pd.MultiIndex):
            prices_raw = raw["Close"]
        else:
            prices_raw = raw[["Close"]].rename(columns={"Close": all_yf[0]})

    prices = prices_raw.ffill()
    print(f"  Price data: {len(prices)} rows, {len(prices.columns)} symbols")
    print(f"  Columns: {list(prices.columns)}")

    # ── Step 4: USD/BRL history ─────────────────────────────────────────────
    print("\nDownloading USD/BRL history...")
    usd_brl_hist = get_usd_brl_history(start_str, end_str)
    fallback_rate = 5.75
    print(f"  Got {len(usd_brl_hist)} BRL rate days")

    def get_rate(day_str: str) -> float:
        if day_str in usd_brl_hist:
            return usd_brl_hist[day_str]
        # forward-fill up to 5 days
        d = date.fromisoformat(day_str)
        for offset in range(1, 6):
            prev = str(d - timedelta(days=offset))
            if prev in usd_brl_hist:
                return usd_brl_hist[prev]
        return fallback_rate

    # ── Step 5: generate snapshots ──────────────────────────────────────────
    cutoff = end_date - timedelta(days=HISTORY_DAYS)
    trading_days = [d for d in prices.index.tolist() if d.date() >= cutoff]
    print(f"\nTrading days in last {HISTORY_DAYS} calendar days: {len(trading_days)}")

    snapshots = []
    skipped_coverage = 0
    skipped_value = 0
    total_symbols = len(symbol_qty)

    for day in trading_days:
        day_str = str(day.date())

        # Coverage check
        valid_count = sum(
            1 for s in symbol_qty
            if sym_to_yf[s] in prices.columns
            and not pd.isna(prices.loc[day, sym_to_yf[s]])
            and float(prices.loc[day, sym_to_yf[s]]) > 0
        )
        coverage = valid_count / total_symbols if total_symbols > 0 else 0
        if coverage < MIN_COVERAGE:
            skipped_coverage += 1
            continue

        # Compute portfolio value
        rate = get_rate(day_str)
        total_usd = 0.0
        sleeve_values: dict[str, float] = {}

        for symbol, qty in symbol_qty.items():
            yf_sym = sym_to_yf[symbol]
            if yf_sym not in prices.columns:
                continue
            price = prices.loc[day, yf_sym]
            if pd.isna(price) or float(price) <= 0:
                continue
            price = float(price)
            value_usd = (price * qty) / rate if symbol in brl_symbols else price * qty
            total_usd += value_usd
            ac = asset_class_map.get(symbol, "other")
            sleeve_values[ac] = sleeve_values.get(ac, 0.0) + value_usd

        if total_usd < 1000:
            skipped_value += 1
            continue

        sleeve_weights = {k: round(v / total_usd, 6) for k, v in sleeve_values.items()}

        snapshots.append({
            "user_id": DEFAULT_USER_ID,
            "snapshot_date": day_str,
            "total_value_usd": round(total_usd, 2),
            "total_value_brl": round(total_usd * rate, 2),
            "usd_brl_rate": round(rate, 4),
            "sleeve_weights": sleeve_weights,
        })

    # ── Step 6: sanity check ────────────────────────────────────────────────
    print(f"\nSnapshot generation summary:")
    print(f"  Generated:             {len(snapshots)}")
    print(f"  Skipped (coverage):    {skipped_coverage}")
    print(f"  Skipped (value<$1000): {skipped_value}")

    if len(snapshots) >= 2:
        values = [s["total_value_usd"] for s in snapshots]
        vmin, vmax = min(values), max(values)
        ratio = vmax / vmin if vmin > 0 else 999
        print(f"  Value range: ${vmin:,.0f} - ${vmax:,.0f}  (max/min ratio: {ratio:.2f}x)")

        returns = [(values[i] - values[i-1]) / values[i-1] for i in range(1, len(values))]
        avg_abs = sum(abs(r) for r in returns) / len(returns) if returns else 0
        print(f"  Avg daily move: {avg_abs*100:.2f}%  (healthy = 0.3-1.5%)")

        if ratio > 1.5:
            print(f"\n  WARNING: max/min ratio {ratio:.2f}x exceeds 1.5x threshold")
            print("     Possible causes: yfinance data gap, wrong symbol mapping, BRL rate spike")
            ans = input("  Proceed anyway? [y/N] ").strip().lower()
            if ans != "y":
                print("Aborted.")
                return

    if not snapshots:
        print("\nNothing to insert — check holdings and price downloads above.")
        return

    # ── Step 7: upsert ──────────────────────────────────────────────────────
    inserted = 0
    for i in range(0, len(snapshots), 50):
        batch = snapshots[i : i + 50]
        r = requests.post(
            f"{SUPABASE_URL}/rest/v1/portfolio_snapshots",
            headers={**headers, "Prefer": "resolution=merge-duplicates,return=minimal"},
            json=batch,
        )
        if r.status_code in (200, 201):
            inserted += len(batch)
            print(f"  Inserted batch {i//50 + 1}: {len(batch)} rows  OK")
        else:
            print(f"  ERROR batch {i//50 + 1}: HTTP {r.status_code} — {r.text[:300]}")

    first = snapshots[0]["snapshot_date"]
    last = snapshots[-1]["snapshot_date"]
    print(f"\nDone — {inserted}/{len(snapshots)} snapshots written")
    print(f"Date range: {first} to {last}")
    print(f"\nNext: force-create today's live snapshot:")
    print(f"  curl -X POST 'https://investapi.ovelha.us/performance/snapshot?force=true'")


if __name__ == "__main__":
    rebuild()
