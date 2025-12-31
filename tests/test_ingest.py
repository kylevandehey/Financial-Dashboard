import io
from datetime import date

import pandas as pd
import pytest

from src.ingest import CANONICAL_COLUMNS, normalize_transactions


def test_normalize_transactions_happy_path():
    csv_content = """Transaction Date,Amount,Merchant,Category,Account,Notes
2024-12-31,"$1,000.50",Acme Corp,Salary,Checking,Year-end bonus
2025-01-15,"($250.75)",Grocery Store,Groceries,Checking,Weekly shop
"""
    df = normalize_transactions(io.StringIO(csv_content), today=date(2025, 2, 1))

    expected_columns = [col for col in CANONICAL_COLUMNS if col in df.columns]
    assert list(df.columns) == expected_columns

    assert df.loc[0, "amount"] == 1000.50
    assert df.loc[1, "amount"] == -250.75
    assert bool(df.loc[0, "is_income"]) is True
    assert bool(df.loc[1, "is_expense"]) is True

    assert df.loc[0, "year"] == 2024
    assert df.loc[1, "year_month"] == "2025-01"
    assert df.loc[1, "quarter"] == "Q1"
    assert bool(df.loc[1, "is_ytd"]) is True  # 2025-01-15 with today=2025-02-01
    assert bool(df.loc[0, "is_ytd"]) is False  # 2024 data excluded from 2025 YTD


def test_normalize_transactions_missing_required_column():
    csv_content = """Transaction Date,Merchant,Category,Account,Notes
2024-01-01,Acme Corp,Salary,Checking,Missing amount column
"""
    with pytest.raises(ValueError) as excinfo:
        normalize_transactions(io.StringIO(csv_content))

    assert "Add the following fields to your Monarch export: amount" in str(excinfo.value)


def test_smoke_imports():
    # Lightweight smoke test to ensure module imports and callable exists
    assert callable(normalize_transactions)
    assert isinstance(CANONICAL_COLUMNS, tuple) or isinstance(CANONICAL_COLUMNS, list)
