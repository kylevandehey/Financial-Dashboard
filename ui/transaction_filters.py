"""Shared transaction filter controls for the dashboard."""

from __future__ import annotations

import streamlit as st

from src.filters import TransactionFilterConfig, get_transaction_filter_config, set_transaction_filter_config


def _current_config() -> TransactionFilterConfig:
    return get_transaction_filter_config()


def render_transaction_filters() -> None:
    """Render Configure Transactions controls once and persist to session state."""
    config = _current_config()
    key_prefix = "dashboard_configure"

    st.markdown("#### Configure Transactions")
    with st.container(border=True):
        type_col, include_col, exclude_col = st.columns([1.2, 1.4, 1.4])

        available_types = ["transfer", "payment", "refund", "adjustment"]
        excluded_types = type_col.multiselect(
            "Exclude transaction types",
            options=available_types,
            default=sorted(config.excluded_types),
            key=f"{key_prefix}_excluded_types",
        )

        include_keywords = include_col.text_input(
            "Only include keywords",
            value=", ".join(config.include_keywords),
            key=f"{key_prefix}_include_keywords",
            placeholder="paycheck, bonus",
        )
        exclude_keywords = exclude_col.text_input(
            "Exclude keywords",
            value=", ".join(config.exclude_keywords),
            key=f"{key_prefix}_exclude_keywords",
            placeholder="transfer, move",
        )

        toggle_col1, toggle_col2 = st.columns(2)
        include_transfers = toggle_col1.checkbox(
            "Include transfers",
            value=config.include_transfers,
            key=f"{key_prefix}_include_transfers",
        )
        include_refunds = toggle_col2.checkbox(
            "Include refunds",
            value=config.include_refunds,
            key=f"{key_prefix}_include_refunds",
        )

    set_transaction_filter_config(
        TransactionFilterConfig.from_keyword_strings(
            excluded_types=excluded_types,
            include_keywords=include_keywords,
            exclude_keywords=exclude_keywords,
            include_transfers=include_transfers,
            include_refunds=include_refunds,
        )
    )
