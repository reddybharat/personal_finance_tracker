"""Search tab UI for the Personal Finance Tracker Streamlit app."""

from datetime import date

import streamlit as st

from database import execute_query
from ui.common import DATABASE_ERROR_MSG, is_db_connection_error
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

                sort_col = st.session_state.search_sort_column
                sort_desc = st.session_state.search_sort_desc
                # Safe: sort_col is one of ("transaction_date", "amount") from filters
                order_dir = "DESC" if sort_desc else "ASC"
                order_clause = f"ORDER BY {sort_col} {order_dir}"

                cols = "id, amount, category, transaction_date, description"
                if category and category != "All":
                    count_sql = """
                        SELECT COUNT(*) AS n FROM transactions
                        WHERE transaction_date >= %s AND transaction_date <= %s AND category = %s
                    """
                    count_params: tuple = (start_date.isoformat(), end_date.isoformat(), category)
                    data_sql = f"""
                        SELECT {cols} FROM transactions
                        WHERE transaction_date >= %s AND transaction_date <= %s AND category = %s
                        {order_clause}
                        LIMIT %s OFFSET %s
                    """
                    data_params = (start_date.isoformat(), end_date.isoformat(), category, page_size, offset_start)
                else:
                    count_sql = """
                        SELECT COUNT(*) AS n FROM transactions
                        WHERE transaction_date >= %s AND transaction_date <= %s
                    """
                    count_params = (start_date.isoformat(), end_date.isoformat())
                    data_sql = f"""
                        SELECT {cols} FROM transactions
                        WHERE transaction_date >= %s AND transaction_date <= %s
                        {order_clause}
                        LIMIT %s OFFSET %s
                    """
                    data_params = (start_date.isoformat(), end_date.isoformat(), page_size, offset_start)

                count_rows = execute_query(count_sql, count_params)
                total_count = int(count_rows[0]["n"]) if count_rows else 0
                st.session_state.search_results_total = total_count

                rows = execute_query(data_sql, data_params)

                if total_count == 0:
                    st.info("No transactions found for the selected filters.")
                    st.session_state.search_results_total = 0
                elif not rows:
                    st.info("No transactions on this page.")
                else:
                    render_search_results(rows, total_count, page_size)
            elif total_from_last is not None and total_from_last == 0:
                st.info("No transactions found for the selected filters.")
    except ValueError:
        st.warning("Database not configured. Set DATABASE_URL in .env to search.")
    except Exception as e:
        err = str(e)
        if is_db_connection_error(err):
            st.warning(DATABASE_ERROR_MSG)
        else:
            st.warning(f"Could not search: {err[:200]}" + ("…" if len(err) > 200 else ""))
