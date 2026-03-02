"""
Simple Streamlit UI to add transactions to the Personal Finance Tracker.
Light mode. Inserts into Supabase transactions table.
Tabs: Summary, Add Transaction, Search.
"""

import streamlit as st

from tabs.summary_tab import render_summary
from tabs.add_tab import render_add_transaction
from tabs.search_tab import render_search

st.set_page_config(page_title="Personal Finance Tracker", page_icon="💰", layout="centered")

tab1, tab2, tab3 = st.tabs(["Summary", "Add", "Search"])
with tab1:
    render_summary()
with tab2:
    render_add_transaction()
with tab3:
    render_search()
