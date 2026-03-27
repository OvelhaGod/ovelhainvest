"""
CSV Import API — Phase 11.

Accepts CSV uploads for:
- M1 Finance (brokerage transactions)
- Binance (crypto trades)
- Generic format (auto-detected or manual column mapping)

POST /import/csv         → detect format + parse + preview (dry run)
POST /import/csv/confirm → confirm import into spending_transactions
GET  /import/csv/formats → list supported formats with column specs
"""

from __future__ import annotations

import csv
import io
import logging
from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from pydantic import BaseModel

from app.db.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Format specs ──────────────────────────────────────────────────────────────

CSV_FORMATS: dict[str, dict] = {
    "m1_finance": {
        "name": "M1 Finance",
        "description": "M1 Finance brokerage transaction history export",
        "detect_headers": ["Date", "Description", "Amount", "Account"],
        "column_map": {
            "date": "Date",
            "description": "Description",
            "amount": "Amount",
            "account": "Account",
            "type": None,          # derived from amount sign
            "notes": None,
        },
        "date_format": "%Y-%m-%d",
        "amount_sign": "signed",   # positive = credit, negative = debit
    },
    "binance": {
        "name": "Binance / Binance US",
        "description": "Binance transaction history CSV",
        "detect_headers": ["Date(UTC)", "Account", "Operation", "Coin", "Change", "Remark"],
        "column_map": {
            "date": "Date(UTC)",
            "description": "Operation",
            "amount": "Change",
            "account": "Account",
            "currency": "Coin",
            "notes": "Remark",
        },
        "date_format": "%Y-%m-%d %H:%M:%S",
        "amount_sign": "signed",
    },
    "generic": {
        "name": "Generic (Auto-detect)",
        "description": "Attempts to auto-map common column names",
        "detect_headers": [],      # fallback — always matches
        "column_map": {},
        "date_format": None,       # try multiple
        "amount_sign": "signed",
    },
}

GENERIC_DATE_FORMATS = [
    "%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d",
    "%m-%d-%Y", "%d-%m-%Y", "%b %d, %Y", "%B %d, %Y",
]

GENERIC_DATE_ALIASES = ["date", "Date", "DATE", "transaction_date", "Transaction Date", "posted", "Posted"]
GENERIC_DESC_ALIASES = ["description", "Description", "DESC", "memo", "Memo", "narrative", "Narrative", "name", "Name"]
GENERIC_AMOUNT_ALIASES = ["amount", "Amount", "AMOUNT", "value", "Value", "debit", "credit", "sum", "Sum"]


# ── Schemas ───────────────────────────────────────────────────────────────────

class ImportPreviewRow(BaseModel):
    row_num: int
    date: str
    description: str
    amount: float
    type: str          # "income" or "expense"
    currency: str
    notes: str | None
    account_id: str | None
    category_guess: str | None
    error: str | None


class ImportPreviewResponse(BaseModel):
    format_detected: str
    total_rows: int
    valid_rows: int
    error_rows: int
    date_range: dict[str, str]
    preview: list[ImportPreviewRow]
    import_token: str   # base64 of raw CSV for confirm step


class ImportConfirmResponse(BaseModel):
    imported: int
    skipped: int
    errors: int
    message: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def _detect_format(headers: list[str]) -> str:
    """Detect CSV format based on header names."""
    header_set = set(h.strip() for h in headers)
    for fmt_key, fmt in CSV_FORMATS.items():
        if fmt_key == "generic":
            continue
        required = set(fmt["detect_headers"])
        if required and required.issubset(header_set):
            return fmt_key
    return "generic"


def _parse_date(value: str, fmt: str | None) -> str | None:
    """Parse date string to ISO YYYY-MM-DD. Try multiple formats if fmt=None."""
    value = value.strip()
    formats_to_try = [fmt] if fmt else GENERIC_DATE_FORMATS
    for f in formats_to_try:
        try:
            return datetime.strptime(value, f).strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            continue
    return None


def _parse_amount(value: str) -> float | None:
    """Parse amount string to float, stripping currency symbols and commas."""
    try:
        cleaned = value.strip().replace(",", "").replace("$", "").replace("R$", "").replace(" ", "")
        return float(cleaned)
    except (ValueError, TypeError):
        return None


def _find_column(row: dict, aliases: list[str]) -> str | None:
    """Find a column by checking multiple alias names."""
    for alias in aliases:
        if alias in row:
            return alias
    return None


def _map_generic_row(row: dict) -> dict[str, Any]:
    """Map a generic CSV row by guessing column names."""
    date_col = _find_column(row, GENERIC_DATE_ALIASES)
    desc_col = _find_column(row, GENERIC_DESC_ALIASES)
    amount_col = _find_column(row, GENERIC_AMOUNT_ALIASES)
    return {
        "date_raw": row.get(date_col, "") if date_col else "",
        "description": row.get(desc_col, "Unknown") if desc_col else "Unknown",
        "amount_raw": row.get(amount_col, "0") if amount_col else "0",
    }


def _simple_category_guess(description: str, amount: float) -> str:
    """Rule-based category guess without AI (for preview)."""
    desc_lower = description.lower()
    if amount > 0:
        return "Other Income"
    patterns = [
        (["amazon", "amzn"], "Shopping"),
        (["uber eats", "doordash", "grubhub", "delivery"], "Food"),
        (["netflix", "spotify", "hulu", "disney", "apple tv"], "Subscriptions"),
        (["shell", "chevron", "exxon", "bp", "sunoco", "gas"], "Transport"),
        (["publix", "kroger", "whole foods", "trader joe", "walmart", "target", "costco"], "Food"),
        (["uber", "lyft", "taxi"], "Transport"),
        (["rent", "mortgage", "hoa"], "Housing"),
        (["electric", "water", "internet", "phone", "utilities"], "Housing"),
        (["gym", "fitness"], "Health"),
        (["doctor", "pharmacy", "medical", "dental"], "Health"),
        (["restaurant", "cafe", "coffee", "starbucks", "mcdonald", "subway"], "Food"),
        (["airline", "flight", "hotel", "airbnb", "travel"], "Travel"),
    ]
    for keywords, category in patterns:
        if any(kw in desc_lower for kw in keywords):
            return category
    return "Uncategorized"


def _parse_csv_rows(
    content: str,
    fmt_key: str,
    account_id: str | None,
) -> tuple[list[ImportPreviewRow], int]:
    """Parse CSV content into preview rows. Returns (rows, error_count)."""
    fmt = CSV_FORMATS[fmt_key]
    col_map = fmt["column_map"]
    date_fmt = fmt["date_format"]

    reader = csv.DictReader(io.StringIO(content))
    rows: list[ImportPreviewRow] = []
    errors = 0

    for i, row in enumerate(reader, start=2):  # row 1 is header
        try:
            if fmt_key == "generic":
                mapped = _map_generic_row(row)
                date_raw = mapped["date_raw"]
                description = mapped["description"]
                amount_raw = mapped["amount_raw"]
                currency = "USD"
                notes = None
            else:
                date_raw = row.get(col_map["date"], "")
                description = row.get(col_map["description"], "Unknown")
                amount_raw = row.get(col_map["amount"], "0")
                currency_col = col_map.get("currency")
                currency = row.get(currency_col, "USD") if currency_col else "USD"
                notes_col = col_map.get("notes")
                notes = row.get(notes_col) if notes_col else None

            date_str = _parse_date(date_raw, date_fmt)
            amount = _parse_amount(amount_raw)

            if date_str is None:
                raise ValueError(f"Cannot parse date: {date_raw!r}")
            if amount is None:
                raise ValueError(f"Cannot parse amount: {amount_raw!r}")

            txn_type = "income" if amount > 0 else "expense"
            category = _simple_category_guess(description, amount)

            rows.append(ImportPreviewRow(
                row_num=i,
                date=date_str,
                description=str(description)[:255],
                amount=abs(amount),
                type=txn_type,
                currency=str(currency)[:10].upper(),
                notes=str(notes)[:500] if notes else None,
                account_id=account_id,
                category_guess=category,
                error=None,
            ))
        except Exception as exc:
            errors += 1
            rows.append(ImportPreviewRow(
                row_num=i,
                date="",
                description="",
                amount=0,
                type="expense",
                currency="USD",
                notes=None,
                account_id=None,
                category_guess=None,
                error=str(exc),
            ))

    return rows, errors


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/formats")
def list_formats():
    """List supported CSV import formats."""
    return [
        {
            "key": key,
            "name": fmt["name"],
            "description": fmt["description"],
            "expected_headers": fmt["detect_headers"],
        }
        for key, fmt in CSV_FORMATS.items()
    ]


@router.post("/csv")
async def preview_csv_import(
    file: UploadFile = File(...),
    account_id: str = Query(default=None),
    format: str = Query(default=None),
    user_id: str = Query(default="default"),
):
    """
    Parse and preview a CSV file import (dry run — no DB writes).
    Returns first 50 rows parsed with detected format and column mapping.
    """
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a .csv")

    try:
        raw_bytes = await file.read()
        # Try UTF-8 first, fall back to latin-1
        try:
            content = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            content = raw_bytes.decode("latin-1")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not read file: {exc}") from exc

    # Detect format
    try:
        sample = io.StringIO(content)
        reader = csv.reader(sample)
        headers = next(reader, [])
    except Exception:
        headers = []

    fmt_key = format if format and format in CSV_FORMATS else _detect_format(headers)
    rows, error_count = _parse_csv_rows(content, fmt_key, account_id)

    valid_rows = [r for r in rows if r.error is None]
    dates = [r.date for r in valid_rows if r.date]

    import base64
    import_token = base64.b64encode(content.encode("utf-8")).decode("utf-8")

    return ImportPreviewResponse(
        format_detected=fmt_key,
        total_rows=len(rows),
        valid_rows=len(valid_rows),
        error_rows=error_count,
        date_range={
            "earliest": min(dates) if dates else "",
            "latest": max(dates) if dates else "",
        },
        preview=rows[:50],
        import_token=import_token,
    )


@router.post("/csv/confirm")
async def confirm_csv_import(
    payload: dict,
    user_id: str = Query(default="default"),
):
    """
    Confirm and execute a previously previewed CSV import.
    Expects: {import_token, account_id, format, skip_duplicates}
    """
    import_token = payload.get("import_token", "")
    account_id = payload.get("account_id")
    fmt_key = payload.get("format", "generic")
    skip_duplicates = payload.get("skip_duplicates", True)

    if not import_token:
        raise HTTPException(status_code=400, detail="import_token required")

    import base64
    try:
        content = base64.b64decode(import_token.encode("utf-8")).decode("utf-8")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid import_token: {exc}") from exc

    rows, _ = _parse_csv_rows(content, fmt_key, account_id)
    valid_rows = [r for r in rows if r.error is None]

    db = get_supabase_client()
    imported = 0
    skipped = 0
    errors = 0

    for row in valid_rows:
        try:
            txn = {
                "user_id": user_id,
                "date": row.date,
                "description": row.description,
                "amount": -abs(row.amount) if row.type == "expense" else abs(row.amount),
                "type": row.type,
                "currency": row.currency,
                "notes": row.notes,
                "account_id": account_id,
                "source": fmt_key,
            }

            if skip_duplicates:
                # Simple dedup: check description + date + amount
                existing = (
                    db.table("spending_transactions")
                    .select("id")
                    .eq("user_id", user_id)
                    .eq("date", row.date)
                    .eq("description", row.description)
                    .eq("amount", txn["amount"])
                    .limit(1)
                    .execute()
                )
                if existing.data:
                    skipped += 1
                    continue

            db.table("spending_transactions").insert(txn).execute()
            imported += 1
        except Exception as exc:
            logger.warning("CSV import row error: %s", exc)
            errors += 1

    return ImportConfirmResponse(
        imported=imported,
        skipped=skipped,
        errors=errors,
        message=f"Import complete: {imported} imported, {skipped} skipped (duplicates), {errors} errors.",
    )
