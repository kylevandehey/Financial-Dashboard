import pandas as pd

from ui.transactions_table import (
    TransactionsTableConfig,
    apply_multi_filter,
    prepare_transactions_dataframe,
    search_filter,
)


def sample_df():
    return pd.DataFrame(
        {
            "date": pd.to_datetime([
                "2024-03-01",
                "2024-02-15",
                "2024-01-10",
            ]),
            "merchant": ["Coffee Shop", "Grocery Store", "Gym"],
            "category": ["Food", "Groceries", "Health"],
            "account": ["Checking", "Credit", "Checking"],
            "amount": [-5.25, -120.40, 45.00],
            "notes": ["latte", "weekly groceries", "membership"],
        }
    )


def test_search_filter_matches_merchant_and_notes():
    df = sample_df()

    result = search_filter(df, "coffee")
    assert len(result) == 1
    assert result.iloc[0]["merchant"] == "Coffee Shop"

    notes_result = search_filter(df, "weekly")
    assert len(notes_result) == 1
    assert notes_result.iloc[0]["notes"] == "weekly groceries"


def test_multi_filter_handles_empty_selection():
    df = sample_df()
    result = apply_multi_filter(df, "category", [])
    pd.testing.assert_frame_equal(df, result)


def test_category_and_account_filtering_combined():
    df = sample_df()
    filtered = prepare_transactions_dataframe(
        df,
        categories=["Food"],
        accounts=["Checking"],
    )
    assert len(filtered) == 1
    assert filtered.iloc[0]["Merchant"] == "Coffee Shop"


def test_sorting_descending_by_date():
    df = sample_df()
    prepared = prepare_transactions_dataframe(df)
    dates = list(prepared["Date"])
    assert dates == sorted(dates, reverse=True)


def test_amount_formatting_accounting_style():
    df = sample_df()
    prepared = prepare_transactions_dataframe(df)
    assert prepared.iloc[0]["Amount"] == "($5.25)"
    assert prepared.iloc[-1]["Amount"] == "$45.00"


def test_optional_notes_column_hidden():
    df = sample_df()
    config = TransactionsTableConfig(hide_notes=True)
    prepared = prepare_transactions_dataframe(df, config=config)
    assert "Notes" not in prepared.columns

