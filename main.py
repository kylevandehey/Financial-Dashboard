# main.py
import streamlit as st
import pandas as pd

from src.config import APP_TITLE, NAV_ITEMS
from src.data_loader import load_transactions_and_balances

from ui.dashboard import render_dashboard_tab
from ui.transactions import render_transactions_tab


# -------------------------------------------------
# App config (ONE TIME)
# -------------------------------------------------

st.set_page_config(
    page_title=APP_TITLE,
    layout="wide",
)


# -------------------------------------------------
# File ingestion (top-level, canonical)
# -------------------------------------------------

st.sidebar.markdown("## Upload Monarch CSVs")
uploaded_files = st.sidebar.file_uploader(
    "Transactions + Balances CSVs",
    type=["csv"],
    accept_multiple_files=True,
    help="Upload Monarch Money Transactions and Balances exports.",
)

transactions_df, balances_df = load_transactions_and_balances(uploaded_files)

if transactions_df is None or transactions_df.empty:
    st.sidebar.info("Upload Monarch CSVs to begin.")
    st.stop()


# -------------------------------------------------
# Derive available years (for tabs)
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
# Dashboard tab (canonical cash flow + charts)
# -------------------------------------------------

with tabs_by_label["Dashboard"]:
    render_dashboard_tab(
        transactions=transactions_df,
        available_years=available_years,
    )


# -------------------------------------------------
# Transactions tab (table only)
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
# Disabled tabs (intentional)
# -------------------------------------------------

for label, tab in tabs_by_label.items():
    if label in {"Dashboard", "Transactions"}:
        continue
    with tab:
        st.subheader(label)
        st.info(
            "Temporarily disabled during core rebuild. "
            "Will be re-enabled after baseline metrics and charts are finalized."
        )





