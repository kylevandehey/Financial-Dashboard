import streamlit as st
import pandas as pd

from ui.dashboard import render_dashboard_tab
from src.data_loader import load_transactions_and_balances


# -----------------------------
# App setup
# -----------------------------

st.set_page_config(
    page_title="Financial Dashboard",
    layout="wide",
)


# -----------------------------
# Sidebar: Control Panel (CLEAN)
# -----------------------------

with st.sidebar:
    st.markdown("## Control Panel")

    if st.button("Reset Dashboard"):
        st.session_state.clear()
        st.rerun()

    st.markdown("### Upload Monarch CSVs (Transactions + Balances)")
    uploaded_files = st.file_uploader(
        "Drag and drop files here",
        type=["csv"],
        accept_multiple_files=True,
        help="Upload Monarch Money Transactions and Balances CSV exports.",
    )

    st.markdown("### Period Selection")
    period = st.radio(
        "Period",
        ["Q1", "Q2", "Q3", "Q4", "ALL YEARS"],
        index=4,
    )

    st.markdown("### Status")
    status_placeholder = st.empty()


# -----------------------------
# Data loading
# -----------------------------

transactions_df, balances_df = load_transactions_and_balances(uploaded_files)

if transactions_df is None or transactions_df.empty:
    status_placeholder.info("Upload Monarch CSVs to begin.")
    st.stop()

status_placeholder.success("CSV upload processed. Dashboard refreshed.")


# -----------------------------
# Available years (tabs)
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
# Main content
# -----------------------------

render_dashboard_tab(
    transactions=transactions_df,
    available_years=available_years,
)




