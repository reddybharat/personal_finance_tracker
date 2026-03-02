"""
Transaction and summary API endpoints.
"""

from datetime import date

from fastapi import APIRouter, HTTPException

from database import get_supabase
from schemas import TransactionCreate, TransactionResponse
from validations import validate_transaction_date

router = APIRouter(prefix="", tags=["transactions"])


@router.post("/transactions", response_model=TransactionResponse)
def create_transaction(payload: TransactionCreate) -> TransactionResponse:
    """Insert a new transaction. Column names: amount, category, transaction_date, description."""
    try:
        validate_transaction_date(payload.transaction_date)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    row = {
        "amount": float(payload.amount),
        "category": payload.category.strip(),
        "transaction_date": payload.transaction_date.isoformat(),
        "description": payload.description,
    }
    response = get_supabase().table("transactions").insert(row).execute()
    data = response.data
    if not data:
        raise HTTPException(status_code=500, detail="Insert failed")
    record = data[0]
    return TransactionResponse(
        id=str(record["id"]),
        amount=float(record["amount"]),
        category=record["category"],
        transaction_date=date.fromisoformat(record["transaction_date"]),
        description=record.get("description"),
    )


@router.get("/transactions", response_model=list[TransactionResponse])
def list_transactions() -> list[TransactionResponse]:
    """Fetch the last 20 transactions ordered by transaction_date descending."""
    response = (
        get_supabase().table("transactions")
        .select("id, amount, category, transaction_date, description")
        .order("transaction_date", desc=True)
        .limit(20)
        .execute()
    )
    out = []
    for record in response.data or []:
        out.append(
            TransactionResponse(
                id=str(record["id"]),
                amount=float(record["amount"]),
                category=record["category"],
                transaction_date=date.fromisoformat(record["transaction_date"]),
                description=record.get("description"),
            )
        )
    return out


@router.get("/summary")
def get_summary() -> dict:
    """
    Current month summary:
    - total_spend: total amount for the current month
    - by_category: { "CategoryName": total_inr, ... }
    """
    today = date.today()
    start = today.replace(day=1).isoformat()
    end = today.isoformat()

    response = (
        get_supabase().table("transactions")
        .select("amount, category")
        .gte("transaction_date", start)
        .lte("transaction_date", end)
        .execute()
    )

    total = 0.0
    by_category: dict[str, float] = {}
    for row in response.data or []:
        amt = float(row.get("amount", 0))
        cat = row.get("category") or "Uncategorized"
        total += amt
        by_category[cat] = by_category.get(cat, 0) + amt

    return {
        "total_spend": round(total, 2),
        "by_category": {k: round(v, 2) for k, v in sorted(by_category.items())},
        "month": today.strftime("%Y-%m"),
    }
