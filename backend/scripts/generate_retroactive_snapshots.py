"""
Generates retroactive portfolio snapshots using:
- Current holdings (quantities from holdings table)
- Historical prices from yfinance (forward-filled to eliminate gaps)
- USD/BRL rate history from yfinance (BRL=X)

Fixes vs v1:
- Prices are forward-filled so weekend/holiday gaps don't create phantom drops
- Day skipped if < 80% of portfolio value has valid (non-NaN) prices
- Capped at 90 days (enough for Sharpe/Sortino/Calmar; prevents distortion from
  distant history where holdings may not have existed at those prices)
"""
import os
import sys
from datetime import date, timedelta

from dotenv import load_dotenv
import yfinance as yf
import pandas as pd
import requests

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
DEFAULT_USER_ID = os.getenv("DEFAULT_USER_ID", "df6f002d-c8c0-4d03-9298-1e58e8025a35")

# How many calendar days back to generate (90 = ~63 trading days)
HISTORY_DAYS = 90
# Minimum fraction of symbols (weighted by quantity > 0) that must have valid prices
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


def get_holdings():
    r = requests.get(
        f"{SUPABASE_URL}/rest/v1/holdings?select=*,assets(symbol,asset_class)",
        headers=headers,
    )
    return r.json()


def get_usd_brl_history(start: str, end: str) -> dict:
    ticker = yf.Ticker("BRL=X")
    hist = ticker.history(start=start, end=end)
    return {str(d.date()): float(r["Close"]) for d, r in hist.iterrows()}


def generate_retroactive_snapshots():
    holdings = get_holdings()
    if not holdings:
        print("No holdings found")
        return

    # Map yfinance tickers
    yf_map = {
        "BTC":   "BTC-USD",
        "ETH":   "ETH-USD",
        "SOL":   "SOL-USD",
        "LINK":  "LINK-USD",
        "PETR4": "PETR4.SA",
        "VALE3": "VALE3.SA",
        "ITUB4": "ITUB4.SA",
    }

    # Group by currency
    brl_symbols = []
    symbol_qty: dict = {}
    asset_class_map: dict = {}

    for h in holdings:
        asset = h.get("assets") or {}
        symbol = asset.get("symbol")
        asset_class = asset.get("asset_class", "")
        qty = float(h.get("quantity", 0))
        if not symbol or qty <= 0:
            continue
        symbol_qty[symbol] = qty
        asset_class_map[symbol] = asset_class.lower().replace(" ", "_")
        if "brazil" in asset_class.lower():
            brl_symbols.append(symbol)

    if not symbol_qty:
        print("No valid holdings found")
        return

    total_symbols = len(symbol_qty)
    print(f"Holdings: {total_symbols} symbols — {', '.join(sorted(symbol_qty.keys()))}")

    # Resolve to yfinance symbols
    all_symbols = list(symbol_qty.keys())
    all_symbols_yf = [yf_map.get(s, s) for s in all_symbols]
    sym_to_yf = {s: yf_map.get(s, s) for s in all_symbols}

    # Download HISTORY_DAYS of price history with extra buffer
    end_date = date.today()
    start_date = end_date - timedelta(days=HISTORY_DAYS + 30)
    start_str = str(start_date)
    end_str = str(end_date)

    print(f"Downloading price history {start_str} to {end_str} for {len(all_symbols_yf)} symbols...")

    if len(all_symbols_yf) == 1:
        raw = yf.download(all_symbols_yf[0], start=start_str, end=end_str,
                          auto_adjust=True, progress=False)
        prices_raw = raw[["Close"]].rename(columns={"Close": all_symbols_yf[0]})
    else:
        raw = yf.download(all_symbols_yf, start=start_str, end=end_str,
                          auto_adjust=True, progress=False)
        if isinstance(raw.columns, pd.MultiIndex):
            prices_raw = raw["Close"]
        else:
            prices_raw = raw[["Close"]].rename(columns={"Close": all_symbols_yf[0]})

    # KEY FIX: Forward-fill to eliminate gaps from holidays/weekends/missing data
    # This means a missing day reuses the most recent valid price
    prices = prices_raw.ffill()
    print(f"  Got {len(prices)} trading days after ffill")

    # Get USD/BRL history + forward-fill
    print("Downloading USD/BRL history...")
    usd_brl = get_usd_brl_history(start_str, end_str)
    default_rate = 5.75  # current approximate rate

    # Check existing snapshots to avoid duplicates
    existing_r = requests.get(
        f"{SUPABASE_URL}/rest/v1/portfolio_snapshots"
        f"?user_id=eq.{DEFAULT_USER_ID}&select=snapshot_date",
        headers=headers,
    )
    existing_dates = {r["snapshot_date"] for r in existing_r.json()}
    print(f"Existing snapshots: {len(existing_dates)}")

    # Generate one snapshot per trading day
    cutoff = end_date - timedelta(days=HISTORY_DAYS)
    trading_days = [d for d in prices.index.tolist() if d.date() >= cutoff]
    print(f"Trading days in last {HISTORY_DAYS} calendar days: {len(trading_days)}")

    snapshots = []
    skipped_coverage = 0
    skipped_existing = 0
    skipped_value = 0

    for day in trading_days:
        day_str = str(day.date())
        if day_str in existing_dates:
            skipped_existing += 1
            continue

        # Coverage check: how many symbols have valid (non-NaN) prices?
        valid_count = 0
        for symbol in symbol_qty:
            yf_symbol = sym_to_yf[symbol]
            try:
                if yf_symbol in prices.columns:
                    price = prices.loc[day, yf_symbol]
                    if not pd.isna(price) and float(price) > 0:
                        valid_count += 1
            except Exception:
                pass

        coverage = valid_count / total_symbols if total_symbols > 0 else 0
        if coverage < MIN_COVERAGE:
            skipped_coverage += 1
            continue

        # Compute portfolio value
        total_usd = 0.0
        rate = usd_brl.get(day_str, default_rate)
        # Forward-fill BRL rate too: find the most recent available rate
        if day_str not in usd_brl:
            # Use the last known rate within 5 days
            for offset in range(1, 6):
                prev_day = str((day.date() - timedelta(days=offset)))
                if prev_day in usd_brl:
                    rate = usd_brl[prev_day]
                    break

        sleeve_values: dict = {}
        for symbol, qty in symbol_qty.items():
            yf_symbol = sym_to_yf[symbol]
            try:
                if yf_symbol in prices.columns:
                    price = prices.loc[day, yf_symbol]
                    if pd.isna(price) or float(price) <= 0:
                        continue
                    price = float(price)
                    value_usd = (price * qty) / rate if symbol in brl_symbols else price * qty
                    total_usd += value_usd
                    ac = asset_class_map.get(symbol, "other")
                    sleeve_values[ac] = sleeve_values.get(ac, 0.0) + value_usd
            except Exception:
                continue

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

    print(f"\nSnapshot generation summary:")
    print(f"  Generated: {len(snapshots)}")
    print(f"  Skipped (already exist): {skipped_existing}")
    print(f"  Skipped (coverage < {MIN_COVERAGE*100:.0f}%): {skipped_coverage}")
    print(f"  Skipped (value < $1000): {skipped_value}")

    if len(snapshots) >= 2:
        values = [s["total_value_usd"] for s in snapshots]
        print(f"  Value range: ${min(values):,.0f} — ${max(values):,.0f}")
        # Quick sanity check: daily return volatility
        import math
        returns = [(values[i] - values[i-1]) / values[i-1] for i in range(1, len(values))]
        if returns:
            avg_abs = sum(abs(r) for r in returns) / len(returns)
            print(f"  Avg daily move: {avg_abs*100:.2f}% (healthy = 0.3-1.5%)")
            if avg_abs > 0.03:
                print("  WARNING: avg daily move > 3% — data may still have quality issues")
                print("           Consider checking for outlier snapshots before proceeding")

    if not snapshots:
        print("\nNothing to insert.")
        return

    # Insert in batches of 50
    inserted = 0
    for i in range(0, len(snapshots), 50):
        batch = snapshots[i : i + 50]
        r = requests.post(
            f"{SUPABASE_URL}/rest/v1/portfolio_snapshots",
            headers={**headers, "Prefer": "return=minimal"},
            json=batch,
        )
        if r.status_code in (200, 201):
            inserted += len(batch)
            print(f"  Inserted batch {i//50 + 1}: {len(batch)} snapshots")
        else:
            print(f"  Error on batch {i//50 + 1}: HTTP {r.status_code} — {r.text[:300]}")

    if snapshots:
        first = snapshots[0]["snapshot_date"]
        last = snapshots[-1]["snapshot_date"]
        print(f"\nDone — {inserted}/{len(snapshots)} snapshots inserted")
        print(f"Date range: {first} to {last}")
        print("\nNext steps:")
        print("  curl -X POST https://investapi.ovelha.us/performance/snapshot")
        print("  Then check /performance page for Sharpe/drawdown numbers")


if __name__ == "__main__":
    generate_retroactive_snapshots()
