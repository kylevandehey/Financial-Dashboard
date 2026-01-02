# main.py
from typing import Optional

import pandas as pd
import streamlit as st

from src.config import APP_SUBTITLE, APP_TITLE, DASHBOARD_TITLE, NAV_ITEMS
from src.ingest import identify_csv_roles, normalize_accounts, normalize_transactions
from ui.benchmarking import render_benchmarking_tab
from ui.dashboard import render_dashboard_tab
from ui.transactions import render_transactions_tab


st.set_page_config(layout="wide", page_title=APP_TITLE)

st.title(APP_TITLE)
st.caption(APP_SUBTITLE)

transactions_df: Optional[pd.DataFrame] = None
accounts_df: Optional[pd.DataFrame] = None

with st.container(border=True):
    st.markdown("### Upload Monarch CSVs")
    st.caption(
        "Upload both your Monarch Transactions CSV and Accounts/Balances CSV to initialize the dashboard. "
        "Both files are required for accurate balance sheet and cash flow calculations."
    )

    uploaded_files = st.file_uploader(
        "Upload Monarch CSVs",
        accept_multiple_files=True,
        type=["csv"],
        key="monarch_csvs",
    )

    if not uploaded_files:
        st.warning("Please upload both Transactions and Balances CSVs.")
    elif len(uploaded_files) < 2:
        st.warning("Please upload both Transactions and Balances CSVs.")
    else:
        transactions_file, accounts_file, _diagnostics, error_message = identify_csv_roles(uploaded_files)
        if error_message:
            st.error(error_message)
        else:
            try:
                transactions_df = normalize_transactions(transactions_file)
            except ValueError as exc:
                st.error(f"Transactions CSV error: {exc}")
            try:
                accounts_df = normalize_accounts(accounts_file)
            except ValueError as exc:
                st.error(f"Accounts CSV error: {exc}")

years = (
    sorted(transactions_df["year"].dropna().unique().tolist(), reverse=True)
    if transactions_df is not None and not transactions_df.empty
    else []
)
year_labels = ["ALL"] + [str(y) for y in years]

primary_tabs = st.tabs(NAV_ITEMS)

with primary_tabs[0]:
    st.subheader(DASHBOARD_TITLE)
    year_tabs = st.tabs(year_labels)
    for tab, label in zip(year_tabs, year_labels):
        with tab:
            render_dashboard_tab(
                transactions_df,
                accounts_df,
                year_label=label,
            )

with primary_tabs[1]:
    st.subheader(NAV_ITEMS[1])
    year_tabs = st.tabs(year_labels)
    for tab, label in zip(year_tabs, year_labels):
        with tab:
            render_transactions_tab(transactions_df, year_label=label)

with primary_tabs[2]:
    st.subheader(f"{NAV_ITEMS[2]} (Financial IQ layer)")
    year_tabs = st.tabs(year_labels)
    for tab, label in zip(year_tabs, year_labels):
        with tab:
            st.info("Insights pipeline will arrive in a future task.")

with primary_tabs[3]:
    st.subheader(NAV_ITEMS[3])
    year_tabs = st.tabs(year_labels)
    for tab, label in zip(year_tabs, year_labels):
        with tab:
            st.info("Coming soon — amortization tracking and payoff planning.")

with primary_tabs[4]:
    st.subheader(NAV_ITEMS[4])
    year_tabs = st.tabs(year_labels)
    for tab, label in zip(year_tabs, year_labels):
        with tab:
            render_benchmarking_tab(transactions_df, accounts_df, year_label=label)
            st.info("Additional tools and calculators will be wired in a future release.")

with primary_tabs[5]:
    st.subheader(NAV_ITEMS[5])
    year_tabs = st.tabs(year_labels)
    for tab, label in zip(year_tabs, year_labels):
        with tab:
            st.info("Assistant functionality will be integrated here.")
