# main.py
from typing import Optional

import pandas as pd
import streamlit as st

from src.ingest import normalize_accounts, normalize_transactions
from ui.benchmarking import render_benchmarking_tab
from ui.dashboard import render_dashboard_tab
from ui.transactions import render_transactions_tab


st.set_page_config(layout="wide", page_title="Monarch+ Dashboard")

st.title("Monarch+ Dashboard")
st.caption("CFO-style control tower for your finances. Upload Monarch CSVs to get started.")

transactions_df: Optional[pd.DataFrame] = None
accounts_df: Optional[pd.DataFrame] = None

with st.container(border=True):
    st.markdown("### Upload Monarch CSVs")
    st.caption(
        "Upload both your Monarch Transactions CSV and Accounts CSV to initialize the dashboard. "
        "Both files are required for accurate balance sheet and cash flow calculations."
    )

    upload_col1, upload_col2 = st.columns(2)
    with upload_col1:
        transactions_file = st.file_uploader("Monarch Transactions CSV", type="csv", key="transactions")
    with upload_col2:
        accounts_file = st.file_uploader("Monarch Accounts CSV", type="csv", key="accounts")

    transactions_uploaded = transactions_file is not None
    accounts_uploaded = accounts_file is not None

    if transactions_uploaded and accounts_uploaded:
        try:
            transactions_df = normalize_transactions(transactions_file)
        except ValueError as exc:
            st.error(f"Transactions CSV error: {exc}")
        try:
            accounts_df = normalize_accounts(accounts_file)
        except ValueError as exc:
            st.error(f"Accounts CSV error: {exc}")
    else:
        if not transactions_uploaded:
            st.warning("Transactions CSV is required. Please add your Monarch Transactions export.")
        if not accounts_uploaded:
            st.warning("Accounts CSV is required. Please add your Monarch Accounts export.")

years = (
    sorted(transactions_df["year"].dropna().unique().tolist(), reverse=True)
    if transactions_df is not None and not transactions_df.empty
    else []
)
year_labels = ["ALL"] + [str(y) for y in years]

primary_tabs = st.tabs(
    [
        "🏠 Dashboard",
        "📄 Transactions",
        "📈 Benchmarking",
        "📊 Insights",
        "📈 Loan Tracker",
        "🧮 Loan Calculator",
        "💬 Assistant",
    ]
)

with primary_tabs[0]:
    st.subheader("Dashboard")
    year_tabs = st.tabs(year_labels)
    for tab, label in zip(year_tabs, year_labels):
        with tab:
            render_dashboard_tab(
                transactions_df,
                accounts_df,
                year_label=label,
            )

with primary_tabs[1]:
    st.subheader("Transactions")
    year_tabs = st.tabs(year_labels)
    for tab, label in zip(year_tabs, year_labels):
        with tab:
            render_transactions_tab(transactions_df, year_label=label)

with primary_tabs[2]:
    st.subheader("Benchmarking")
    render_benchmarking_tab(transactions_df, accounts_df, years=year_labels[1:])

with primary_tabs[3]:
    st.subheader("Insights")
    year_tabs = st.tabs(year_labels)
    for tab, label in zip(year_tabs, year_labels):
        with tab:
            st.info("Insights pipeline will arrive in a future task.")

with primary_tabs[4]:
    st.subheader("Loan Tracker")
    st.info("Coming soon — amortization tracking and payoff planning.")

with primary_tabs[5]:
    st.subheader("Loan Calculator")
    st.info("Calculator functionality will be wired in a future release.")

with primary_tabs[6]:
    st.subheader("Assistant")
    st.info("Assistant functionality will be integrated here.")
