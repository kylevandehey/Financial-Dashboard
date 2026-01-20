# main.py
import streamlit as st
import pandas as pd

from src.config import APP_TITLE, NAV_ITEMS
from src.ingest import identify_csv_roles, normalize_transactions, normalize_accounts

from ui.dashboard import render_dashboard_tab
from ui.transactions import render_transactions_tab

# -----------------------------
# App setup
# -----------------------------
st.set_page_config(
    page_title=APP_TITLE,
    layout="wide",
)

# -----------------------------
# Top navigation
# -----------------------------
primary_tabs = st.tabs(NAV_ITEMS)
tabs_by_label = dict(zip(NAV_ITEMS, primary_tabs))

# -----------------------------
# File upload (minimal, no dead controls)
# -----------------------------
with st.sidebar:
    st.markdown("## Upload Monarch CSVs")
    uploaded_files = st.file_uploader(
        "Upload Transactions + Balances CSVs",
        type=["csv"],
        accept_multiple_files=True,
        help="Upload Monarch Money Transactions and Accounts CSV exports.",
    )

# -----------------------------
# Load + normalize data
# -----------------------------
if not uploaded_files:
    with tabs_by_label.get("Dashboard", primary_tabs[0]):
        st.info("Upload Monarch CSVs to begin.")
    st.stop()

tx_file, bal_file, diagnostics, error_message = identify_csv_roles(uploaded_files)

if error_message:
    with tabs_by_label.get("Dashboard", primary_tabs[0]):
        st.error(error_message)
    st.stop()

transactions_df = normalize_transactions(tx_file)
accounts_df = normalize_accounts(bal_file)

# -----------------------------
# Year tabs
# -----------------------------
if "date" in transactions_df.columns:
    years = (
        pd.to_datetime(transactions_df["date"], errors="coerce")
        .dt.year.dropna()
        .astype(int)
        .unique()
        .tolist()
    )
    years = sorted(years, reverse=True)
else:
    years = []

available_years = ["ALL YEARS"] + [str(y) for y in years]

# -----------------------------
# Dashboard tab
# -----------------------------
with tabs_by_label.get("Dashboard", primary_tabs[0]):
    st.subheader("Dashboard (Core Rebuild)")
    render_dashboard_tab(
        transactions=transactions_df,
        available_years=available_years,
    )

# -----------------------------
# Transactions tab
# -----------------------------
with tabs_by_label.get(
    "Transactions",
    primary_tabs[1] if len(primary_tabs) > 1 else primary_tabs[0],
):
    st.subheader("Transactions (Core Rebuild)")
    render_transactions_tab(
        transactions_df,
        accounts_df,
        year_label="ALL YEARS",
        selected_period="ALL YEARS",
        date_range=None,
    )

# -----------------------------
# Disabled tabs (future PRs)
# -----------------------------
for label, tab in tabs_by_label.items():
    if label in {"Dashboard", "Transactions"}:
        continue
    with tab:
        st.subheader(label)
        st.info(
            "Temporarily disabled during core rebuild. "
            "Will be re-enabled after canonical metrics + charts are finalized."
        )







