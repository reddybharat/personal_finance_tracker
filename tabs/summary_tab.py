"""Summary tab UI for the Personal Finance Tracker Streamlit app."""

from datetime import date

import streamlit as st

from database import get_supabase
from ui_common import SUPABASE_ERROR_MSG, is_supabase_connection_error


def render_summary() -> None:
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
        by_category: dict[str, float] = {}
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
            st.dataframe(table_data, width="stretch", hide_index=True)
    except ValueError:
        st.warning("Database not configured. Set SUPABASE_URL and SUPABASE_KEY in .env to see summary.")
    except Exception as e:
        err = str(e)
        if is_supabase_connection_error(err):
            st.warning(SUPABASE_ERROR_MSG)
        else:
            st.warning(f"Could not load summary: {err[:200]}" + ("…" if len(err) > 200 else ""))
