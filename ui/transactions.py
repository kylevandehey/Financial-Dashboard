"""Transactions tab wrapper that preserves thin UI and shared controls."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.filters import TransactionFilterConfig, apply_transaction_config
from src.date_filters import compute_date_range, filter_dataframe_by_date
from ui.transactions_table import render_transactions_table


def _render_transaction_configuration(prefix: str) -> TransactionFilterConfig:
    st.markdown("#### Configure Transactions")
    with st.container(border=True):
        left, right = st.columns([1.5, 1.5])

        available_types = ["transfer", "payment", "refund", "adjustment"]
        excluded_types = st.multiselect(
            "Exclude transaction types",
            options=available_types,
            default=list(st.session_state.get("excluded_transaction_types", [])),
            key=f"excluded_types_{prefix}",
        )

        with right:
            include_keywords = st.text_input(
                "Only include keywords (comma-separated)",
                value=", ".join(st.session_state.get("include_keywords", [])),
                key=f"include_keywords_{prefix}",
                placeholder="e.g., paycheck, bonus",
            )
            exclude_keywords = st.text_input(
                "Exclude keywords (comma-separated)",
                value=", ".join(st.session_state.get("exclude_keywords", [])),
                key=f"exclude_keywords_{prefix}",
                placeholder="e.g., transfer, move",
            )

    config = TransactionFilterConfig.from_keyword_strings(
        excluded_types=excluded_types,
        include_keywords=include_keywords,
        exclude_keywords=exclude_keywords,
    )
    st.session_state["excluded_transaction_types"] = config.excluded_types
    st.session_state["include_keywords"] = config.include_keywords
    st.session_state["exclude_keywords"] = config.exclude_keywords
    return config


def render_transactions_tab(transactions_df: pd.DataFrame, *, year_label: str) -> None:
    if transactions_df is None or transactions_df.empty:
        st.info("Upload a Transactions CSV to explore table views.")
        return

    if year_label == "ALL":
        min_date = pd.to_datetime(transactions_df["date"]).min().date()
        max_date = pd.to_datetime(transactions_df["date"]).max().date()
        start_date, end_date = min_date, max_date
    else:
        start_date, end_date = compute_date_range("full_year", year=year_label)

    config = _render_transaction_configuration(prefix=year_label)

    filtered_tx = filter_dataframe_by_date(
        transactions_df,
        (start_date, end_date),
        date_column="date",
    )
    filtered_tx = apply_transaction_config(filtered_tx, config)
    render_transactions_table(filtered_tx)

