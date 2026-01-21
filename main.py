# main.py

import streamlit as st
import pandas as pd

from src.config import APP_TITLE, NAV_ITEMS
from src.ingest import identify_csv_roles, normalize_transactions, normalize_accounts
from ui.control_panel import render_control_panel
from ui.dashboard import render_dashboard_tab
from ui.transactions import render_transactions_tab

st.set_page_config(page_title=APP_TITLE, layout="wide")

# -----------------------------
# File Upload
# -----------------------------
st.sidebar.markdown("## 📤 Upload Monarch CSVs")

uploaded_files = st.sidebar.file_uploader(
    "Upload Transactions + Balances CSVs",
    type=["csv"],
    accept_multiple_files=True,
)

if not uploaded_files:
    st.info("Upload Monarch CSV exports to begin.")
    st.stop()

tx_file, acct_file, diagnostics, error = identify_csv_roles(uploaded_files)

if error:
    st.error(error)
    st.stop()

transactions = normalize_transactions(tx_file)
accounts = normalize_accounts(acct_file)

# -----------------------------
# Controls
# -----------------------------
control_state = render_control_panel(transactions)

# Apply date filter ONCE
filtered_tx = transactions.copy()
if control_state.start_date and control_state.end_date:
    mask = (
        (filtered_tx["date"].dt.date >= control_state.start_date)
        & (filtered_tx["date"].dt.date <= control_state.end_date)
    )
    filtered_tx = filtered_tx.loc[mask]

# -----------------------------
# Tabs
# -----------------------------
tabs = st.tabs(NAV_ITEMS)
tabs_by_label = dict(zip(NAV_ITEMS, tabs))

with tabs_by_label["📊 Dashboard"]:
    render_dashboard_tab(
        transactions=filtered_tx,
        available_years=["ALL YEARS"],
    )

with tabs_by_label["📋 Transactions"]:
    render_transactions_tab(
        filtered_tx,
        accounts,
        year_label="ALL YEARS",
        selected_period=control_state.selected_preset,
        date_range=(control_state.start_date, control_state.end_date),
    )

# Disabled tabs (for now)
for label, tab in tabs_by_label.items():
    if label in {"📊 Dashboard", "📋 Transactions"}:
        continue
    with tab:
        st.info("Temporarily disabled during dashboard rebuild.")
