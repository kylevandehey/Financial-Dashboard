# main.py

import streamlit as st

from src.config import APP_TITLE, NAV_ITEMS
from ui.control_panel import render_control_panel
from ui.dashboard import render_dashboard_tab
from ui.transactions import render_transactions_tab

st.set_page_config(page_title=APP_TITLE, layout="wide")

# -----------------------------
# Control Panel
# -----------------------------
control_state = render_control_panel()

transactions = control_state.transactions
accounts = control_state.accounts
start_date = control_state.start_date
end_date = control_state.end_date

if transactions.empty:
    st.info("Upload Monarch CSV exports to begin.")
    st.stop()

# -----------------------------
# Apply Date Filter ONCE
# -----------------------------
filtered_tx = transactions.copy()

if start_date and end_date:
    filtered_tx = filtered_tx[
        (filtered_tx["date"].dt.date >= start_date)
        & (filtered_tx["date"].dt.date <= end_date)
    ]

# -----------------------------
# Navigation Tabs
# -----------------------------
tabs = st.tabs(NAV_ITEMS)
tabs_by_label = dict(zip(NAV_ITEMS, tabs))

# -----------------------------
# Dashboard
# -----------------------------
with tabs_by_label["📊 Dashboard"]:
    render_dashboard_tab(
        transactions=filtered_tx,
        start_date=start_date,
        end_date=end_date,
    )

# -----------------------------
# Transactions
# -----------------------------
with tabs_by_label["📋 Transactions"]:
    render_transactions_tab(
        transactions=filtered_tx,
        accounts=accounts,
    )

# -----------------------------
# Disabled Tabs
# -----------------------------
for label, tab in tabs_by_label.items():
    if label in {"📊 Dashboard", "📋 Transactions"}:
        continue
    with tab:
        st.info("Temporarily disabled during dashboard rebuild.")
