# main.py
import streamlit as st
import pandas as pd

from src.config import APP_TITLE, NAV_ITEMS
from src.ingest import load_transactions_and_balances
from ui.dashboard import render_dashboard_tab
from ui.transactions import render_transactions_tab

# -------------------------------------------------
# App configuration
# -------------------------------------------------

st.set_page_config(
    page_title=APP_TITLE,
    layout="wide",
)

# -------------------------------------------------
# File upload (top-level, no sidebar clutter)
# -------------------------------------------------

st.markdown("## Upload Monarch CSVs (Transactions + Balances)")

uploaded_files = st.file_uploader(
    "Drag and drop Monarch Money CSV exports here",
    type=["csv"],
    accept_multiple_files=True,
    help="Upload both Transactions and Balances CSVs from Monarch Money.",
)

transactions_df, balances_df = load_transactions_and_balances(uploaded_files)

if transactions_df is None or transactions_df.empty:
    st.info("Upload Monarch CSVs to begin.")
    st.stop()

st.success("CSV upload processed. Dashboard refreshed.")

# -------------------------------------------------
# Available years (derived once, canonical)
# -------------------------------------------------

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

# -------------------------------------------------
# Top navigation
# -------------------------------------------------

primary_tabs = st.tabs(NAV_ITEMS)
tabs_by_label = dict(zip(NAV_ITEMS, primary_tabs))

# -------------------------------------------------
# Dashboard tab (canonical)
# -------------------------------------------------

with tabs_by_label.get("Dashboard", primary_tabs[0]):
    render_dashboard_tab(
        transactions=transactions_df,
        available_years=available_years,
    )

# -------------------------------------------------
# Transactions tab (table-only)
# -------------------------------------------------

with tabs_by_label.get(
    "Transactions",
    primary_tabs[1] if len(primary_tabs) > 1 else primary_tabs[0],
):
    render_transactions_tab(
        transactions_df,
        balances_df,
        year_label="ALL YEARS",
    )

# -------------------------------------------------
# Disable other tabs for now (safe guardrail)
# -------------------------------------------------

for label, tab in tabs_by_label.items():
    if label in {"Dashboard", "Transactions"}:
        continue
    with tab:
        st.subheader(label)
        st.info(
            "Temporarily disabled during core rebuild. "
            "Will be re-enabled after canonical metrics and charts are finalized."
        )






