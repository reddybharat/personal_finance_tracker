"""
Simple Streamlit UI to add transactions to the Personal Finance Tracker.
Light mode. Inserts into Supabase transactions table.
Tabs: Summary, Add Transaction, Search, Chat.
"""

import streamlit as st

from logger import get_logger  # noqa: F401 — triggers logging config on app start

from ui.tabs.summary_tab import render_summary
from ui.tabs.add_txn_tab import render_add_transaction
from ui.tabs.search_tab import render_search
from ui.tabs.chat_tab import render_chat

st.set_page_config(page_title="Personal Finance Tracker", page_icon="💰", layout="centered")

tab1, tab2, tab3, tab4 = st.tabs(["Summary", "Add", "Search", "Chat"])
with tab1:
    render_summary()
with tab2:
    render_add_transaction()
with tab3:
    render_search()
with tab4:
    render_chat()
