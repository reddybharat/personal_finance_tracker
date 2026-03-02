"""
Simple Streamlit UI to add transactions to the Personal Finance Tracker.
Light mode. Inserts into Supabase transactions table.
Tabs: This Month, Add Transaction, Search.
"""

import streamlit as st
from datetime import date

from database import get_supabase
from constants import CATEGORIES

st.set_page_config(page_title="Personal Finance Tracker", page_icon="💰", layout="centered")


def _validate_category(category: str) -> None:
    """Raise ValueError if category is not in CATEGORIES."""
    if not category or not (c := category.strip()):
        raise ValueError("Please select a category.")
    if c not in CATEGORIES:
        raise ValueError(
            f"Invalid category: '{c}'. Must be one of: {', '.join(CATEGORIES)}."
        )


SUPABASE_ERROR_MSG = (
    "**Could not reach Supabase.** This is usually:\n\n"
    "• **Project paused** — Free-tier projects pause after inactivity. "
    "Open your [Supabase Dashboard](https://supabase.com/dashboard), select the project, and click **Restore**.\n\n"
    "• **Temporary outage** — Try again in a few minutes.\n\n"
    "• **Network/firewall** — Check VPN or corporate network if the problem continues."
)


def _is_supabase_connection_error(err: str) -> bool:
    return "525" in err or "SSL handshake" in err or "JSON could not be generated" in err


def _render_this_month():
    st.subheader("This month")
    try:
        today = date.today()
        start = today.replace(day=1).isoformat()
        end = today.isoformat()
        response = (
            get_supabase()
            .table("transactions")
            .select("amount, category")
            .gte("transaction_date", start)
            .lte("transaction_date", end)
            .execute()
        )
        total = 0.0
        by_category = {}
        for row in response.data or []:
            amt = float(row.get("amount", 0))
            cat = row.get("category") or "Uncategorized"
            total += amt
            by_category[cat] = by_category.get(cat, 0) + amt
        st.metric("Total spend", f"₹{total:,.2f}")
        if by_category:
            st.caption("By category")
            for cat, val in sorted(by_category.items()):
                st.write(f"• **{cat}**: ₹{val:,.2f}")
        else:
            st.caption("No transactions this month yet.")
    except ValueError:
        st.warning("Database not configured. Set SUPABASE_URL and SUPABASE_KEY in .env to see summary.")
    except Exception as e:
        err = str(e)
        if _is_supabase_connection_error(err):
            st.warning(SUPABASE_ERROR_MSG)
        else:
            st.warning(f"Could not load summary: {err[:200]}" + ("…" if len(err) > 200 else ""))

def _render_add_transaction():
    st.subheader("Add")
    st.caption("Amount in ₹ (INR)")
    with st.form("transaction_form", clear_on_submit=True):
        amount = st.number_input(
            "Amount (₹)",
            min_value=0.00,
            step=100.00,
            format="%.2f",
            help="Enter amount in INR",
        )
        category = st.selectbox("Category", options=CATEGORIES)
        transaction_date = st.date_input("Date", value=date.today())
        description = st.text_input("Description (optional)", placeholder="Short note")
        submitted = st.form_submit_button("Save transaction")

    if submitted:
        try:
            _validate_category(category)
        except ValueError as e:
            st.error(str(e))
        else:
            if amount <= 0:
                st.error("Amount must be greater than 0.")
            else:
                try:
                    supabase = get_supabase()
                    row = {
                        "amount": float(amount),
                        "category": category,
                        "transaction_date": transaction_date.isoformat(),
                        "description": description.strip() or None,
                    }
                    response = supabase.table("transactions").insert(row).execute()
                    if response.data:
                        st.success(f"Saved: ₹{amount:,.2f} — {category} on {transaction_date}")
                    else:
                        st.error("Insert failed. Check your database.")
                except ValueError as e:
                    st.error(str(e))
                except Exception as e:
                    err = str(e)
                    if _is_supabase_connection_error(err):
                        st.error(SUPABASE_ERROR_MSG)
                    elif "42501" in err or "row-level security policy" in err.lower():
                        st.error(
                            "**Row Level Security (RLS) is blocking this.** Add policies in Supabase:\n\n"
                            "1. Open [Supabase Dashboard](https://supabase.com/dashboard) → your project → **SQL Editor**.\n"
                            "2. Run the SQL from **`supabase_rls_policies.sql`** in this project (or create policies that allow INSERT/SELECT on `transactions` for your role)."
                        )
                    else:
                        st.error(f"Error: {err}")

def _render_search():
    st.subheader("Search transactions")
    try:
        col11, col12, col13 = st.columns([1, 1, 1])
        with col11:
            start_date = st.date_input("From Date", value=date.today().replace(day=1))
        with col12:
            end_date = st.date_input("To Date", value=date.today())

        col21, col22, col23 = st.columns([1, 1, 1])
        with col21:
            category = st.selectbox(
                "Category (optional)",
                options=["All"] + CATEGORIES,
                index=0,
            )
        with col22:
            limit = st.number_input("Max results", min_value=5, max_value=100, value=10, step=5)

        if start_date > end_date:
            st.error("From date must be on or before To date.")
        else:
            if st.button("Search"):
                query = (
                    get_supabase()
                    .table("transactions")
                    .select("id, amount, category, transaction_date, description")
                    .gte("transaction_date", start_date.isoformat())
                    .lte("transaction_date", end_date.isoformat())
                    .order("transaction_date", desc=True)
                    .limit(limit)
                )
                if category and category != "All":
                    query = query.eq("category", category)
                response = query.execute()
                rows = response.data or []
                if not rows:
                    st.info("No transactions found for the selected filters.")
                else:
                    total_amt = sum(float(r.get("amount", 0)) for r in rows)
                    # st.caption(f"{len(rows)} transaction(s) · **Total: ₹{total_amt:,.2f}**")
                    table_data = [
                        {
                            "Date": r.get("transaction_date", ""),
                            "Amount (₹)": f"₹{float(r.get('amount', 0)):,.2f}",
                            "Category": r.get("category", ""),
                            "Description": r.get("description") or "—",
                        }
                        for r in rows
                    ]
                    st.dataframe(table_data, use_container_width=True, hide_index=True)
    except ValueError:
        st.warning("Database not configured. Set SUPABASE_URL and SUPABASE_KEY in .env to search.")
    except Exception as e:
        err = str(e)
        if _is_supabase_connection_error(err):
            st.warning(SUPABASE_ERROR_MSG)
        else:
            st.warning(f"Could not search: {err[:200]}" + ("…" if len(err) > 200 else ""))

tab1, tab2, tab3 = st.tabs(["This Month", "Add", "Search"])
with tab1:
    _render_this_month()
with tab2:
    _render_add_transaction()
with tab3:
    _render_search()
