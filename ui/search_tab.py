"""Search tab UI with pagination and edit/delete for the Personal Finance Tracker Streamlit app."""

from datetime import date

import streamlit as st

from constants import CATEGORIES
from database import get_supabase
from ui.common import SUPABASE_ERROR_MSG, is_supabase_connection_error
from validations import validate_amount, validate_category, validate_transaction_date


def _show_pagination_footer(total_count: int, page_size: int, current_page: int) -> None:
    """Render Prev/Next below the results; on click updates session state and reruns."""
    total_pages = max(1, (total_count + page_size - 1) // page_size)
    col_prev, col_next, _ = st.columns([1, 1, 2])
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


def _render_edit_form(row: dict) -> None:
    """Show edit form for one transaction; on submit updates via Supabase and clears state."""
    row_id = row.get("id")
    if not row_id:
        return
    with st.form(key="edit_txn_form"):
        st.caption("Edit transaction")
        amount = st.number_input(
            "Amount (₹)",
            min_value=0.01,
            value=float(row.get("amount", 0)),
            step=0.01,
            format="%.2f",
            key="edit_amount",
        )
        category = st.selectbox(
            "Category",
            options=CATEGORIES,
            index=CATEGORIES.index(row["category"]) if row.get("category") in CATEGORIES else 0,
            key="edit_category",
        )
        txn_date = st.date_input(
            "Date",
            value=date.fromisoformat(row["transaction_date"]) if isinstance(row.get("transaction_date"), str) else date.today(),
            key="edit_date",
        )
        description = st.text_input(
            "Description (optional)",
            value=row.get("description") or "",
            key="edit_desc",
        )
        col1, col2, _ = st.columns([1, 1, 2])
        with col1:
            submitted = st.form_submit_button("Save")
        with col2:
            cancel = st.form_submit_button("Cancel")
        if cancel:
            if "editing_transaction" in st.session_state:
                del st.session_state.editing_transaction
            st.rerun()
        if submitted:
            try:
                validate_amount(amount)
                validate_category(category)
                validate_transaction_date(txn_date)
            except ValueError as e:
                st.error(str(e))
                return
            try:
                get_supabase().table("transactions").update({
                    "amount": amount,
                    "category": category.strip(),
                    "transaction_date": txn_date.isoformat(),
                    "description": (description or "").strip() or None,
                }).eq("id", row_id).execute()
                if "editing_transaction" in st.session_state:
                    del st.session_state.editing_transaction
                st.success("Transaction updated.")
                st.rerun()
            except Exception as e:
                st.error(f"Update failed: {str(e)[:200]}")


def _render_delete_confirm(row: dict) -> None:
    """Show delete confirmation; on confirm deletes via Supabase and clears state."""
    row_id = row.get("id")
    if not row_id:
        return
    amt = row.get("amount", 0)
    cat = row.get("category", "")
    st.warning(f"Delete this transaction? **₹{float(amt):,.2f}** — {cat}")
    col1, col2, _ = st.columns([1, 1, 2])
    with col1:
        if st.button("Confirm delete", type="primary", key="confirm_del"):
            try:
                get_supabase().table("transactions").delete().eq("id", row_id).execute()
                if "deleting_transaction" in st.session_state:
                    del st.session_state.deleting_transaction
                st.success("Transaction deleted.")
                st.rerun()
            except Exception as e:
                st.error(f"Delete failed: {str(e)[:200]}")
    with col2:
        if st.button("Cancel", key="cancel_del"):
            if "deleting_transaction" in st.session_state:
                del st.session_state.deleting_transaction
            st.rerun()


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
    # Sort: column and direction for search results
    if "search_sort_column" not in st.session_state:
        st.session_state.search_sort_column = "transaction_date"
    if "search_sort_desc" not in st.session_state:
        st.session_state.search_sort_desc = True

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

        # Sort options: label -> Supabase column name
        sort_options = [
            ("Date", "transaction_date"),
            ("Amount", "amount"),
        ]
        sort_labels = [opt[0] for opt in sort_options]
        # Resolve current label from session state column
        current_col = st.session_state.search_sort_column
        current_index = next(
            (i for i, (_, col) in enumerate(sort_options) if col == current_col),
            0,
        )
        col31, col32 = st.columns([1, 1])
        with col31:
            sort_label = st.selectbox(
                "Sort by",
                options=sort_labels,
                index=current_index,
                key="search_sort_by",
            )
            sort_column = next(col for label, col in sort_options if label == sort_label)
        with col32:
            sort_desc = st.radio(
                "Order",
                options=["Descending", "Ascending"],
                index=0 if st.session_state.search_sort_desc else 1,
                horizontal=True,
                key="search_sort_order",
            )
            sort_desc_bool = sort_desc == "Descending"
        # Persist sort in session state for the query
        st.session_state.search_sort_column = sort_column
        st.session_state.search_sort_desc = sort_desc_bool

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
                    total_pages = max(1, (total_count + page_size - 1) // page_size)
                    if page > total_pages:
                        st.session_state.search_page = total_pages
                        st.rerun()

                    # If we're editing or deleting, show the form/confirm at top
                    if st.session_state.editing_transaction:
                        _render_edit_form(st.session_state.editing_transaction)
                        st.divider()
                    if st.session_state.deleting_transaction:
                        _render_delete_confirm(st.session_state.deleting_transaction)
                        st.divider()

                    start_one = offset_start + 1
                    end_one = min(offset_start + len(rows), total_count)
                    st.caption(f"Showing **{start_one}–{end_one}** of **{total_count}** transactions")

                    header_cols = st.columns([1, 1, 1, 2, 2])
                    headers = ["Date", "Amount", "Category", "Description", ""]
                    for c, h in zip(header_cols, headers):
                        c.markdown(f"**{h}**")

                    # One row per transaction with Edit / Delete buttons in one Actions column
                    for r in rows:
                        row_id = r.get("id")
                        if not row_id:
                            continue
                        cols = st.columns([1, 1, 1, 2, 2])
                        with cols[0]:
                            st.text(r.get("transaction_date", ""))
                        with cols[1]:
                            st.text(f"₹{float(r.get('amount', 0)):,.2f}")
                        with cols[2]:
                            st.text(r.get("category", ""))
                        with cols[3]:
                            st.text((r.get("description") or "—")[:40] + ("…" if (r.get("description") or "") and len(r.get("description", "") or "") > 40 else ""))
                        with cols[4]:
                            b1, b2 = st.columns(2)
                            with b1:
                                edit_clicked = st.button("Edit", key=f"edit_{row_id}")
                                if edit_clicked:
                                    st.session_state.editing_transaction = r
                                    st.session_state.deleting_transaction = None
                                    st.rerun()
                            with b2:
                                delete_clicked = st.button("Delete", key=f"del_{row_id}")
                                if delete_clicked:
                                    st.session_state.deleting_transaction = r
                                    st.session_state.editing_transaction = None
                                    st.rerun()

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
