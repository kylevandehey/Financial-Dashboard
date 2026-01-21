# main.py

import streamlit as st

from src.config import APP_TITLE, NAV_ITEMS
from ui.control_panel import render_control_panel
from ui.dashboard import render_dashboard_tab
from ui.transactions import render_transactions_tab

# -----------------------------
# App Config
# -----------------------------
st.set_page_config(page_title=APP_TITLE, layout="wide")

# -----------------------------
# Control Panel (Uploads + Date Logic)
# -----------------------------
control_state = render_control_panel()

transactions = control_state.transactions
accounts = control_state.accounts

if transactions.empty:
    st.info("Upload Monarch CSV exports to begin.")
    st.stop()

# -----------------------------
# Resolve Date Range (DEFENSIVE)
# -----------------------------
filtered_tx = transactions.copy()

start_date = None
end_date = None

# Preferred unified interface
if hasattr(control_state, "date_range") and control_state.date_range:
    start_date, end_date = control_state.date_range

# Backward compatibility fallback
elif hasattr(control_state, "start_date") and hasattr(control_state, "end_date"):
    start_date = control_state.start_date
    end_date = control_state.end_date

if start_date and end_date:
    mask = (
        (filtered_tx["date"].dt.date >= start_date)
        & (filtered_tx["date"].dt.date <= end_date)
    )
    filtered_tx = filtered_tx.loc[mask]

# -----------------------------
# Navigation Tabs
# -----------------------------
tabs = st.tabs(NAV_ITEMS)
tabs_by_label = dict(zip(NAV_ITEMS, tabs))

# -----------------------------
# Dashboard Tab
# (Date logic already applied)
# -----------------------------
with tabs_by_label["📊 Dashboard"]:
    render_dashboard_tab(
        transactions=filtered_tx,
        available_years=["ALL YEARS"],
        date_range=(start_date, end_date),
        selected_preset=getattr(control_state, "selected_preset", None),
    )

# -----------------------------
# Transactions Tab
# (Year tabs live here)
# -----------------------------
with tabs_by_label["📋 Transactions"]:
    render_transactions_tab(
        transactions=filtered_tx,
        accounts=accounts,
        year_label="ALL YEARS",
        selected_period=getattr(control_state, "selected_preset", None),
        date_range=(start_date, end_date),
    )

# -----------------------------
# Disabled Tabs (Temporary)
# -----------------------------
for label, tab in tabs_by_label.items():
    if label in {"📊 Dashboard", "📋 Transactions"}:
        continue
    with tab:
        st.info("Temporarily disabled during dashboard rebuild.")
