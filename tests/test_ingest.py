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


def test_normalize_accounts_maps_and_signs(tmp_path):
    sample = tmp_path / "accounts.csv"
    sample.write_text(
        "Date,Account,Type,Balance\n"
        "2024-01-15,Checking,Asset,1500\n"
        "2024-01-15,Credit Card,Liability,2500\n"
    )

    from src.ingest import normalize_accounts

    df = normalize_accounts(sample)
    assert list(df.columns) == [
        "date",
        "account",
        "type",
        "subtype",
        "balance",
        "signed_balance",
        "is_asset",
        "is_liability",
        "institution",
    ]
    assert df.loc[df["account"] == "Checking", "signed_balance"].iloc[0] == 1500
    assert df.loc[df["account"] == "Credit Card", "signed_balance"].iloc[0] == -2500


def test_income_flags_exclude_transfers_and_adjustments():
    csv_content = """Date,Amount,Merchant,Category,Account,Transaction Type,Notes
2024-03-01,1500,Employer,Salary,Checking,Deposit,Paycheck
2024-03-02,200,Transfer In,Transfer,Checking,Transfer,Internal move
2024-03-03,-250,Payment,Transfer,Checking,Transfer,Card payment
2024-03-04,-120,Grocery Store,Groceries,Checking,Debit,Weekly shop
"""
    df = normalize_transactions(io.StringIO(csv_content))

    assert bool(df.loc[df["merchant"] == "Employer", "is_income"].iloc[0]) is True
    assert bool(df.loc[df["merchant"] == "Transfer In", "is_income"].iloc[0]) is False
    assert bool(df.loc[df["merchant"] == "Payment", "is_expense"].iloc[0]) is False
    assert bool(df.loc[df["merchant"] == "Grocery Store", "is_expense"].iloc[0]) is True
