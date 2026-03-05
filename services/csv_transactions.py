"""
CSV export, template, and import for transactions.
Uses database and schemas; no UI dependencies.
"""

import csv
import io
from datetime import date
from typing import Optional

from database import get_supabase
from schemas import TransactionCreate

# CSV column names (used for export, template, and import)
CSV_FIELDS = ["transaction_date", "category", "amount", "description"]


def export_transactions_csv(
    start_date: date, end_date: date, category: Optional[str]
) -> str:
    """Return CSV string for all transactions matching the given filters."""
    query = (
        get_supabase()
        .table("transactions")
        .select("transaction_date, category, amount, description")
        .gte("transaction_date", start_date.isoformat())
        .lte("transaction_date", end_date.isoformat())
        .order("transaction_date", desc=False)
    )
    if category and category != "All":
        query = query.eq("category", category)
    response = query.execute()
    rows = response.data or []

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=CSV_FIELDS)
    writer.writeheader()
    for row in rows:
        writer.writerow(
            {
                "transaction_date": row.get("transaction_date", ""),
                "category": row.get("category", ""),
                "amount": row.get("amount", ""),
                "description": row.get("description") or "",
            }
        )
    return output.getvalue()


def transactions_csv_template() -> str:
    """Return CSV string with correct headers and example rows for import."""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=CSV_FIELDS)
    writer.writeheader()
    example_rows = [
        {
            "transaction_date": "2026-03-01",
            "category": "Grocery",
            "amount": "1250.50",
            "description": "Weekly groceries",
        },
        {
            "transaction_date": "2026-03-02",
            "category": "Dining",
            "amount": "450",
            "description": "Lunch",
        },
        {
            "transaction_date": "2026-03-03",
            "category": "Transportation",
            "amount": "320",
            "description": "",
        },
    ]
    for row in example_rows:
        writer.writerow(row)
    return output.getvalue()


def import_transactions_from_csv(content: bytes) -> tuple[int, list[str]]:
    """
    Parse CSV content and insert valid rows into the transactions table.

    Expected columns (case-insensitive): transaction_date (YYYY-MM-DD), category, amount, description (optional).
    Returns (inserted_count, list of error messages for failed rows).
    """
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))

    if reader.fieldnames is None:
        return 0, ["CSV file has no header row."]

    header_map = {name.lower(): name for name in reader.fieldnames}
    required_cols = ["transaction_date", "category", "amount"]
    missing = [c for c in required_cols if c not in header_map]
    if missing:
        return 0, [
            "Missing required column(s): "
            + ", ".join(missing)
            + ". Expected at least: transaction_date, category, amount."
        ]

    errors: list[str] = []
    rows_to_insert: list[dict] = []

    for idx, row in enumerate(reader, start=2):
        try:
            raw_date = (row.get(header_map["transaction_date"]) or "").strip()
            raw_category = (row.get(header_map["category"]) or "").strip()
            raw_amount = (row.get(header_map["amount"]) or "").strip()
            raw_description = (
                row.get(header_map.get("description", ""))
                if "description" in header_map
                else None
            )

            if not raw_date or not raw_category or not raw_amount:
                raise ValueError(
                    "transaction_date, category, and amount are required."
                )

            try:
                parsed_date = date.fromisoformat(raw_date)
            except ValueError:
                raise ValueError(
                    f"Invalid date format '{raw_date}'. Use YYYY-MM-DD."
                )

            try:
                parsed_amount = float(raw_amount)
            except ValueError:
                raise ValueError(
                    f"Invalid amount '{raw_amount}'. Must be a number."
                )

            tx = TransactionCreate(
                amount=parsed_amount,
                category=raw_category,
                transaction_date=parsed_date,
                description=raw_description,
            )
            rows_to_insert.append(
                {
                    "amount": float(tx.amount),
                    "category": tx.category.strip(),
                    "transaction_date": tx.transaction_date.isoformat(),
                    "description": tx.description,
                }
            )
        except Exception as e:
            errors.append(f"Row {idx}: {e}")

    inserted_count = 0
    if rows_to_insert:
        response = (
            get_supabase().table("transactions").insert(rows_to_insert).execute()
        )
        inserted_count = len(response.data or [])

    return inserted_count, errors
