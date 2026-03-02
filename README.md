# Personal Finance Tracker

A simple personal finance tracker. All amounts are in **INR (₹)**. Backend is **Supabase** (PostgreSQL).

## Features

- **FastAPI** — REST API for transactions and monthly summary
- **Streamlit** — Light-mode UI to add transactions (amount, category, date, description)
- **Supabase** — Stores transactions; optional Row Level Security (RLS)

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

Opens at http://localhost:8501. Use the form to add transactions (amount, category, date, description).

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Basic API info |
| POST | `/transactions` | Create a transaction |
| GET | `/transactions` | List last 20 transactions |
| GET | `/summary` | Current month total and spend by category |

## Project structure

```
├── app.py              # Streamlit UI
├── main.py             # FastAPI app
├── database.py         # Supabase client
├── schemas.py          # Pydantic models
├── requirements.txt
├── supabase_rls_policies.sql
└── routers/
    └── transactions.py # Transaction & summary routes
```
