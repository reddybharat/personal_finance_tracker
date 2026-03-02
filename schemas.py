"""
Pydantic models for Personal Finance Tracker.
All monetary values in INR (₹).
"""

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from constants import CATEGORIES

# Expected `transactions` columns (verify via Supabase): id, amount, category, transaction_date, description


class TransactionCreate(BaseModel):
    amount: float = Field(..., gt=0, description="Amount in INR (must be > 0)")
    category: str = Field(..., min_length=1)
    transaction_date: date = Field(default_factory=date.today)
    description: Optional[str] = None

    @field_validator("category")
    @classmethod
    def category_must_be_allowed(cls, v: str) -> str:
        v = v.strip()
        if v not in CATEGORIES:
            raise ValueError(
                f"Invalid category. Must be one of: {', '.join(CATEGORIES)}"
            )
        return v


class TransactionResponse(BaseModel):
    id: str
    amount: float
    category: str
    transaction_date: date
    description: Optional[str] = None

    class Config:
        from_attributes = True
