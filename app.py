"""
Simple Streamlit UI to add transactions to the Personal Finance Tracker.
Light mode. Inserts into Supabase transactions table.
"""

import streamlit as st
from datetime import date

from database import get_supabase

st.set_page_config(page_title="Add Transaction", page_icon="💰", layout="centered")

st.title("Add Transaction")
st.caption("Amount in ₹ (INR)")

with st.form("transaction_form", clear_on_submit=True):
    amount = st.number_input(
        "Amount (₹)",
        min_value=0.00,
        step=100.00,
        format="%.2f",
        help="Enter amount in INR",
    )
    category = st.text_input("Category", placeholder="e.g. Food, Transport, Bills")
    transaction_date = st.date_input("Date", value=date.today())
    description = st.text_input("Description (optional)", placeholder="Short note")

    submitted = st.form_submit_button("Save transaction")

if submitted:
    if not category or not category.strip():
        st.error("Please enter a category.")
    elif amount <= 0:
        st.error("Amount must be greater than 0.")
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
            # Supabase/Cloudflare 525 SSL handshake or connection errors
            if "525" in err or "SSL handshake" in err or "JSON could not be generated" in err:
                st.error(
                    "**Could not reach Supabase.** This is usually:\n\n"
                    "• **Project paused** — Free-tier projects pause after inactivity. "
                    "Open your [Supabase Dashboard](https://supabase.com/dashboard), select the project, and click **Restore**.\n\n"
                    "• **Temporary outage** — Try again in a few minutes.\n\n"
                    "• **Network/firewall** — Check VPN or corporate network if the problem continues."
                )
            elif "42501" in err or "row-level security policy" in err.lower():
                st.error(
                    "**Row Level Security (RLS) is blocking this.** Add policies in Supabase:\n\n"
                    "1. Open [Supabase Dashboard](https://supabase.com/dashboard) → your project → **SQL Editor**.\n"
                    "2. Run the SQL from **`supabase_rls_policies.sql`** in this project (or create policies that allow INSERT/SELECT on `transactions` for your role)."
                )
            else:
                st.error(f"Error: {err}")
