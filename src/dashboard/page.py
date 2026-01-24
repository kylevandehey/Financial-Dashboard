# src/dashboard/page.py

import streamlit as st

# TEMPORARY imports
# These will be progressively moved into the dashboard module
from ui.dashboard import (
    render_date_controls,
    render_snapshot_section,
    render_configure_metrics_section,
    render_income_section,
    render_expense_section,
    render_frequency_section,
)


def render_dashboard_tab(transactions):
    """
    Thin orchestrator for the Dashboard tab.

    Responsibilities:
    - Control layout order
    - Delegate rendering to section-level functions
    - NO business logic
    - NO calculations
    """

    # -----------------------------
    # Date Controls
    # -----------------------------
    tx_filtered, start_date, end_date = render_date_controls(transactions)

    # -----------------------------
    # Snapshot + Financial Health
    # -----------------------------
    render_snapshot_section(
        filtered_transactions=tx_filtered,
        all_transactions=transactions,
        start_date=start_date,
        end_date=end_date,
    )

    # -----------------------------
    # Configurator (collapsed by default)
    # -----------------------------
    (
        income_categories,
        expense_categories,
        frequency_categories,
    ) = render_configure_metrics_section(tx_filtered)

    # -----------------------------
    # Charts Layout
    # -----------------------------
    col1, col2, col3 = st.columns(3)

    with col1:
        render_income_section(
            filtered_transactions=tx_filtered,
            selected_categories=income_categories,
        )

    with col2:
        render_expense_section(
            filtered_transactions=tx_filtered,
            selected_categories=expense_categories,
        )

    with col3:
        render_frequency_section(
            filtered_transactions=tx_filtered,
            selected_categories=frequency_categories,
        )
