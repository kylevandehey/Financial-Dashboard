# src/dashboard/date_controls.py

import streamlit as st
import pandas as pd
from datetime import date


def render_date_controls(transactions: pd.DataFrame):
    """
    Ledger-style date range preset selector.
    Returns: filtered_df, start_date, end_date
    """

    if transactions.empty:
        return transactions, None, None

    min_date = transactions["date"].min().date()
    max_date = transactions["date"].max().date()

    PRESETS = {
        "ALL_YEARS": (min_date, max_date),
        "Last 7 Days": (max_date - pd.Timedelta(days=6), max_date),
        "Last 30 Days": (max_date - pd.Timedelta(days=29), max_date),
        "Last 90 Days": (max_date - pd.Timedelta(days=89), max_date),
        "Last 180 Days": (max_date - pd.Timedelta(days=179), max_date),
    }

    years = sorted(transactions["date"].dt.year.unique())
    for y in years:
        PRESETS[str(y)] = (date(y, 1, 1), date(y, 12, 31))

    PRESETS["Custom Range"] = None

    if "dash_date_preset_v2" not in st.session_state:
        st.session_state.dash_date_preset_v2 = "ALL_YEARS"

    preset = st.selectbox(
        "Date Range Presets",
        options=list(PRESETS.keys()),
        key="dash_date_preset_v2",
    )

    if preset == "Custom Range":
        c1, c2 = st.columns(2)
        start = c1.date_input("Start date", min_date)
        end = c2.date_input("End date", max_date)
    else:
        start, end = PRESETS[preset]

    st.caption(f"Viewing: {start} → {end}")

    mask = (
        (transactions["date"].dt.date >= start)
        & (transactions["date"].dt.date <= end)
    )

    return transactions.loc[mask], start, end
