# Personal Finance Tracker

A simple personal finance tracker. All amounts are in **INR (₹)**. Backend is **Supabase** (PostgreSQL).

## Features

- **FastAPI** — REST API for transactions: create, list, get by id, update (PATCH), delete, and current-month summary
- **Streamlit** — Tabbed UI: **Summary** (current month + latest transactions), **Add** (form + **Import from CSV**), **Search** (filter by date range/category, pagination, **Export to CSV**, edit and delete per transaction), **Chat** (Finance Assistant)
- **Chat / Finance Assistant** — Natural language questions about your transactions. Uses a LangGraph SQL agent (Gemini LLM) with tools: list tables, get schema, execute read-only SQL. Answers summarize spending, breakdowns by category, and similar queries.
- **Import from CSV** — In the **Add** tab: download a template (correct headers + example rows), upload a CSV, and bulk-import transactions. Columns: `transaction_date` (YYYY-MM-DD), `category`, `amount`, `description` (optional). Category must be one of the fixed list; validation and row-level errors are shown.
- **Export to CSV** — In the **Search** tab: after you run a search, an **Export to CSV** button appears next to the Search button and downloads all transactions matching the current filters (date range and category).
- **Supabase** — Stores transactions; optional Row Level Security (RLS)
- **Fixed categories** — Transactions use one of: Grocery, Dining, Transportation, Utilities, Entertainment, Health, Housing, Personal, Investments, Misc (enforced in UI and API)
- **Validations** — Shared rules in `validations.py`: amount must be > 0, category required, transaction date cannot be in the future (enforced in UI and API)

## Prerequisites

- Python 3.8+
- A [Supabase](https://supabase.com) project with a `transactions` table
- For the **Chat** tab: a [Google AI Studio](https://ai.google.dev/gemini-api/docs/api-key) API key (Gemini) and a Postgres connection string for your Supabase database

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
GOOGLE_API_KEY=your-gemini-api-key
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@db.YOUR_PROJECT_REF.supabase.co:5432/postgres
```

- **SUPABASE_URL**, **SUPABASE_KEY** — From Supabase Dashboard → Project Settings → API. Required for Summary, Add, and Search.
- **GOOGLE_API_KEY** — From [Google AI Studio](https://ai.google.dev/gemini-api/docs/api-key). Required for the Chat (Finance Assistant) tab.
- **DATABASE_URL** — Postgres connection string for your Supabase database (Dashboard → Connect → URI). Required for the Chat agent to run read-only SQL. If omitted, the Chat tab will show a configuration message.

### 4. Row Level Security (optional)

If your table has RLS enabled, run the policies in **Supabase Dashboard → SQL Editor** using `supabase_rls_policies.sql` so the app can insert, select, update, and delete from `transactions`.

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

Opens at http://localhost:8501. Four tabs:

- **Summary** — Current month total spend and breakdown by category; plus a table of the latest 5–7 transactions
- **Add** — Form: amount, category (required), date (today or past only), optional description. **Import from CSV** expander: download template, upload CSV, import (with validation and error report)
- **Search** — Filter by date range, optional category, sort, and per-page count. **Search** and **Export to CSV** buttons side by side; Export appears after you run a search and downloads all results for the current filters. Table supports edit and delete per transaction
- **Chat** — Finance Assistant: ask questions in plain English (e.g. “What is my total spend this month?”, “Spending by category”). The agent uses Gemini and read-only SQL against your `transactions` table and returns summarized answers

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Basic API info |
| POST | `/transactions` | Create a transaction (amount > 0, category required, date not in future) |
| GET | `/transactions` | List last 20 transactions |
| GET | `/transactions/{transaction_id}` | Get one transaction by id |
| PATCH | `/transactions/{transaction_id}` | Update a transaction (partial) |
| DELETE | `/transactions/{transaction_id}` | Delete a transaction |
| GET | `/summary` | Current month total and spend by category |

## Project structure

```
├── app.py                      # Streamlit UI (tabs: Summary, Add, Search, Chat)
├── main.py                     # FastAPI app
├── database.py                 # Supabase client
├── logger.py                   # Shared logging config
├── schemas.py                  # Pydantic models (with category validation)
├── constants.py                # Allowed categories list
├── validations.py              # Shared validations (amount, category, date)
├── requirements.txt
├── supabase_rls_policies.sql
├── agent/                      # LangGraph SQL agent (Chat tab)
│   ├── __init__.py
│   ├── graph.py                # Edgeless StateGraph, run_agent()
│   ├── nodes.py                # agent_node (create_agent + tools)
│   ├── tools.py                # list_tables, get_schema, execute_sql
│   ├── state.py                # AgentState (messages)
│   ├── prompt.py               # System prompt for the agent
│   └── llm.py                  # Gemini LLM (get_llm)
├── routers/
│   └── transactions.py         # Transaction & summary routes
├── services/
│   ├── __init__.py
│   ├── csv_transactions.py     # CSV export, template, import (no UI)
│   └── sql_runner.py           # Read-only SQL executor (guardrails, psycopg2)
└── ui/
    ├── __init__.py
    ├── common.py               # Shared UI helpers
    ├── tabs/
    │   ├── summary_tab.py
    │   ├── add_txn_tab.py
    │   ├── search_tab.py
    │   └── chat_tab.py         # Chat UI, invokes agent
    ├── add/
    │   ├── __init__.py
    │   └── import_csv_section.py   # Import from CSV (Add tab)
    └── search/
        ├── filters.py              # Date/category/sort + Search + Export to CSV
        └── results.py              # Results table with edit/delete
```
