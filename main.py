"""
Personal Finance Tracker - FastAPI MVP
All monetary values in INR (₹). Uses Supabase (PostgreSQL).
"""

from fastapi import FastAPI

from routers import transactions

app = FastAPI(title="Personal Finance Tracker", version="0.1.0")


@app.get("/")
def root():
    return {"message": "Personal Finance Tracker API", "docs": "/docs"}


app.include_router(transactions.router)
