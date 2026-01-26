# src/dashboard/page.py

import pandas as pd
import streamlit as st

from src.formatting import format_date_range
from src.cash_flow import compute_cash_flow

from .date_controls import render_date_controls

from .sections.health_strip import render_health_strip
from .sections.snapshot import render_snapshot
from .sections.snapshot_summary import render_snapshot_summary
from .sections.charts import render_charts


def render_dashboard_page(transactions: pd.DataFrame) -> None:
    st.markdown("# Dashboard (Core Rebuild)")
    st.markdown("## Dashboard Overview")

    if transactions is None or transactions.empty:
        st.info("No transactions available. Upload Monarch CSV exports to begin.")
        return

    # -------------------------------------------------
    # Date Range Controls (single source of truth)
    # -------------------------------------------------
    filtered_tx, start_date, end_date, selected_label = render_date_controls(
        transactions
    )

    # Defensive fallback (should never occur, but prevents blank states)
    if filtered_tx is None:
        filtered_tx = transactions.copy()

    # Date range display
    if start_date and end_date:
        st.caption(f"Viewing: {format_date_range((start_date, end_date))}")
    elif "date" in filtered_tx.columns:
        try:
            d = pd.to_datetime(filtered_tx["date"], errors="coerce").dropna()
            if not d.empty:
                st.caption(
                    f"Viewing: {format_date_range((d.min().date(), d.max().date()))}"
                )
        except Exception:
            pass

    # -------------------------------------------------
    # Canonical Cash Flow (computed once, reused everywhere)
    # -------------------------------------------------
    cash_flow = compute_cash_flow(filtered_tx)

    # -------------------------------------------------
    # Financial Health Strip
    # -------------------------------------------------
    render_health_strip(
        cash_flow=cash_flow,
        start_date=start_date,
        end_date=end_date,
        selected_label=selected_label,
    )

    st.divider()

    # -------------------------------------------------
    # Snapshot
    # -------------------------------------------------
    render_snapshot(cash_flow=cash_flow)

    st.markdown("## Snapshot Details")

    render_snapshot_summary(filtered_tx=filtered_tx)

    # -------------------------------------------------
    # Charts
    # -------------------------------------------------
    render_charts(filtered_tx=filtered_tx)
