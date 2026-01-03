"""Shared transaction filter controls for the dashboard."""

from __future__ import annotations

import streamlit as st
from streamlit.delta_generator import DeltaGenerator

from src.filters import TransactionFilterConfig, get_transaction_filter_config, set_transaction_filter_config


def _current_config() -> TransactionFilterConfig:
    return get_transaction_filter_config()


def render_transaction_filters(target: DeltaGenerator | None = None) -> None:
    """Render Configure Transactions controls once and persist to session state."""
    host = target or st
    config = _current_config()
    key_prefix = "dashboard_configure"

    host.markdown("#### Configure Transactions")
    with host.container(border=True):
        available_types = ["transfer", "payment", "credit card payment", "refund", "adjustment"]
        excluded_types = host.multiselect(
            "Exclude transaction types",
            options=available_types,
            default=sorted(config.excluded_types, key=str.lower),
            key=f"{key_prefix}_excluded_types",
        )

        include_keywords = host.text_input(
            "Only include keywords",
            value=", ".join(config.include_keywords),
            key=f"{key_prefix}_include_keywords",
            placeholder="paycheck, bonus",
        )
        exclude_keywords = host.text_input(
            "Exclude keywords",
            value=", ".join(config.exclude_keywords),
            key=f"{key_prefix}_exclude_keywords",
            placeholder="transfer, move",
        )

        include_transfers = host.checkbox(
            "Include transfers",
            value=config.include_transfers,
            key=f"{key_prefix}_include_transfers",
            help="Uncheck to exclude transfers from income, expenses, and net cash flow metrics.",
        )
        include_refunds = host.checkbox(
            "Include refunds",
            value=config.include_refunds,
            key=f"{key_prefix}_include_refunds",
            help="Uncheck to treat refunds as non-income adjustments in all charts and tables.",
        )
        include_credit_card_payments = host.checkbox(
            "Include credit card payments",
            value=config.include_credit_card_payments,
            key=f"{key_prefix}_include_credit_card_payments",
            help="Uncheck to remove card payments from income/expense math so net cash flow is not distorted.",
        )

    set_transaction_filter_config(
        TransactionFilterConfig.from_keyword_strings(
            excluded_types=excluded_types,
            include_keywords=include_keywords,
            exclude_keywords=exclude_keywords,
            include_transfers=include_transfers,
            include_refunds=include_refunds,
            include_credit_card_payments=include_credit_card_payments,
        )
    )
