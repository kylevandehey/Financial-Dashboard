import pandas as pd
import streamlit as st

from src.filters import TransactionFilterConfig, apply_transaction_config, get_filtered_transactions, set_transaction_filter_config
from src.filters import filter_transactions_for_scope


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


def test_include_credit_card_payments_toggle_respected():
    df = pd.DataFrame(
        {
            "merchant": ["Card Payment"],
            "notes": [""],
            "category": ["Payment"],
            "transaction_type": ["credit card payment"],
            "amount": [-250],
        }
    )
    config = TransactionFilterConfig.from_keyword_strings(include_credit_card_payments=False)

    filtered = apply_transaction_config(df, config)

    assert filtered.empty


def test_filter_transactions_for_scope_respects_year_and_quarter():
    st.session_state.clear()
    transactions = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-15", "2024-04-10", "2023-02-20"]),
            "year": [2024, 2024, 2023],
            "amount": [100, 200, 300],
            "transaction_type": ["payment", "payment", "payment"],
        }
    )

    q1_all_years = filter_transactions_for_scope(
        transactions,
        year_label="ALL YEARS",
        period_label="Q1",
        date_range=None,
    )
    assert len(q1_all_years) == 2
    assert set(q1_all_years["year"].unique()) == {2023, 2024}

    full_year_2024 = filter_transactions_for_scope(
        transactions,
        year_label="2024",
        period_label="FULL YEAR",
        date_range=None,
    )
    assert len(full_year_2024) == 2
    assert set(full_year_2024["year"].unique()) == {2024}


def test_credit_card_payment_exclusions_are_normalized():
    df = pd.DataFrame(
        {
            "merchant": ["Card Pay"],
            "notes": [""],
            "category": ["Payment"],
            "transaction_type": ["Credit_Card_Payment"],
            "amount": [-250],
        }
    )

    config = TransactionFilterConfig.from_keyword_strings(excluded_types=["Credit Card Payment"])
    filtered = apply_transaction_config(df, config)

    assert filtered.empty


def test_transfer_prefixes_are_excluded():
    df = pd.DataFrame(
        {
            "merchant": ["Transfer Out"],
            "notes": [""],
            "category": ["Transfer"],
            "transaction_type": ["Transfer Out"],
            "amount": [-500],
        }
    )

    config = TransactionFilterConfig.from_keyword_strings(include_transfers=False)
    filtered = apply_transaction_config(df, config)

    assert filtered.empty
