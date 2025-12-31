# main.py
from datetime import datetime

import pandas as pd
import streamlit as st

from src.date_filters import compute_date_range, filter_dataframe_by_date
from src.ingest import normalize_accounts, normalize_transactions
from ui.dashboard import render_dashboard_tab
from ui.transactions_table import render_transactions_table


st.set_page_config(layout="wide", page_title="Monarch+ Dashboard")

st.title("Monarch+ Dashboard")
st.caption("CFO-style control tower for your finances. Upload Monarch CSVs to get started.")

transactions_df: pd.DataFrame | None = None
accounts_df: pd.DataFrame | None = None

upload_col1, upload_col2 = st.columns(2)
with upload_col1:
    transactions_file = st.file_uploader("Upload Transactions CSV", type="csv", key="transactions")
with upload_col2:
    accounts_file = st.file_uploader("Upload Accounts CSV", type="csv", key="accounts")

if transactions_file:
    try:
        transactions_df = normalize_transactions(transactions_file)
    except ValueError as exc:
        st.error(f"Transactions CSV error: {exc}")

if accounts_file:
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

primary_tabs = st.tabs(
    ["🏠 Dashboard", "📄 Transactions", "📊 Insights", "📈 Loan Tracker", "🧮 Loan Calculator", "💬 Assistant"]
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
            if transactions_df is None or transactions_df.empty:
                st.info("Upload a Transactions CSV to explore table views.")
                continue
            if label == "ALL":
                min_date = pd.to_datetime(transactions_df["date"]).min().date()
                max_date = pd.to_datetime(transactions_df["date"]).max().date()
                start_date, end_date = min_date, max_date
            else:
                start_date, end_date = compute_date_range("full_year", year=label)
            filtered_tx = filter_dataframe_by_date(
                transactions_df,
                (start_date, end_date),
                date_column="date",
            )
            render_transactions_table(filtered_tx)

with primary_tabs[2]:
    st.subheader("Insights")
    year_tabs = st.tabs(year_labels)
    for tab, label in zip(year_tabs, year_labels):
        with tab:
            st.info("Insights pipeline will arrive in a future task.")

with primary_tabs[3]:
    st.subheader("Loan Tracker")
    st.info("Coming soon — amortization tracking and payoff planning.")

with primary_tabs[4]:
    st.subheader("Loan Calculator")
    st.info("Calculator functionality will be wired in a future release.")

with primary_tabs[5]:
    st.subheader("Assistant")
    st.info("Assistant functionality will be integrated here.")






