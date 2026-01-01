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

st.markdown(
    "**Upload both your Monarch Transactions CSV and Accounts CSV to initialize the dashboard. "
    "Both files are required for accurate balance sheet and cash flow calculations.**"
)
with st.container(border=True):
    upload_col1, upload_col2 = st.columns(2)
    with upload_col1:
        transactions_file = st.file_uploader("Transactions CSV", type="csv", key="transactions")
    with upload_col2:
        accounts_file = st.file_uploader("Accounts CSV", type="csv", key="accounts")

    if transactions_file:
        try:
            transactions_df = normalize_transactions(transactions_file)
        except ValueError as exc:
            st.error(f"Transactions CSV error: {exc}")

    if accounts_file:
        try:
            accounts_df = normalize_accounts(accounts_file)
        except ValueError as exc:
            missing_type = "type" in str(exc).lower()
            if missing_type:
                st.error(
                    "Accounts CSV error: Missing required column 'type'. "
                    "Monarch typically labels this as the account category (e.g., Asset, Liability, Credit). "
                    "Please include or map the column so ingestion can normalize accounts."
                )
            else:
                st.error(f"Accounts CSV error: {exc}")

    if transactions_df is None and accounts_df is not None:
        st.warning("Transactions CSV is required. Please add your Monarch Transactions export.")
    if accounts_df is None and transactions_df is not None:
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

