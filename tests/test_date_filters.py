from datetime import date

import pandas as pd
import pytest

from src.date_filters import compute_date_range, compute_month_range, filter_dataframe_by_date, filter_dataframe_by_date_and_month


def test_full_year_without_year_uses_anchor_year():
    start, end = compute_date_range("full_year", today=date(2024, 8, 15))
    assert start == date(2024, 1, 1)
    assert end == date(2024, 12, 31)


def test_quarter_range_honors_year_context():
    start, end = compute_date_range("q2", year=2025, today=date(2024, 5, 10))
    assert start == date(2025, 4, 1)
    assert end == date(2025, 6, 30)


def test_full_year_preset():
    start, end = compute_date_range("full_year", year=2024)
    assert start == date(2024, 1, 1)
    assert end == date(2024, 12, 31)


def test_custom_range_overrides_presets():
    custom_start = date(2023, 5, 1)
    custom_end = date(2023, 7, 15)
    start, end = compute_date_range(
        "full_year", year=2024, custom_start=custom_start, custom_end=custom_end, today=date(2024, 8, 15)
    )
    assert start == custom_start
    assert end == custom_end


def test_invalid_custom_range_raises_error():
    with pytest.raises(ValueError):
        compute_date_range("full_year", custom_start=date(2024, 2, 10), custom_end=date(2024, 2, 1))


def test_dataframe_filtering_respects_date_range_and_preserves_original():
    df = pd.DataFrame(
        {
            "Date": pd.to_datetime(
                [
                    "2024-01-15",
                    "2024-02-20",
                    "2024-03-10",
                    "2025-01-01",
                ]
            ),
            "Amount": [100, -50, 200, 300],
        }
    )
    filtered = filter_dataframe_by_date(df, (date(2024, 2, 1), date(2024, 3, 31)))

    assert len(filtered) == 2
    assert filtered["Amount"].tolist() == [-50, 200]
    assert len(df) == 4  # Original frame unmodified


def test_filtering_missing_date_column_raises():
    df = pd.DataFrame({"Amount": [1, 2, 3]})
    with pytest.raises(ValueError):
        filter_dataframe_by_date(df, (date(2024, 1, 1), date(2024, 12, 31)), date_column="Date")


def test_compute_month_range_returns_full_month():
    start, end = compute_month_range(2024, 2)
    assert start == date(2024, 2, 1)
    assert end == date(2024, 2, 29)


def test_filter_dataframe_by_date_and_month_across_years():
    df = pd.DataFrame(
        {
            "date": pd.to_datetime(["2023-01-15", "2024-01-20", "2024-03-05", "2025-01-10"]),
            "amount": [100, 200, 300, 400],
        }
    )
    filtered = filter_dataframe_by_date_and_month(
        df,
        (date(2023, 1, 1), date(2025, 12, 31)),
        months=[1],
        date_column="date",
    )
    assert len(filtered) == 3
    assert filtered["amount"].tolist() == [100, 200, 400]


def test_filter_dataframe_by_date_and_month_rejects_invalid_month():
    df = pd.DataFrame({"date": pd.to_datetime(["2024-01-01"]), "amount": [1]})
    with pytest.raises(ValueError):
        filter_dataframe_by_date_and_month(df, (date(2024, 1, 1), date(2024, 12, 31)), months=[0], date_column="date")
