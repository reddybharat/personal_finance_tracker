# Personal Finance Tracker

A simple personal finance tracker. All amounts are in **INR (₹)**. Backend is **Supabase** (PostgreSQL).

## Features

- **FastAPI** — REST API for creating transactions and current-month summary
- **Streamlit** — Tabbed UI: **This Month** (summary), **Add Transaction** (form), **Search** (filter by date range and category)
- **Supabase** — Stores transactions; optional Row Level Security (RLS)
- **Fixed categories** — Transactions use one of: Grocery, Dining, Transportation, Utilities, Entertainment, Health, Housing, Personal, Investments, Misc (enforced in UI and API)

## Prerequisites

- Python 3.8+
- A [Supabase](https://supabase.com) project with a `transactions` table

### Table schema

`transactions` should have at least: `id`, `amount`, `category`, `transaction_date`, `description`.

## Setup

### 1. Clone and virtual environment

```bash
cd personal_finance_tracker
python -m venv venv
```

**Windows (PowerShell):**
```powershell
.\venv\Scripts\Activate.ps1
```

**macOS/Linux:**
```bash
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Environment variables

Create a `.env` in the project root:

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
```

Get these from Supabase Dashboard → Project Settings → API.

### 4. Row Level Security (optional)

If your table has RLS enabled, run the policies in **Supabase Dashboard → SQL Editor** using `supabase_rls_policies.sql` so the app can insert and select from `transactions`.

## Running the app

### API server

```bash
uvicorn main:app --reload
```

- API: http://127.0.0.1:8000  
- Interactive docs: http://127.0.0.1:8000/docs  

### Streamlit UI

```bash
streamlit run app.py
```

Opens at http://localhost:8501. Three tabs:

- **This Month** — Current month total spend and breakdown by category
- **Add Transaction** — Form: amount, category (dropdown), date, optional description
- **Search** — Filter by date range and optional category; results shown in a table with total

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Basic API info |
| POST | `/transactions` | Create a transaction (category must be one of the allowed list) |
| GET | `/transactions` | List last 20 transactions |
| GET | `/summary` | Current month total and spend by category |

## Project structure

```
├── app.py                  # Streamlit UI (tabs: This Month, Add, Search)
├── main.py                 # FastAPI app
├── database.py             # Supabase client
├── schemas.py              # Pydantic models (with category validation)
├── constants.py            # Allowed categories list
├── requirements.txt
├── supabase_rls_policies.sql
└── routers/
    └── transactions.py     # Transaction & summary routes
```
