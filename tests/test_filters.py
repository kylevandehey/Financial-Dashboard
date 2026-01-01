import pandas as pd

from src.filters import TransactionFilterConfig, apply_transaction_config


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
