# main.py
from typing import Optional

import pandas as pd
import streamlit as st

from src.config import ALL_YEARS_LABEL, APP_TITLE, DASHBOARD_TITLE, NAV_ITEMS
from ui.benchmarking import render_benchmarking_tab
from ui.compare import render_compare_tab
from ui.dashboard import render_dashboard_tab
from ui.insights import render_insights_tab
from ui.loan_tracker import render_loan_tracker_tab
from ui.transactions import render_transactions_tab


st.set_page_config(layout="wide", page_title=APP_TITLE)

transactions_df: Optional[pd.DataFrame] = None
accounts_df: Optional[pd.DataFrame] = None

active_transactions = st.session_state.get("transactions_df", transactions_df)
active_accounts = st.session_state.get("accounts_df", accounts_df)
years = (
    sorted(active_transactions["year"].dropna().unique().tolist(), reverse=True)
    if active_transactions is not None and not active_transactions.empty and "year" in active_transactions.columns
    else []
)
year_labels = [ALL_YEARS_LABEL] + [str(y) for y in years]

primary_tabs = st.tabs(NAV_ITEMS)
tabs_by_label = dict(zip(NAV_ITEMS, primary_tabs))

with tabs_by_label["Dashboard"]:
    st.subheader(DASHBOARD_TITLE)
    year_tabs = st.tabs(year_labels)
    for tab, label in zip(year_tabs, year_labels):
        with tab:
            render_dashboard_tab(
                active_transactions,
                active_accounts,
                year_label=label,
            )

with tabs_by_label["Transactions"]:
    st.subheader("Transactions")
    year_tabs = st.tabs(year_labels)
    for tab, label in zip(year_tabs, year_labels):
        with tab:
            render_transactions_tab(active_transactions, active_accounts, year_label=label)

with tabs_by_label["Compare"]:
    st.subheader("Compare")
    year_tabs = st.tabs(year_labels)
    for tab, label in zip(year_tabs, year_labels):
        with tab:
            render_compare_tab(active_transactions, active_accounts, year_label=label)

with tabs_by_label["Insights"]:
    st.subheader(f"{NAV_ITEMS[3]} (Financial IQ layer)")
    year_tabs = st.tabs(year_labels)
    for tab, label in zip(year_tabs, year_labels):
        with tab:
            render_insights_tab(active_transactions, active_accounts, year_label=label)

with tabs_by_label["Loan Tracker"]:
    st.subheader("Loan Tracker")
    year_tabs = st.tabs(year_labels)
    for tab, label in zip(year_tabs, year_labels):
        with tab:
            render_loan_tracker_tab(active_transactions, active_accounts, year_label=label)

with tabs_by_label["Tools"]:
    st.subheader("Tools")
    year_tabs = st.tabs(year_labels)
    for tab, label in zip(year_tabs, year_labels):
        with tab:
            render_benchmarking_tab(active_transactions, active_accounts, year_label=label)
            st.info("Additional tools and calculators will be wired in a future release.")

with tabs_by_label["Assistance"]:
    st.subheader("Assistance")
    year_tabs = st.tabs(year_labels)
    for tab, label in zip(year_tabs, year_labels):
        with tab:
            st.info("Assistant functionality will be integrated here.")
