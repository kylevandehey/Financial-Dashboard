# main.py
import streamlit as st

from src.config import ALL_YEARS_LABEL, APP_TITLE, DASHBOARD_TITLE, NAV_ITEMS
from src.filters import compute_scope_date_range, filter_transactions_for_scope
from src.date_filters import filter_dataframe_by_date
from ui.benchmarking import render_benchmarking_tab
from ui.control_panel import render_control_panel
from ui.compare import render_compare_tab
from ui.dashboard import render_dashboard_tab
from ui.insights import render_insights_tab
from ui.loan_tracker import render_loan_tracker_tab
from ui.transactions import render_transactions_tab


st.set_page_config(layout="wide", page_title=APP_TITLE)

control_state = render_control_panel()
active_transactions = control_state.transactions
active_accounts = control_state.accounts

years = []
if not active_transactions.empty and "year" in active_transactions.columns:
    years = sorted(active_transactions["year"].dropna().unique().tolist(), reverse=True)

year_labels = [ALL_YEARS_LABEL] + [str(y) for y in years]


def _filter_accounts_for_range(accounts_df, date_range):
    if accounts_df is None or accounts_df.empty or not date_range:
        return accounts_df
    try:
        start_date, end_date = date_range
    except Exception:
        return accounts_df
    return filter_dataframe_by_date(accounts_df, (start_date, end_date), date_column="date")

primary_tabs = st.tabs(NAV_ITEMS)
tabs_by_label = dict(zip(NAV_ITEMS, primary_tabs))

with tabs_by_label["Dashboard"]:
    st.subheader(DASHBOARD_TITLE)
    year_tabs = st.tabs(year_labels)
    for tab, label in zip(year_tabs, year_labels):
        with tab:
            date_bounds = compute_scope_date_range(
                active_transactions,
                year_label=label,
                period_label=control_state.selected_period,
                fallback_df=active_accounts,
            )
            scoped_transactions = filter_transactions_for_scope(
                active_transactions,
                year_label=label,
                period_label=control_state.selected_period,
                date_range=date_bounds,
            )
            scoped_accounts = _filter_accounts_for_range(active_accounts, date_bounds)
            render_dashboard_tab(
                scoped_transactions,
                scoped_accounts,
                year_label=label,
                selected_period=control_state.selected_period,
                date_range=date_bounds,
                months_filter=control_state.months_filter,
            )

with tabs_by_label["Transactions"]:
    st.subheader("Transactions")
    year_tabs = st.tabs(year_labels)
    for tab, label in zip(year_tabs, year_labels):
        with tab:
            date_bounds = compute_scope_date_range(
                active_transactions,
                year_label=label,
                period_label=control_state.selected_period,
                fallback_df=active_accounts,
            )
            scoped_transactions = filter_transactions_for_scope(
                active_transactions,
                year_label=label,
                period_label=control_state.selected_period,
                date_range=date_bounds,
            )
            render_transactions_tab(
                scoped_transactions,
                active_accounts,
                year_label=label,
                selected_period=control_state.selected_period,
                date_range=date_bounds,
            )

with tabs_by_label["Compare"]:
    st.subheader("Compare")
    year_tabs = st.tabs(year_labels)
    for tab, label in zip(year_tabs, year_labels):
        with tab:
            date_bounds = compute_scope_date_range(
                active_transactions,
                year_label=label,
                period_label=control_state.selected_period,
                fallback_df=active_accounts,
            )
            scoped_transactions = filter_transactions_for_scope(
                active_transactions,
                year_label=label,
                period_label=control_state.selected_period,
                date_range=date_bounds,
            )
            scoped_accounts = _filter_accounts_for_range(active_accounts, date_bounds)
            render_compare_tab(
                scoped_transactions,
                scoped_accounts,
                year_label=label,
                selected_period=control_state.selected_period,
                date_range=date_bounds,
            )

with tabs_by_label["Insights"]:
    st.subheader(f"{NAV_ITEMS[3]} (Financial IQ layer)")
    year_tabs = st.tabs(year_labels)
    for tab, label in zip(year_tabs, year_labels):
        with tab:
            date_bounds = compute_scope_date_range(
                active_transactions,
                year_label=label,
                period_label=control_state.selected_period,
                fallback_df=active_accounts,
            )
            scoped_transactions = filter_transactions_for_scope(
                active_transactions,
                year_label=label,
                period_label=control_state.selected_period,
                date_range=date_bounds,
            )
            scoped_accounts = _filter_accounts_for_range(active_accounts, date_bounds)
            render_insights_tab(
                scoped_transactions,
                scoped_accounts,
                year_label=label,
                selected_period=control_state.selected_period,
                date_range=date_bounds,
            )

with tabs_by_label["Loan Tracker"]:
    st.subheader("Loan Tracker")
    year_tabs = st.tabs(year_labels)
    for tab, label in zip(year_tabs, year_labels):
        with tab:
            date_bounds = compute_scope_date_range(
                active_transactions,
                year_label=label,
                period_label=control_state.selected_period,
                fallback_df=active_accounts,
            )
            scoped_transactions = filter_transactions_for_scope(
                active_transactions,
                year_label=label,
                period_label=control_state.selected_period,
                date_range=date_bounds,
            )
            scoped_accounts = _filter_accounts_for_range(active_accounts, date_bounds)
            render_loan_tracker_tab(
                scoped_transactions,
                scoped_accounts,
                year_label=label,
                selected_period=control_state.selected_period,
            )

with tabs_by_label["Tools"]:
    st.subheader("Tools")
    year_tabs = st.tabs(year_labels)
    for tab, label in zip(year_tabs, year_labels):
        with tab:
            date_bounds = compute_scope_date_range(
                active_transactions,
                year_label=label,
                period_label=control_state.selected_period,
                fallback_df=active_accounts,
            )
            scoped_accounts = _filter_accounts_for_range(active_accounts, date_bounds)
            render_benchmarking_tab(active_transactions, scoped_accounts, year_label=label)
            st.info("Additional tools and calculators will be wired in a future release.")

with tabs_by_label["Assistance"]:
    st.subheader("Assistance")
    year_tabs = st.tabs(year_labels)
    for tab, label in zip(year_tabs, year_labels):
        with tab:
            st.info("Assistant functionality will be integrated here.")
