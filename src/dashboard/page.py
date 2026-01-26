# src/dashboard/page.py

import streamlit as st
import pandas as pd

from src.formatting import format_date_range
from src.cash_flow import compute_cash_flow

from .date_controls import render_date_controls
from .sections import (
render_health_strip,
render_snapshot,
render_snapshot_summary,
render_charts,
)


def render_dashboard_page(transactions: pd.DataFrame) -> None:
    st.markdown("# Dashboard (Core Rebuild)")
    st.markdown("## Dashboard Overview")

    if transactions is None or transactions.empty:
        st.info("No transactions available. Upload Monarch CSV exports to begin.")
        return

    # -----------------------------
    # Date Range Controls (Single Source of Truth)
    # -----------------------------
    filtered_tx,start_date,end_date,selected_label=render_date_controls(transactions)

    # Defensive fallback (should not happen, but avoids blank-page failures)
    if filtered_tx is None:
        filtered_tx=transactions.copy()

    # Date Range display
    if start_date and end_date:
        st.caption(f"Viewing: {format_date_range((start_date,end_date))}")
    elif "date" in filtered_tx.columns:
        # If controls didn’t return dates for some reason, derive best-effort range
        try:
            d=pd.to_datetime(filtered_tx["date"],errors="coerce").dropna()
            if not d.empty:
                st.caption(f"Viewing: {format_date_range((d.min().date(),d.max().date()))}")
        except Exception:
            pass

    # -----------------------------
    # Canonical Cash Flow (ONE calculation, reused everywhere)
    # -----------------------------
    cash_flow=compute_cash_flow(filtered_tx)

    # -----------------------------
    # Financial Health Strip
    # -----------------------------
    render_health_strip(
        cash_flow=cash_flow,
        start_date=start_date,
        end_date=end_date,
        selected_label=selected_label,
    )

    st.divider()

    # -----------------------------
    # Snapshot (If you want this removed later, we remove it here centrally)
    # -----------------------------
    render_snapshot(cash_flow=cash_flow)

    st.markdown("## Snapshot Details")

    # If your snapshot_summary needs tx for charts/tables, pass filtered_tx too
    render_snapshot_summary(filtered_tx=filtered_tx)

    # Charts section (Top Income / Top Expenses / Frequency)
    render_charts(filtered_tx=filtered_tx)
