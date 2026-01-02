"""Compare tab scaffold that reuses the shared left control rail."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.config import ALL_YEARS_LABEL
from src.formatting import format_date_range


def _coerce_dataframe(data: pd.DataFrame | None) -> pd.DataFrame:
    if data is None:
        return pd.DataFrame()
    return pd.DataFrame(data).copy()


def render_compare_tab(
    transactions_df: pd.DataFrame | None,
    accounts_df: pd.DataFrame | None,
    *,
    year_label: str,
    selected_period: str,
    date_range: tuple,
) -> None:
    year_context = year_label or ALL_YEARS_LABEL
    scoped_transactions = _coerce_dataframe(transactions_df)
    scoped_accounts = _coerce_dataframe(accounts_df)

    st.markdown("### Compare")
    st.caption(f"Scope: {year_context} · Period: {selected_period}")
    st.caption("Date Range")
    st.caption(format_date_range(date_range))
    if scoped_transactions.empty and scoped_accounts.empty:
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
