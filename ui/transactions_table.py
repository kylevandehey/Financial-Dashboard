"""Transactions table UI and filtering logic.

This module keeps Streamlit UI thin while ensuring filtering, search, and
sorting can be unit tested. It assumes the incoming DataFrame is already
normalized and date-filtered by the centralized date engine.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

import pandas as pd
import streamlit as st

from src.formatting import format_currency_series


DISPLAY_COLUMNS = [
    "date",
    "merchant",
    "category",
    "account",
    "amount",
    "notes",
]

COLUMN_LABELS = {
    "date": "Date",
    "merchant": "Merchant",
    "category": "Category",
    "account": "Account",
    "amount": "Amount",
    "notes": "Notes",
}


@dataclass
class TransactionsTableConfig:
    """Configuration for the transactions table display."""

    hide_notes: bool = False

    @property
    def columns(self) -> list[str]:
        columns = DISPLAY_COLUMNS.copy()
        if self.hide_notes:
            columns.remove("notes")
        return columns


def search_filter(df: pd.DataFrame, query: str) -> pd.DataFrame:
    """Filter rows where query matches merchant or notes (case-insensitive)."""

    if not query:
        return df

    lowered = query.lower()
    merchant_match = df["merchant"].str.contains(lowered, case=False, na=False)
    notes_match = df["notes"].str.contains(lowered, case=False, na=False)
    return df[merchant_match | notes_match]


def apply_multi_filter(df: pd.DataFrame, column: str, values: Iterable[str]) -> pd.DataFrame:
    """Apply a multi-select filter without mutating the original DataFrame."""

    selected = [v for v in values if v]
    if not selected:
        return df
    return df[df[column].isin(selected)]


def prepare_transactions_dataframe(
    transactions: pd.DataFrame,
    search_term: str = "",
    categories: Optional[Iterable[str]] = None,
    accounts: Optional[Iterable[str]] = None,
    config: Optional[TransactionsTableConfig] = None,
) -> pd.DataFrame:
    """Return a filtered, sorted, and formatted DataFrame for display."""

    cfg = config or TransactionsTableConfig()
    df = transactions.copy()

    # Ensure required columns exist
    missing_cols = [col for col in DISPLAY_COLUMNS if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns: {', '.join(missing_cols)}")

    # Filters
    df = search_filter(df, search_term)
    df = apply_multi_filter(df, "category", categories or [])
    df = apply_multi_filter(df, "account", accounts or [])

    # Sorting (descending by date)
    df = df.sort_values("date", ascending=False)

    # Formatting
    df = df.reset_index(drop=True)
    df["amount"] = format_currency_series(df["amount"])

    # Column ordering / optional notes column
    df = df[cfg.columns]
    df = df.rename(columns=COLUMN_LABELS)
    return df


def render_transactions_table(
    transactions: pd.DataFrame,
    config: Optional[TransactionsTableConfig] = None,
    *,
    key_prefix: str = "transactions",
) -> None:
    """Render the transactions table with search and filter controls."""

    cfg = config or TransactionsTableConfig()

    st.subheader("Transactions")

    search_col, category_col, account_col, reset_col = st.columns([2, 2, 2, 1])

    with search_col:
        search_term = st.text_input(
            "Search Merchant / Notes",
            value="",
            placeholder="e.g., coffee",
            key=f"{key_prefix}_search_term",
        )

    categories = sorted(transactions["category"].dropna().unique())
    accounts = sorted(transactions["account"].dropna().unique())

    with category_col:
        selected_categories = st.multiselect(
            "Category",
            options=categories,
            key=f"{key_prefix}_categories",
        )

    with account_col:
        selected_accounts = st.multiselect(
            "Account",
            options=accounts,
            key=f"{key_prefix}_accounts",
        )

    if reset_col.button("Reset", key=f"{key_prefix}_reset"):
        st.experimental_rerun()

    prepared_df = prepare_transactions_dataframe(
        transactions,
        search_term=search_term,
        categories=selected_categories,
        accounts=selected_accounts,
        config=cfg,
    )

    st.dataframe(prepared_df, use_container_width=True)
