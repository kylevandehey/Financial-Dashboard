"""Transactions tab wrapper that preserves thin UI and shared controls."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.config import ALL_YEARS_LABEL
from ui.transactions_table import render_transactions_table


def _coerce_dataframe(data: pd.DataFrame | None) -> pd.DataFrame:
    if data is None:
        return pd.DataFrame()
    return pd.DataFrame(data).copy()


def _scope_keys(year_label: str) -> str:
    return str(year_label).lower().replace(" ", "_")


def render_transactions_tab(
    transactions: pd.DataFrame | None,
    accounts: pd.DataFrame | None = None,
    *,
    year_label: str,
    selected_period: str,
) -> None:
    year_context = year_label or ALL_YEARS_LABEL
    scoped_transactions = _coerce_dataframe(transactions)

    st.markdown("### Transactions")
    st.caption(f"Scope: {year_context} · Period: {selected_period}")
    if scoped_transactions.empty:
        st.info("No data available for selected filters.")
        return

    safe_year = _scope_keys(year_context)
    render_transactions_table(scoped_transactions, key_prefix=f"transactions_{safe_year}")
