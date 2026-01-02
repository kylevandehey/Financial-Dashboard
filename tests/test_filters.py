import pandas as pd
import streamlit as st

from src.filters import TransactionFilterConfig, apply_transaction_config, get_filtered_transactions, set_transaction_filter_config


def sample_tx():
    return pd.DataFrame(
        {
            "merchant": ["Transfer to savings", "Coffee Shop", "Refund Store"],
            "notes": ["move money", "latte", "returned item"],
            "category": ["Transfer", "Food", "Shopping"],
            "transaction_type": ["transfer", "payment", "refund"],
            "amount": [-100, -5, 20],
        }
    )


def test_exclude_transaction_types_filters_rows():
    df = sample_tx()
    config = TransactionFilterConfig.from_keyword_strings(excluded_types=["transfer"])
    filtered = apply_transaction_config(df, config)
    assert len(filtered) == 2
    assert "transfer" not in filtered["transaction_type"].str.lower().values


def test_keyword_include_and_exclude_stack():
    df = sample_tx()
    config = TransactionFilterConfig.from_keyword_strings(include_keywords=["shop"], exclude_keywords=["latte"])
    filtered = apply_transaction_config(df, config)
    assert len(filtered) == 1
    assert filtered.iloc[0]["merchant"] == "Refund Store"


def test_get_filtered_transactions_reads_session_state():
    st.session_state.clear()
    set_transaction_filter_config(TransactionFilterConfig.from_keyword_strings(excluded_types=["transfer"]))
    df = sample_tx()

    filtered = get_filtered_transactions(df)

    assert len(filtered) == 2
    assert "transfer" not in filtered["transaction_type"].str.lower().values


def test_include_transfers_toggle_respected():
    df = sample_tx()
    config = TransactionFilterConfig.from_keyword_strings(include_transfers=False)

    filtered = apply_transaction_config(df, config)

    assert "transfer" not in filtered["transaction_type"].str.lower().values
    assert len(filtered) == 2


def test_include_refunds_toggle_respected():
    df = sample_tx()
    config = TransactionFilterConfig.from_keyword_strings(include_refunds=False)

    filtered = apply_transaction_config(df, config)

    assert "refund" not in filtered["transaction_type"].str.lower().values
    assert len(filtered) == 2
