# main.py
from typing import Optional

import pandas as pd
import streamlit as st

from src.config import ALL_YEARS_LABEL, APP_SUBTITLE, APP_TITLE, DASHBOARD_TITLE, NAV_ITEMS
from src.filters import get_filtered_transactions
from ui.benchmarking import render_benchmarking_tab
from ui.dashboard import render_dashboard_tab
from ui.transaction_filters import render_transaction_filters
from ui.transactions import render_transactions_tab


st.set_page_config(layout="wide", page_title=APP_TITLE)

st.title(APP_TITLE)
st.caption(APP_SUBTITLE)

transactions_df: Optional[pd.DataFrame] = st.session_state.get("transactions_df")
accounts_df: Optional[pd.DataFrame] = st.session_state.get("accounts_df")
filtered_transactions: Optional[pd.DataFrame] = None

years = (
    sorted(transactions_df["year"].dropna().unique().tolist(), reverse=True)
    if transactions_df is not None and not transactions_df.empty
    else []
)
year_labels = [ALL_YEARS_LABEL] + [str(y) for y in years]

primary_tabs = st.tabs(NAV_ITEMS)
tabs_by_label = dict(zip(NAV_ITEMS, primary_tabs))

with tabs_by_label["Dashboard"]:
    st.subheader(DASHBOARD_TITLE)
    render_transaction_filters()
    filtered_transactions = get_filtered_transactions(transactions_df)
    year_tabs = st.tabs(year_labels)
    for tab, label in zip(year_tabs, year_labels):
        with tab:
            render_dashboard_tab(
                filtered_transactions,
                accounts_df,
                year_label=label,
            )

with tabs_by_label["Transactions"]:
    st.subheader("Transactions")
    year_tabs = st.tabs(year_labels)
    for tab, label in zip(year_tabs, year_labels):
        with tab:
            render_transactions_tab(filtered_transactions, year_label=label)

with tabs_by_label["Compare"]:
    st.subheader("Compare")
    year_tabs = st.tabs(year_labels)
    for tab, label in zip(year_tabs, year_labels):
        with tab:
            st.info(
                "This tab will compare transactions and balance sheet metrics across calendar years.\n"
                "Planned features include:\n"
                "- Year-by-year charts\n"
                "- Delta $ vs prior year\n"
                "- Delta % vs prior year\n"
                "- Income, expenses, assets, liabilities, and net worth comparisons."
            )

with tabs_by_label["Insights"]:
    st.subheader(f"{NAV_ITEMS[3]} (Financial IQ layer)")
    year_tabs = st.tabs(year_labels)
    for tab, label in zip(year_tabs, year_labels):
        with tab:
            st.info("Insights pipeline will arrive in a future task.")

with tabs_by_label["Loan Tracker"]:
    st.subheader("Loan Tracker")
    year_tabs = st.tabs(year_labels)
    for tab, label in zip(year_tabs, year_labels):
        with tab:
            st.info("Coming soon — amortization tracking and payoff planning.")

with tabs_by_label["Tools"]:
    st.subheader("Tools")
    year_tabs = st.tabs(year_labels)
    for tab, label in zip(year_tabs, year_labels):
        with tab:
            render_benchmarking_tab(filtered_transactions, accounts_df, year_label=label)
            st.info("Additional tools and calculators will be wired in a future release.")

with tabs_by_label["Assistance"]:
    st.subheader("Assistance")
    year_tabs = st.tabs(year_labels)
    for tab, label in zip(year_tabs, year_labels):
        with tab:
            st.info("Assistant functionality will be integrated here.")
