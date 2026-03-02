"""Search tab UI with pagination for the Personal Finance Tracker Streamlit app."""

from datetime import date

import streamlit as st

from constants import CATEGORIES
from database import get_supabase
from ui.common import SUPABASE_ERROR_MSG, is_supabase_connection_error


def _show_pagination_footer(total_count: int, page_size: int, current_page: int) -> None:
    """Render Prev/Next below the results; on click updates session state and reruns."""
    total_pages = max(1, (total_count + page_size - 1) // page_size)
    col_prev, _, col_next = st.columns([1, 2, 1])
    with col_prev:
        prev_clicked = st.button("← Prev", disabled=(current_page <= 1), key="search_prev")
    with col_next:
        next_clicked = st.button("Next →", disabled=(current_page >= total_pages), key="search_next")
    if prev_clicked and current_page > 1:
        st.session_state.search_page = current_page - 1
        st.rerun()
    if next_clicked and current_page < total_pages:
        st.session_state.search_page = current_page + 1
        st.rerun()


def render_search() -> None:
    st.subheader("Search transactions")
    # Pagination state: which page we're on (1-based). Reset when user clicks "Search".
    if "search_page" not in st.session_state:
        st.session_state.search_page = 1
    if "search_results_total" not in st.session_state:
        st.session_state.search_results_total = None  # total count from last query

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
            page_size = st.number_input("Per page", min_value=5, max_value=50, value=10, step=5)

        if start_date > end_date:
            st.error("From date must be on or before To date.")
        else:
            search_clicked = st.button("Search")
            if search_clicked:
                st.session_state.search_page = 1

            # Run query when: user clicked Search, or we already have a result set (e.g. after Prev/Next rerun)
            total_from_last = st.session_state.search_results_total
            run_query = search_clicked or (total_from_last is not None)

            if run_query:
                page = st.session_state.search_page
                offset_start = (page - 1) * page_size
                offset_end = offset_start + page_size - 1

                query = (
                    get_supabase()
                    .table("transactions")
                    .select("id, amount, category, transaction_date, description", count="exact")
                    .gte("transaction_date", start_date.isoformat())
                    .lte("transaction_date", end_date.isoformat())
                    .order("transaction_date", desc=True)
                    .range(offset_start, offset_end)
                )
                if category and category != "All":
                    query = query.eq("category", category)
                response = query.execute()
                rows = response.data or []
                total_count = getattr(response, "count", None)
                if total_count is None and rows is not None:
                    total_count = len(rows)
                st.session_state.search_results_total = total_count

                if total_count is not None and total_count == 0:
                    st.info("No transactions found for the selected filters.")
                    st.session_state.search_results_total = 0
                elif not rows:
                    st.info("No transactions on this page.")
                else:
                    # Clamp page if we're past last page (e.g. user changed "Per page" then clicked Next)
                    total_pages = max(1, (total_count + page_size - 1) // page_size)
                    if page > total_pages:
                        st.session_state.search_page = total_pages
                        st.rerun()

                    start_one = offset_start + 1
                    end_one = min(offset_start + len(rows), total_count)
                    st.caption(f"Showing **{start_one}–{end_one}** of **{total_count}** transactions")
                    total_amt = sum(float(r.get("amount", 0)) for r in rows)
                    if len(rows) < total_count:
                        st.caption(f"Page total: ₹{total_amt:,.2f}")
                    else:
                        st.caption(f"Total: ₹{total_amt:,.2f}")
                    table_data = [
                        {
                            "Date": r.get("transaction_date", ""),
                            "Amount (₹)": f"₹{float(r.get('amount', 0)):,.2f}",
                            "Category": r.get("category", ""),
                            "Description": r.get("description") or "—",
                        }
                        for r in rows
                    ]
                    st.dataframe(table_data, width="stretch", hide_index=True)

                    # Render Prev/Next below the table when we have results
                    if total_count and total_count > 0:
                        _show_pagination_footer(total_count, page_size, st.session_state.search_page)
            elif total_from_last is not None and total_from_last == 0:
                st.info("No transactions found for the selected filters.")
    except ValueError:
        st.warning("Database not configured. Set SUPABASE_URL and SUPABASE_KEY in .env to search.")
    except Exception as e:
        err = str(e)
        if is_supabase_connection_error(err):
            st.warning(SUPABASE_ERROR_MSG)
        else:
            st.warning(f"Could not search: {err[:200]}" + ("…" if len(err) > 200 else ""))
