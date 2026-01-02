"""Transactions tab wrapper that preserves thin UI and shared controls."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.config import ALL_YEARS_LABEL
from src.date_filters import compute_date_range, filter_dataframe_by_date
from ui.transactions_table import render_transactions_table


def render_transactions_tab(filtered_transactions: pd.DataFrame, *, year_label: str) -> None:
    if filtered_transactions is None or filtered_transactions.empty:
        st.info("Upload a Transactions CSV to explore table views.")
        return

    if str(year_label).upper() in {"ALL", ALL_YEARS_LABEL}:
        min_date = pd.to_datetime(filtered_transactions["date"]).min().date()
        max_date = pd.to_datetime(filtered_transactions["date"]).max().date()
        start_date, end_date = min_date, max_date
    else:
        start_date, end_date = compute_date_range("full_year", year=year_label)

    filtered_tx = filter_dataframe_by_date(
        filtered_transactions,
        (start_date, end_date),
        date_column="date",
    )
    safe_year = str(year_label).lower().replace(" ", "_")
    render_transactions_table(filtered_tx, key_prefix=f"transactions_{safe_year}")
