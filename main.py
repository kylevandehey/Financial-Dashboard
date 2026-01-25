# main.py

import streamlit as st

from src.theme import apply_theme_a
apply_theme_a()

from src.config import APP_TITLE, NAV_ITEMS
from ui.control_panel import render_control_panel
from src.dashboard.page import render_dashboard_page
from ui.transactions import render_transactions_tab

# -------------------------------------------------
# App Config
# -------------------------------------------------
st.set_page_config(
    page_title=APP_TITLE,
    layout="wide",
)

# -------------------------------------------------
# Control Panel
# - Uploads
# - CSV normalization
# - NO date logic here
# -------------------------------------------------
control_state = render_control_panel()

transactions = control_state.transactions
accounts = control_state.accounts

if transactions.empty:
    st.info("Upload Monarch CSV exports to begin.")
    st.stop()

# -------------------------------------------------
# Navigation Tabs
# -------------------------------------------------
tabs = st.tabs(NAV_ITEMS)
tabs_by_label = dict(zip(NAV_ITEMS, tabs))

# -------------------------------------------------
# Dashboard Tab
# - Owns ALL date logic internally
# -------------------------------------------------
with tabs_by_label["📊 Dashboard"]:
    render_dashboard_page(transactions=transactions)

# -------------------------------------------------
# Transactions Tab
# - Year tabs live here
# - Date range will be added later (optional)
# -------------------------------------------------
with tabs_by_label["📋 Transactions"]:
    render_transactions_tab(
        transactions=transactions,
        accounts=accounts,
    )

# -------------------------------------------------
# Disabled Tabs (temporary)
# -------------------------------------------------
for label, tab in tabs_by_label.items():
    if label in {"📊 Dashboard", "📋 Transactions"}:
        continue
    with tab:
        st.info("Temporarily disabled during dashboard rebuild.")
