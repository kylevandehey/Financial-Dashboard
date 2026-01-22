# ui/dashboard.py

import streamlit as st
import pandas as pd
from datetime import date, timedelta

from src.cash_flow import compute_cash_flow
from src.formatting import format_currency, format_date_range

# =====================================================
# Date Range Presets (Ledger-Style)
# =====================================================

def _resolve_date_range(tx: pd.DataFrame):
    """
    Unified Ledger-style date range resolver.
    Returns: (filtered_df, start_date, end_date)
    """

    if tx.empty or "date" not in tx.columns:
        return tx, None, None

    tx = tx.copy()
    tx["date"] = pd.to_datetime(tx["date"]).dt.date

    min_date = tx["date"].min()
    max_date = tx["date"].max()
    today = max_date

    years = sorted(tx["date"].apply(lambda d: d.year).unique(), reverse=True)

    preset_options = (
        ["ALL YEARS"]
        + ["Last 7 Days", "Last 30 Days", "Last 90 Days", "Last 180 Days", "Last Full Year"]
        + [str(y) for y in years]
        + ["Custom Range"]
    )

    preset = st.selectbox(
        "Date Range Presets",
        preset_options,
        index=0,
        key="date_range_preset",
    )

    start_date = None
    end_date = None

    if preset == "ALL YEARS":
        start_date, end_date = min_date, max_date

    elif preset.startswith("Last "):
        days = int(preset.split()[1])
        start_date = today - timedelta(days=days)
        end_date = today

    elif preset == "Last Full Year":
        last_year = today.year - 1
        start_date = date(last_year, 1, 1)
        end_date = date(last_year, 12, 31)

    elif preset.isdigit():
        year = int(preset)
        start_date = date(year, 1, 1)
        end_date = date(year, 12, 31)

    elif preset == "Custom Range":
        start_date, end_date = st.date_input(
            "Custom Date Range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
            key="custom_date_range",
        )

    # Safety: ensure valid tuple
    if not start_date or not end_date:
        return tx, None, None

    mask = (tx["date"] >= start_date) & (tx["date"] <= end_date)
    return tx.loc[mask], start_date, end_date


# =====================================================
# Dashboard Renderer
# =====================================================

def render_dashboard_tab(transactions: pd.DataFrame) -> None:
    st.markdown("## Dashboard (Core Rebuild)")
    st.markdown("### Dashboard Overview")

    # -----------------------------
    # Date Controls (Canonical)
    # -----------------------------
    filtered_tx, start_date, end_date = _resolve_date_range(transactions)

    if start_date and end_date:
        st.caption("Date Range")
        st.caption(format_date_range((start_date, end_date)))

    if filtered_tx.empty:
        st.info("No transactions in selected date range.")
        return

    # -----------------------------
    # Snapshot Metrics
    # -----------------------------
    result = compute_cash_flow(filtered_tx)

    st.markdown("### Snapshot")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Income", format_currency(result.income))
    with c2:
        st.metric("Expenses", format_currency(result.net_expenses))
    with c3:
        st.metric("Net Cash Flow", format_currency(result.net_cash))

    # -----------------------------
    # Snapshot Details (existing logic continues)
    # -----------------------------
    # IMPORTANT:
    # All existing snapshot charts, category charts,
    # rolling smoothing, audits, etc. remain unchanged
    # below this point in your file.
    #
    # This PR ONLY fixes date controls.
    # -----------------------------
