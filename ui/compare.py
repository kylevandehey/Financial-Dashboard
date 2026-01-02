"""Compare tab scaffold that reuses the shared left control rail."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.config import ALL_YEARS_LABEL
from src.filters import filter_transactions_for_scope
from ui.dashboard import render_left_control_panel


def _coerce_dataframe(data: pd.DataFrame | None) -> pd.DataFrame:
    if data is None:
        return pd.DataFrame()
    return pd.DataFrame(data).copy()


def render_compare_tab(
    transactions_df: pd.DataFrame | None,
    accounts_df: pd.DataFrame | None,
    *,
    year_label: str,
) -> None:
    year_context = year_label or ALL_YEARS_LABEL
    base_transactions = _coerce_dataframe(st.session_state.get("transactions_df") or transactions_df)
    base_accounts = _coerce_dataframe(st.session_state.get("accounts_df") or accounts_df)

    left_col, right_col = st.columns([1.1, 2.9], gap="large")

    with left_col:
        selected_period, date_range, _months_filter = render_left_control_panel(
            base_transactions,
            base_accounts,
            year_context,
        )
        active_transactions = _coerce_dataframe(st.session_state.get("transactions_df") or base_transactions)
        active_accounts = _coerce_dataframe(st.session_state.get("accounts_df") or base_accounts)

    scoped_transactions = filter_transactions_for_scope(
        active_transactions,
        year_label=year_context,
        period_label=selected_period,
        date_range=date_range,
    )

    with right_col:
        st.markdown("### Compare")
        st.caption(f"Scope: {year_context} · Period: {selected_period}")
        if scoped_transactions.empty and active_accounts.empty:
            st.info("Upload transactions and accounts CSVs to compare year-over-year performance.")
            return

        st.info(
            "This tab will compare transactions and balance sheet metrics across calendar years.\n"
            "Planned features include:\n"
            "- Year-by-year charts\n"
            "- Delta $ vs prior year\n"
            "- Delta % vs prior year\n"
            "- Income, expenses, assets, liabilities, and net worth comparisons."
        )
