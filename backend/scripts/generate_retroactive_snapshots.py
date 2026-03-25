"""
Generates 365 days of retroactive portfolio snapshots using:
- Current holdings (quantities from holdings table)
- Historical prices from yfinance
- USD/BRL rate history from yfinance (BRL=X)

This gives the performance engine enough data to compute:
- Rolling Sharpe (needs 20+ days)
- Max drawdown (needs price history)
- Beta vs SPY (needs correlated daily returns)
- Monthly returns heatmap
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
        "BTC": "BTC-USD",
        "ETH": "ETH-USD",
        "SOL": "SOL-USD",
        "LINK": "LINK-USD",
        "PETR4": "PETR4.SA",
        "VALE3": "VALE3.SA",
        "ITUB4": "ITUB4.SA",
    }

    # Group by currency
    usd_symbols = []
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
        else:
            usd_symbols.append(symbol)

    if not symbol_qty:
        print("No valid holdings found")
        return

    # Resolve to yfinance symbols
    all_symbols = list(symbol_qty.keys())
    all_symbols_yf = [yf_map.get(s, s) for s in all_symbols]
    sym_to_yf = {s: yf_map.get(s, s) for s in all_symbols}

    # Download 365 days of price history
    end_date = date.today()
    start_date = end_date - timedelta(days=400)  # extra buffer for trading days
    start_str = str(start_date)
    end_str = str(end_date)

    print(f"Downloading price history {start_str} to {end_str} for {len(all_symbols_yf)} symbols...")

    if len(all_symbols_yf) == 1:
        raw = yf.download(all_symbols_yf[0], start=start_str, end=end_str,
                          auto_adjust=True, progress=False)
        prices = raw[["Close"]].rename(columns={"Close": all_symbols_yf[0]})
    else:
        raw = yf.download(all_symbols_yf, start=start_str, end=end_str,
                          auto_adjust=True, progress=False)
        if isinstance(raw.columns, pd.MultiIndex):
            prices = raw["Close"]
        else:
            prices = raw[["Close"]].rename(columns={"Close": all_symbols_yf[0]})

    print(f"  Got {len(prices)} trading days")

    # Get USD/BRL history
    print("Downloading USD/BRL history...")
    usd_brl = get_usd_brl_history(start_str, end_str)
    default_rate = 5.23

    # Check existing snapshots
    existing_r = requests.get(
        f"{SUPABASE_URL}/rest/v1/portfolio_snapshots"
        f"?user_id=eq.{DEFAULT_USER_ID}&select=snapshot_date",
        headers=headers,
    )
    existing_dates = {r["snapshot_date"] for r in existing_r.json()}
    print(f"Existing snapshots: {len(existing_dates)}")

    # Generate one snapshot per trading day
    snapshots = []
    trading_days = prices.index.tolist()

    # Limit to 365 days
    cutoff = end_date - timedelta(days=365)
    trading_days = [d for d in trading_days if d.date() >= cutoff]

    for day in trading_days:
        day_str = str(day.date())
        if day_str in existing_dates:
            continue

        total_usd = 0.0
        rate = usd_brl.get(day_str, default_rate)
        sleeve_values: dict = {}

        for symbol, qty in symbol_qty.items():
            yf_symbol = sym_to_yf[symbol]
            try:
                if yf_symbol in prices.columns:
                    price = prices.loc[day, yf_symbol]
                    if pd.isna(price):
                        continue
                    price = float(price)
                    if symbol in brl_symbols:
                        value_usd = (price * qty) / rate
                    else:
                        value_usd = price * qty
                    total_usd += value_usd
                    ac = asset_class_map.get(symbol, "other")
                    sleeve_values[ac] = sleeve_values.get(ac, 0.0) + value_usd
            except Exception:
                continue

        if total_usd < 1000:
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

    print(f"Generated {len(snapshots)} new snapshots to insert")

    if not snapshots:
        print("Nothing to insert — all dates already exist")
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
        print(f"\nDone — {inserted} retroactive snapshots inserted")
        print(f"Date range: {first} → {last}")
        print("\nNext steps:")
        print("  curl -X POST https://investapi.ovelha.us/performance/snapshot")
        print("  Then check /performance page for Sharpe/drawdown numbers")


if __name__ == "__main__":
    generate_retroactive_snapshots()
