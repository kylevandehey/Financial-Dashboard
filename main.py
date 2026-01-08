# main.py

import streamlit as st

from src.config import ALL_YEARS_LABEL, APP_TITLE, DASHBOARD_TITLE, NAV_ITEMS
from src.filters import (
    compute_scope_date_range,
    filter_transactions_for_scope,
    get_filtered_transactions,
)
from src.date_filters import filter_dataframe_by_date
from ui.benchmarking import render_benchmarking_tab
from ui.control_panel import render_control_panel
from ui.compare import render_compare_tab
from ui.dashboard import render_dashboard_tab
from ui.insights import render_insights_tab
from ui.loan_tracker import render_loan_tracker_tab
from ui.transactions import render_transactions_tab


# -------------------------------------------------
# App setup
# -------------------------------------------------

st.set_page_config(layout="wide", page_title=APP_TITLE)

control_state = render_control_panel()

raw_transactions = control_state.transactions
raw_accounts = control_state.accounts


# -------------------------------------------------
# Year tabs
# -------------------------------------------------

years = []
if not raw_transactions.empty and "year" in raw_transactions.columns:
    years = sorted(raw_transactions["year"].dropna().unique().tolist(), reverse=True)

year_labels = [ALL_YEARS_LABEL] + [str(y) for y in years]


def _filter_accounts_for_range(accounts_df, date_range):
    if accounts_df is None or accounts_df.empty or not date_range:
        return accounts_df
    try:
        start_date, end_date = date_range
    except Exception:
        return accounts_df
    return filter_dataframe_by_date(accounts_df, (start_date, end_date), date_column="date")


# -------------------------------------------------
# Tabs
# -------------------------------------------------

primary_tabs = st.tabs(NAV_ITEMS)
tabs_by_label = dict(zip(NAV_ITEMS, primary_tabs))


# =============================
# Dashboard
# =============================

with tabs_by_label["Dashboard"]:
    st.subheader(DASHBOARD_TITLE)
    year_tabs = st.tabs(year_labels)

    for tab, label in zip(year_tabs, year_labels):
        with tab:
            date_bounds = compute_scope_date_range(
                raw_transactions,
                year_label=label,
                period_label=control_state.selected_period,
                fallback_df=raw_accounts,
            )

            # 1) Apply date / year / quarter scope
            scoped_transactions = filter_transactions_for_scope(
                raw_transactions,
                year_label=label,
                period_label=control_state.selected_period,
                date_range=date_bounds,
            )

            # 2) Apply transfer / CC / refund filters (CRITICAL)
            filtered_transactions = get_filtered_transactions(scoped_transactions)

            scoped_accounts = _filter_accounts_for_range(raw_accounts, date_bounds)

            render_dashboard_tab(
                transactions=filtered_transactions,
                accounts=scoped_accounts,
                date_range=date_bounds,
                year_label=label,
                selected_period=control_state.selected_period,
            )


# =============================
# Transactions
# =============================

with tabs_by_label["Transactions"]:
    st.subheader("Transactions")
    year_tabs = st.tabs(year_labels)

    for tab, label in zip(year_tabs, year_labels):
        with tab:
            date_bounds = compute_scope_date_range(
                raw_transactions,
                year_label=label,
                period_label=control_state.selected_period,
                fallback_df=raw_accounts,
            )

            scoped_transactions = filter_transactions_for_scope(
                raw_transactions,
                year_label=label,
                period_label=control_state.selected_period,
                date_range=date_bounds,
            )

            filtered_transactions = get_filtered_transactions(scoped_transactions)

            render_transactions_tab(
                filtered_transactions,
                raw_accounts,
                year_label=label,
                selected_period=control_state.selected_period,
                date_range=date_bounds,
            )


# =============================
# Compare
# =============================

with tabs_by_label["Compare"]:
    st.subheader("Compare")
    year_tabs = st.tabs(year_labels)

    for tab, label in zip(year_tabs, year_labels):
        with tab:
            date_bounds = compute_scope_date_range(
                raw_transactions,
                year_label=label,
                period_label=control_state.selected_period,
                fallback_df=raw_accounts,
            )

            scoped_transactions = filter_transactions_for_scope(
                raw_transactions,
                year_label=label,
                period_label=control_state.selected_period,
                date_range=date_bounds,
            )

            filtered_transactions = get_filtered_transactions(scoped_transactions)
            scoped_accounts = _filter_accounts_for_range(raw_accounts, date_bounds)

            render_compare_tab(
                filtered_transactions,
                scoped_accounts,
                year_label=label,
                selected_period=control_state.selected_period,
                date_range=date_bounds,
            )


# =============================
# Insights
# =============================

with tabs_by_label["Insights"]:
    st.subheader(f"{NAV_ITEMS[3]} (Financial IQ layer)")
    year_tabs = st.tabs(year_labels)

    for tab, label in zip(year_tabs, year_labels):
        with tab:
            date_bounds = compute_scope_date_range(
                raw_transactions,
                year_label=label,
                period_label=control_state.selected_period,
                fallback_df=raw_accounts,
            )

            scoped_transactions = filter_transactions_for_scope(
                raw_transactions,
                year_label=label,
                period_label=control_state.selected_period,
                date_range=date_bounds,
            )

            filtered_transactions = get_filtered_transactions(scoped_transactions)
            scoped_accounts = _filter_accounts_for_range(raw_accounts, date_bounds)

            render_insights_tab(
                filtered_transactions,
                scoped_accounts,
                year_label=label,
                selected_period=control_state.selected_period,
                date_range=date_bounds,
            )


# =============================
# Loan Tracker
# =============================

with tabs_by_label["Loan Tracker"]:
    st.subheader("Loan Tracker")
    year_tabs = st.tabs(year_labels)

    for tab, label in zip(year_tabs, year_labels):
        with tab:
            date_bounds = compute_scope_date_range(
                raw_transactions,
                year_label=label,
                period_label=control_state.selected_period,
                fallback_df=raw_accounts,
            )

            scoped_transactions = filter_transactions_for_scope(
                raw_transactions,
                year_label=label,
                period_label=control_state.selected_period,
                date_range=date_bounds,
            )

            filtered_transactions = get_filtered_transactions(scoped_transactions)
            scoped_accounts = _filter_accounts_for_range(raw_accounts, date_bounds)

            render_loan_tracker_tab(
                filtered_transactions,
                scoped_accounts,
                year_label=label,
                selected_period=control_state.selected_period,
            )


# =============================
# Tools
# =============================

with tabs_by_label["Tools"]:
    st.subheader("Tools")
    year_tabs = st.tabs(year_labels)

    for tab, label in zip(year_tabs, year_labels):
        with tab:
            date_bounds = compute_scope_date_range(
                raw_transactions,
                year_label=label,
                period_label=control_state.selected_period,
                fallback_df=raw_accounts,
            )

            scoped_accounts = _filter_accounts_for_range(raw_accounts, date_bounds)
            render_benchmarking_tab(raw_transactions, scoped_accounts, year_label=label)
            st.info("Additional tools and calculators will be wired in a future release.")


# =============================
# Assistance
# =============================

with tabs_by_label["Assistance"]:
    st.subheader("Assistance")
    year_tabs = st.tabs(year_labels)

    for tab, label in zip(year_tabs, year_labels):
        with tab:
            st.info("Assistant functionality will be integrated here.")

