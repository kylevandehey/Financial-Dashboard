"""Transactions tab wrapper that preserves thin UI and shared controls."""

from __future__ import annotations

from typing import Tuple

import pandas as pd
import streamlit as st

from src.config import ALL_YEARS_LABEL
from src.filters import compute_scope_date_range, filter_transactions_for_scope, period_options_for_scope
from ui.transactions_table import render_transactions_table


def _scope_keys(year_label: str) -> str:
    return str(year_label).lower().replace(" ", "_")


def _render_scope_controls(transactions: pd.DataFrame, year_label: str) -> Tuple[str, tuple]:
    period_options = period_options_for_scope(year_label)
    default_period = period_options[0]
    safe_year = _scope_keys(year_label)

    st.markdown("#### Date Scope")
    with st.container(border=True):
        col1, col2 = st.columns([1.2, 1.8])
        with col1:
            selected_period = st.radio(
                "Period",
                period_options,
                index=period_options.index(default_period),
                key=f"transactions_{safe_year}_period",
            )

        start_date, end_date = compute_scope_date_range(transactions, year_label=year_label, period_label=selected_period)
        with col2:
            date_selection = st.date_input(
                "Start / End",
                (start_date, end_date),
                key=f"transactions_{safe_year}_dates",
            )
            if isinstance(date_selection, (tuple, list)) and len(date_selection) == 2:
                start_date, end_date = date_selection

    return selected_period, (start_date, end_date)


def render_transactions_tab(transactions: pd.DataFrame, *, year_label: str) -> None:
    if transactions is None or transactions.empty:
        st.info("Upload a Transactions CSV to explore table views.")
        return

    selected_period, date_range = _render_scope_controls(transactions, year_label)
    scoped_transactions = filter_transactions_for_scope(
        transactions,
        year_label=year_label,
        period_label=selected_period,
        date_range=date_range,
    )

    if scoped_transactions.empty:
        st.info("No data available for selected filters.")
        return

    safe_year = _scope_keys(year_label)
    render_transactions_table(scoped_transactions, key_prefix=f"transactions_{safe_year}")
