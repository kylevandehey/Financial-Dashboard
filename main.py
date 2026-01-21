# main.py

import streamlit as st
import pandas as pd

from src.config import APP_TITLE, NAV_ITEMS
from ui.control_panel import render_control_panel
from ui.dashboard import render_dashboard_tab
from ui.transactions import render_transactions_tab

st.set_page_config(page_title=APP_TITLE, layout="wide")

# -----------------------------
# Control Panel (Uploads + Date Presets)
# -----------------------------
control_state = render_control_panel()

transactions = control_state.transactions
accounts = control_state.accounts

if transactions.empty:
    st.info("Upload Monarch CSV exports to begin.")
    st.stop()

# -----------------------------
# APPLY DATE FILTER (ONCE)
# -----------------------------
filtered_tx = transactions.copy()

if control_state.start_date and control_state.end_date:
    mask = (
        (filtered_tx["date"].dt.date >= control_state.start_date)
        & (filtered_tx["date"].dt.date <= control_state.end_date)
    )
    filtered_tx = filtered_tx.loc[mask]

# -----------------------------
# Available Years (for future use)
# -----------------------------
if "date" in transactions.columns:
    years = (
        pd.to_datetime(transactions["date"], errors="coerce")
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
# Navigation Tabs
# -----------------------------
tabs = st.tabs(NAV_ITEMS)
tabs_by_label = dict(zip(NAV_ITEMS, tabs))

# -----------------------------
# Dashboard Tab
# -----------------------------
with tabs_by_label["📊 Dashboard"]:
    render_dashboard_tab(
        transactions=filtered_tx,
        available_years=["ALL YEARS"],  # dashboard is date-driven, not year-tab-driven
        date_range=(control_state.start_date, control_state.end_date),
        selected_preset=control_state.selected_preset,
    )

# -----------------------------
# Transactions Tab
# (Year tabs will live here later)
# -----------------------------
with tabs_by_label["📋 Transactions"]:
    render_transactions_tab(
        transactions=filtered_tx,
        accounts=accounts,
        year_label="ALL YEARS",
        selected_period=control_state.selected_preset,
        date_range=(control_state.start_date, control_state.end_date),
    )

# -----------------------------
# Disabled Tabs (Temporary)
# -----------------------------
for label, tab in tabs_by_label.items():
    if label in {"📊 Dashboard", "📋 Transactions"}:
        continue
    with tab:
        st.info("Temporarily disabled during dashboard rebuild.")
