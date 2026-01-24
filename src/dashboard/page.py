# src/dashboard/page.py

import streamlit as st

# Controls
from src.dashboard.date_controls import render_date_controls

# Sections
from src.dashboard.sections.health_strip import render_health_strip
from src.dashboard.sections.snapshot_summary import render_snapshot_summary
from src.dashboard.sections.income_chart import render_income_chart
from src.dashboard.sections.expense_chart import render_expense_chart
from src.dashboard.sections.frequency_chart import render_frequency_chart


def render_dashboard_page(transactions):
    """
    Primary dashboard page orchestrator.
    All heavy logic is delegated to section modules.
    """

    st.markdown("# Dashboard (Core Rebuild)")
    st.markdown("## Dashboard Overview")

    # -------------------------------------------------
    # Date Controls (single source of truth)
    # -------------------------------------------------
    filtered_tx, start_date, end_date = render_date_controls(transactions)

    if filtered_tx.empty:
        st.info("No transactions in selected date range.")
        return

    # -------------------------------------------------
    # Health Strip (High-level financial indicators)
    # -------------------------------------------------
    render_health_strip(filtered_tx)

    # -------------------------------------------------
    # Snapshot Summary
    # -------------------------------------------------
    render_snapshot_summary(filtered_tx)

    # -------------------------------------------------
    # Snapshot Details (Configurable Sections)
    # -------------------------------------------------
    st.markdown("## Snapshot Details")

    with st.expander("⚙️ Configure metrics per section", expanded=False):
        col1, col2, col3 = st.columns(3)

        with col1:
            income_exclusions = st.multiselect(
                "Income",
                options=sorted(filtered_tx["category"].dropna().unique()),
                default=[],
                key="income_exclusions",
            )

        with col2:
            expense_exclusions = st.multiselect(
                "Expenses",
                options=sorted(filtered_tx["category"].dropna().unique()),
                default=[],
                key="expense_exclusions",
            )

        with col3:
            frequency_exclusions = st.multiselect(
                "Most Frequent Expenses",
                options=sorted(filtered_tx["category"].dropna().unique()),
                default=[],
                key="frequency_exclusions",
            )

        if st.button("Reset to Defaults"):
            st.session_state.pop("income_exclusions", None)
            st.session_state.pop("expense_exclusions", None)
            st.session_state.pop("frequency_exclusions", None)
            st.rerun()

    # -------------------------------------------------
    # Charts
    # -------------------------------------------------
    c1, c2, c3 = st.columns(3)

    with c1:
        render_income_chart(filtered_tx, income_exclusions)

    with c2:
        render_expense_chart(filtered_tx, expense_exclusions)

    with c3:
        render_frequency_chart(filtered_tx, frequency_exclusions)
