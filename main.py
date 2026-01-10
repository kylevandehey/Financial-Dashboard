# main.py
import streamlit as st

from src.config import APP_TITLE, NAV_ITEMS
from ui.control_panel import render_control_panel
from ui.dashboard import render_dashboard_tab
from ui.transactions import render_transactions_tab

st.set_page_config(layout="wide", page_title=APP_TITLE)

# 1) Sidebar ingestion + persistent controls
control_state = render_control_panel()

canonical_transactions = control_state.transactions
canonical_accounts = control_state.accounts  # kept for later, not used yet

# 2) Top navigation (keep your existing NAV_ITEMS)
primary_tabs = st.tabs(NAV_ITEMS)
tabs_by_label = dict(zip(NAV_ITEMS, primary_tabs))

# 3) Dashboard tab (core rebuild)
with tabs_by_label.get("Dashboard", primary_tabs[0]):
    st.subheader("Dashboard (Core Rebuild)")

    years = []
    if not canonical_transactions.empty and "year" in canonical_transactions.columns:
        years = sorted(
            canonical_transactions["year"].dropna().unique().tolist(),
            reverse=True,
        )

    year_labels = ["ALL YEARS"] + [str(y) for y in years]

    render_dashboard_tab(
        transactions=canonical_transactions,
        available_years=year_labels,
    )

# 4) Transactions tab (table only)
with tabs_by_label.get(
    "Transactions",
    primary_tabs[1] if len(primary_tabs) > 1 else primary_tabs[0],
):
    st.subheader("Transactions (Core Rebuild)")
    render_transactions_tab(
        canonical_transactions,
        canonical_accounts,
        year_label="ALL YEARS",
        selected_period=control_state.selected_period,
        date_range=control_state.date_range,
    )

# 5) Disable everything else for now (tabs remain but show “disabled” message)
for label, tab in tabs_by_label.items():
    if label in {"Dashboard", "Transactions"}:
        continue
    with tab:
        st.subheader(label)
        st.info(
            "Temporarily disabled during core rebuild. Will be re-enabled after baseline metrics are correct."
        )



