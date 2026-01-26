# src/dashboard/date_controls.py

import streamlit as st
import pandas as pd
from datetime import date
from typing import Optional, Tuple


def render_date_controls(
    transactions: pd.DataFrame,
) -> Tuple[pd.DataFrame, Optional[date], Optional[date], str]:
    """
    Ledger-style date range preset selector.

    Always returns:
        filtered_tx, start_date, end_date, selected_label
    """

    if transactions is None or transactions.empty:
        return transactions, None, None, "NO_DATA"

    # Ensure datetime
    tx = transactions.copy()
    tx["date"] = pd.to_datetime(tx["date"], errors="coerce")
    tx = tx.dropna(subset=["date"])

    if tx.empty:
        return transactions, None, None, "NO_VALID_DATES"

    min_date = tx["date"].min().date()
    max_date = tx["date"].max().date()

    PRESETS = {
        "ALL_YEARS": (min_date, max_date),
        "Last 7 Days": (max_date - pd.Timedelta(days=6), max_date),
        "Last 30 Days": (max_date - pd.Timedelta(days=29), max_date),
        "Last 90 Days": (max_date - pd.Timedelta(days=89), max_date),
        "Last 180 Days": (max_date - pd.Timedelta(days=179), max_date),
    }

    years = sorted(tx["date"].dt.year.unique())
    for y in years:
        PRESETS[str(y)] = (date(y, 1, 1), date(y, 12, 31))

    PRESETS["Custom Range"] = None

    if "dash_date_preset_v2" not in st.session_state:
        st.session_state.dash_date_preset_v2 = "ALL_YEARS"

    selected_label = st.selectbox(
        "Date Range Presets",
        options=list(PRESETS.keys()),
        key="dash_date_preset_v2",
    )

    if selected_label == "Custom Range":
        c1, c2 = st.columns(2)
        start_date = c1.date_input("Start date", min_date)
        end_date = c2.date_input("End date", max_date)
    else:
        start_date, end_date = PRESETS[selected_label]

    # Defensive guard
    if start_date is None or end_date is None:
        return transactions, None, None, selected_label

    st.caption(f"Viewing: {start_date} → {end_date}")

    mask = (
        (tx["date"].dt.date >= start_date)
        & (tx["date"].dt.date <= end_date)
    )

    filtered_tx = tx.loc[mask].copy()

    return filtered_tx, start_date, end_date, selected_label
