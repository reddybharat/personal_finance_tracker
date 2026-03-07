# Refactor Plan: Tracker + Chat Structure, Chat APIs, Tracker DB via DATABASE_URL

## 1. Target folder structure

- **Main folders:** `tracker` and `chat` (not `transactions`).
- **common:** shared code only (e.g. `logger`).
- **tracker:** transaction CRUD, CSV, API, and Streamlit UI (summary, add, search).
- **chat:** agent (under `chat/agent/`), read-only SQL service, chat API, and Streamlit Chat tab.

```
personal_finance_tracker/
├── app.py
├── main.py
├── common/
│   └── logger.py
│
├── tracker/
│   ├── __init__.py
│   ├── database.py      # CRUD via psycopg2 + DATABASE_URL (replaces Supabase client)
│   ├── schemas.py
│   ├── constants.py
│   ├── validations.py
│   ├── services.py      # CSV export, template, import (from services/csv_transactions.py)
│   ├── api/
│   │   ├── __init__.py
│   │   └── transactions.py
│   └── ui/
│       ├── __init__.py
│       ├── common.py
│       ├── tabs/
│       │   ├── summary_tab.py
│       │   ├── add_txn_tab.py
│       │   └── search_tab.py
│       ├── add/
│       │   └── import_csv_section.py
│       └── search/
│           ├── filters.py
│           └── results.py
│
└── chat/
    ├── __init__.py
    ├── services.py      # Read-only SQL executor (from services/sql_runner.py)
    ├── api/
    │   ├── __init__.py
    │   └── chat.py      # invoke, resume, exit endpoints
    ├── agent/
    │   ├── __init__.py
    │   ├── graph.py
    │   ├── nodes.py
    │   ├── tools.py
    │   ├── state.py
    │   ├── prompt.py
    │   └── llm.py
    └── ui/
        ├── __init__.py
        └── chat_tab.py
```

- **Naming:** `tracker` and `chat` as top-level feature packages; `chat/agent/` kept as subpackage; single `services.py` in each of `tracker` and `chat` (no nested `services/`).

---

## 2. Tracker database: DATABASE_URL + psycopg2 (no Supabase client, no RLS)

**Goal:** Same application behaviour for the tracker (insert, update, delete, select) using a direct Postgres connection and `DATABASE_URL` only. No Supabase client, no dependency on RLS.

**New `tracker/database.py`:**

- Use `psycopg2` + `DATABASE_URL` from env (same as chat).
- All operations via parameterized queries to avoid SQL injection.
- Provide a small, explicit API used by tracker API and UI:

  - **get_connection()** — context manager or function returning a connection (read from `DATABASE_URL`; raise clear error if missing).
  - **create_transaction(amount, category, transaction_date, description)** → dict (with `id` from `RETURNING id, ...`).
  - **get_transaction(transaction_id)** → dict | None.
  - **list_transactions(limit=20)** → list[dict] (order by `transaction_date` desc).
  - **update_transaction(transaction_id, payload_dict)** → dict | None (only update provided keys).
  - **delete_transaction(transaction_id)** → bool (True if a row was deleted).
  - **get_summary(start_date, end_date)** → list[dict] with `amount`, `category` for current-month summary.
  - **query_transactions(start_date, end_date, category=None, order_by='transaction_date', desc=True, limit=20, offset=0)** → (list[dict], total_count) for search/export (pagination + count).

- No RLS: the connection uses the role in `DATABASE_URL` (e.g. `postgres` or a dedicated app user). Security is application-level; RLS is not required for this refactor.

**Call sites to update:**

- **tracker/api/transactions.py** — replace every `get_supabase().table("transactions")` call with the new `tracker.database` functions. Keep the same HTTP contract (status codes, response shapes).
- **tracker/services.py** — CSV export and import: use `tracker.database` (e.g. `query_transactions` for export, `create_transaction` in a loop or batch for import).
- **tracker/ui/** — summary_tab, add_txn_tab, search_tab, search/results.py, search/filters.py: replace `get_supabase()` with calls to `tracker.database` (and, if needed, a thin wrapper that returns data in the same shape the UI expects). Update `tracker/ui/common.py` to a generic “database connection” error message instead of Supabase-specific text.

**Env:** Only `DATABASE_URL` is required for both tracker and chat. `SUPABASE_URL` / `SUPABASE_KEY` can be removed from tracker usage and from README for the tracker flow (optional: keep in README as “optional for Supabase Dashboard” if you still use the dashboard elsewhere).

**Dependencies:** Remove `supabase` from `requirements.txt` if nothing else uses it after this refactor.

---

## 3. Chat: `services.py` and `chat/agent/`

- **chat/services.py** — Rename and move from `services/sql_runner.py`. Same behaviour: read-only SQL executor (validate SELECT-only, row limit, etc.) using `DATABASE_URL` and psycopg2. Update any imports (e.g. `agent/tools.py` → `chat.agent.tools` will import from `chat.services`).
- **chat/agent/** — Keep all current agent modules (graph, nodes, tools, state, prompt, llm). Update internal imports to use `chat.agent.*` and `chat.services` where applicable. No change to LangGraph/LangChain logic.

---

## 4. Chat APIs: invoke, resume, exit

Add three FastAPI endpoints under a `chat` router, so they are present and documented like the tracker APIs. Only **invoke** needs to be fully implemented; **resume** and **exit** can be stubs.

**File:** `chat/api/chat.py`

- **POST /chat/invoke**
  - Request body: `{ "messages": [ {"role": "user" | "assistant", "content": "..." } ] }`.
  - Response: `{ "reply": "<assistant text>" }` or appropriate error (e.g. 400/500).
  - Implementation: call existing `run_agent(chat_history)` (e.g. from `chat.agent.graph`), return the string as `reply`.

- **POST /chat/resume**
  - Request body: e.g. `{ "thread_id": "<optional>", "payload": {} }` (or empty body).
  - Response: e.g. `{ "status": "resume_not_implemented" }` with 200 or 501. No persistence required for the plan; just present so the API surface matches the idea of “resume”.

- **POST /chat/exit**
  - Request body: e.g. `{ "thread_id": "<optional>" }` or empty.
  - Response: e.g. `{ "status": "ok" }` or “exit not implemented”. Stub only.

**main.py:** Include the chat router with prefix `"/chat"` and tags `["chat"]`, e.g.:

- `from chat.api.chat import router as chat_router`
- `app.include_router(chat_router, prefix="/chat", tags=["chat"])`

---

## 5. Tracker: single `services.py` (no `services/` folder)

- **tracker/services.py** — Contains CSV logic from current `services/csv_transactions.py`: `export_transactions_csv`, `transactions_csv_template`, `import_transactions_from_csv`. All DB access via `tracker.database` (no Supabase). Imports: `tracker.database`, `tracker.schemas` (e.g. `TransactionCreate`), `tracker.constants` if needed.

---

## 6. Imports and entrypoints

- **app.py (Streamlit):**
  - `from common.logger import get_logger`
  - `from tracker.ui.tabs.summary_tab import render_summary`
  - `from tracker.ui.tabs.add_txn_tab import render_add_transaction`
  - `from tracker.ui.tabs.search_tab import render_search`
  - `from chat.ui.chat_tab import render_chat`

- **main.py (FastAPI):**
  - Include `tracker.api.transactions` router (same prefix/tags as today if desired).
  - Include `chat.api.chat` router with prefix `"/chat"`, tags `["chat"]`.

- **chat/agent/** modules: import from `chat.agent.*` and `chat.services` (e.g. `from chat.services import execute_readonly_query`, `SQLSecurityError`, `is_configured`). Graph entrypoint `run_agent` remains in `chat.agent.graph`; chat API and Streamlit chat tab call that.

- **chat/ui/chat_tab.py:** Import `run_agent` from `chat.agent.graph` (or `chat.agent` if re-exported there).

---

## 7. Files to add, move, or remove

| Action   | Path |
|----------|------|
| Create   | `common/__init__.py`, `common/logger.py` (move from `logger.py`) |
| Create   | `tracker/__init__.py`, `tracker/database.py` (new impl), `tracker/schemas.py`, `tracker/constants.py`, `tracker/validations.py`, `tracker/services.py` |
| Create   | `tracker/api/__init__.py`, `tracker/api/transactions.py` (from `routers/transactions.py`) |
| Create   | `tracker/ui/` subtree (from `ui/`: common, tabs, add, search) |
| Create   | `chat/__init__.py`, `chat/services.py` (from `services/sql_runner.py`) |
| Create   | `chat/api/__init__.py`, `chat/api/chat.py` (new: invoke, resume, exit) |
| Create   | `chat/agent/*` (from `agent/*`) |
| Create   | `chat/ui/__init__.py`, `chat/ui/chat_tab.py` (from `ui/tabs/chat_tab.py`) |
| Update   | `app.py`, `main.py`, `README.md` |
| Remove   | Root-level `database.py`, `logger.py`, `schemas.py`, `constants.py`, `validations.py`, `routers/`, `services/`, `ui/`, `agent/` after migration |

---

## 8. README and env

- **README:** Describe the new layout (tracker vs chat, common), that the tracker and chat both use `DATABASE_URL`, and list the three chat endpoints (invoke, resume, exit). Remove or soften Supabase client/RLS as the primary path for tracker; mention Supabase only as the Postgres host if applicable.
- **.env:** Document `DATABASE_URL` as the single DB connection for app (tracker + chat). Optionally keep `SUPABASE_URL`/`SUPABASE_KEY` only if still used for something else (e.g. dashboard).

---

## 9. Order of implementation

1. Add **common/** and move logger.
2. Implement **tracker/database.py** (psycopg2 CRUD) and **tracker/** (schemas, constants, validations, services, api, ui); then point **main.py** and **app.py** to tracker.
3. Add **chat/** layout: **chat/services.py** (from sql_runner), **chat/agent/** (from agent), **chat/ui/chat_tab.py**; fix all imports; add **chat/api/chat.py** (invoke implemented, resume/exit stubbed).
4. Wire **main.py** to include chat router; ensure **app.py** uses **chat.ui.chat_tab**.
5. Remove old roots: **routers/**, **services/**, **ui/**, **agent/**, **database.py**, **logger.py**, **schemas.py**, **constants.py**, **validations.py**.
6. Update **README** and **requirements.txt** (remove `supabase` if unused).
7. Smoke-test: tracker CRUD + summary + search + CSV; chat tab and **POST /chat/invoke**; **POST /chat/resume** and **POST /chat/exit** return stub responses.
