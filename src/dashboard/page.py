# src/dashboard/page.py

import streamlit as st
import pandas as pd

from src.formatting import format_date_range
from src.dashboard.date_controls import render_date_controls
from src.dashboard.sections.snapshot import render_snapshot_section
from src.dashboard.sections.charts import render_charts_section
from src.dashboard.sections.health_strip import render_health_strip


def render_dashboard_page(transactions: pd.DataFrame) -> None:
    """
    Dashboard (Core Rebuild)
    Orchestrates dashboard sections.
    All date filtering happens ONCE and is passed downstream.
    """

    st.markdown("# Dashboard (Core Rebuild)")
    st.markdown("## Dashboard Overview")

    if transactions.empty:
        st.info("No transactions available.")
        return

    # -------------------------------------------------
    # Date Range Controls (Ledger-style)
    # -------------------------------------------------
    filtered_tx, start_date, end_date = render_date_controls(transactions)

    if start_date and end_date:
        st.caption("Date Range")
        st.caption(format_date_range((start_date, end_date)))

    # -------------------------------------------------
    # Snapshot (High-Level KPIs)
    # -------------------------------------------------
    render_snapshot_section(filtered_tx)

    # -------------------------------------------------
    # Snapshot Details (Charts + Config)
    # -------------------------------------------------
    render_charts_section(filtered_tx)

    # -------------------------------------------------
    # Financial Health Strip (Trends + Ratios)
    # -------------------------------------------------
    render_health_strip(filtered_tx)
