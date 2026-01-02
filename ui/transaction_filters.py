"""Shared transaction filter controls for the dashboard."""

from __future__ import annotations

import streamlit as st

from src.filters import TransactionFilterConfig, get_transaction_filter_config, set_transaction_filter_config


def _current_config() -> TransactionFilterConfig:
    return get_transaction_filter_config()


def render_transaction_filters() -> None:
    """Render Configure Transactions controls once and persist to session state."""
    config = _current_config()

    st.markdown("#### Configure Transactions")
    with st.container(border=True):
        type_col, include_col, exclude_col = st.columns([1.2, 1.4, 1.4])

        available_types = ["transfer", "payment", "refund", "adjustment"]
        excluded_types = type_col.multiselect(
            "Exclude transaction types",
            options=available_types,
            default=sorted(config.excluded_types),
            key="tx_filter_excluded_types",
        )

        include_keywords = include_col.text_input(
            "Only include keywords",
            value=", ".join(config.include_keywords),
            key="tx_filter_include_keywords",
            placeholder="paycheck, bonus",
        )
        exclude_keywords = exclude_col.text_input(
            "Exclude keywords",
            value=", ".join(config.exclude_keywords),
            key="tx_filter_exclude_keywords",
            placeholder="transfer, move",
        )

    set_transaction_filter_config(
        TransactionFilterConfig.from_keyword_strings(
            excluded_types=excluded_types,
            include_keywords=include_keywords,
            exclude_keywords=exclude_keywords,
        )
    )
