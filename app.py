"""
Simple Streamlit UI to add transactions to the Personal Finance Tracker.
Light mode. Inserts into Supabase transactions table.
Tabs: Summary, Add Transaction, Search.
"""

import streamlit as st
from datetime import date

from database import get_supabase
from constants import CATEGORIES
from validations import validate_amount, validate_category, validate_transaction_date

st.set_page_config(page_title="Personal Finance Tracker", page_icon="💰", layout="centered")


SUPABASE_ERROR_MSG = (
    "**Could not reach Supabase.** This is usually:\n\n"
    "• **Project paused** — Free-tier projects pause after inactivity. "
    "Open your [Supabase Dashboard](https://supabase.com/dashboard), select the project, and click **Restore**.\n\n"
    "• **Temporary outage** — Try again in a few minutes.\n\n"
    "• **Network/firewall** — Check VPN or corporate network if the problem continues."
)


def _is_supabase_connection_error(err: str) -> bool:
    return "525" in err or "SSL handshake" in err or "JSON could not be generated" in err


def _render_summary():
    st.subheader("Summary")
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

        # Latest 5–7 transactions
        st.subheader("Latest transactions")
        latest_response = (
            get_supabase()
            .table("transactions")
            .select("id, amount, category, transaction_date, description")
            .order("transaction_date", desc=True)
            .limit(7)
            .execute()
        )
        latest_rows = latest_response.data or []
        if not latest_rows:
            st.caption("No transactions yet.")
        else:
            table_data = [
                {
                    "Date": r.get("transaction_date", ""),
                    "Amount (₹)": f"₹{float(r.get('amount', 0)):,.2f}",
                    "Category": r.get("category", ""),
                    "Description": r.get("description") or "—",
                }
                for r in latest_rows
            ]
            st.dataframe(table_data, width='stretch', hide_index=True)
    except ValueError:
        st.warning("Database not configured. Set SUPABASE_URL and SUPABASE_KEY in .env to see summary.")
    except Exception as e:
        err = str(e)
        if _is_supabase_connection_error(err):
            st.warning(SUPABASE_ERROR_MSG)
        else:
            st.warning(f"Could not load summary: {err[:200]}" + ("…" if len(err) > 200 else ""))

REQUIRED_LABEL = "<span style='color: red'>*</span>"


def _render_add_transaction():
    st.subheader("Add")
    st.caption("Amount in ₹ (INR)")
    with st.form("transaction_form", clear_on_submit=True):
        st.markdown(f"Amount (₹) {REQUIRED_LABEL}", unsafe_allow_html=True)
        amount = st.number_input(
            "Amount (₹)",
            min_value=0.00,
            step=100.00,
            format="%.2f",
            help="Enter amount in INR",
            label_visibility="collapsed",
        )
        st.markdown(f"Category {REQUIRED_LABEL}", unsafe_allow_html=True)
        category = st.selectbox(
            "Category",
            options=CATEGORIES,
            index=None,
            placeholder="Select category",
            label_visibility="collapsed",
        )
        st.markdown(f"Date {REQUIRED_LABEL}", unsafe_allow_html=True)
        transaction_date = st.date_input("Date", value=date.today(), label_visibility="collapsed")
        description = st.text_input("Description (optional)", placeholder="Short note")
        submitted = st.form_submit_button("Save transaction")

    if submitted:
        errors = []
        try:
            validate_amount(amount)
        except ValueError as e:
            errors.append(str(e))
        try:
            validate_category(category)
        except ValueError as e:
            errors.append(str(e))
        try:
            validate_transaction_date(transaction_date)
        except ValueError as e:
            errors.append(str(e))

        if errors:
            for msg in errors:
                st.error(msg)
        else:
            try:
                supabase = get_supabase()
                row = {
                    "amount": float(amount),
                    "category": category.strip(),
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
                    st.dataframe(table_data, width='stretch', hide_index=True)
    except ValueError:
        st.warning("Database not configured. Set SUPABASE_URL and SUPABASE_KEY in .env to search.")
    except Exception as e:
        err = str(e)
        if _is_supabase_connection_error(err):
            st.warning(SUPABASE_ERROR_MSG)
        else:
            st.warning(f"Could not search: {err[:200]}" + ("…" if len(err) > 200 else ""))

tab1, tab2, tab3 = st.tabs(["Summary", "Add", "Search"])
with tab1:
    _render_summary()
with tab2:
    _render_add_transaction()
with tab3:
    _render_search()
