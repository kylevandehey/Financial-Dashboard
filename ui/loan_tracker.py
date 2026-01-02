"""Loan Tracker tab scaffold that shares the sticky control rail."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.config import ALL_YEARS_LABEL


def _coerce_dataframe(data: pd.DataFrame | None) -> pd.DataFrame:
    if data is None:
        return pd.DataFrame()
    return pd.DataFrame(data).copy()


def render_loan_tracker_tab(
    transactions_df: pd.DataFrame | None,
    accounts_df: pd.DataFrame | None,
    *,
    year_label: str,
    selected_period: str,
) -> None:
    year_context = year_label or ALL_YEARS_LABEL
    scoped_transactions = _coerce_dataframe(transactions_df)
    scoped_accounts = _coerce_dataframe(accounts_df)

    st.markdown("### Loan Tracker")
    st.caption(f"Scope: {year_context} · Period: {selected_period}")
    if scoped_transactions.empty and scoped_accounts.empty:
        st.info("Upload transactions and accounts CSVs to view loan tracking once available.")
        return

    st.info("Coming soon — amortization tracking and payoff planning.")
