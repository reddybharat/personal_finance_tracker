"""
Transaction and summary API endpoints.
"""

from datetime import date

from fastapi import APIRouter, HTTPException

from database import get_supabase
from schemas import TransactionCreate, TransactionResponse, TransactionUpdate
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
    return _record_to_response(data[0])


def _record_to_response(record: dict) -> TransactionResponse:
    return TransactionResponse(
        id=str(record["id"]),
        amount=float(record["amount"]),
        category=record["category"],
        transaction_date=date.fromisoformat(record["transaction_date"]),
        description=record.get("description"),
    )


@router.get("/transactions/{transaction_id}", response_model=TransactionResponse)
def get_transaction(transaction_id: str) -> TransactionResponse:
    """Fetch a single transaction by id."""
    response = (
        get_supabase()
        .table("transactions")
        .select("id, amount, category, transaction_date, description")
        .eq("id", transaction_id)
        .execute()
    )
    data = response.data or []
    if not data:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return _record_to_response(data[0])


@router.patch("/transactions/{transaction_id}", response_model=TransactionResponse)
def update_transaction(transaction_id: str, payload: TransactionUpdate) -> TransactionResponse:
    """Update a transaction by id. Only provided fields are updated."""
    payload_dict = payload.model_dump(exclude_unset=True)
    if not payload_dict:
        return get_transaction(transaction_id)
    if "transaction_date" in payload_dict:
        try:
            validate_transaction_date(payload_dict["transaction_date"])
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    if "amount" in payload_dict:
        payload_dict["amount"] = float(payload_dict["amount"])
    if "transaction_date" in payload_dict:
        payload_dict["transaction_date"] = payload_dict["transaction_date"].isoformat()
    if "category" in payload_dict and payload_dict["category"] is not None:
        payload_dict["category"] = payload_dict["category"].strip()

    response = (
        get_supabase()
        .table("transactions")
        .update(payload_dict)
        .eq("id", transaction_id)
        .execute()
    )
    data = response.data or []
    if not data:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return _record_to_response(data[0])


@router.delete("/transactions/{transaction_id}", status_code=204)
def delete_transaction(transaction_id: str) -> None:
    """Delete a transaction by id."""
    response = (
        get_supabase()
        .table("transactions")
        .delete()
        .eq("id", transaction_id)
        .execute()
    )
    # Supabase delete returns the deleted row(s); if nothing was deleted, we treat as 404
    if not (response.data and len(response.data) > 0):
        raise HTTPException(status_code=404, detail="Transaction not found")


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
    return [_record_to_response(record) for record in (response.data or [])]


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
