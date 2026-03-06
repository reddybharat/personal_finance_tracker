"""Add-transaction tab UI for the Personal Finance Tracker Streamlit app."""

from datetime import date

import streamlit as st

from constants import CATEGORIES
from database import get_supabase
from validations import validate_amount, validate_category, validate_transaction_date
from ui.add.import_csv_section import render_import_csv_section
from ui.common import SUPABASE_ERROR_MSG, is_supabase_connection_error

REQUIRED_LABEL = "<span style='color: red'>*</span>"


def render_add_transaction() -> None:
    st.subheader("Add Transaction")
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
        errors: list[str] = []
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
                if is_supabase_connection_error(err):
                    st.error(SUPABASE_ERROR_MSG)
                elif "42501" in err or "row-level security policy" in err.lower():
                    st.error(
                        "**Row Level Security (RLS) is blocking this.** Add policies in Supabase:\n\n"
                        "1. Open [Supabase Dashboard](https://supabase.com/dashboard) → your project → **SQL Editor**.\n"
                        "2. Run the SQL from **`supabase_rls_policies.sql`** in this project (or create policies that allow INSERT/SELECT on `transactions` for your role)."
                    )
                else:
                    st.error(f"Error: {err}")

    # Import from CSV (template + file upload + import)
    try:
        render_import_csv_section()
    except ValueError:
        pass  # DB not configured; expander still visible but import will fail
