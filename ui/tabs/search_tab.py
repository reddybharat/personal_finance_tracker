"""Search tab UI for the Personal Finance Tracker Streamlit app."""

from datetime import date

import streamlit as st

from database import get_supabase
from ui.common import SUPABASE_ERROR_MSG, is_supabase_connection_error
from ui.search.filters import render_search_filters
from ui.search.results import render_search_results


def render_search() -> None:
    st.subheader("Search transactions")
    # Pagination state: which page we're on (1-based). Reset when user clicks "Search".
    if "search_page" not in st.session_state:
        st.session_state.search_page = 1
    if "search_results_total" not in st.session_state:
        st.session_state.search_results_total = None  # total count from last query
    # Edit/delete: which transaction is being edited or pending delete (full row dict or id)
    if "editing_transaction" not in st.session_state:
        st.session_state.editing_transaction = None
    if "deleting_transaction" not in st.session_state:
        st.session_state.deleting_transaction = None
    try:
        start_date, end_date, category, page_size, sort_column, sort_desc_bool, search_clicked = render_search_filters()

        if start_date > end_date:
            st.error("From date must be on or before To date.")
        else:
            # Run query when: user clicked Search, or we already have a result set (e.g. after Prev/Next rerun)
            total_from_last = st.session_state.search_results_total
            run_query = search_clicked or (total_from_last is not None)

            if run_query:
                page = st.session_state.search_page
                offset_start = (page - 1) * page_size
                offset_end = offset_start + page_size - 1

                sort_col = st.session_state.search_sort_column
                sort_desc = st.session_state.search_sort_desc
                query = (
                    get_supabase()
                    .table("transactions")
                    .select("id, amount, category, transaction_date, description", count="exact")
                    .gte("transaction_date", start_date.isoformat())
                    .lte("transaction_date", end_date.isoformat())
                    .order(sort_col, desc=sort_desc)
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
                    render_search_results(rows, total_count, page_size)
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
